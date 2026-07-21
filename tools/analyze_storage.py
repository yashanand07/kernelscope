import os
import sqlite3
from collections import Counter

cache_dir = "ks_cache"
nodes_db = os.path.join(cache_dir, "semantic_nodes.ks")

print("==================================================")
print("       KernelScope Storage Profiler v1.2         ")
print("==================================================")

if not os.path.exists(nodes_db):
    print(f"[!] Target database not found: {nodes_db}")
    exit(1)

conn = sqlite3.connect(nodes_db)
cursor = conn.cursor()

# 1. Discover the exact table name dynamically
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
if not tables:
    print("[!] Error: No tables found inside semantic_nodes.ks.")
    conn.close()
    exit(1)

table_name = tables[0][0]
print(f"[*] Found active storage boundary table: [{table_name}]")

# 2. Discover columns inside this table dynamically
cursor.execute(f"PRAGMA table_info({table_name});")
columns = [info[1] for info in cursor.fetchall()]
print(f"[*] Detected columns: {columns}")

# Fallback column resolution matching typical patterns
id_col = next((c for c in columns if "id" in c or "key" in c or "name" in c), columns[0])
meta_col = next((c for c in columns if "meta" in c or "json" in c or "data" in c), None)

print(f"[*] Selecting Identifier column: [{id_col}]")
if meta_col:
    print(f"[*] Selecting Data Payload column: [{meta_col}]")

# 3. Execute the diagnostic sweep profiling records
print("[*] Slicing string matrices to capture repetition indices...")
query = f"SELECT {id_col} " + (f", {meta_col}" if meta_col else "") + f" FROM {table_name} LIMIT 100000;"
cursor.execute(query)
rows = cursor.fetchall()

total_records = len(rows)
path_counter = Counter()
domain_counter = Counter()
total_string_bytes = 0

for row in rows:
    sem_id = row[0]
    total_string_bytes += len(sem_id)
    if meta_col and row[1]:
        total_string_bytes += len(row[1])

    # Isolate repeated file system path tokens
    if ":" in sem_id:
        parts = sem_id.split(":")
        domain_counter[parts[0]] += 1
        for p in parts:
            if "/" in p or ".c" in p or ".h" in p:
                path_counter[p] += 1

conn.close()

print("\n==================================================")
print(f"    Total Sampled Nodes    : {total_records:,}")
print(f"    Avg Memory Per Record  : {total_string_bytes / max(1, total_records):.1f} bytes")
print("--------------------------------------------------")
print("Top Repeated File/Path Tokens in Identifiers:")
for path, count in path_counter.most_common(5):
    print(f"    - {path:<35} : {count:,} hits")
    
print("\nTop Semantic Domain Distributions:")
for domain, count in domain_counter.most_common(5):
    print(f"    - {domain:<35} : {count:,} hits")
print("==================================================")