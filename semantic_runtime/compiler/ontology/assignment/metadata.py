import json
from dataclasses import dataclass
from semantic_runtime.compiler.ontology.base import SemanticMetadata

@dataclass(frozen=True)
class AssignmentMetadata(SemanticMetadata):
    """
    Formal Ontology Contract for Assignment actions.
    Holds exclusively local syntax variables, completely free of spatial metrics.
    """
    operator: str          # e.g., "=", "+="
    assignment_kind: str   # e.g., "direct", "pointer_dereference", "register_write"
    lhs_expression: str
    rhs_expression: str

    @property
    def version(self) -> int:
        return 1

    def to_json_payload(self) -> str:
        return json.dumps({
            "op": self.operator,
            "kind": self.assignment_kind,
            "lhs": self.lhs_expression,
            "rhs": self.rhs_expression
        })