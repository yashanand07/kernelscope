import sqlite3
import os
import time

cache_dir = "ks_cache"
# TARGET SHIFT: Connect directly to the dedicated relationships database
relationships_db = os.path.join(cache_dir, "relationships.ks")

print("[*] Opening decoupled architecture database handles...")
if not os.path.exists(relationships_db):
    print(f"[!] Target not found: {relationships_db}")
    exit(1)

conn = sqlite3.connect(relationships_db)
cursor = conn.cursor()

start_time = time.perf_counter()

# Perform the targeted lookup on the correct file boundary
cursor.execute("SELECT source_id, relationship_type FROM relationships WHERE relationship_type = 'writes' LIMIT 5;")
rows = cursor.fetchall()

end_time = time.perf_counter()

print("\n==================================================")
print(f"Query executed in: {(end_time - start_time) * 1000:.3f} ms")
print("==================================================")
for row in rows:
    print(f"Source: {row[0]:<40} | Type: {row[1]}")
print("==================================================")

conn.close()