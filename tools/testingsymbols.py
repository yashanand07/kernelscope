import sqlite3
from pathlib import Path

symbols_db = Path("workspace/linux-kernel/symbols.ks")

with sqlite3.connect(symbols_db) as conn:
    cur = conn.cursor()

    # 1. Canonical Vocabulary (Unique symbol names like 'spin_lock', 'kfree', 'flags')
    cur.execute("SELECT COUNT(DISTINCT name) FROM symbols")
    print(f"Unique Symbol Names (DISTINCT name): {cur.fetchone()[0]:,}")

    # 2. Total Scoped Symbol Records
    cur.execute("SELECT COUNT(*) FROM symbols")
    print(f"Total Scoped Symbol Records:        {cur.fetchone()[0]:,}")