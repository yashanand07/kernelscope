import re
import time
from semantic_runtime.extractors.base import BaseExtractor
from semantic_runtime.ontology.metadata import (
    SourceLocation, AssignmentMetadata, SemanticDomain, ExtractionReport
)

class AssignmentExtractor(BaseExtractor):
    def extract(self, source: str, context, indices, kit) -> ExtractionReport:
        start_time = time.perf_counter()
        events = []
        warnings = []

        # Wipes out all single and multiline comment artifacts via the active kit configuration
        clean_source = kit.clean_source_code(source)

        assign_prof = kit.assignment_profile()
        mutation_pattern = assign_prof.pattern
        classify_kind = assign_prof.kind_classifier  # ◄── Call the delegate hook directly

        for match in mutation_pattern.finditer(clean_source):
            target_expr = match.group(1).strip()
            operator = match.group(2).strip()

            # 1. Evaluate kind via purely abstract functional delegation
            kind = classify_kind(target_expr)

            relative_line = clean_source.count('\n', 0, match.start())
            absolute_line = context.start_line + relative_line
            loc = SourceLocation(file=context.file_path, line=absolute_line)

            # Root symbol tracking stays safe via basic identifier matching
            root_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)', target_expr)
            resolved = None
            if root_match:
                root_symbol = root_match.group(1)
                if root_symbol in context.local_symbols:
                    resolved = root_symbol

            kind_slug = "local" if kind == assign_prof.kind_classifier("var") else "struct"
            clean_expr = target_expr.replace('->', '_').replace('.', '_').replace('[', '_').replace(']', '')
            semantic_id = f"assign:{context.file_path}:{absolute_line}:{kind_slug}:{clean_expr}"

            events.append(AssignmentMetadata(
                semantic_id=semantic_id,
                location=loc,
                domain=SemanticDomain.ASSIGNMENT,
                target_expression=target_expr,
                resolved_symbol=resolved,
                assignment_kind=kind,
                operator=operator
            ))

        if events:
            context.semantic_constructs.extend(events)

        duration = (time.perf_counter() - start_time) * 1000.0
        return ExtractionReport(
            extractor_name=self.__class__.__name__,
            discovered=len(events),
            duration_ms=duration,
            warnings=warnings
        )