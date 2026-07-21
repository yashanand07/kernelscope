import os
import sqlite3

class SemanticStore:
    """
    Manages persistence for immutable normalized semantic records.
    Operates strictly on fixed-width uint64/uint32 binary coordinates.
    """
    def __init__(self, db_path: str = "ks_cache/semantic_nodes.ks"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._conn = None
        self._cursor = None
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS semantic_records (
                node_id INTEGER PRIMARY KEY,
                ontology_kind TEXT NOT NULL,
                file_id INTEGER NOT NULL,
                symbol_id INTEGER NOT NULL,
                line_number INTEGER NOT NULL,
                metadata_version INTEGER NOT NULL,
                metadata_payload TEXT NOT NULL
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

    def write_node(self, node_id: int, ontology_kind: str, file_id: int, symbol_id: int, line: int, version: int, payload: str):
        if not self._cursor: raise RuntimeError("Transaction context not active. Call begin().")

        # Enforce strict 64-bit signed conversion to eliminate OverflowError
        if node_id >= 0x8000000000000000:
            node_id -= 0x10000000000000000

        self._cursor.execute("""
            INSERT OR REPLACE INTO semantic_records
            (node_id, ontology_kind, file_id, symbol_id, line_number, metadata_version, metadata_payload)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (node_id, ontology_kind, file_id, symbol_id, line, version, payload))