from dataclasses import dataclass

#yashtbd

@dataclass(slots=True)
class SynchronizationProfile:
    """Ontology representation of concurrency and locking behavior."""
    # # YASHTBD: Migrate SynchronizationExtractor raw dictionary lookup to this profile
    raw_data: dict

@dataclass(slots=True)
class IteratorProfile:
    """Ontology representation of framework custom control loop macros."""
    # # YASHTBD: Migrate IteratorExtractor configuration parsing to this profile
    raw_data: dict

@dataclass(slots=True)
class RcuProfile:
    """Ontology representation of Read-Copy-Update boundary primitives."""
    # # YASHTBD: Define RCU read-side critical section and dereference markers
    raw_data: dict

@dataclass(slots=True)
class AssignmentProfile:
    """Ontology representation of target structural mutation qualifiers."""
    # # YASHTBD: Define global variable and atomic update classification rules
    raw_data: dict

@dataclass(slots=True)
class DispatchProfile:
    """Ontology representation of runtime function routing/vtable structures."""
    # # YASHTBD: Define dynamic routing and function pointer table signatures
    raw_data: dict