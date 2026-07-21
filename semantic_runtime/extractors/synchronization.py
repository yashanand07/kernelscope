import re
import time
from semantic_runtime.extractors.base import BaseExtractor
from semantic_runtime.ontology.metadata import (
    SourceLocation, LockAcquireMetadata, LockReleaseMetadata,
    InterruptStateMetadata, ExtractionReport
)
from semantic_runtime.ontology.metadata import SemanticDomain

class SynchronizationExtractor(BaseExtractor):
    def extract(self, source: str, context, indices, kit) -> ExtractionReport:
        start_time = time.perf_counter()
        events = []
        warnings = []

        # Wipes out all single and multiline comment artifacts via the active kit configuration
        clean_source = kit.clean_source_code(source)

        sync_map = kit.synchronization_primitives()
        acquire_prims = sync_map.get("acquire", {})
        release_prims = sync_map.get("release", {})
        interrupt_prims = sync_map.get("interrupt", {})

        all_primitives = list(acquire_prims.keys()) + list(release_prims.keys()) + list(interrupt_prims.keys())

        if all_primitives:
            pattern = re.compile(r'\b(' + '|'.join(re.escape(p) for p in all_primitives) + r')\s*\(([^;]*)\)')

            for match in pattern.finditer(clean_source):
                primitive = match.group(1)
                raw_expr = match.group(2).strip()

                expr_parts = [p.strip() for p in raw_expr.split(',')]
                lock_expr = expr_parts[0] if expr_parts else raw_expr

                relative_line = clean_source.count('\n', 0, match.start())
                absolute_line = context.start_line + relative_line
                loc = SourceLocation(file=context.file_path, line=absolute_line)

                resolved = None
                clean_symbol_match = re.search(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', lock_expr)
                if clean_symbol_match:
                    possible_symbol = clean_symbol_match.group(1)
                    if possible_symbol in context.local_symbols:
                        resolved = possible_symbol

                if primitive in acquire_prims:
                    attrs = acquire_prims[primitive]
                    events.append(LockAcquireMetadata(
                        semantic_id = f"sync:{context.file_path}:{absolute_line}:acquire:{primitive}",
                        location=loc,
                        domain=SemanticDomain.SYNCHRONIZATION,
                        primitive=primitive,
                        lock_expression=lock_expr,
                        resolved_symbol=resolved,
                        irqsave=attrs.get("irqsave", False),
                        recursive=attrs.get("recursive", False)
                    ))
                elif primitive in release_prims:
                    attrs = release_prims[primitive]
                    events.append(LockReleaseMetadata(
                        semantic_id = f"sync:{context.file_path}:{absolute_line}:release:{primitive}",
                        location=loc,
                        domain=SemanticDomain.SYNCHRONIZATION,
                        primitive=primitive,
                        lock_expression=lock_expr,
                        resolved_symbol=resolved,
                        irqrestore=attrs.get("irqrestore", False)
                    ))
                elif primitive in interrupt_prims:
                    attrs = interrupt_prims[primitive]
                    events.append(InterruptStateMetadata(
                        semantic_id=f"sync:{context.file_path}:{absolute_line}:interrupt:{primitive}",
                        location=loc,
                        domain=SemanticDomain.SYNCHRONIZATION,
                        primitive=primitive,
                        action=attrs.get("action", "unknown")
                    ))

        if events:
            context.semantic_constructs.extend(events)

        duration = (time.perf_counter() - start_time) * 1000.0

        # ────► RETURN THE EXPECTED TELEMETRY CONTRACT
        return ExtractionReport(
            extractor_name=self.__class__.__name__,
            discovered=len(events),
            duration_ms=duration,
            warnings=warnings
        )