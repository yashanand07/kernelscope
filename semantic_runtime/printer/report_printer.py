import time
from semantic_runtime.compiler.result import CompilationResult

class ReportPrinter:
    """Consolidated system execution telemetry and analytics formatter."""
    
    @staticmethod
    def print_summary(result: CompilationResult):
        print("\n" + "=" * 40)
        print("          COMPILER SUMMARY REPORT        ")
        print("=" * 40)
        print(f"Functions compiled     : {result.functions_compiled}")
        print(f"Collections discovered : {result.collections_discovered}")
        print(f"Total Local Symbols    : {result.total_symbols}")
        print(f"Warnings / Skips       : {result.total_warnings}")
        print(f"Total Compilation time : {result.duration_seconds:.3f} sec")
        print("=" * 40)