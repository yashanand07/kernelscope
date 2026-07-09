from adaptation.linux import kit
from semantic_runtime.printer.report_printer import ReportPrinter
from semantic_runtime.compiler.result import ExtractorTelemetry
from semantic_runtime.compiler.result import CompilationResult
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

# Adaptation imports
from adaptation.linux.kit import LinuxAdaptationKit
from adaptation.linux.synchronisation import get_linux_sync_profile

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
        # self.extractor_stats = {
        #     "LocalSymbolExtractor": {"discovered": 0, "duration_ms": 0.0, "warnings": 0},
        #     "IteratorExtractor": {"discovered": 0, "duration_ms": 0.0, "warnings": 0},
        #     "CallExtractor": {"discovered": 0, "duration_ms": 0.0, "warnings": 0},
        #     "SynchronizationExtractor": {"discovered": 0, "duration_ms": 0.0, "warnings": 0}
        # }
        os.makedirs(self.cache_dir, exist_ok=True)

    def log(self, level: int, message: str):
        """Enforces clean logging visibility thresholds without inline DEBUG pollution."""
        if self.verbosity >= level:
            print(message)

    def run_pipeline(self, chunks_jsonl_path: str, symbol_db: dict):
        result = CompilationResult()
        
        # Start Phase 0
        p0_start = time.perf_counter()
        compiler_index_builder = CompilerIndexBuilder(symbol_db)
        functions_to_compile = []
        
        # Ingest lines
        with open(chunks_jsonl_path, 'r') as f:
            for line in f:
                if not line.strip(): continue
                chunk = json.loads(line)
                result.chunks_scanned += 1
                
                # Resilient schema lookup (checks content, then source, then code)
                code_text = chunk.get("content") or chunk.get("source") or chunk.get("code") or ""
                
                p0_ext_start = time.perf_counter()
                compiler_index_builder.process_chunk(chunk["file"], code_text)
                p0_duration = (time.perf_counter() - p0_ext_start) * 1000.0
                
                # Catch either the mock's 'symbol_id' or the production 'symbol' key
                if "symbol_id" in chunk or "symbol" in chunk:
                    # Normalize production chunks to match our internal strict formatting
                    if "symbol_id" not in chunk:
                        chunk["symbol_id"] = f"func:{chunk['file']}:{chunk['symbol']}"
                        
                    functions_to_compile.append(chunk)

        self.indices = compiler_index_builder.indices
        result.collections_discovered = len(self.indices.collections)
        result.phase_0_time_s = time.perf_counter() - p0_start
        
        # Record Phase 0 telemetry metrics
        result.extractor_metrics["CollectionIndexBuilder"] = ExtractorTelemetry(
            discovered=result.collections_discovered,
            duration_ms=result.phase_0_time_s * 1000.0
        )
        kit = LinuxAdaptationKit()
        # Start Phase 1 Function Processing
        p1_start = time.perf_counter()
        semantic_compiler = SemanticCompiler(self.indices, kit)
        
        for func in functions_to_compile:
            code_text = func.get("code") or func.get("content") or func.get("source") or ""
            start_line = func.get("start_line", 1)
            end_line = func.get("end_line", 1)
            
            context = semantic_compiler.compile_function(
                symbol_id=func["symbol_id"],
                file_path=func["file"],
                code=code_text,
                start_line=start_line,
                end_line=end_line
            )
            context.finalize()
            
            # Aggregate structural metric logs out of the stateless execution frame
            for report in getattr(context, '_reports_cached', []):
                if report.extractor_name not in result.extractor_metrics:
                    result.extractor_metrics[report.extractor_name] = ExtractorTelemetry()
                
                telemetry = result.extractor_metrics[report.extractor_name]
                telemetry.discovered += report.discovered
                telemetry.duration_ms += report.duration_ms
                if report.warnings:
                    telemetry.warnings_count += len(report.warnings)
                    telemetry.warnings_list.extend(report.warnings)
                    
            result.functions_compiled += 1
            result.total_symbols += sum(len(v) for v in context.local_symbols.values())
            result.total_semantic_objects += len(context.semantic_constructs)
            self.semantic_contexts[func["symbol_id"]] = context
            
        result.phase_1_time_s = time.perf_counter() - p1_start
        result.total_time_s = result.phase_0_time_s + result.phase_1_time_s
        result.capture_memory_profile()
        
        # Save indices and display the dashboard
        self._persist_global_indices()
        ReportPrinter.print_instrumentation_dashboard(result)

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
    
    def _persist_global_indices(self):
        """Serializes the Phase 0 index registry cache cleanly to disk."""
        if self.indices:
            index_path = os.path.join(self.cache_dir, "global_compiler_indices.pkl")
            with open(index_path, 'wb') as f:
                pickle.dump(self.indices, f)
                
    def _load_cached_indices(self) -> bool:
        """Attempts to pre-load a compiled Phase 0 global cache map."""
        index_path = os.path.join(self.cache_dir, "global_compiler_indices.pkl")
        if os.path.exists(index_path):
            with open(index_path, 'rb') as f:
                self.indices = pickle.load(f)
            return True
        return False
