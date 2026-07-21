from enum import Enum, auto

class RelationshipKind(Enum):
    """
    Formal compiler enums representing directed structural edges.
    Maps execution, concurrency, state, and ownership tracking domains.
    """
    # State Interactions
    WRITES = auto()
    READS = auto()
    DATA_FLOW = auto()

    # Concurrency Boundaries
    PROTECTS = auto()
    MATCHES = auto()

    # Execution Tracing
    CALLS = auto()
    TARGETS = auto()

    def to_persistence_str(self) -> str:
        """Returns the uniform string identifier for persistence storage engines."""
        return self.name