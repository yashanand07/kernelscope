import os
import sqlite3
import json

class CollectionStore:
    """
    Manages global collection registries and macro index mappings.
    Decoupled directly from the monolithic tracking infrastructure.
    """
    def __init__(self, db_path: str = "ks_cache/collections.ks"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._conn = None
        self._cursor = None
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                collection_id TEXT PRIMARY KEY,
                family TEXT,
                raw_descriptor TEXT
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

    def write_collection(self, collection_id: str, family: str, raw_descriptor: str):
        if not self._cursor:
            raise RuntimeError("Transaction context not active. Call begin().")
        self._cursor.execute("""
            INSERT OR REPLACE INTO collections (collection_id, family, raw_descriptor)
            VALUES (?, ?, ?);
        """, (collection_id, family, raw_descriptor))