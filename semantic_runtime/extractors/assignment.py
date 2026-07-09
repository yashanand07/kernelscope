import importlib.resources
from semantic_runtime.ontology.metadata import AssignmentKind
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
        
        # Pattern captures: LHS, Operator, and a basic lookahead guard to drop == comparisons
        mutation_pattern = re.compile(
            r'\b([a-zA-Z_][a-zA-Z0-9_\->.]*(?:\s*\[[^\]]+\])?)\s*(=|\+=|-=|\*=|/=|\|=|&=|\^=|\+\+|--)(?!=)([^;\n]*);?'
        )
        
        for match in mutation_pattern.finditer(source):
            target_expr = match.group(1).strip()
            operator = match.group(2).strip()
            
            if "->" in target_expr or "." in target_expr:
                kind = AssignmentKind.STRUCT_FIELD
            elif "[" in target_expr:
                kind = AssignmentKind.ARRAY_ELEMENT
            else:
                kind = AssignmentKind.LOCAL_VARIABLE



            relative_line = source.count('\n', 0, match.start())
            absolute_line = context.start_line + relative_line
            loc = SourceLocation(file=context.file_path, line=absolute_line)
            
            root_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)', target_expr)
            resolved = None
            if root_match:
                root_symbol = root_match.group(1)
                if root_symbol in context.local_symbols:
                    resolved = root_symbol

            # 1. Map out a clean string slug for the kind
            kind_slug = "local" if kind == AssignmentKind.LOCAL_VARIABLE else "struct"            

            # Form clean slug for URI compliance
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
            
        # 5. Commit mutations back to the shared timeline registry
        if events:
            context.semantic_constructs.extend(events)
            
        duration = (time.perf_counter() - start_time) * 1000.0
        return ExtractionReport(
            extractor_name=self.__class__.__name__,
            discovered=len(events),
            duration_ms=duration,
            warnings=warnings
        )