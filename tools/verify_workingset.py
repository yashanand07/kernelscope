import sqlite3
import time
from semantic_runtime.compiler.persistence_store import PersistenceStore

def run_diagnostic():
    print("Connecting to Tier 1 Storage Layer...")
    conn = sqlite3.connect("ks_cache/graph.ks")
    cursor = conn.cursor()

    # Discovery Step: Query for an edge type that we KNOW exists from the sample dump
    cursor.execute("SELECT source_id, relationship_type FROM relationships WHERE relationship_type = 'writes' LIMIT 1;")
    sample_row = cursor.fetchone()
    conn.close()

    if not sample_row:
        print("\n[!] Error: No relational edges found in the database. Run compiler pipeline first.")
        return

    target_sample_id = sample_row[0]
    print(f"Targeting Real Interned Statement Node ID: {target_sample_id}")

    store = PersistenceStore(cache_dir="ks_cache")
    t_start = time.perf_counter()

    # Query the database for the active working set of this specific statement
    working_set = store.fetch_localized_working_set(
        source_node_id=target_sample_id,
        allowed_types=["writes", "describes", "matches", "protects"]
    )
    t_duration_ms = (time.perf_counter() - t_start) * 1000.0

    print("\n==================================================")
    print("     LAW 6 VERIFIED LOCALIZED WORKING SET LAYER   ")
    print("==================================================")
    print(f"Active Query Latency : {t_duration_ms:.3f} ms")
    print(f"Materialized Nodes   : {len(working_set)}")
    print("==================================================")

    for idx, edge in enumerate(working_set, 1):
        print(f"\n[{idx}] Edge Type: {edge['relationship_type'].upper()}")
        print(f"    └── Source: {target_sample_id}")
        print(f"    └── Target: {edge['target_id']}")
        print(f"    └── Domain: {edge['target_domain']}")
        print(f"    └── Facts : {edge['metadata']}")

    store.close()

if __name__ == "__main__":
    run_diagnostic()