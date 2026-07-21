import sqlite3
import os

cache_dir = "ks_cache"
target_db = os.path.join(cache_dir, "dictionary.ks")

if not os.path.exists(target_db):
    print(f"[!] Target not found: {target_db}")
    exit(1)

conn = sqlite3.connect(target_db)
cursor = conn.cursor()

print("=== REGISTRY ROW COUNTS ===")
for tbl in ["file_registry", "symbol_registry", "primitive_registry"]:
    cursor.execute(f"SELECT COUNT(*) FROM {tbl};")
    count = cursor.fetchone()[0]
    print(f"  └─ {tbl:20s}: {count:,} rows")

print("\n=== SAMPLE OF REGISTERED SYMBOLS (symbol_registry) ===")
cursor.execute("SELECT symbol_id, name_string FROM symbol_registry LIMIT 25;")
for row in cursor.fetchall():
    print(f"  {row[0]:<8} | {row[1]}")

print("\n=== PATTERN BREAKDOWN (symbol_registry) ===")
cursor.execute("""
    SELECT
        CASE
            WHEN name_string LIKE '%:%' THEN 'CONTAINS_COLON (e.g. file:line/scope)'
            WHEN name_string LIKE '%/%' THEN 'CONTAINS_SLASH (e.g. path string)'
            WHEN name_string LIKE '%(%' THEN 'CONTAINS_PAREN (e.g. signature)'
            WHEN name_string LIKE '% %' THEN 'CONTAINS_SPACE (e.g. full statement)'
            ELSE 'CLEAN_IDENTIFIER'
        END AS pattern_type,
        COUNT(*) as total_count
    FROM symbol_registry
    GROUP BY pattern_type
    ORDER BY total_count DESC;
""")
for row in cursor.fetchall():
    print(f"  └─ {row[0]:42s}: {row[1]:,} rows")

conn.close()