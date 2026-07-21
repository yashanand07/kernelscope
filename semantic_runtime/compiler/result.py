import resource
from dataclasses import dataclass, field
from typing import Dict, List, Any
from semantic_runtime.semantic_model import FunctionSemanticContext

@dataclass
class ExtractorTelemetry:
    discovered: int = 0
    duration_ms: float = 0.0
    warnings_count: int = 0
    warnings_list: List[str] = field(default_factory=list)

@dataclass
class PipelineExecutionReport:
    """The complete structural telemetry report for a compiler execution sweep."""
    chunks_scanned: int = 0
    functions_compiled: int = 0
    collections_discovered: int = 0
    total_symbols: int = 0
    total_semantic_objects: int = 0
    total_warnings: int = 0

    phase_0_time_s: float = 0.0
    phase_1_time_s: float = 0.0
    total_time_s: float = 0.0
    peak_rss_gb: float = 0.0

    # Granular reporting dictionary mapping: ExtractorName -> ExtractorTelemetry
    extractor_metrics: Dict[str, ExtractorTelemetry] = field(default_factory=dict)
    contexts: Dict[str, FunctionSemanticContext] = field(default_factory=dict)

    def capture_memory_profile(self):
        """Snapshots peak resident set size natively using platform resource metrics."""
        usage = resource.getrusage(resource.RUSAGE_SELF)
        # On Linux, maxrss is reported in kilobytes
        self.peak_rss_gb = usage.ru_maxrss / (1024.0 * 1024.0)