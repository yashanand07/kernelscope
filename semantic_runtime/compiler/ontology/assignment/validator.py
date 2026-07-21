from semantic_runtime.compiler.ontology.assignment.metadata import AssignmentMetadata

class AssignmentValidator:
    """Enforces correctness constraints on emitted assignment metadata structures."""
    @staticmethod
    def validate(metadata: AssignmentMetadata) -> bool:
        """Validates structural invariants before data execution."""
        if not metadata.operator:
            return False
        if not metadata.lhs_expression or not metadata.lhs_expression.strip():
            return False
        return True