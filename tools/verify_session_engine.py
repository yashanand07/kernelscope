import os
import json
from semantic_runtime.compiler.identity.manager import IdentityManager
from semantic_runtime.compiler.persistence.relationship_store import RelationshipStore
from semantic_runtime.compiler.working_set.query_context import QueryContext
from semantic_runtime.compiler.working_set.coordinator import WorkingSetCoordinator

print("==================================================================")
print("     KernelScope 2.1 Phase 5: Engineering Session Engine Test     ")
print("==================================================================")

# 1. Initialize DB Pathways
edge_db = "ks_cache/session_edges.ks"
dict_db = "ks_cache/session_dict.ks"

edge_store = RelationshipStore(db_path=edge_db)
id_manager = IdentityManager(vocabulary_db=dict_db)

# 2. Derive Opaque Node Coordinates
src_id  = id_manager.derive_node_id("assign", "kernel/sched/core.c", "local", "rq", "mutation")
lock_id = id_manager.derive_node_id("sync", "kernel/sched/core.c", "local", "rq->lock", "lock_primitive")
unrelated_id = id_manager.derive_node_id("call", "kernel/sched/core.c", "local", "printk", "logging")

# 3. Populate Active Binary Adjacency Index
edge_store.begin()
edge_store.write_edge(src_id, lock_id, "PROTECTS")
edge_store.write_edge(src_id, unrelated_id, "DATA_FLOW") # Should be filtered out by the session profile!
edge_store.commit()

# 4. Construct an Active Cognitive Question Profile Matrix
concurrency_question = QueryContext(
    profile_name="CONCURRENCY_BOUNDARY_SCAN",
    allowed_relationships={"PROTECTS", "MATCHES"},
    max_depth=2
)

# 5. Spin up the Coordinator and Fire the Investigation Session
session_engine = WorkingSetCoordinator(dict_db=dict_db, edge_db=edge_db)
engineering_context = session_engine.execute_session(target_node_id=src_id, context=concurrency_question)

print("[✓] Session execution complete.")
print("\n------------------------------------------------------------------")
print("               LOCALIZED ENGINEERING CONTEXT                      ")
print("------------------------------------------------------------------")
print(json.dumps(engineering_context, indent=2))
print("==================================================================")

# Cleanup
for p in [edge_db, dict_db]:
    if os.path.exists(p): os.remove(p)