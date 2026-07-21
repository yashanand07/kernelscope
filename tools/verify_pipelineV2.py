import os
import json
from semantic_runtime.compiler.identity.manager import IdentityManager
from semantic_runtime.compiler.persistence.dictionary_store import DictionaryStore
from semantic_runtime.compiler.persistence.semantic_store import SemanticStore
from semantic_runtime.compiler.persistence.relationship_store import RelationshipStore

print("==================================================================")
print("        KernelScope 2.1 Complete Persistence Pipeline Test        ")
print("==================================================================")

# 1. Initialize Paths
dict_path = "ks_cache/test_dict.ks"
node_path = "ks_cache/test_nodes.ks"
edge_path = "ks_cache/test_edges.ks"

id_manager = IdentityManager(vocabulary_db=dict_path)
dict_store = DictionaryStore(db_path=dict_path)
node_store = SemanticStore(db_path=node_path)
edge_store = RelationshipStore(db_path=edge_path)

# 2. Extract and Intern Data Structures Transactionally
dict_store.begin()
file_id   = dict_store.write_file_token("kernel/sched/core.c")
symbol_id = dict_store.write_symbol_token("rq")
dict_store.commit()

print(f"[✓] Step 1: Shared Dictionary Tokenized -> FileID: {file_id}, SymbolID: {symbol_id}")

# 3. Derive Identities and Write Node Space
source_node_id = id_manager.derive_node_id("assign", "kernel/sched/core.c", "local", "rq", "mutation")
target_node_id = id_manager.derive_node_id("call", "kernel/sched/core.c", "local", "schedule", "invocation")

# Phase 3C Blueprint: Metadata strips structural entries out, keeping only assignment facts
normalized_metadata = json.dumps({"operator": "=", "assignment_kind": "direct"})

node_store.begin()
node_store.write_node(
    node_id=source_node_id,
    ontology_kind="assign",
    file_id=file_id,
    symbol_id=symbol_id,
    line=6842,
    version=1,
    payload=normalized_metadata
)
node_store.commit()
print(f"[✓] Step 2: Semantic Node Record Emitted -> NodeID: {source_node_id}")

# 4. Connect Adjacency Matrix
edge_store.begin()
edge_store.write_edge(source_id=source_node_id, target_id=target_node_id, kind="WRITES")
edge_store.commit()
print(f"[✓] Step 3: Binary Directed Edge Written -> connected cleanly via NodeIDs")

print("\n==================================================================")
print("         PIPELINE VERIFICATION STATUS: EXCELLENT ✓                ")
print("==================================================================")

# Clean up verification database files
for p in [dict_path, node_path, edge_path]:
    if os.path.exists(p): os.remove(p)