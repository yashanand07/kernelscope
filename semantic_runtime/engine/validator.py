import sqlite3
from pathlib import Path
from typing import List
from semantic_runtime.engine.types import CompilationArtifacts, Diagnostic


class ArtifactValidator:
    """Validates structural integrity and schemas of generated KernelScope artifacts."""

    @staticmethod
    def validate_artifacts(artifacts: CompilationArtifacts) -> List[Diagnostic]:
        diagnostics: List[Diagnostic] = []

        # 1. Existence and size check
        for name, path in [
            ("semantic_nodes_db", artifacts.semantic_nodes_db),
            ("relationships_db", artifacts.relationships_db),
            ("dictionary_db", artifacts.dictionary_db),
            ("manifest_json", artifacts.manifest_json),
        ]:
            if not path.exists():
                diagnostics.append(
                    Diagnostic(
                        level="ERROR",
                        message=f"Missing expected artifact: {name} at {path}",
                    )
                )
            elif path.stat().st_size == 0:
                diagnostics.append(
                    Diagnostic(
                        level="WARNING",
                        message=f"Artifact {name} at {path} is empty (0 bytes)",
                    )
                )

        # 2. SQLite integrity checks for .ks / .db files
        db_artifacts = [
            artifacts.semantic_nodes_db,
            artifacts.relationships_db,
            artifacts.dictionary_db,
        ]

        for db_path in db_artifacts:
            if db_path.exists() and db_path.stat().st_size > 0:
                try:
                    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA integrity_check;")
                    result = cursor.fetchone()
                    if not result or result[0] != "ok":
                        diagnostics.append(
                            Diagnostic(
                                level="ERROR",
                                message=f"SQLite integrity check failed for {db_path.name}: {result}",
                            )
                        )
                    conn.close()
                except sqlite3.Error as e:
                    diagnostics.append(
                        Diagnostic(
                            level="ERROR",
                            message=f"Failed to open SQLite database {db_path.name}: {str(e)}",
                        )
                    )

        return diagnostics