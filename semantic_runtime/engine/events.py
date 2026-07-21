"""Event telemetry models for KernelScope compilation stages."""

from dataclasses import dataclass
from typing import Callable, Any, Optional


@dataclass
class CompilationEvent:
    """Telemetry payload emitted during stage transitions and compilation events."""

    stage_id: int
    total_stages: int
    stage_name: str
    progress_pct: float
    message: str
    payload: Optional[Any] = None


# Callback listener signature
CompilationListener = Callable[[CompilationEvent], None]


def default_cli_listener(event: CompilationEvent) -> None:
    """Standard console logger format for CLI usage."""
    bar_len = 20
    filled = int(bar_len * (event.progress_pct / 100.0))
    bar = "█" * filled + "░" * (bar_len - filled)

    print(
        f"[{event.stage_id}/{event.total_stages}] [{bar}] "
        f"{event.progress_pct:5.1f}% | {event.stage_name:<22} :: {event.message}"
    )