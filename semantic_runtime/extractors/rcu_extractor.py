from semantic_runtime.ontology.metadata import RCUIterationMetadata
import re
import time
from semantic_runtime.extractors.base import BaseExtractor
from semantic_runtime.ontology.metadata import (
    SourceLocation, SemanticDomain, ExtractionReport,
    RcuReadLockMetadata, RcuReadUnlockMetadata,
    RcuDereferenceMetadata, RcuPublishMetadata, RcuGracePeriodMetadata
)

class RCUExtractor(BaseExtractor):
    def extract(self, source: str, context, indices, kit) -> ExtractionReport:
        start_time = time.perf_counter()
        events = []
        warnings = []

        # Wipes out all single and multiline comment artifacts via the active kit configuration
        clean_source = kit.clean_source_code(source)

        rcu_prof = kit.rcu_profile()
        # High performance cached token compiled match string evaluation
        pattern = rcu_prof.pattern

        for match in pattern.finditer(clean_source):
            token = match.group(1)
            raw_expr = match.group(2).strip()

            relative_line = clean_source.count('\n', 0, match.start())
            absolute_line = context.start_line + relative_line
            loc = SourceLocation(file=context.file_path, line=absolute_line)

            # TODO: Replace raw comma-splitting with a strict balancing parentheses parser
            # to flawlessly handle nested call constructs like container_of(...)
            expr_parts = [p.strip() for p in raw_expr.split(',')]
            target_expr = expr_parts[0] if expr_parts else raw_expr

            # Identifiers resolution tracking
            # TODO: Move this pattern into a top-level context.resolve_symbol(expr) method
            resolved = None
            symbol_match = re.search(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', target_expr)
            if symbol_match:
                possible_sym = symbol_match.group(1)
                if possible_sym in context.local_symbols:
                    resolved = possible_sym

            # Emit telemetry warnings if pointer extraction leaves an orphaned expression
            if not resolved and token in (rcu_prof.dereference | rcu_prof.publish):
                warnings.append(
                    f"Line {absolute_line}: Unresolved RCU tracking symbol expression reference context target '{target_expr}'"
                )

            semantic_token = target_expr.replace('->', '_').replace('.', '_').replace('[', '_').replace(']', '')

            # Semantic Class Mapping Engine
            if token in rcu_prof.read_lock:
                events.append(RcuReadLockMetadata(
                    semantic_id=f"rcu:{context.file_path}:{absolute_line}:read_lock:{token}",
                    location=loc, domain=SemanticDomain.RCU, source_text=match.group(0).strip(),
                    api=token
                ))
            elif token in rcu_prof.read_unlock:
                events.append(RcuReadUnlockMetadata(
                    semantic_id=f"rcu:{context.file_path}:{absolute_line}:read_unlock:{token}",
                    location=loc, domain=SemanticDomain.RCU, source_text=match.group(0).strip(),
                    api=token
                ))
            elif token in rcu_prof.dereference:
                events.append(RcuDereferenceMetadata(
                    semantic_id=f"rcu:{context.file_path}:{absolute_line}:deref:{token}_{semantic_token}",
                    location=loc, domain=SemanticDomain.RCU, source_text=match.group(0).strip(),
                    api=token, target_expression=target_expr, resolved_symbol=resolved
                ))
            elif token in rcu_prof.publish:
                events.append(RcuPublishMetadata(
                    semantic_id=f"rcu:{context.file_path}:{absolute_line}:publish:{token}_{semantic_token}",
                    location=loc, domain=SemanticDomain.RCU, source_text=match.group(0).strip(),
                    api=token, target_expression=target_expr, resolved_symbol=resolved
                ))
            elif token in rcu_prof.grace_period:
                events.append(RcuGracePeriodMetadata(
                    semantic_id=f"rcu:{context.file_path}:{absolute_line}:grace_period:{token}",
                    location=loc, domain=SemanticDomain.RCU, source_text=match.group(0).strip(),
                    api=token
                ))
            elif token in rcu_prof.iterators:
                events.append(RCUIterationMetadata(
                    semantic_id=f"rcu:{context.file_path}:{absolute_line}:loop:{token}_{semantic_token}",
                    location=loc, domain=SemanticDomain.RCU, source_text=match.group(0).strip(),
                    api=token, target_expression=target_expr, resolved_symbol=resolved
                ))

        if events:
            context.semantic_constructs.extend(events)

        duration = (time.perf_counter() - start_time) * 1000.0
        return ExtractionReport(self.__class__.__name__, len(events), duration, warnings)