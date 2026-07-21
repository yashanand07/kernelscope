from dataclasses import dataclass, field
from typing import Set

@dataclass(frozen=True)
class QueryContext:
    """
    Defines the structural boundaries, relationship filters, and constraints
    for an isolated, question-driven engineering session sweep.
    """
    profile_name: str
    allowed_relationships: Set[str]
    max_depth: int = 3
    max_nodes: int = 50