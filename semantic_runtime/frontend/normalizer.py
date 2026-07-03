from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from semantic_runtime.frontend.tag import Tag, NormalizedTag

class TagNormalizerRule(ABC):
    """Abstract interface for system-specific structural token normalization rules."""
    @abstractmethod
    def normalize(self, tag: Tag) -> Optional[NormalizedTag]:
        """Processes a raw tag, returning a NormalizedTag if matched, else None."""
        pass

@dataclass
class FrontendTelemetry:
    raw_tags: int = 0
    functions: int = 0
    variables: int = 0
    wrappers_canonicalized: int = 0
    duplicates_removed: int = 0
    canonical_symbols: int = 0

class NormalizerPipeline:
    """Orchestrates sequential tag normalization passes and tracking telemetry metrics."""
    def __init__(self, rules: List[TagNormalizerRule]):
        self.rules = rules

    def execute(self, raw_tags: List[Tag]) -> Tuple[List[NormalizedTag], FrontendTelemetry]:
        stats = FrontendTelemetry(raw_tags=len(raw_tags))
        normalized_map: Dict[Tuple[str, str], NormalizedTag] = {}

        for tag in raw_tags:
            # Classify raw base types
            if tag.kind in ("function", "f"):
                stats.functions += 1
            elif tag.kind in ("variable", "v"):
                stats.variables += 1
            else:
                continue

            # Fallback default: pass-through rule
            final_tag = NormalizedTag(
                symbol=tag.symbol,
                file=tag.file,
                line=tag.line,
                kind=tag.kind,
                original_tag=tag
            )
            is_canonicalized = False

            # Evaluate macro rules
            for rule in self.rules:
                result = rule.normalize(tag)
                if result:
                    final_tag = result
                    is_canonicalized = True
                    break

            # If a rule evaluated to explicitly drop the tag (e.g., SEC attributes)
            if final_tag is None:
                continue

            if is_canonicalized:
                stats.wrappers_canonicalized += 1

            unique_key = (final_tag.file, final_tag.symbol)

            # Check for duplicate identities targeting the same structural range
            if unique_key in normalized_map:
                stats.duplicates_removed += 1
                if final_tag.line < normalized_map[unique_key].line:
                    normalized_map[unique_key] = final_tag
            else:
                normalized_map[unique_key] = final_tag

        stats.canonical_symbols = len(normalized_map)
        return list(normalized_map.values()), stats