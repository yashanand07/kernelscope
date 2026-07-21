from semantic_runtime.compiler.result import PipelineExecutionReport

class ReportPrinter:
    """Consolidated master dashboard formatter for execution diagnostics."""

    @staticmethod
    def print_instrumentation_dashboard(res: PipelineExecutionReport):
        # Calculate dynamic fallbacks if field was left at 0
        functions_count = res.functions_compiled
        if functions_count == 0:
            functions_count = len(res.contexts) or res.extractor_metrics.get("function", {}).get("discovered", 0)

        semantic_objects_count = res.total_semantic_objects
        if semantic_objects_count == 0:
            semantic_objects_count = sum(m.discovered for m in res.extractor_metrics.values())

        print("Phase 1")
        print("-" * 50)
        print("Functions")
        print(f"    Total                   : {functions_count:,}")
        print("Semantic Objects")
        print(f"    Total                   : {semantic_objects_count:,}")
        print("\nKernelScope 2.0 Semantic Compiler")
        print("==================================================")

        print("Phase 0")
        print(f"    Chunks scanned          : {res.chunks_scanned:,}")
        telemetry_p0 = res.extractor_metrics.get("CollectionIndexBuilder")
        col_count = telemetry_p0.discovered if telemetry_p0 else res.collections_discovered
        print(f"    Collections indexed     : {col_count:,}")
        print(f"    Time                    : {res.phase_0_time_s:.2f} sec")
        print("--------------------------------------------------")

        print("Phase 1")
        for ext_name, metrics in res.extractor_metrics.items():
            if ext_name == "CollectionIndexBuilder":
                continue
            metric_label = "Symbols" if "Symbol" in ext_name else ("Iterations" if "Iterator" in ext_name else "Calls")
            print(f"{ext_name}")
            print(f"    {metric_label:<24}: {metrics.discovered:,}")
            print(f"    Time                    : {metrics.duration_ms / 1000.0:.2f} s")
            if metrics.warnings_count > 0:
                print(f"    Warnings                : {metrics.warnings_count}")

        print("--------------------------------------------------")
        print("Functions")
        print(f"    Total                   : {res.functions_compiled:,}")
        print("Semantic Objects")
        print(f"    Total                   : {res.total_semantic_objects:,}")
        print("Compilation Time")
        print(f"    Total Time              : {res.total_time_s:.2f} s")
        print(f"    Peak RSS                : {res.peak_rss_gb:.2f} GB")
        print("==================================================")