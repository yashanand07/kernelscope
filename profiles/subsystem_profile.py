from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any

from semantic_runtime.provider_patterns import (
    ProviderPattern
)
@dataclass
class SubsystemSemanticProfile:

    subsystem_name: str

    entrypoints: list[str]

    entrypoint_files: List[str]

    associated_structs: set[str]

    dispatch_provider_files: List[str]

    low_signal_calls: set[str]

    execution_spine_boost: dict[str, float]

    high_value_transitions: dict[
        tuple[str, str],
        float
    ]

    synthetic_bridges: dict[str, str]

    provider_patterns: List[
        ProviderPattern
    ] = field(default_factory=list)

    valid_dispatch_operations: Set[str] = field(default_factory=set)

    runtime_depth_limit: int = 16

    terminal_symbols: set[str] = field(default_factory=set)

    def requires_dispatch_analysis(
        self,
        symbol: str
    ) -> bool:

        return (
            self.resolve_provider_pattern(symbol)
            is not None
        )

    def resolve_provider_pattern(
        self,
        symbol: str
    ) -> Optional[ProviderPattern]:

        for pattern in self.provider_patterns:

            if symbol.endswith(pattern.suffix):
                return pattern

        return None