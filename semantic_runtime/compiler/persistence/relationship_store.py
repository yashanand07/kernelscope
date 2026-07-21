import os
import sqlite3

class RelationshipStore:
    def __init__(self, db_path: str = "ks_cache/relationships.ks"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._conn = None
        self._cursor = None
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS normalized_edges (
                source_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                edge_kind TEXT NOT NULL,
                PRIMARY KEY (source_id, target_id, edge_kind)
            );
        """)
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

    def write_edge(self, source_id: int, target_id: int, kind: str):
        if not self._cursor: raise RuntimeError("Transaction context not active. Call begin().")

        # Safe 64-bit signed mappings
        if source_id >= 0x8000000000000000: source_id -= 0x10000000000000000
        if target_id >= 0x8000000000000000: target_id -= 0x10000000000000000

        self._cursor.execute("""
            INSERT OR IGNORE INTO normalized_edges (source_id, target_id, edge_kind)
            VALUES (?, ?, ?);
        """, (source_id, target_id, kind))