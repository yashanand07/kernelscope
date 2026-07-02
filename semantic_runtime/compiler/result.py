from typing import Dict, List, Any
from dataclasses import dataclass, field
from semantic_runtime.semantic_model import FunctionSemanticContext

@dataclass
class CompilationResult:
    """The unified data token representing the full output of a compiler run."""
    functions_compiled: int = 0
    collections_discovered: int = 0
    total_symbols: int = 0
    total_warnings: int = 0
    duration_seconds: float = 0.0
    contexts: Dict[str, FunctionSemanticContext] = field(default_factory=dict)
    extractor_telemetry: Dict[str, Dict[str, Any]] = field(default_factory=dict)