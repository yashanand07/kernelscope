import re
import time
from semantic_runtime.extractors.base import BaseExtractor
from semantic_runtime.ontology.metadata import (
    SourceLocation, IterationMetadata, SemanticDomain, ExtractionReport
)

class IteratorExtractor(BaseExtractor):
    def extract(self, source: str, context, indices, kit) -> ExtractionReport:
        start_time = time.perf_counter()
        discovered = 0
        warnings = []

        # Wipes out all single and multiline comment artifacts via the active kit configuration
        clean_source = kit.clean_source_code(source)

        iter_prof = kit.iterator_profile()
        pattern = iter_prof.pattern

        for match in pattern.finditer(clean_source):
            macro_name = match.group(1).strip()
            raw_args = match.group(2).strip()

            relative_line = clean_source.count('\n', 0, match.start())
            absolute_line = context.start_line + relative_line
            loc = SourceLocation(file=context.file_path, line=absolute_line)

            # Fetch the declarative structural specification directly from the profile template
            spec = iter_prof.specs.get(macro_name)
            if not spec:
                continue

            # Parse arguments strictly using the structural positions provided by the kit
            args = [arg.strip() for arg in raw_args.split(',')]
            if not args:
                continue

            cursor_expr = args[spec.cursor_index] if spec.cursor_index < len(args) else "unknown"
            coll_expr = args[spec.collection_index] if spec.collection_index < len(args) else ""

            # Extract structured member fields if it's an entry wrapper
            member_expr = args[-1] if "_entry" in macro_name and len(args) >= 3 else "next"

            # Variable identity resolution tracking
            resolved = None
            if coll_expr:
                symbol_match = re.search(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', coll_expr)
                if symbol_match and symbol_match.group(1) in context.local_symbols:
                    resolved = symbol_match.group(1)

            action_id = f"iter:{context.file_path}:{absolute_line}:{macro_name}"

            context.semantic_constructs.append(IterationMetadata(
                semantic_id=action_id,
                location=loc,
                domain=SemanticDomain.ITERATION,
                source_text=match.group(0).strip(),
                macro=macro_name,
                collection_name=coll_expr,
                collection_family=spec.family,
                collection_type="struct list_head",
                declared_by=macro_name,
                cursor_variable=cursor_expr,
                element_type="Unknown",
                member_field=member_expr,
                properties=None,
                collection_symbol_id=resolved
            ))
            discovered += 1

        duration = (time.perf_counter() - start_time) * 1000.0
        return ExtractionReport(self.__class__.__name__, discovered, duration, warnings)