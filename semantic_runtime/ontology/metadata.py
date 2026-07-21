from enum import auto
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

class SemanticDomain(Enum):
    SYNCHRONIZATION = "Synchronization"
    ASSIGNMENT = "Assignment"
    STATE = "State"
    DISPATCH = "Dispatch"
    RCU = "RCU"
    CALL = "Call"
    ITERATION = "Iteration"
    # Future expansion: WORKQUEUE, TIMER, IRQ, etc.

class AssignmentKind(Enum):
    LOCAL_VARIABLE = "Local Variable"
    STRUCT_FIELD = "Struct Field"
    ARRAY_ELEMENT = "Array Element"

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
    domain: SemanticDomain

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

@dataclass(slots=True)
class AssignmentMetadata(SemanticMetadata):
    """Ontology Node: Represents an explicit modification to data context state."""
    target_expression: str          # The full LHS of the mutation (e.g., "rq->curr")
    resolved_symbol: Optional[str]   # The extracted root local symbol (e.g., "rq")
    assignment_kind: AssignmentKind  # ◄── Replaces 'mutation_type'
    operator: str

# ---------------------------------------------------------
# Future Semantic Constructs
# ---------------------------------------------------------

#
# class LockMetadata(SemanticMetadata):
#     ...
#
#
# class AssignmentMetadata(SemanticMetadata):
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

@dataclass(slots=True)
class LockAcquireMetadata(SemanticMetadata):
    """Ontology Node: Represents a concurrency boundary entry point."""
    primitive: str
    lock_expression: str
    resolved_symbol: Optional[str] = None  # Holds the identifier string if bound
    irqsave: bool = False
    recursive: bool = False

@dataclass(slots=True)
class LockReleaseMetadata(SemanticMetadata):
    """Ontology Node: Represents a concurrency boundary exit point."""
    primitive: str
    lock_expression: str
    resolved_symbol: Optional[str] = None
    irqrestore: bool = False

@dataclass(slots=True)
class InterruptStateMetadata(SemanticMetadata):
    """Ontology Node: Represents a hardware interrupt constraint boundary."""
    primitive: str
    action: str  # "disable" or "enable"


class RelationshipType(Enum):
    DESCRIBES = "describes"  # Maps a semantic node to a syntactic node on the same line
    CONTAINS  = "contains"   # Maps a scope boundary to its internal operations
    MODIFIES  = "modifies"   # Maps a state mutation to a tracked local/global symbol

@dataclass(slots=True)
class SemanticRelationship:
    """Represents a directed structural edge between two unique Semantic URIs."""
    relationship_type: RelationshipType
    source_id: str  # The origin URI
    target_id: str  # The destination URI

@dataclass(slots=True)
class RcuReadLockMetadata(SemanticMetadata):
    """Ontology Node: Entry point into an execution-protected reader section."""
    api: str

@dataclass(slots=True)
class RcuReadUnlockMetadata(SemanticMetadata):
    """Ontology Node: Exit point from an execution-protected reader section."""
    api: str

@dataclass(slots=True)
class RcuDereferenceMetadata(SemanticMetadata):
    """Ontology Node: Safe lockless pointer acquisition / context load."""
    api: str
    target_expression: str
    resolved_symbol: Optional[str] = None

@dataclass(slots=True)
class RcuPublishMetadata(SemanticMetadata):
    """Ontology Node: Concurrent safe pointer publication / memory barrier allocation."""
    api: str
    target_expression: str
    resolved_symbol: Optional[str] = None

@dataclass(slots=True)
class RcuGracePeriodMetadata(SemanticMetadata):
    """Ontology Node: Synchronous or asynchronous deferred recycling barrier."""
    api: str

@dataclass(slots=True)
class RCUIterationMetadata(SemanticMetadata):
    """Ontology Node: Loops traversing lockless RCU-protected data topologies."""
    api: str
    target_expression: str
    resolved_symbol: Optional[str] = None

class RelationshipType(Enum):
    PROTECTS = auto()     # Concurrency guards (Locks, RCU critical sections)
    CONTAINS = auto()     # Structural loops encapsulating operations
    WRITES = auto()       # Mutation ties back to local symbols
    READS = auto()        # Value lookups tracking identifiers
    DATA_FLOW = auto()    # Chronological register/data dependency steps
    CO_LOCATED = auto()   # Multi-domain overlaps on the same code line

# Relationship definitions and edge types
@dataclass(slots=True)
class SemanticRelationship:
    """Represents a synthesized behavioral or structural dependency graph edge."""
    relationship_id: str
    type: RelationshipType
    source_id: str
    target_id: str