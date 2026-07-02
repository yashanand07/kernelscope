from semantic_runtime.compiler.indices import CollectionIndex

class CollectionIndexPrinter:
    """Structural layout formatter for verified Phase 0 Collection Indices."""

    @staticmethod
    def print_index(index: CollectionIndex):
        print("=" * 80)
        print(f"{'Compiler Collection Index':^80}")
        print("=" * 80)

        if len(index) == 0:
            print("\n  [Collection Index Empty]")
            return

        for item in index:
            print(f"\n{item.name}")
            print(f"    Family             : {item.collection_family.value if hasattr(item.collection_family, 'value') else item.collection_family}")
            print(f"    Type               : {item.type_name}")
            print(f"    Declared In        : {item.declaration_file}")
            print(f"    Declaration Macro  : {item.declaration_macro}")
            print("    Symbol Identity")
            print(f"        symbol_id      : {item.symbol_id or '<anonymous>'}")
            print(f"        namespace      : Global")
            print(f"        scope          : File")
            print(f"        line           : {item.declaration_line or 'N/A'}")

            # Placeholder for future consumer cross-reference features
            print("\n    Known Users")
            print("        - (Not yet computed)")   # yashtbd
            print("")
        print("=" * 80)