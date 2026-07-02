from typing import Optional
import os
import json
import time
import pickle
from typing import Dict, List, Any
from dataclasses import dataclass

# Core compiler imports
from semantic_runtime.compiler.indices import CompilerIndexBuilder, CompilerIndices
from semantic_runtime.compiler.semantic_ir import SemanticCompiler
from semantic_runtime.semantic_model import FunctionSemanticContext

# Mocking a lightweight structure for Function/Chunk iteration if not already present
@dataclass
class MockFunction:
    symbol_id: str
    file: str
    source: str

class KernelScopeRunner:
    def __init__(self, cache_dir: str = "semantic_context_cache"):
        self.cache_dir = cache_dir
        self.semantic_contexts: Dict[str, FunctionSemanticContext] = {}
        self.indices: Optional[CompilerIndices] = None

        # Telemetry Aggregators
        self.total_compilation_time = 0.0
        self.phase0_time = 0.0
        self.phase1_time = 0.0
        self.extractor_stats = {
            "LocalSymbolExtractor": {"discovered": 0, "duration_ms": 0.0, "warnings": 0},
            "IteratorExtractor": {"discovered": 0, "duration_ms": 0.0, "warnings": 0}
        }

        os.makedirs(self.cache_dir, exist_ok=True)

    def run_pipeline(self, chunks_jsonl_path: str, symbol_db: dict):
        """Executes the complete Phase 0 and Phase 1 Compilation Pipeline."""
        print("\nKernelScope 2.0 Semantic Compiler")
        print("Version -")
        print("\t\tKernelScope 2.0 BootStrap")
        print("-----------------------------------------")

        global_start = time.perf_counter()

        # =========================================================
        # PHASE 0: Global Index Construction
        # =========================================================
        print("Executing Phase 0: Building Global Indices...")
        p0_start = time.perf_counter()

        compiler_index_builder = CompilerIndexBuilder(symbol_db)

        functions_to_compile: List[MockFunction] = []

        with open(chunks_jsonl_path, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                chunk = json.loads(line)

                # Phase 0 Processes chunks directly
                compiler_index_builder.process_chunk(chunk["file"], chunk["content"])

                # If this chunk represents a function definition, harvest it for Phase 1
                # Adjust key names based on your real chunks.jsonl structure
                if "symbol_id" in chunk:
                    functions_to_compile.append(MockFunction(
                        symbol_id=chunk["symbol_id"],
                        file=chunk["file"],
                        source=chunk["content"]
                    ))

        self.indices = compiler_index_builder.indices
        self.phase0_time = (time.perf_counter() - p0_start)

        # =========================================================
        # PHASE 1: Function Semantic Compilation
        # =========================================================
        print("Executing Phase 1: Compiling Function Semantics...")
        p1_start = time.perf_counter()

        semantic_compiler = SemanticCompiler(self.indices)

        for func in functions_to_compile:
            context = semantic_compiler.compile_function(
                symbol_id=func.symbol_id,
                file_path=func.file,
                code=func.source
            )

            # Post-processing sorting / freezing
            context.finalize()

            # Save to in-memory index
            self.semantic_contexts[func.symbol_id] = context

            # Persist directly to disk cache
            self._persist_context(context)

            # Aggregate Telemetry from the pipeline execution
            # Access timing data dynamically recorded inside SemanticCompiler.compile_function
            # Since reports are passed back internally or printed, we track totals here via context inspection:
            for report in getattr(context, '_reports_cached', []): # fallback safety hook
                if report.extractor_name in self.extractor_stats:
                    self.extractor_stats[report.extractor_name]["discovered"] += report.discovered
                    self.extractor_stats[report.extractor_name]["duration_ms"] += report.duration_ms
                    self.extractor_stats[report.extractor_name]["warnings"] += len(report.warnings)

        self.phase1_time = (time.perf_counter() - p1_start)
        self.total_compilation_time = time.perf_counter() - global_start

        # Print final instrumented reports
        self._print_compiler_report(len(functions_to_compile))

    def _persist_context(self, context: FunctionSemanticContext):
        """Serializes and writes the context object securely to disk."""
        # Sanitize symbol ID to prevent directory traversal issues in filenames
        safe_filename = context.symbol_id.replace(":", "_").replace("/", "_") + ".pkl"
        target_path = os.path.join(self.cache_dir, safe_filename)
        with open(target_path, 'wb') as f:
            pickle.dump(context, f)

    def _print_compiler_report(self, num_functions: int):
        """Outputs precise compiler profiling telemetry."""
        print("\n========================================")
        print("          COMPILER IR REPORT            ")
        print("========================================")

        for extractor, stats in self.extractor_stats.items():
            print(f"\n{extractor}")
            print("-" * 40)
            print(f"Functions  : {num_functions}")
            if extractor == "LocalSymbolExtractor":
                print(f"Symbols    : {stats['discovered']}")
            elif extractor == "IteratorExtractor":
                print(f"Iterations : {stats['discovered']}")
            print(f"Warnings   : {stats['warnings']}")
            print(f"Time       : {stats['duration_ms'] / 1000.0:.3f} sec")

        print("\n-----------------------------------------")
        print(f"Functions compiled     : {num_functions}")
        print(f"Collections discovered : {len(self.indices.collections)}")
        print(f"Total Compilation time : {self.total_compilation_time:.2f} sec")
        print("-----------------------------------------")

    def interactive_shell(self):
        """Clean command line debugger interface for verifying compiled IR."""
        while True:
            print("\nKernelScope Semantic IR Inspector")
            print("1 - Explain Linux Scheduler (Disabled in IR-only mode)")
            print("2 - Dump Semantic Context")
            print("3 - Dump Collection Index")
            print("4 - Exit")

            choice = input("\nSelect an option: ").strip()

            if choice == "1":
                print("\n[Notice] LLM Explanations are currently disabled. Pipeline is strictly Compiler -> IR.")
            elif choice == "2":
                sym_id = input("Enter symbol_id (or press enter for list): ").strip()
                if not sym_id:
                    print("\nAvailable Compiled Functions:")
                    for k in self.semantic_contexts.keys():
                        print(f"  {k}")
                    continue

                context = self.semantic_contexts.get(sym_id)
                if not context:
                    print(f"Error: Symbol '{sym_id}' not found in compiled context memory.")
                    continue

                print(f"\n{context.symbol_id}()")
                print(f"Source file: {context.file_path}")
                print("\nLocal Symbols")
                print("────────────────────────────────────────")
                for name, symbols in context.local_symbols.items():
                    for idx, sym in enumerate(symbols):
                        shadow_suffix = f" [Shadow Entry {idx}]" if idx > 0 else ""
                        print(f"  {name:<15} ──> {sym.type_info.kind.value} {sym.type_info.type_name}{'*' * sym.type_info.pointer_level:<12} ({sym.storage.value}) @ Line {sym.declaration_line}{shadow_suffix}")

                print("\nSemantic Constructs")
                print("────────────────────────────────────────")
                for m in context.semantic_constructs:
                    if m.__class__.__name__ == "IterationMetadata":
                        print("  Iteration")
                        print(f"    Line              : {m.source_line}")
                        print(f"    Macro             : {m.macro}")
                        print(f"    Collection        : {m.collection_expression}")
                        print(f"    Collection Family : {m.collection_family.value if hasattr(m.collection_family, 'value') else m.collection_family}")
                        print(f"    Cursor            : {m.cursor_variable}")
                        print(f"    Member            : {m.member_field or 'N/A'}")

                        # --- Global Collection Lineage Visualizer ---
                        print("    Collection Lineage:")
                        # Look up the collection descriptor from Phase 0 to pull extended origin metrics
                        desc = self.indices.collections.lookup(m.collection_expression)
                        if desc:
                            print(f"        {m.collection_expression}")
                            print("        │")
                            print(f"        ▼\n        {desc.collection_family.value}")
                            print("        │")
                            print(f"        ▼\n        {desc.declaration_macro}")
                            print("        │")
                            print(f"        ▼\n        {desc.declaration_file}")
                        else:
                            print(f"        {m.collection_expression} (Local / Unindexed Expression)")
                        print("") # Padding between constructs
            elif choice == "3":
                print("\nGlobal Collection Index (Phase 0 Cache)")
                print("-------------")
                if len(self.indices.collections) == 0:
                    print("  [Index Empty]")
                for item in self.indices.collections:
                    print(f"  Name: {item.name:<20} | Family: {item.collection_family.value:<12} | Macro: {item.declaration_macro:<18} | File: {item.declaration_file}")
            elif choice == "4":
                print("Exiting KernelScope Compiler Interface.")
                break
            else:
                print("Invalid option selection.")

# Execution entrypoint
if __name__ == "__main__":
    import tempfile

    # Establish base directory context dynamically
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir) # linux-kernel-flow-explorer/

    # Create mock chunks.jsonl
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".jsonl") as tmp:
        # 1. Global list setup
        tmp.write(json.dumps({"file": "kernel/sched/core.c", "content": "LIST_HEAD(clkdm_list);"}) + "\n")
        # 2. Function chunk containing local variables and an entry iterator loop
        func_src = (
            "void schedule(struct device *dev, int cpu) {\n"
            "    struct clockdomain *temp_clkdm;\n"
            "    int cpu;\n" # Shadowed variable
            "    list_for_each_entry_safe(temp_clkdm, n, &clkdm_list, node) {\n"
            "        // context loop logic\n"
            "    }\n"
            "}"
        )
        tmp.write(json.dumps({
            "symbol_id": "func:kernel/sched/core.c:schedule",
            "file": "kernel/sched/core.c",
            "content": func_src
        }) + "\n")
        tmp_name = tmp.name

    try:
        # Construct cache directory relative to your actual execution environment
        cache_path = os.path.join(current_dir, "semantic_context_cache")
        runner = KernelScopeRunner(cache_dir=cache_path)

        # Empty mock symbol database for Phase 0 resolution checks
        mock_symbol_db = {"clkdm_list": [None]}
        runner.run_pipeline(tmp_name, mock_symbol_db)
        runner.interactive_shell()
    finally:
        os.unlink(tmp_name)