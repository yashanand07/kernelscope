from dataclasses import dataclass
import os
import json
import time
import pickle
from typing import Dict, List, Any, Optional

# Core infrastructure imports
from semantic_runtime.compiler.indices import CompilerIndexBuilder, CompilerIndices
from semantic_runtime.compiler.semantic_ir import SemanticCompiler
from semantic_runtime.semantic_model import FunctionSemanticContext

# Clean specialized printing imports
from semantic_runtime.printer.ir_printer import SemanticIRPrinter
from semantic_runtime.printer.collection_printer import CollectionIndexPrinter
from semantic_runtime.printer.symbol_printer import SymbolPrinter

# Mocking a lightweight structure for Function/Chunk iteration if not already present
@dataclass
class MockFunction:
    symbol_id: str
    file: str
    source: str

class KernelScopeRunner:
    def __init__(self, cache_dir: str = "semantic_context_cache", verbosity: int = 1):
        self.cache_dir = cache_dir
        self.verbosity = verbosity # Configurable Verbosity: 0, 1, 2, 3
        self.semantic_contexts: Dict[str, FunctionSemanticContext] = {}
        self.indices: Optional[CompilerIndices] = None

        self.total_compilation_time = 0.0
        self.extractor_stats = {
            "LocalSymbolExtractor": {"discovered": 0, "duration_ms": 0.0, "warnings": 0},
            "IteratorExtractor": {"discovered": 0, "duration_ms": 0.0, "warnings": 0}
        }
        os.makedirs(self.cache_dir, exist_ok=True)

    def log(self, level: int, message: str):
        """Enforces clean logging visibility thresholds without inline DEBUG pollution."""
        if self.verbosity >= level:
            print(message)

    def run_pipeline(self, chunks_jsonl_path: str, symbol_db: dict):
        global_start = time.perf_counter()

        # =========================================================
        # PHASE 0: Global Index Construction
        # =========================================================
        self.log(1, "\nKernelScope 2.0 Semantic Compiler")
        self.log(1, "Version -")
        self.log(1, "\t\tKernelScope 2.0 BootStrap")
        self.log(1, "-----------------------------------------")
        self.log(1, "Executing Phase 0: Building Global Indices...")

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

        # =========================================================
        # PHASE 1: Function Semantic Compilation
        # =========================================================
        self.log(1, "Executing Phase 1: Compiling Function Semantics...")

        semantic_compiler = SemanticCompiler(self.indices)

        for func in functions_to_compile:
            context = semantic_compiler.compile_function(
                symbol_id=func.symbol_id,
                file_path=func.file,
                code=func.source
            )
            context.finalize()
            self.semantic_contexts[func.symbol_id] = context
            self._persist_context(context)

            # Dynamic extraction report parsing hooks
            for report in getattr(context, '_reports_cached', []):
                if report.extractor_name in self.extractor_stats:
                    self.extractor_stats[report.extractor_name]["discovered"] += report.discovered
                    self.extractor_stats[report.extractor_name]["duration_ms"] += report.duration_ms
                    self.extractor_stats[report.extractor_name]["warnings"] += len(report.warnings)

        self.total_compilation_time = time.perf_counter() - global_start

        # Verbosity Level 1 summary printout
        if self.verbosity >= 1:
            self._print_compiler_summary(len(functions_to_compile))

        # Verbosity Level 3 triggers instant raw output generation of full IR blocks
        if self.verbosity >= 3:
            for ctx in self.semantic_contexts.values():
                SemanticIRPrinter.print_function_ir(ctx, self.indices)

    def _persist_context(self, context: FunctionSemanticContext):
        safe_filename = context.symbol_id.replace(":", "_").replace("/", "_") + ".pkl"
        with open(os.path.join(self.cache_dir, safe_filename), 'wb') as f:
            pickle.dump(context, f)

    def _print_compiler_summary(self, num_functions: int):
        print("\n========================================")
        print("          COMPILER SUMMARY REPORT        ")
        print("========================================")
        print(f"Functions compiled     : {num_functions}")
        print(f"Collections discovered : {len(self.indices.collections)}")
        print(f"Total Local Symbols    : {self.extractor_stats['LocalSymbolExtractor']['discovered']}")
        print(f"Total Compilation time : {self.total_compilation_time:.3f} sec")
        print("========================================")

    def interactive_shell(self):
        """Shell interface mapping directly to the new printer components."""
        while True:
            print("\nKernelScope Debugger Shell")
            print("1 - Adjust Compiler Verbosity (Current: {})".format(self.verbosity))
            print("2 - Dump Semantic Context (SemanticIRPrinter)")
            print("3 - Dump Collection Index (CollectionIndexPrinter)")
            print("4 - Dump Local Symbol Details (SymbolPrinter)")
            print("5 - Exit")

            choice = input("\nSelect an option: ").strip()

            if choice == "1":
                val = input("Enter verbosity level (0-3): ").strip()
                if val in {"0", "1", "2", "3"}:
                    self.verbosity = int(val)
                    print(f"Verbosity shifted to Level {self.verbosity}")
            elif choice == "2":
                while True:
                    sym_id = input("Enter symbol_id (or Enter for list, 'q' to go back): ").strip()
                    if sym_id.lower() == 'q':
                        break

                    if not sym_id:
                        print("\nAvailable Compiled Functions:")
                        for k in self.semantic_contexts.keys():
                            print(f"  {k}")
                        print("") # Padding
                        continue # Keep them inside the prompt!

                    context = self.semantic_contexts.get(sym_id)
                    if context:
                        SemanticIRPrinter.print_function_ir(context, self.indices)
                        break # Break the sticky prompt after a successful print
                    else:
                        print(f"Symbol '{sym_id}' not found. Please try again or type 'q' to exit.")
            elif choice == "3":
                CollectionIndexPrinter.print_index(self.indices.collections)
            elif choice == "4":
                sym_id = input("Enter symbol_id: ").strip()
                context = self.semantic_contexts.get(sym_id)
                if not context:
                    print("Symbol context record missing.")
                    continue

                print("\nAvailable Symbols")
                print("─────────────────")
                symbol_names = list(context.local_symbols.keys())
                for idx, name in enumerate(symbol_names, 1):
                    print(f"{idx}. {name}")

                var_input = input("\nEnter variable name or number to audit: ").strip()
                if not var_input:
                    continue

                # Handle Numeric Index Input Selection
                if var_input.isdigit():
                    selected_idx = int(var_input) - 1
                    if 0 <= selected_idx < len(symbol_names):
                        var_name = symbol_names[selected_idx]
                    else:
                        print("Invalid selection number.")
                        continue
                else:
                    var_name = var_input

                symbols = context.local_symbols.get(var_name)
                if symbols:
                    for s in symbols:
                        SymbolPrinter.print_detailed_symbol(var_name, s, context)
                else:
                    print(f"Variable '{var_name}' not found inside context scope.")
            elif choice == "5":
                break

# Local runner scaffolding for validation
if __name__ == "__main__":
    import tempfile
    current_dir = os.path.dirname(os.path.abspath(__file__))

    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".jsonl") as tmp:
        tmp.write(json.dumps({"file": "kernel/sched/core.c", "content": "LIST_HEAD(clkdm_list);"}) + "\n")
        func_src = (
            "void schedule(struct device *dev, int cpu) {\n"
            "    struct clockdomain *temp_clkdm;\n"
            "    int cpu;\n"
            "    list_for_each_entry_safe(temp_clkdm, n, &clkdm_list, node) {}\n"
            "}"
        )
        tmp.write(json.dumps({
            "symbol_id": "func:kernel/sched/core.c:schedule",
            "file": "kernel/sched/core.c",
            "content": func_src
        }) + "\n")
        tmp_name = tmp.name

    try:
        # Initializing default execution shell tracking at Verbosity Level 1
        runner = KernelScopeRunner(cache_dir=os.path.join(current_dir, "semantic_context_cache"), verbosity=1)
        runner.run_pipeline(tmp_name, {"clkdm_list": [None]})
        runner.interactive_shell()
    finally:
        os.unlink(tmp_name)