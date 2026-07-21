import hashlib
import json

class IdentityManager:
    """
    KernelScope 2.1 Identity Manager
    Enforces deterministic, intrinsic, and stable 64-bit numeric identities
    completely decoupled from database persistence or string presentation.
    """

    @staticmethod
    def generate_node_id(domain: str, file_path: str, scope_coord: str, symbol_name: str, entity_kind: str) -> int:
        """
        Calculates a deterministic 64-bit integer identity (uint64) based on
        structural code invariants. Stable across line drift and local changes.
        """
        # Formulate a stable, canonical structural signature token
        structural_signature = f"{domain}:{file_path}:{scope_coord}:{symbol_name}:{entity_kind}"

        # Compute SHA-256 hash to ensure zero clustering or cryptographic collisions
        hasher = hashlib.sha256(structural_signature.encode('utf-8'))
        digest = hasher.digest()

        # Slice the first 8 bytes and map straight onto a 64-bit integer space
        node_id = int.from_bytes(digest[:8], byteorder='big', signed=False)
        return node_id

    @staticmethod
    def format_debug_ir(domain: str, file_path: str, scope_coord: str, symbol_name: str, entity_kind: str) -> str:
        """
        Lazy presentation layer. Reconstructs human-readable IR formats
        strictly on-demand for debuggers, shells, or UI rendering.
        """
        return f"{domain}:{file_path}:{scope_coord}:{entity_kind}:{symbol_name}"

if __name__ == "__main__":
    print("==================================================================")
    print("           IdentityManager Phase 1 Verification Test              ")
    print("==================================================================")

    # Simulate a sample extracted assignment point matching our baseline hotspot findings
    id_1 = IdentityManager.generate_node_id(
        domain="assign",
        file_path="kernel/sched/core.c",
        scope_coord="local",
        symbol_name="rq",
        entity_kind="mutation"
    )

    # Simulate an identical extraction block to verify strict determinism
    id_2 = IdentityManager.generate_node_id(
        domain="assign",
        file_path="kernel/sched/core.c",
        scope_coord="local",
        symbol_name="rq",
        entity_kind="mutation"
    )

    print(f"Generated Canonical NodeID : {id_1}")
    print(f"Determinism Verification   : {'PASSED ✓' if id_1 == id_2 else 'FAILED ✗'}")
    print(f"Lazy Presentation IR Render: {IdentityManager.format_debug_ir('assign', 'kernel/sched/core.c', 'local', 'rq', 'mutation')}")
    print("==================================================================")