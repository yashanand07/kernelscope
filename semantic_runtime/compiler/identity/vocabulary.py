import os
import sqlite3

class VocabularyManager:
    """
    Manages typed vocabulary tables inside dictionary.ks.
    Protects type namespaces from contamination.
    Operates transactionally to prevent fsync penalties.
    """
    def __init__(self, db_path: str = "ks_cache/dictionary.ks"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._files = {}
        self._symbols = {}
        self._primitives = {}
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

        #  BOUNDED CACHE FIX: Add LIMIT so we don't load 6 million strings on startup
        cursor.execute("SELECT path_string, file_id FROM file_registry LIMIT 50000;")
        for row in cursor.fetchall(): self._files[row[0]] = row[1]

        cursor.execute("SELECT name_string, symbol_id FROM symbol_registry LIMIT 50000;")
        for row in cursor.fetchall(): self._symbols[row[0]] = row[1]

        cursor.execute("SELECT primitive_string, primitive_id FROM primitive_registry LIMIT 50000;")
        for row in cursor.fetchall(): self._primitives[row[0]] = row[1]

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

    def intern_file(self, path: str) -> int:
        if not path: return 0
        if path in self._files: return self._files[path]
        if not self._cursor: raise RuntimeError("Transaction not active. Call begin().")

        self._cursor.execute("INSERT OR IGNORE INTO file_registry (path_string) VALUES (?);", (path,))
        self._cursor.execute("SELECT file_id FROM file_registry WHERE path_string = ?;", (path,))
        file_id = self._cursor.fetchone()[0]

        # Cap the dictionary size to prevent memory leaks
        if len(self._files) > 50000:
            self._files.clear()

        self._files[path] = file_id
        return file_id

    def intern_symbol(self, name: str) -> int:
        if not name: return 0
        if name in self._symbols: return self._symbols[name]
        if not self._cursor: raise RuntimeError("Transaction not active. Call begin().")

        self._cursor.execute("INSERT OR IGNORE INTO symbol_registry (name_string) VALUES (?);", (name,))
        self._cursor.execute("SELECT symbol_id FROM symbol_registry WHERE name_string = ?;", (name,))
        symbol_id = self._cursor.fetchone()[0]

        #  BOUNDED CACHE FIX: Cap the dictionary size to prevent OOM crashes
        if len(self._symbols) > 50000:
            self._symbols.clear()

        self._symbols[name] = symbol_id
        return symbol_id

    def intern_primitive(self, string: str) -> int:
        if not string: return 0
        if string in self._primitives: return self._primitives[string]
        if not self._cursor: raise RuntimeError("Transaction not active. Call begin().")

        self._cursor.execute("INSERT OR IGNORE INTO primitive_registry (primitive_string) VALUES (?);", (string,))
        self._cursor.execute("SELECT primitive_id FROM primitive_registry WHERE primitive_string = ?;", (string,))
        primitive_id = self._cursor.fetchone()[0]

        # Cap the dictionary size to prevent memory leaks
        if len(self._primitives) > 50000:
            self._primitives.clear()

        self._primitives[string] = primitive_id
        return primitive_id