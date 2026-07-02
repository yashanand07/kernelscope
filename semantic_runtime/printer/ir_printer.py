import time
from typing import Dict, List, Any
from semantic_runtime.semantic_model import FunctionSemanticContext, CollectionDescriptor
from semantic_runtime.compiler.indices import CompilerIndices

class SemanticIRPrinter:
    """Master formatting controller for KernelScope Function Semantic IR."""

    @staticmethod
    def print_horizontal_rule(char: str = "=", length: int = 80):
        print(char * length)

    @classmethod
    def print_function_ir(cls, context: FunctionSemanticContext, indices: CompilerIndices):
        """Generates a complete, beautiful Semantic IR representation of a function context."""
        cls.print_horizontal_rule("=")
        print(f"{'KernelScope Function Semantic IR':^80}")
        cls.print_horizontal_rule("=")

        # 1. Core Header
        print("\nFunction")
        cls.print_horizontal_rule("-")
        print(f"Symbol ID        : {context.symbol_id}")
        clean_name = context.symbol_id.split(":")[-1] + "()" if ":" in context.symbol_id else context.symbol_id
        print(f"Function         : {clean_name}")
        print(f"Source File      : {context.file_path}")

        # 2. Local Symbol Table Section
        print("\n" + "=" * 80)
        print("Local Symbol Table")
        print("=" * 80)

        # Segregate parameters vs locals
        params = []
        locals_list = []
        for name, sym_list in context.local_symbols.items():
            for sym in sym_list:
                if sym.storage.value == "parameter":
                    params.append(sym)
                else:
                    locals_list.append(sym)

        print("\n[Parameter]\n")
        if not params:
            print("  - None -")
        for sym in params:
            print(f"{sym.name}")
            # Change the Type printer inside your loops to this:
            kind_prefix = f"{sym.type_info.kind.value} " if sym.type_info.kind.value in ["struct", "union", "enum"] else ""
            pointer_suffix = f" {'*' * sym.type_info.pointer_level}" if sym.type_info.pointer_level > 0 else ""
            print(f"    Type              : {kind_prefix}{sym.type_info.type_name}{pointer_suffix}".strip())
            print(f"    Kind              : {sym.type_info.kind.value.capitalize()}")
            print(f"    Qualifiers        : {', '.join(sym.type_info.qualifiers) if sym.type_info.qualifiers else '-'}")
            print(f"    Declaration Line  : {sym.declaration_line}")
            print(f"    Scope             : Global Function Scope")
            print("")

        cls.print_horizontal_rule("-")
        print("\n[Local]\n")
        if not locals_list:
            print("  - None -")
        for sym in locals_list:
            print(f"{sym.name}")
            # Change the Type printer inside your loops to this:
            kind_prefix = f"{sym.type_info.kind.value} " if sym.type_info.kind.value in ["struct", "union", "enum"] else ""
            pointer_suffix = f" {'*' * sym.type_info.pointer_level}" if sym.type_info.pointer_level > 0 else ""
            print(f"    Type              : {kind_prefix}{sym.type_info.type_name}{pointer_suffix}".strip())
            print(f"    Kind              : {sym.type_info.kind.value.capitalize()}")
            if sym.type_info.pointer_level > 0:
                print(f"    Pointer Level     : {sym.type_info.pointer_level}")
            print(f"    Declaration Line  : {sym.declaration_line}")
            if sym.scope_depth > 1:
                print(f"    Shadow Level      : {sym.scope_depth - 1}")
            print("")

        # 3. Semantic Timeline
        print("=" * 80)
        print("Semantic Timeline")
        print("=" * 80)

        if not context.semantic_constructs:
            print("\n  [No Semantic Constructs Encountered]")
        for idx, m in enumerate(context.semantic_constructs, 1):
            if m.__class__.__name__ == "IterationMetadata":
                print(f"\n[{idx}]\n")
                print(f"Semantic Type     : {m.__class__.__name__}")
                print(f"Source Line       : {m.source_line}")
                print("\nMacro")
                print(f"    {m.macro}")

                print("\nCollection")
                print(f"    Name           : {m.collection_name}")
                print(f"    Family         : {m.collection_family.value if hasattr(m.collection_family, 'value') else m.collection_family}")
                print(f"    Type           : struct {m.collection_type.replace('struct ', '') if m.collection_type else 'list_head'}")
                print(f"    Declared By    : {m.declared_by}")      # FIX: Separation
                print(f"    Referenced Via : {m.macro}")            # FIX: Separation
                print(f"    Symbol         : {m.collection_symbol_id or '<unresolved_global_identity>'}")

                print("\nCursor")
                print(f"    Variable       : {m.cursor_variable}")
                print(f"    Type           : {m.element_type or 'Unknown'} *")

                print("\nTraversal")
                print(f"    Member         : {m.member_field or 'N/A'}")
                print(f"    Deletion Safe  : {'Yes' if m.properties.deletion_safe else 'No'}")
                print(f"    Reverse        : {'Yes' if m.properties.reverse else 'No'}")
                print(f"    RCU            : {'Yes' if m.properties.rcu_protected else 'No'}")
                print("")

        # 4. Statistics Block Summary
        print("=" * 80)
        print("Compiler Statistics")
        print("=" * 80)
        print(f"Semantic Objects          : {len(context.semantic_constructs)}")
        print(f"Local Symbols             : {sum(len(v) for v in context.local_symbols.values())}")
        # Direct lookup safely against discovered cache metrics
        coll_refs = sum(1 for m in context.semantic_constructs if hasattr(m, 'collection_name') and m.collection_name)
        print(f"Collection References     : {coll_refs}")
        print(f"Warnings                  : 0")
        cls.print_horizontal_rule("=")