import os
import sqlite3

class DictionaryStore:
    """
    Manages transactional persistence for the typed global vocabularies.
    Guarantees performance by batching token writes.
    """
    def __init__(self, db_path: str = "ks_cache/dictionary.ks"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._conn = None
        self._cursor = None
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_registry (
                file_id INTEGER PRIMARY KEY AUTOINCREMENT,
                path_string TEXT UNIQUE NOT NULL
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS symbol_registry (
                symbol_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name_string TEXT UNIQUE NOT NULL
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS primitive_registry (
                primitive_id INTEGER PRIMARY KEY AUTOINCREMENT,
                primitive_string TEXT UNIQUE NOT NULL
            );
        """)
        conn.commit()
        conn.close()

    def begin(self):
        """Opens a reusable transaction block for high-volume interning."""
        self._conn = sqlite3.connect(self.db_path)
        self._cursor = self._conn.cursor()
        self._cursor.execute("BEGIN TRANSACTION;")

    def commit(self):
        """Commits the batch modifications down to physical storage."""
        if self._conn:
            self._conn.commit()
            self._conn.close()
            self._conn = None
            self._cursor = None

    def write_file_token(self, path: str) -> int:
        if not self._cursor: raise RuntimeError("Transaction context not active. Call begin().")
        self._cursor.execute("INSERT OR IGNORE INTO file_registry (path_string) VALUES (?);", (path,))
        self._cursor.execute("SELECT file_id FROM file_registry WHERE path_string = ?;", (path,))
        return self._cursor.fetchone()[0]

    def write_symbol_token(self, name: str) -> int:
        if not self._cursor: raise RuntimeError("Transaction context not active. Call begin().")
        self._cursor.execute("INSERT OR IGNORE INTO symbol_registry (name_string) VALUES (?);", (name,))
        self._cursor.execute("SELECT symbol_id FROM symbol_registry WHERE name_string = ?;", (name,))
        return self._cursor.fetchone()[0]

    def write_primitive_token(self, string: str) -> int:
        if not self._cursor: raise RuntimeError("Transaction context not active. Call begin().")
        self._cursor.execute("INSERT OR IGNORE INTO primitive_registry (primitive_string) VALUES (?);", (string,))
        self._cursor.execute("SELECT primitive_id FROM primitive_registry WHERE primitive_string = ?;", (string,))
        return self._cursor.fetchone()[0]