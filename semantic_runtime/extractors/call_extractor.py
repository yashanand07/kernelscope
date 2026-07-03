import re
from typing import List, Optional, TYPE_CHECKING
from semantic_runtime.ontology.metadata import ExtractionReport, CallMetadata, CallArgument, SourceLocation

if TYPE_CHECKING:
    from semantic_runtime.semantic_model import FunctionSemanticContext
    from semantic_runtime.compiler.indices import CompilerIndices

class CallExtractor():
    """
    Phase 1 Pass 3: Extracts standard function calls while strictly ignoring 
    the function definition signature and dedicated semantic macros.
    """
    
    # Core language control constructs to ignore completely
    CONTROL_KEYWORDS = {'if', 'for', 'while', 'switch', 'return', 'sizeof'}

    # EXCLUDE SEMANTIC MACROS: Keep generic calls clear of dedicated engine domains
    SEMANTIC_MACROS = {
        # Iterators
        'list_for_each', 'list_for_each_safe', 'list_for_each_entry', 'list_for_each_entry_safe',
        'hlist_for_each', 'hlist_for_each_safe', 'hlist_for_each_entry', 'hlist_for_each_entry_safe',
        'hash_for_each', 'hash_for_each_safe', 'hash_for_each_rcu', 'for_each_cpu',
        
        # Locking Primitives
        'spin_lock', 'spin_unlock', 'spin_lock_irqsave', 'spin_unlock_irqrestore',
        'mutex_lock', 'mutex_unlock', 'read_lock', 'read_unlock', 'write_lock', 'write_unlock',
        
        # RCU Helpers
        'rcu_read_lock', 'rcu_read_unlock', 'rcu_assign_pointer', 'rcu_dereference',
        
        # Workqueues & Timers
        'queue_work', 'schedule_work', 'mod_timer', 'del_timer'
    }

    # Generic function call pattern: token(args)
    CALL_PATTERN = re.compile(r'\b([a-zA-Z_]\w*)\s*\(([^;]*)\)')

    def extract(self, source: str, context: 'FunctionSemanticContext', indices: 'CompilerIndices') -> ExtractionReport:
        discovered = 0
        warnings = []
        
        # 1. Clean out comments to protect evaluation safety
        clean_source = re.sub(r'//.*', '', source)
        
        # 2. STRIP THE FUNCTION SIGNATURE BOUNDARY
        # Locate the first outermost opening brace '{' marking the start of the function body block
        body_start_idx = clean_source.find('{')
        if body_start_idx == -1:
            return ExtractionReport(extractor_name="CallExtractor", discovered=0, warnings=["No function body scope found"])
            
        # Only evaluate code text strictly after the opening brace boundary
        function_body = clean_source[body_start_idx + 1:]
        body_offset_lines = clean_source[:body_start_idx + 1].count('\n')
        
        for match in self.CALL_PATTERN.finditer(function_body):
            try:
                target_name = match.group(1).strip()
                args_str = match.group(2).strip()
                
                # Check control keywords and exclusive macro boundaries
                if target_name in self.CONTROL_KEYWORDS or target_name in self.SEMANTIC_MACROS:
                    continue
                    
                if ')' in args_str:
                    args_str = args_str.split(')')[0]
                    
                # Calculate correct line alignment taking the chopped signature header into account
                line_num = function_body.count('\n', 0, match.start()) + 1 + body_offset_lines
                action_id = f"{context.symbol_id}#call:{target_name}:L{line_num}"
                
                resolved_args = []
                raw_args = [a.strip() for a in args_str.split(',') if a.strip()]
                
                for arg_expr in raw_args:
                    clean_var = arg_expr.lstrip('&').strip()
                    local_sym = context.lookup_local(clean_var)
                    
                    if local_sym:
                        resolved_args.append(CallArgument(
                            raw_expression=arg_expr,
                            resolved_symbol_name=local_sym.name,
                            type_name=local_sym.type_info.type_name,
                            pointer_level=local_sym.type_info.pointer_level + (1 if arg_expr.startswith('&') else 0)
                        ))
                    else:
                        resolved_args.append(CallArgument(raw_expression=arg_expr))

                # Calculate absolute line
                relative_line = function_body.count('\n', 0, match.start())
                absolute_line = context.start_line + body_offset_lines + relative_line
                
                loc = SourceLocation(file=context.file_path, line=absolute_line)
                action_id = f"{context.symbol_id}#call:{target_name}:L{absolute_line}"
                
                # ... argument parsing ...                        
                metadata = CallMetadata(
                    semantic_id=action_id,
                    location=loc,
                    source_text=match.group(0).strip(),
                    target_function=target_name,
                    arguments=resolved_args
                )
                
                context.semantic_constructs.append(metadata)
                discovered += 1
                
            except Exception as e:
                # Trace exactly where evaluation ran into trouble
                warnings.append(f"Call parser error near token '{target_name}': {str(e)}")
                
        return ExtractionReport(
            extractor_name="CallExtractor",
            discovered=discovered,
            warnings=warnings
        )