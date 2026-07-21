from semantic_runtime.ontology.metadata import TypeKind
from semantic_runtime.ontology.metadata import TypeDescriptor
from semantic_runtime.frontend.profiles import SymbolProfile
from semantic_runtime.frontend.profiles import CallProfile
from semantic_runtime.ontology.metadata import AssignmentKind
from semantic_runtime.frontend.profiles import IteratorMacroSpec
from typing import List, Set, Dict
import re
# Semantic Runtime imports
from semantic_runtime.frontend.adaptation import AdaptationKit
from semantic_runtime.frontend.normalizer import TagNormalizerRule

# Linux Adaptation imports
from adaptation.linux.synchronisation import get_linux_sync_profile
from semantic_runtime.drivers.linux.tag_normalizers import ACPINormalizer, BPFNormalizer, ModuleNormalizer
from semantic_runtime.frontend.profiles import (
    SynchronizationProfile,
    IteratorProfile,
    RcuProfile,
    AssignmentProfile,
    DispatchProfile
)

class LinuxAdaptationKit(AdaptationKit):
    """Encapsulates all architectural and DSL knowledge for the Linux Kernel ecosystem."""

    def synchronization_profile(self) -> SynchronizationProfile:
        # # YASHTBD: Wrap the raw dict from get_linux_sync_profile() into a SynchronizationProfile object
        return SynchronizationProfile(raw_data=get_linux_sync_profile())

    def iterator_profile(self) -> IteratorProfile:
        return IteratorProfile(
            specs={
                # Standard Iterators (Collection at index 1)
                "list_for_each_entry": IteratorMacroSpec(cursor_index=0, collection_index=1, family="list"),
                "hlist_for_each_entry": IteratorMacroSpec(cursor_index=0, collection_index=1, family="hlist"),

                # Safe Iterators (Collection shifted to index 2 due to safe pointer storage variable)
                "list_for_each_entry_safe": IteratorMacroSpec(cursor_index=0, collection_index=2, family="list"),
                "hlist_for_each_entry_safe": IteratorMacroSpec(cursor_index=0, collection_index=2, family="hlist"),

                # RCU Iterators (Enabling orthogonal double-capture)
                "list_for_each_entry_rcu": IteratorMacroSpec(cursor_index=0, collection_index=1, family="list"),
                "hlist_bl_for_each_entry_rcu": IteratorMacroSpec(cursor_index=0, collection_index=2, family="hlist_bl"),

                # Hash Iterators (Hashtable root placed at index 0)
                "hash_for_each": IteratorMacroSpec(cursor_index=3, collection_index=0, family="hash"),
                "hash_for_each_rcu": IteratorMacroSpec(cursor_index=3, collection_index=0, family="hash"),

                # RBTrees
                "rbtree_postorder_for_each_entry_safe": IteratorMacroSpec(cursor_index=0, collection_index=2, family="rbtree")
            }
        )

    def rcu_profile(self) -> RcuProfile:
        return RcuProfile(
            read_lock={
                "rcu_read_lock", "srcu_read_lock", "rcu_read_lock_bh", "rcu_read_lock_sched"
            },
            read_unlock={
                "rcu_read_unlock", "srcu_read_unlock", "rcu_read_unlock_bh", "rcu_read_unlock_sched"
            },
            dereference={
                "rcu_dereference", "rcu_access_pointer", "rcu_dereference_bh",
                "rcu_dereference_sched", "rcu_dereference_raw", "rcu_dereference_check"
            },
            publish={
                "rcu_assign_pointer", "RCU_INIT_POINTER"
            },
            grace_period={
                "synchronize_rcu", "synchronize_rcu_bh", "synchronize_sched",
                "call_rcu", "kfree_rcu"
            },
            iterators={
                "hlist_for_each_entry_rcu", "hlist_bl_for_each_entry_rcu",
                "list_for_each_entry_rcu", "list_for_each_entry_continue_rcu",
                "hlist_for_each_entry_rcu_bh"
            }
        )

    def assignment_profile(self) -> AssignmentProfile:
        def linux_classifier(target_expr: str) -> AssignmentKind:
            if "->" in target_expr or "." in target_expr:
                return AssignmentKind.STRUCT_FIELD
            if "[" in target_expr:
                return AssignmentKind.ARRAY_ELEMENT
            return AssignmentKind.LOCAL_VARIABLE

        return AssignmentProfile(
            base_mutation_regex=r'\b([a-zA-Z_][a-zA-Z0-9_\->.]*(?:\s*\[[^\]]+\])?)\s*(=|\+=|-=|\*=|/=|\|=|&=|\^=|\+\+|--)(?!=)([^;\n]*);?',
            atomic_macros={"atomic_set", "atomic_inc", "atomic_dec", "atomic_add", "atomic_sub"},
            kind_classifier=linux_classifier  # ◄── Pass the structural rule here
        )

    def call_profile(self) -> CallProfile:
        return CallProfile(
            call_regex=r'\b([a-zA-Z_]\w*)\s*\(([^;]*)\)',
            control_keywords={'if', 'for', 'while', 'switch', 'return', 'sizeof'}
        )

    def symbol_profile(self) -> SymbolProfile:
        def linux_type_parser(raw_type: str, declarator: str) -> TypeDescriptor:
            qualifiers = [q for q in ['const', 'volatile', 'restrict'] if q in raw_type]
            pointer_level = raw_type.count('*') + declarator.count('*')

            clean_type = re.sub(r'\b(const|volatile|restrict)\b', '', raw_type).replace('*', '').strip()

            kind = TypeKind.BUILTIN
            type_name = clean_type

            if re.search(r'\bstruct\b', clean_type):
                kind = TypeKind.STRUCT
                type_name = re.sub(r'\bstruct\b', '', clean_type).strip()
            elif re.search(r'\benum\b', clean_type):
                kind = TypeKind.ENUM
                type_name = re.sub(r'\benum\b', '', clean_type).strip()
            elif re.search(r'\bunion\b', clean_type):
                kind = TypeKind.UNION
                type_name = re.sub(r'\bunion\b', '', clean_type).strip()
            elif clean_type.endswith('_t') or clean_type not in {'int', 'char', 'void', 'long', 'short', 'float', 'double', 'unsigned', 'signed'}:
                kind = TypeKind.TYPEDEF

            return TypeDescriptor(
                type_name=type_name,
                kind=kind,
                qualifiers=qualifiers,
                pointer_level=pointer_level
            )

        return SymbolProfile(
            decl_regex=r'^\s*((?:(?:static|const|struct|union|enum|unsigned|signed|long|short|volatile)\s+)*[a-zA-Z_]\w*)\s+([*a-zA-Z_][^;]*);\s*$',
            reserved_words={'return', 'goto', 'if', 'else', 'while', 'for', 'switch', 'case', 'break', 'continue', 'sizeof'},
            type_parser=linux_type_parser
        )

    def dispatch_profile(self) -> DispatchProfile:
        # # YASHTBD: Implement proper DispatchProfile mapping for Linux dispatch structures
        return DispatchProfile(raw_data=self.dispatch_structures())

    # --- Keep these legacy methods temporarily if older extractors still query them directly ---
    def frontend_rules(self) -> List[TagNormalizerRule]:
        return [
            ACPINormalizer(),
            BPFNormalizer(),
            ModuleNormalizer()
        ]

    def comment_pattern(self) -> re.Pattern:
        """Returns a pre-compiled layout wrapper used to safely strip comments while preserving layout geometry."""
        return re.compile(r'(/\*.*?\*/)|(//.*)', re.DOTALL)

    def clean_source_code(self, source: str) -> str:
        """Slices out comments cleanly while substituting vertical newlines to maintain line synchronization."""
        def replacer(match: re.Match) -> str:
            # Count how many newlines were in the matched comment block
            newline_count = match.group(0).count('\n')
            # Return exactly that many newlines to preserve structural row positions
            return '\n' * newline_count

        return self.comment_pattern().sub(replacer, source)

    def noise_prefixes(self) -> Set[str]:
        return {"tools/", "samples/", "Documentation/"}

    def collection_types(self) -> Set[str]:
        return {"list_head", "hlist_head", "hlist_node", "rb_node"}

    def dispatch_structures(self) -> Set[str]:
        return {"sched_class", "file_operations", "irq_chip", "net_device_ops"}

    def synchronization_primitives(self) -> dict:
        return get_linux_sync_profile()