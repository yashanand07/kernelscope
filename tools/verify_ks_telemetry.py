#!/usr/bin/env python3
"""
verify_ks_telemetry.py (v4)
Extracts distinct function count and total semantic objects.
"""

import sqlite3
from pathlib import Path

WORKSPACE_DIR = Path("./workspace/linux-kernel")
NODES_DB = WORKSPACE_DIR / "semantic_nodes.ks"
SYMBOLS_DB = WORKSPACE_DIR / "symbols.ks"

def verify_distinct_functions():
    print("=" * 60)
    print("      KERNEL SCOPE DISTINCT FUNCTION TELEMETRY TEST      ")
    print("=" * 60)

    # 1. Total Semantic Objects
    if NODES_DB.exists():
        conn_nodes = sqlite3.connect(NODES_DB)
        cur = conn_nodes.cursor()
        cur.execute("SELECT COUNT(*) FROM semantic_records")
        total_nodes = cur.fetchone()[0]
        print(f" Total Semantic Objects : {total_nodes:,}")
        conn_nodes.close()

    # 2. Distinct Functions from symbols.ks
    if SYMBOLS_DB.exists():
        conn_sym = sqlite3.connect(SYMBOLS_DB)
        cur = conn_sym.cursor()

        print("🔍 Scanning symbol keys for distinct function signatures...")

        # Pull symbol keys containing :func:
        cur.execute("SELECT symbol_key FROM symbols WHERE symbol_key LIKE '%:func:%'")

        unique_functions = set()
        total_syms = 0

        for (key,) in cur:
            total_syms += 1
            parts = key.split(":func:")
            if len(parts) > 1:
                # Extract file + function name (e.g., "arch/alpha/boot/bootp.c:find_pa")
                func_signature = parts[1].rsplit(":", 2)[0]
                unique_functions.add(func_signature)

        print(f" Total Symbols Processed : {total_syms:,}")
        print(f"🔥 Unique Functions Count  : {len(unique_functions):,}")

        # Show top 5 unique function signatures
        print("\n--- Sample Unique Functions ---")
        for func in list(unique_functions)[:5]:
            print(f"  * {func}")

        conn_sym.close()

    print("=" * 60)

if __name__ == "__main__":
    verify_distinct_functions()