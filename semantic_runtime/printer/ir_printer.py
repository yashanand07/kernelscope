from semantic_runtime.ontology.metadata import SemanticDomain
from semantic_runtime.ontology.metadata import AssignmentMetadata
import time
from typing import Dict, List, Any
from semantic_runtime.semantic_model import FunctionSemanticContext
from semantic_runtime.compiler.indices import CompilerIndices
from semantic_runtime.ontology.metadata import (
    LockAcquireMetadata,
    LockReleaseMetadata,
    IterationMetadata,
    CallMetadata,
    InterruptStateMetadata
)

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

        params = [sym for sym_list in context.local_symbols.values() for sym in sym_list if sym.storage.value == "parameter"]
        locals_list = [sym for sym_list in context.local_symbols.values() for sym in sym_list if sym.storage.value != "parameter"]

        print("\n[Parameter]\n")
        if not params:
            print("  - None -")
        for sym in params:
            print(f"{sym.name}")
            kind_prefix = f"{sym.type_info.kind.value} " if sym.type_info.kind.value in ["struct", "union", "enum"] else ""
            pointer_suffix = f" {'*' * sym.type_info.pointer_level}" if sym.type_info.pointer_level > 0 else ""
            print(f"    Type              : {kind_prefix}{sym.type_info.type_name}{pointer_suffix}".strip())
            print(f"    Kind              : {sym.type_info.kind.value.capitalize()}")
            print(f"    Declaration Line  : {sym.declaration_line}")
            print("")

        cls.print_horizontal_rule("-")
        print("\n[Local]\n")
        if not locals_list:
            print("  - None -")
        for sym in locals_list:
            print(f"{sym.name}")
            kind_prefix = f"{sym.type_info.kind.value} " if sym.type_info.kind.value in ["struct", "union", "enum"] else ""
            pointer_suffix = f" {'*' * sym.type_info.pointer_level}" if sym.type_info.pointer_level > 0 else ""
            print(f"    Type              : {kind_prefix}{sym.type_info.type_name}{pointer_suffix}".strip())
            print(f"    Declaration Line  : {sym.declaration_line}")
            print("")

        # 3. Semantic Timeline Output (Single, Clean Loop)
        print("=" * 80)
        print("Semantic Timeline")
        print("=" * 80)

        if not context.semantic_constructs:
            print("  - No Semantic Events Detected -")
        else:
            for idx, event in enumerate(context.semantic_constructs, start=1):
                print(f"\n[{idx}]")
                cls.print_timeline_event(event)
                print("-" * 80)

        counts = {domain.value: 0 for domain in SemanticDomain}
        for obj in context.semantic_constructs:
            counts[obj.domain.value] = counts.get(obj.domain.value, 0) + 1

        print("================================================================================")
        print("Semantic Graph Relationships (Phase 1.5 Substrate)")
        print("================================================================================")
        if not context.relationships:
            print("    No explicit graph relationships established.")
        else:
            for idx, rel in enumerate(context.relationships, 1):
                print(f"[{idx}]")
                print(f"Relationship ID   : {rel.relationship_id}")
                print(f"Relationship Type : {rel.relationship_type.value.upper()}")
                print(f"Source Node       : {rel.source_semantic_id}")
                print(f"Target Node       : {rel.target_semantic_id}\n")
                print("-" * 40)

        # 4. Statistics Block Summary
        print("\n" + "=" * 80)
        print("Compiler Statistics")
        print("=" * 80)
        print(f"Semantic Objects\n")
        for domain_name, count in counts.items():
            print(f"    {domain_name:<20} : {count}")
        print("    ----------------------------------------")
        print(f"    Total                : {len(context.semantic_constructs)}")
        print(f"Local Symbols            : {len(context.local_symbols)}")
        cls.print_horizontal_rule("=")

    @classmethod
    def print_timeline_event(cls, event):
        """Polymorphically matches and formats individual structural timeline nodes."""
        # 1. Universal Header
        print(f"Semantic ID      : {event.semantic_id}")
        print(f"Semantic Domain  : {event.domain.value}")
        print(f"Semantic Type    : {event.__class__.__name__}\n")

        # 2. Universal Source Block
        print("Source Location")
        print(f"    File         : {event.location.file}")
        print(f"    Line         : {event.location.line}\n")

        # 3. Type-Specific Blocks ONLY (No redundant lines)
        if isinstance(event, IterationMetadata):
            print(f"Macro            : {event.macro}")
            print(f"Collection Name  : {event.collection_name}")
            # ... print other iteration properties here ...

        elif isinstance(event, CallMetadata):
            print(f"Target           : {event.target_function}()")

        elif isinstance(event, LockAcquireMetadata):
            print(f"Primitive               : {event.primitive}")
            print(f"Synchronization Object  : {event.lock_expression}")
            print(f"Resolved Symbol         : {event.resolved_symbol or '<unresolved>'}")
            print(f"IRQ Save                : {'Yes' if event.irqsave else 'No'}")
            print(f"Recursive               : {'Yes' if event.recursive else 'No'}")

        elif isinstance(event, LockReleaseMetadata):
            print(f"Primitive               : {event.primitive}")
            print(f"Synchronization Object  : {event.lock_expression}")
            print(f"Resolved Symbol         : {event.resolved_symbol or '<unresolved>'}")
            print(f"IRQ Restor  e             : {'Yes' if event.irqrestore else 'No'}")

        elif isinstance(event, InterruptStateMetadata):
            print(f"Primitive               : {event.primitive}")
            print(f"Action                  : {event.action.upper()}")
        elif isinstance(event, AssignmentMetadata):
            print(f"Target Expression       : {event.target_expression}")
            print(f"Resolved Symbol         : {event.resolved_symbol or '<unresolved>'}")
            print(f"Assignment Kind         : {event.assignment_kind.value.upper()}")