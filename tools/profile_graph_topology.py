import os
import sqlite3
from collections import Counter

cache_dir = "ks_cache"
rel_db = os.path.join(cache_dir, "relationships.ks")

print("==================================================================")
print("          KernelScope Graph Topology Profiler v1.0                ")
print("==================================================================")

if not os.path.exists(rel_db):
    print(f"[!] Target database not found: {rel_db}")
    exit(1)

conn = sqlite3.connect(rel_db)
cursor = conn.cursor()

# 1. Profile Edge Type Distribution
print("[*] Compiling edge distribution matrix...")
cursor.execute("""
    SELECT relationship_type, COUNT(*)
    FROM relationships
    GROUP BY relationship_type
    ORDER BY COUNT(*) DESC;
""")
edge_dist = cursor.fetchall()

# 2. Compute Out-Degree Metrics across Nodes
print("[*] Computing out-degree network metrics...")
cursor.execute("""
    SELECT source_id, COUNT(*) as out_degree
    FROM relationships
    GROUP BY source_id;
""")
out_degrees = [row[1] for row in cursor.fetchall()]

conn.close()

if not out_degrees:
    print("[!] No relationships found to profile.")
    exit(0)

total_edges = sum(out_degrees)
total_source_nodes = len(out_degrees)
avg_out_degree = total_edges / total_source_nodes
max_out_degree = max(out_degrees)

# Calculate simple percentiles
out_degrees.sort()
p50 = out_degrees[int(total_source_nodes * 0.50)]
p95 = out_degrees[int(total_source_nodes * 0.95)]
p99 = out_degrees[int(total_source_nodes * 0.99)]

print("\n------------------------------------------------------------------")
print("                     EDGE TYPE DISTRIBUTION                       ")
print("------------------------------------------------------------------")
for edge_type, count in edge_dist:
    print(f"    - {edge_type:<25} : {count:,} edges")

print("\n------------------------------------------------------------------")
print("                     GRAPH TOPOLOGY METRICS                       ")
print("------------------------------------------------------------------")
print(f"    Total Graph Directed Edges  : {total_edges:,}")
print(f"    Unique Source Nodes mapped  : {total_source_nodes:,}")
print(f"    Average Out-Degree / Node   : {avg_out_degree:.2f}")
print(f"    Median Out-Degree (P50)     : {p50}")
print(f"    95th Percentile Out-Degree  : {p95}")
print(f"    99th Percentile Out-Degree  : {p99}")
print(f"    Maximum Out-Degree Peak     : {max_out_degree}")
print("==================================================================")