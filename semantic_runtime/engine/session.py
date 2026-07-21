import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional, List
from semantic_runtime.engine.types import CompilationArtifacts


class KernelScopeSession:
    """Active query and exploration session over compiled kernel scope artifacts."""

    def __init__(self, workspace_dir: Path, artifacts: CompilationArtifacts):
        self.workspace_dir = Path(workspace_dir)
        self.artifacts = artifacts
        self._is_active = True

    def query_symbol(self, symbol_name: str) -> List[Dict[str, Any]]:
        """Queries the dictionary/symbol index for symbol definitions."""
        if not self._is_active:
            raise RuntimeError("Session is closed.")

        results = []
        if not self.artifacts.dictionary_db.exists():
            return results

        try:
            conn = sqlite3.connect(f"file:{self.artifacts.dictionary_db}?mode=ro", uri=True)
            cursor = conn.cursor()
            # Expecting interned token table or symbol key lookup
            cursor.execute(
                "SELECT id, token FROM dictionary WHERE token LIKE ? LIMIT 50",
                (f"%{symbol_name}%",),
            )
            rows = cursor.fetchall()
            for row in rows:
                results.append({"token_id": row[0], "symbol": row[1]})
            conn.close()
        except sqlite3.Error:
            pass  # Return empty gracefully if table schema varies

        return results

    def close(self) -> None:
        """Closes any open session handles."""
        self._is_active = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()