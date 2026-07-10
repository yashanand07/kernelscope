from semantic_runtime.ontology.metadata import TypeKind
from semantic_runtime.ontology.metadata import TypeDescriptor
from typing import Callable
from ast import Dict
from dataclasses import dataclass, field
from typing import Set
import re
from functools import cached_property
from semantic_runtime.ontology.metadata import AssignmentKind

#yashtbd

@dataclass(slots=True)
class CallProfile:
    """Ontology representation of framework call rules and syntactic keywords."""
    call_regex: str
    control_keywords: set[str] = field(default_factory=set)

    pattern: re.Pattern = field(init=False)

    def __post_init__(self):
        """Compiles the target call pattern exactly once upon instantiation."""
        self.pattern = re.compile(self.call_regex)

@dataclass(slots=True)
class IteratorMacroSpec:
    """Defines the position of parameters within a custom iterator macro."""
    cursor_index: int = 0
    collection_index: int = 1
    family: str = "list"      # e.g., "list", "hlist_bl", "rbtree"

@dataclass(slots=True)
class SynchronizationProfile:
    """Ontology representation of concurrency and locking behavior."""
    # # YASHTBD: Migrate SynchronizationExtractor raw dictionary lookup to this profile
    raw_data: dict

@dataclass(slots=True)
class IteratorProfile:
    """Ontology representation of ecosystem custom loop control macros."""
    # Maps macro name to its positional tracking specifications
    specs: dict[str, IteratorMacroSpec] = field(default_factory=dict)

    # Slot field to capture the pre-compiled layout pattern safely
    pattern: re.Pattern = field(init=False)

    def __post_init__(self):
        """Pre-compiles structural loop macro signatures precisely exactly once."""
        tokens = tuple(self.specs.keys())
        if not tokens:
            self.pattern = re.compile(r'(?!_ )')
        else:
            self.pattern = re.compile(r'\b(' + '|'.join(re.escape(t) for t in tokens) + r')\s*\(([^;]*)\)')

@dataclass(slots=True)
class RcuProfile:
    """Ontology representation of Read-Copy-Update behavior."""
    # Use lowercase native sets for perfect slots validation
    read_lock: set[str] = field(default_factory=set)
    read_unlock: set[str] = field(default_factory=set)
    dereference: set[str] = field(default_factory=set)
    publish: set[str] = field(default_factory=set)
    grace_period: set[str] = field(default_factory=set)
    iterators: set[str] = field(default_factory=set)

    pattern: re.Pattern = field(init=False)

    def __post_init__(self):
        """Compiles the monolithic domain parsing regex exactly once upon instantiation."""
        tokens = tuple(
            self.read_lock | 
            self.read_unlock | 
            self.dereference | 
            self.publish | 
            self.grace_period |
            self.iterators
        )
        if not tokens:
            self.pattern = re.compile(r'(?!_ )') 
        else:
            self.pattern = re.compile(r'\b(' + '|'.join(re.escape(t) for t in tokens) + r')\s*\(([^;]*)\)')

@dataclass(slots=True)
class AssignmentProfile:
    """Ontology representation of framework mutations, writes, and atomic updates."""
    base_mutation_regex: str
    atomic_macros: set[str] = field(default_factory=set)

    # Fully qualified functional signature type hint with structural fallback default
    kind_classifier: Callable[[str], AssignmentKind] = field(default=lambda x: AssignmentKind.LOCAL_VARIABLE)

    pattern: re.Pattern = field(init=False)

    def __post_init__(self):
        """Compiles the target pattern exactly once upon instantiation."""
        self.pattern = re.compile(self.base_mutation_regex)

@dataclass(slots=True)
class SymbolProfile:
    """Ontology representation of dialect symbol tables, declarations, and type spaces."""
    decl_regex: str
    reserved_words: set[str] = field(default_factory=set)

    # A dialect delegate function to decode type strings into clear TypeDescriptors
    type_parser: Callable[[str, str], TypeDescriptor] = field(
        default=lambda rt, dec: TypeDescriptor(type_name=rt.strip(), kind=TypeKind.BUILTIN)
    )

    decl_pattern: re.Pattern = field(init=False)

    def __post_init__(self):
        """Pre-compiles the declaration match layout safely."""
        self.decl_pattern = re.compile(self.decl_regex)

@dataclass(slots=True)
class DispatchProfile:
    """Ontology representation of runtime function routing/vtable structures."""
    # # YASHTBD: Define dynamic routing and function pointer table signatures
    raw_data: dict