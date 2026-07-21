import os
import sqlite3

cache_dir = "ks_cache"
nodes_db = os.path.join(cache_dir, "semantic_nodes.ks")

print("==================================================================")
print("          KernelScope Global Vocabulary Profiler v2.1             ")
print("==================================================================")

if not os.path.exists(nodes_db):
    print(f"[!] Target database not found: {nodes_db}")
    exit(1)

conn = sqlite3.connect(nodes_db)
cursor = conn.cursor()

# 1. Gather exact reference counts across the global dataset
print("[*] Computing total dataset references and identifier costs...")
cursor.execute("""
    SELECT
        COUNT(*),
        COUNT(DISTINCT file_path),
        SUM(LENGTH(file_path)),
        SUM(LENGTH(semantic_id)),
        SUM(LENGTH(domain))
    FROM semantic_nodes;
""")
total_nodes, unique_paths, total_path_bytes, total_id_bytes, total_domain_bytes = cursor.fetchone()

# 2. Extract Top 3 high-frequency offenders for the engineering report
cursor.execute("""
    SELECT file_path, COUNT(*) as occurrences
    FROM semantic_nodes
    GROUP BY file_path
    ORDER BY occurrences DESC
    LIMIT 3;
""")
top_paths = cursor.fetchall()
conn.close()

# 3. Calculate Math-Checked Savings (Variable String vs. Fixed 8-byte uint64 ID)
# Moving file_path to uint64 ID (8 bytes per reference)
current_path_mb = total_path_bytes / (1024 * 1024)
vocabulary_path_mb = (total_nodes * 8) / (1024 * 1024)
net_path_savings_mb = current_path_mb - vocabulary_path_mb

# Moving semantic_id to uint64 NodeID (8 bytes per reference)
current_id_mb = total_id_bytes / (1024 * 1024)
vocabulary_id_mb = (total_nodes * 8) / (1024 * 1024)
net_id_savings_mb = current_id_mb - vocabulary_id_mb

# Moving domain string to uint8 Enum ID (1 byte per reference)
current_domain_mb = total_domain_bytes / (1024 * 1024)
vocabulary_domain_mb = (total_nodes * 1) / (1024 * 1024)
net_domain_savings_mb = current_domain_mb - vocabulary_domain_mb

total_savings_mb = net_path_savings_mb + net_id_savings_mb + net_domain_savings_mb
current_physical_gb = 5.11

print("\n------------------------------------------------------------------")
print("                     STRING INTERNING REPORT                      ")
print("------------------------------------------------------------------")
print(f"    Total Processed References : {total_nodes:,}")
print(f"    Unique File Paths Indexed  : {unique_paths:,}")
print(f"    Average References / Path  : {int(total_nodes / max(1, unique_paths))}")
print(f"    Top High-Density Files     :")
for path, count in top_paths:
    print(f"      • {path:<40} : {count:,} references")

print("\n------------------------------------------------------------------")
print("                   VOCABULARY SAVINGS ANALYSIS                    ")
print("------------------------------------------------------------------")
print(f"    Current Path String Cost   : {current_path_mb:.1f} MB")
print(f"    Vocabulary Path ID Cost    : {vocabulary_path_mb:.1f} MB")
print(f"    [+] Net Path Savings       : {net_path_savings_mb:.1f} MB")
print(f"    ----------------------------------------------------------")
print(f"    Current Raw Identity Cost  : {current_id_mb:.1f} MB")
print(f"    Vocabulary Node ID Cost    : {vocabulary_id_mb:.1f} MB")
print(f"    [+] Net Identity Savings   : {net_id_savings_mb:.1f} MB")
print(f"    ----------------------------------------------------------")
print(f"    [+] Net Domain Enum Savings: {net_domain_savings_mb:.1f} MB")

print("\n------------------------------------------------------------------")
print("                     FINAL TARGET PROJECTIONS                     ")
print("------------------------------------------------------------------")
print(f"    Total Structural Savings   : {total_savings_mb:.1f} MB")
print(f"    Target Optimized Store     : {(current_physical_gb - (total_savings_mb / 1024)):.2f} GB")
print("==================================================================")