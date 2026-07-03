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

class SemanticCategory(Enum):
    CONTROL_FLOW    = "CONTROL_FLOW"
    CALL            = "CALL"
    SYNCHRONIZATION = "SYNCHRONIZATION"
    STATE           = "STATE"
    MEMORY          = "MEMORY"
    CONCURRENCY     = "CONCURRENCY"

@dataclass(frozen=True)
class SourceLocation:
    file: str
    line: int
    column: Optional[int] = None

    def __str__(self):
        col_str = f":{self.column}" if self.column is not None else ""
        return f"{self.file}:{self.line}{col_str}"

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
    location: SourceLocation
    source_text: Optional[str] = None

    @property
    def category(self) -> SemanticCategory:
        raise NotImplementedError("Derived metadata classes must declare a category")

# ---------------------------------------------------------
# Collection Traversal Metadata
# ---------------------------------------------------------

@dataclass
class IterationMetadata(SemanticMetadata):
    macro: str = ""
    collection_name: str = ""
    collection_expression: str = ""
    collection_symbol_id: Optional[str] = None
    collection_family: CollectionFamily = CollectionFamily.LINKED_LIST
    collection_type: Optional[str] = None
    declared_by: str = "Unknown"
    element_type: Optional[str] = None
    cursor_variable: str = ""
    member_field: Optional[str] = None
    properties: TraversalProperties = field(default_factory=TraversalProperties)

    # Explicitly satisfy the base class category requirement
    @property
    def category(self) -> SemanticCategory:
        return SemanticCategory.CONTROL_FLOW


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

# ---------------------------------------------------------
# Function Call Metadata
# ---------------------------------------------------------

@dataclass
class CallArgument:
    raw_expression: str
    resolved_symbol_name: Optional[str] = None
    type_name: Optional[str] = None           # e.g., "struct clockdomain"
    pointer_level: int = 0

@dataclass
class CallMetadata(SemanticMetadata):
    target_function: str = ""
    arguments: List[CallArgument] = field(default_factory=list)

    # Explicitly satisfy the base class category requirement
    @property
    def category(self) -> SemanticCategory:
        return SemanticCategory.CALL

