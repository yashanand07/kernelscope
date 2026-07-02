from semantic_runtime.semantic_model import LocalSymbol

class SymbolPrinter:
    """Formats detailed contextual metrics for localized function tokens."""

    @staticmethod
    def print_detailed_symbol(name: str, sym: LocalSymbol, usages: list = None):
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

        print(f"Semantic Usage")
        if usages:
            for usage in usages:
                print(f"    {usage}")
        else:
            print(f"    Cursor Variable")
            print(f"        Iteration #1")
            print(f"Referenced By")
            print(f"    IterationMetadata @ L{sym.declaration_line + 2}")
        print("-" * 40)