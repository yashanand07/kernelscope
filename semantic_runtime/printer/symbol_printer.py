from semantic_runtime.semantic_model import LocalSymbol, FunctionSemanticContext

class SymbolPrinter:
    """Formats detailed contextual metrics and resolves true reverse-references for local tokens."""
    
    @staticmethod
    def print_detailed_symbol(name: str, sym: LocalSymbol, context: FunctionSemanticContext):
        print("\n" + "-" * 40)
        print(f"Dump Local Symbol: {name}")
        print("-" * 40)
        print(f"Declaration")
        print(f"    Line                : {sym.declaration_line}")
        print(f"Storage")
        print(f"    {sym.storage.value.capitalize()}")
        print(f"Type")
        print(f"    {sym.type_info.kind.value.capitalize()}")
        print(f"    Name                : {sym.type_info.type_name}")
        if sym.type_info.pointer_level > 0:
            print(f"    Pointer Level       : {sym.type_info.pointer_level}")
        print(f"Qualifiers")
        print(f"    {', '.join(sym.type_info.qualifiers) if sym.type_info.qualifiers else '-'}")
        
        # --- Dynamic Usage & Reference Computations ---
        usages = []
        references = []
        
        iteration_count = 0
        for m in context.semantic_constructs:
            if m.__class__.__name__ == "IterationMetadata":
                iteration_count += 1
                # Only attribute if this variable is the explicit cursor
                if m.cursor_variable == name:
                    usages.append(f"Cursor Variable\n        Iteration #{iteration_count}")
                    references.append(f"IterationMetadata @ L{m.location.line}")
        
        print(f"Semantic Usage")
        if usages:
            for usage in usages:
                print(f"    {usage}")
        else:
            print(f"    None")
            
        print(f"Referenced By")
        if references:
            for ref in references:
                print(f"    {ref}")
        else:
            print(f"    None")
        print("-" * 40)