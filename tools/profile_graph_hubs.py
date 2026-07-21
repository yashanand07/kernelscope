import os
import sqlite3

cache_dir = "ks_cache"
rel_db = os.path.join(cache_dir, "relationships.ks")

print("==================================================================")
print("          KernelScope Network Hub & Diagnostics Analyzer         ")
print("==================================================================")

if not os.path.exists(rel_db):
    print(f"[!] Target database not found: {rel_db}")
    exit(1)

conn = sqlite3.connect(rel_db)
cursor = conn.cursor()

print("[*] Sweeping structural nodes to identify core graph hubs...")
cursor.execute("""
    SELECT source_id, COUNT(*) as degree
    FROM relationships
    GROUP BY source_id
    ORDER BY degree DESC
    LIMIT 15;
""")
top_hubs = cursor.fetchall()

print("\n------------------------------------------------------------------")
print("               TOP 15 HIGHEST-DEGREE GRAPH HUBS                   ")
print("------------------------------------------------------------------")
print(f"    {'Rank':<4} | {'Out-Degree':<10} | {'Source Identifier Node String'}")
print("    --------------------------------------------------------------")
for idx, (source, degree) in enumerate(top_hubs, 1):
    print(f"     #{idx:<2} | {degree:<10} | {source}")
print("==================================================================")

conn.close()