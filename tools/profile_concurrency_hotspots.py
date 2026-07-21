import os
import sqlite3
from collections import defaultdict

cache_dir = "ks_cache"
rel_db = os.path.join(cache_dir, "relationships.ks")

print("==================================================================")
print("          KernelScope Engineering Analytics: Concurrency          ")
print("==================================================================")

if not os.path.exists(rel_db):
    print(f"[!] Target database not found: {rel_db}")
    exit(1)

conn = sqlite3.connect(rel_db)
cursor = conn.cursor()

# 1. Fetch the absolute top concurrency hubs to pull their full edge maps
print("[*] Slicing sync boundaries to profile critical section mutations...")
cursor.execute("""
    SELECT source_id, target_id
    FROM relationships
    WHERE source_id LIKE 'sync:%' AND relationship_type = 'protects'
    LIMIT 500000;
""")
edges = cursor.fetchall()
conn.close()

if not edges:
    print("[!] No protected critical sections found in the current index layer.")
    exit(0)

# 2. Categorize the targets inside each synchronization context
lock_profiles = defaultdict(lambda: {"assign": 0, "call": 0, "sync": 0, "iter": 0, "other": 0, "total": 0})

for source, target in edges:
    profiles = lock_profiles[source]
    profiles["total"] += 1

    # Parse the target's semantic domain from its string signature
    if ":" in target:
        domain = target.split(":")[0]
        if domain in profiles:
            profiles[domain] += 1
        else:
            profiles["other"] += 1
    else:
        profiles["other"] += 1

# 3. Sort by total density to expose the heaviest engineering hot-spots
sorted_hotspots = sorted(lock_profiles.items(), key=lambda x: x[1]["total"], reverse=True)

print("\n------------------------------------------------------------------")
print("                CONCURRENCY COMPLEXITY REPORT                     ")
print("------------------------------------------------------------------")
print(f"    {'Rank':<4} | {'Total Ops':<9} | {'Mutations (Assign/Call)':<24} | {'File Location'}")
print("    --------------------------------------------------------------")

for idx, (lock_node, metrics) in enumerate(sorted_hotspots[:10], 1):
    # Extract clean file path and lock type for human reading
    parts = lock_node.split(":")
    file_info = parts[1] if len(parts) > 1 else "unknown"
    line_info = parts[2] if len(parts) > 2 else ""
    lock_primitive = parts[-1] if len(parts) > 0 else "lock"

    mutation_ratio = f"{metrics['assign']} assigns / {metrics['call']} calls"
    location_str = f"{file_info}:{line_info} ({lock_primitive})"

    print(f"     #{idx:<2} | {metrics['total']:<9} | {mutation_ratio:<24} | {location_str}")
print("==================================================================")