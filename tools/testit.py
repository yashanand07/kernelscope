import sqlite3
from pathlib import Path

symbols_db = Path("workspace/linux-kernel/symbols.ks")

if not symbols_db.exists():
    print(f"Could not find {symbols_db}")
    exit(1)

with sqlite3.connect(symbols_db) as conn:
    cur = conn.cursor()

    # 1. Inspect table structure
    cur.execute("PRAGMA table_info(symbols)")
    columns = [row[1] for row in cur.fetchall()]
    print(f"📊 Columns in 'symbols' table: {columns}\n")

    # 2. Total Row Count
    cur.execute("SELECT COUNT(*) FROM symbols")
    total_rows = cur.fetchone()[0]
    print(f"Total Symbol Records (COUNT *):        {total_rows:,}")

    # 3. Canonical Count using detected column
    name_col = next((col for col in ['symbol_key', 'name', 'key'] if col in columns), None)

    if name_col:
        cur.execute(f"SELECT COUNT(DISTINCT {name_col}) FROM symbols")
        distinct_count = cur.fetchone()[0]
        print(f"Distinct Symbol Names (DISTINCT {name_col}): {distinct_count:,}")
    else:
        print("⚠️ Could not auto-detect a name column for distinct count.")