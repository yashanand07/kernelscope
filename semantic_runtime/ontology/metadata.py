from typing import Optional
from re import Pattern
from enum import Enum
import re
from dataclasses import dataclass, field
from typing import List

class CollectionFamily(Enum):
    LINKED_LIST = "linked_list"
    HASH_TABLE  = "hash_table"
    RBTREE      = "rbtree"
    XARRAY      = "xarray"
    IDR         = "idr"
    BITMAP      = "bitmap"
    CPU_MASK    = "cpu_mask"

    # --- Future additions are just one line ---
    RADIX_TREE  = "radix_tree"
    MAPLE_TREE  = "maple_tree"
    B_TREE      = "b_tree"

class TypeKind(Enum):
    STRUCT = "struct"
    BUILTIN = "builtin"
    ENUM = "enum"
    UNION = "union"
    TYPEDEF = "typedef"

class StorageClass(Enum):
    PARAMETER = "parameter"
    LOCAL = "local"
    STATIC = "static"
    GLOBAL = "global"


@dataclass
class ExtractionReport:
    """Standardized telemetry returned by every Semantic Extractor."""
    extractor_name: str
    discovered: int = 0
    warnings: List[str] = field(default_factory=list)
    duration_ms: float = 0.0
    skipped: int = 0

@dataclass
class CollectionPattern:
    """Defines a regex pattern and its semantic meaning for Phase 0 discovery."""
    regex: Pattern
    family: CollectionFamily        # e.g., "linked_list", "rbtree"
    type_name: str                  # e.g., "struct list_head"
    macro_name: str                 # e.g., "LIST_HEAD"


@dataclass
class TypeDescriptor:
    type_name: str              # "task_struct", "unsigned long"
    kind: TypeKind              # STRUCT, BUILTIN, ENUM, UNION, TYPEDEF
    qualifiers: List[str]       # const, volatile, restrict
    pointer_level: int          # 0, 1, 2, ...



# ---------------------------------------------------------
# Traversal Properties
# ---------------------------------------------------------

@dataclass
class TraversalProperties:

    deletion_safe: bool = False

    reverse: bool = False

    rcu_protected: bool = False

    continue_iteration: bool = False


# ---------------------------------------------------------
# Base Semantic Metadata
#
# Every semantic construct derives from this.
# ---------------------------------------------------------

@dataclass(kw_only=True)
class SemanticMetadata:

    semantic_id: str

    source_line: Optional[int] = None

    source_text: Optional[str] = None   # only emit it in debug/validation builds


# ---------------------------------------------------------
# Collection Traversal Metadata
# ---------------------------------------------------------

@dataclass
class IterationMetadata(SemanticMetadata):

    #
    # Original syntax
    #

    macro: str = ""
    # list_for_each_entry

    #
    # Collection
    #

    collection_name: str = ""
    # clkdm_list

    collection_expression: str = ""
    # &clkdm_list
    # adapter->rx_ring_list

    collection_symbol_id: Optional[str] = None

    collection_family: CollectionFamily = CollectionFamily.LINKED_LIST
    # linked_list
    # hash_table
    # bitmap

    collection_type: Optional[str] = None
    # struct list_head

    #
    # Elements
    #

    element_type: Optional[str] = None
    # struct clockdomain

    cursor_variable: str = ""
    # temp_clkdm

    member_field: Optional[str] = None
    # node

    #
    # Traversal semantics
    #

    properties: TraversalProperties = field(
        default_factory=TraversalProperties
    )


# ---------------------------------------------------------
# Future Semantic Constructs
# ---------------------------------------------------------

#
# class LockMetadata(SemanticMetadata):
#     ...
#
#
# class StateMutationMetadata(SemanticMetadata):
#     ...
#
#
# class ConfigBranchMetadata(SemanticMetadata):
#     ...
#
#
# class WaitQueueMetadata(SemanticMetadata):
#     ...
#
#
# class WorkqueueMetadata(SemanticMetadata):
#     ...
#
#
# class TimerMetadata(SemanticMetadata):
#     ...
#
#
# class InterruptMetadata(SemanticMetadata):
#     ...
