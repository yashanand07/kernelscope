from semantic_runtime.ontology.metadata import SemanticDomain
from semantic_runtime.extractors.base import BaseExtractor
import time
import re
from typing import List, Optional, TYPE_CHECKING
from semantic_runtime.ontology.metadata import ExtractionReport, CallMetadata, CallArgument, SourceLocation

if TYPE_CHECKING:
    from semantic_runtime.semantic_model import FunctionSemanticContext
    from semantic_runtime.compiler.indices import CompilerIndices

class CallExtractor(BaseExtractor):
    def extract(self, source: str, context, indices, kit=None) -> ExtractionReport:
        start_time = time.perf_counter()
        discovered = 0
        warnings = []

        # Wipes out all single and multiline comment artifacts via the active kit configuration
        clean_source = kit.clean_source_code(source)

        # Pull the fully isolated call specification from the kit
        call_prof = kit.call_profile()
        call_pattern = call_prof.pattern

        # Assemble the dynamic exclusion barrier from keywords and macro sets
        exclusion_set = set(call_prof.control_keywords)
        
        if kit:
            iter_prof = kit.iterator_profile()
            exclusion_set.update(iter_prof.specs.keys())

            rcu_prof = kit.rcu_profile()
            exclusion_set.update(
                rcu_prof.read_lock |
                rcu_prof.read_unlock |
                rcu_prof.dereference |
                rcu_prof.publish |
                rcu_prof.grace_period |
                rcu_prof.iterators
            )

            if hasattr(kit, 'synchronization_primitives'):
                sync_data = kit.synchronization_primitives()
                for category in ["acquire", "release", "interrupt"]:
                    if category in sync_data:
                        exclusion_set.update(sync_data[category].keys())
        
        # Strip the function signature boundary block
        body_start_idx = clean_source.find('{')
        if body_start_idx == -1:
            return ExtractionReport(extractor_name=self.__class__.__name__, discovered=0, warnings=["No function body scope found"])
            
        function_body = clean_source[body_start_idx + 1:]
        body_offset_lines = clean_source[:body_start_idx + 1].count('\n')
        
        # Sweep and evaluate calls purely using the kit's rules
        for match in call_pattern.finditer(function_body):
            try:
                target_name = match.group(1).strip()
                args_str = match.group(2).strip()
                
                if target_name in exclusion_set:
                    continue
                    
                relative_line = function_body.count('\n', 0, match.start())
                absolute_line = context.start_line + body_offset_lines + relative_line
                loc = SourceLocation(file=context.file_path, line=absolute_line)

                resolved_args = []
                if args_str:
                    resolved_args.append(CallArgument(raw_expression=args_str))
                
                context.semantic_constructs.append(CallMetadata(
                    semantic_id=f"call:{context.file_path}:{absolute_line}:{target_name}",
                    location=loc,
                    domain=SemanticDomain.CALL,
                    source_text=match.group(0).strip(),
                    target_function=target_name,
                    arguments=resolved_args
                ))
                discovered += 1
                
            except Exception as e:
                warnings.append(f"Line {context.start_line}: Failed to parse call token: {str(e)}")
                
        duration = (time.perf_counter() - start_time) * 1000.0
        return ExtractionReport(self.__class__.__name__, discovered, duration, warnings)