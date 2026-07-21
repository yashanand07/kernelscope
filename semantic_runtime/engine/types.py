"""Engine domain types and compilation result data structures."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

@dataclass
class EngineStatus:
    """Status struct tracking current engine compilation state."""
    is_compiled: bool
    active_project: Optional[str]
    cache_dir: Path

@dataclass
class Diagnostic:
    level: str  # "INFO", "WARNING", "ERROR"
    message: str

@dataclass
class CompilationMetrics:
    """Telemetry and counts captured during project compilation."""
    compile_time_sec: float = 0.0
    peak_rss_mb: float = 0.0
    semantic_nodes: int = 0
    relationships: int = 0
    files: int = 0
    symbols: int = 0

    # --- Backward / UI Property Aliases ---
    @property
    def duration_sec(self) -> float:
        return self.compile_time_sec

    @property
    def source_files_count(self) -> int:
        return self.files

    @property
    def indexed_symbols_count(self) -> int:
        return self.symbols

    @property
    def graph_nodes_count(self) -> int:
        return self.semantic_nodes

    @property
    def graph_edges_count(self) -> int:
        return self.relationships


@dataclass
class CompilationArtifacts:
    semantic_nodes_db: Path
    relationships_db: Path
    dictionary_db: Path
    manifest_json: Path


@dataclass
class CompilationResult:
    """Canonical serializable result of a compilation pipeline execution."""

    success: bool
    project_name: str = "unknown"
    profile_name: str = "default"
    compiler_version: str = "2.0.0-alpha"
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metrics: Optional[CompilationMetrics] = None
    artifacts: Optional[CompilationArtifacts] = None
    diagnostics: List[Diagnostic] = field(default_factory=list)
    error: Optional[str] = None

    def summary(self) -> str:
        """Generates clean human-readable CLI summary."""
        status_symbol = "🟢 SUCCESS" if self.success else "🔴 FAILED"

        if not self.success or not self.metrics:
            return (
                f"=== KernelScope Compilation [{status_symbol}] ===\n"
                f" Error: {self.error or 'Unknown failure'}\n"
                f" ⚠️  Diagnostics: {len(self.diagnostics)} item(s)\n"
                f"=================================================="
            )

        m = self.metrics
        return (
            f"=== KernelScope Compilation [{status_symbol}] ===\n"
            f" ⏱️  Duration       : {m.duration_sec:.2f}s\n"
            f" 🧠 Peak Memory     : {m.peak_rss_mb:.2f} MB\n"
            f" 📁 Source Files    : {m.source_files_count:,}\n"
            f" 🔤 Indexed Symbols : {m.indexed_symbols_count:,}\n"
            f" 🧩 Graph Nodes     : {m.graph_nodes_count:,}\n"
            f" 🔗 Graph Edges     : {m.graph_edges_count:,}\n"
            f" ⚠️  Diagnostics     : {len(self.diagnostics)} item(s)\n"
            f"=================================================="
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes result into a JSON-compatible dictionary for REST API responses."""
        return {
            "success": self.success,
            "project_name": self.project_name,
            "profile_name": self.profile_name,
            "compiler_version": self.compiler_version,
            "timestamp": self.timestamp,
            "metrics": {
                "duration_sec": self.metrics.duration_sec,
                "peak_rss_mb": self.metrics.peak_rss_mb,
                "source_files_count": self.metrics.source_files_count,
                "indexed_symbols_count": self.metrics.indexed_symbols_count,
                "graph_nodes_count": self.metrics.graph_nodes_count,
                "graph_edges_count": self.metrics.graph_edges_count,
            } if self.metrics else None,
            "diagnostics": [
                {"level": d.level, "message": d.message} for d in self.diagnostics
            ],
            "error": self.error,
        }