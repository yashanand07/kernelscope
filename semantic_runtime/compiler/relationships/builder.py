from semantic_runtime.compiler.relationships.kind import RelationshipKind
from semantic_runtime.compiler.persistence.relationship_store import RelationshipStore

class RelationshipBuilder:
    """
    Coordinates edge construction across the compiler substrate.
    Enforces strict numeric linkage, completely free of textual layout variables.
    """
    def __init__(self, store: RelationshipStore):
        self.store = store

    def connect(self, source_id: int, target_id: int, kind: RelationshipKind):
        """Routes a verified binary structural link down to the persistence substrate."""
        # Enforce structural tracking invariants
        if not source_id or not target_id:
            raise ValueError("Edge connections require valid non-zero NodeID coordinates.")

        # Write the edge using the normalized string representation of the enum
        self.store.write_edge(
            source_id=source_id,
            target_id=target_id,
            kind=kind.to_persistence_str()
        )