import sqlite3

conn = sqlite3.connect("ks_cache/graph.ks")
cursor = conn.cursor()

print("=== Edge Samples in Database ===")
cursor.execute("SELECT relationship_type, source_id, target_id FROM relationships LIMIT 10;")
rows = cursor.fetchall()
if not rows:
    print("The relationships table is entirely empty! Check your compiler execution pipeline.")
for row in rows:
    print(f"Type: {row[0]!r} | Src: {row[1]!r} | Tgt: {row[2]!r}")

print("\n=== Unique Node Domains ===")
cursor.execute("SELECT DISTINCT domain FROM semantic_nodes;")
for row in cursor.fetchall():
    print(f"Domain: {row[0]}")

conn.close()