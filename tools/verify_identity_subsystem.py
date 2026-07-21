import os
from semantic_runtime.compiler.identity.manager import IdentityManager

print("==================================================================")
print("         KernelScope 2.1 Identity Subsystem Integration Test      ")
print("==================================================================")

# Target a dedicated validation vocabulary instance
db_path = "ks_cache/integration_test_dict.ks"
manager = IdentityManager(vocabulary_db=db_path)

# 1. Test Façade Canonical Identity Derivation
node_id = manager.derive_node_id("assign", "kernel/sched/core.c", "local", "rq", "mutation")
print(f"[✓] Derived Deterministic NodeID : {node_id}")

# 2. Test Vocabulary Namespace Segregation
file_id = manager.intern_file("kernel/sched/core.c")
sym_id  = manager.intern_symbol("rq")
prim_id = manager.intern_primitive("spin_lock_irqsave")

print(f"[✓] Vocabulary Isolation Metrics : FileID: {file_id} | SymbolID: {sym_id} | PrimitiveID: {prim_id}")

# 3. Test Lazy Presentation Evaluation
debug_render = manager.format_debug_ir("assign", "kernel/sched/core.c", "local", "mutation", "rq")
print(f"[✓] Lazy Formatting IR Engine  : {debug_render}")
print("==================================================================")

# Cleanup
if os.path.exists(db_path):
    os.remove(db_path)