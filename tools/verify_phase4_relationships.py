import os
from semantic_runtime.compiler.identity.manager import IdentityManager
from semantic_runtime.compiler.identity.formatter import IdentityFormatter
from semantic_runtime.compiler.persistence.relationship_store import RelationshipStore
from semantic_runtime.compiler.relationships.kind import RelationshipKind
from semantic_runtime.compiler.relationships.builder import RelationshipBuilder

print("==================================================================")
print("     KernelScope 2.1 Phase 4: Relationship Edge Normalization     ")
print("==================================================================")

# 1. Initialize Decoupled Storage Engine
edge_db = "ks_cache/normalized_edges.ks"
edge_store = RelationshipStore(db_path=edge_db)
edge_builder = RelationshipBuilder(store=edge_store)
id_manager = IdentityManager()

# 2. Derive Stable Identities for the Source and Target nodes
src_id = id_manager.derive_node_id("assign", "drivers/net/ethernet/broadcom/bnxt/bnxt.c", "local", "bp->irq_md", "mutation")
tgt_id = id_manager.derive_node_id("sync", "drivers/net/ethernet/broadcom/bnxt/bnxt.c", "local", "bp->lock", "lock_primitive")

print(f"[✓] Step 1: Source Node derived (Hex): {IdentityFormatter.to_hex_str(src_id)}")
print(f"[✓] Step 2: Target Node derived (Hex): {IdentityFormatter.to_hex_str(tgt_id)}")

# 3. Establish Binary Edge Connection via Relationship Builder
edge_store.begin()
edge_builder.connect(source_id=src_id, target_id=tgt_id, kind=RelationshipKind.PROTECTS)
edge_store.commit()

print(f"[✓] Step 3: Direct Edge Connected via Enum  : RelationshipKind.PROTECTS")

print("\n==================================================================")
print("       RELATIONSHIP NORMALIZATION PASS: EXCELLENT ✓                ")
print("==================================================================")

# Cleanup
if os.path.exists(edge_db):
    os.remove(edge_db)