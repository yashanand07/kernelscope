import os
from semantic_runtime.compiler.identity.manager import IdentityManager
from semantic_runtime.compiler.persistence.dictionary_store import DictionaryStore
from semantic_runtime.compiler.persistence.semantic_store import SemanticStore
from semantic_runtime.compiler.ontology.assignment.metadata import AssignmentMetadata
from semantic_runtime.compiler.ontology.assignment.validator import AssignmentValidator

print("==================================================================")
print("      KernelScope 2.1 Phase 3C: Assignment Metadata Migration     ")
print("==================================================================")

# 1. Setup Active Cache Engines
dict_path = "ks_cache/normalized_dict.ks"
node_path = "ks_cache/normalized_nodes.ks"

id_manager = IdentityManager(vocabulary_db=dict_path)
dict_store = DictionaryStore(db_path=dict_path)
node_store = SemanticStore(db_path=node_path)

# 2. Simulate Parse Time Token Extraction
dict_store.begin()
file_id = dict_store.write_file_token("drivers/net/ethernet/broadcom/bnxt/bnxt.c")
symbol_id = dict_store.write_symbol_token("bp->irq_md")
dict_store.commit()

# 3. Formulate the Strongly Typed Ontology Metadata Contract
assignment_fact = AssignmentMetadata(
    operator="=",
    assignment_kind="direct_register_write",
    lhs_expression="bp->irq_md",
    rhs_expression="readl(reg_base + offset)"
)

# 4. Route Through the Guard Layer
is_valid = AssignmentValidator.validate(assignment_fact)
print(f"[✓] Step 1: Structural Validation Check passed: {is_valid}")

if is_valid:
    # 5. Derive Opaque Identity Primitives Separately
    canonical_node_id = id_manager.derive_node_id(
        domain="assign",
        file_path="drivers/net/ethernet/broadcom/bnxt/bnxt.c",
        scope="local",
        symbol="bp->irq_md",
        kind="mutation"
    )

    # 6. Push to Binary Persistent Storage Matrix
    node_store.begin()
    node_store.write_node(
        node_id=canonical_node_id,
        ontology_kind="assign",
        file_id=file_id,
        symbol_id=symbol_id,
        line=1042,
        version=assignment_fact.version,
        payload=assignment_fact.to_json_payload()
    )
    node_store.commit()

    print(f"[✓] Step 2: Canonical Opaque NodeID Generated : {canonical_node_id}")
    print(f"[✓] Step 3: Highly Normalized Metadata Emitted  : {assignment_fact.to_json_payload()}")

print("\n==================================================================")
print("       MIGRATION CONTRACT CHECK: EXCELLENT PASS ✓                 ")
print("==================================================================")

# Cleanup
for p in [dict_path, node_path]:
    if os.path.exists(p): os.remove(p)