import os
import sqlite3

class SymbolStore:
    """
    Manages local variable registrations and function argument metadata mappings.
    Optimized to use normalized vocabulary integer identifiers.
    """
    def __init__(self, db_path: str = "ks_cache/symbols.ks"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._conn = None
        self._cursor = None
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 🔄 MIGRATION: Shift text specifications into optimized INTEGER IDs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS symbols (
                symbol_key TEXT PRIMARY KEY,
                name TEXT,
                type TEXT,
                scope_id INTEGER,
                file_id INTEGER
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sym_lookup ON symbols(name, scope_id);")
        conn.commit()
        conn.close()

    def begin(self):
        self._conn = sqlite3.connect(self.db_path)
        self._cursor = self._conn.cursor()
        self._cursor.execute("BEGIN TRANSACTION;")

    def commit(self):
        if self._conn:
            self._conn.commit()
            self._conn.close()
            self._conn = None
            self._cursor = None

    def write_symbol(self, symbol_key: str, name: str, type_str: str, scope_id: int, file_id: int):
        if not self._cursor:
            raise RuntimeError("Transaction context not active. Call begin().")

        self._cursor.execute("""
            INSERT OR REPLACE INTO symbols (symbol_key, name, type, scope_id, file_id)
            VALUES (?, ?, ?, ?, ?);
        """, (symbol_key, name, type_str, scope_id, file_id))