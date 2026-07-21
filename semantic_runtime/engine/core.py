# semantic_runtime/engine/core.py

import time
import resource
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from semantic_runtime.main_runner import KernelScopeRunner
from semantic_runtime.drivers.mock_driver import MockDriver
from semantic_runtime.drivers.linux_driver import LinuxDriver
from semantic_runtime.engine.project import Project
from semantic_runtime.engine.types import (
    CompilationResult,
    CompilationMetrics,
    CompilationArtifacts,
    EngineStatus,
)


class KernelScopeEngine:
    """Central domain engine wrapping KernelScope execution pipelines,
    drivers, context stores, and session management.
    """

    def __init__(self, workspace_dir: Optional[Path] = None):
        # Default workspace root is strictly inside KernelScope's working directory
        self.base_workspace_dir = Path(workspace_dir or Path.cwd() / "workspace").resolve()
        self.base_workspace_dir.mkdir(parents=True, exist_ok=True)
        self._is_compiled = False
        self._active_driver = None

    def _resolve_project_workspace(self, project: Optional[Project]) -> Path:
        """Resolves an isolated workspace directory inside KernelScope's local workspace."""
        if project and project.workspace_dir:
            return project.workspace_dir

        # Fall back to project name, source dir name, or default workspace
        if project:
            project_slug = project.name.lower().replace(" ", "_") if project.name else project.source_dir.name
        else:
            project_slug = "default"

        target_dir = self.base_workspace_dir / project_slug
        target_dir.mkdir(parents=True, exist_ok=True)

        if project:
            project.workspace_dir = target_dir

        return target_dir

    def _extract_db_metrics(self, workspace_dir: Path) -> Dict[str, int]:
        """Dynamically inspects created .ks SQLite databases to report exact persisted row counts."""
        metrics = {
            "semantic_nodes": 0,
            "relationships": 0,
            "symbols": 0,
            "files": 0,
        }

        # Targeted database file to table name mappings
        targets = [
            ("semantic_nodes.ks", "semantic_records", "semantic_nodes"),
            ("relationships.ks", "normalized_edges", "relationships"),
            ("symbols.ks", "symbols", "symbols"),
            ("dictionary.ks", "file_registry", "files"),
        ]

        for db_file, table_name, metric_key in targets:
            db_path = workspace_dir / db_file
            if not db_path.exists():
                continue

            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                result = cursor.fetchone()
                if result:
                    metrics[metric_key] = result[0]
                conn.close()
            except Exception:
                pass

        return metrics

    def compile(
        self,
        project: Optional[Project] = None,
        profile: Optional[Any] = None,
        driver: str = "linux",
        chunks_path: str = "chunks.jsonl",
    ) -> CompilationResult:
        """Executes full streaming compilation using the provided Project or fallback Driver."""
        start_time = time.perf_counter()
        cleanup_func = lambda: None

        # 1. Resolve Target Workspace correctly
        target_workspace = self._resolve_project_workspace(project)

        # 2. Resolve project and profile names for telemetry
        project_name = project.name if project else driver

        if project:
            profile_name = project.profile_name
        elif profile:
            profile_name = getattr(profile, "name", "linux")
        else:
            profile_name = "linux"

        runner = KernelScopeRunner(cache_dir=str(target_workspace), verbosity=1)

        try:
            # 3. Driver Selection & Asset Resolution
            if driver == "mock":
                resolved_chunks, symbol_db, cleanup_func = MockDriver.get_chunks_and_db()
            else:
                resolved_chunks, symbol_db, cleanup_func = LinuxDriver.get_chunks_and_db(chunks_path)

            # 4. Run Main Streaming Pipeline
            pipeline_stats = runner.run_pipeline(resolved_chunks, symbol_db)

            # 5. Capture Peak Memory (RUSAGE_SELF in MB)
            peak_rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0

            # 6. Target Artifact Locations
            artifacts = CompilationArtifacts(
                semantic_nodes_db=target_workspace / "semantic_nodes.ks",
                relationships_db=target_workspace / "relationships.ks",
                dictionary_db=target_workspace / "dictionary.ks",
                manifest_json=target_workspace / "manifest.json",
            )

            # 7. Query live database counts from disk
            db_counts = self._extract_db_metrics(target_workspace)

            metrics = CompilationMetrics(
                compile_time_sec=time.perf_counter() - start_time,
                peak_rss_mb=peak_rss_mb,
                semantic_nodes=db_counts["semantic_nodes"] or getattr(pipeline_stats, "total_semantic_objects", 0),
                relationships=db_counts["relationships"],
                symbols=db_counts["symbols"] or getattr(pipeline_stats, "total_symbols", 0),
                files=db_counts["files"] or getattr(pipeline_stats, "chunks_scanned", 0),
            )

            # 8. Save Project manifest if project was supplied
            if project:
                project.save_manifest({
                    "compile_time_sec": metrics.compile_time_sec,
                    "peak_rss_mb": metrics.peak_rss_mb,
                    "metrics": {
                        "semantic_nodes": metrics.semantic_nodes,
                        "relationships": metrics.relationships,
                        "symbols": metrics.symbols,
                        "files": metrics.files,
                    },
                })

            self._is_compiled = True
            self._active_driver = project_name

            return CompilationResult(
                success=True,
                project_name=project_name,
                profile_name=profile_name,
                metrics=metrics,
                artifacts=artifacts,
            )

        except Exception as e:
            metrics = CompilationMetrics(
                compile_time_sec=time.perf_counter() - start_time,
                peak_rss_mb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0,
                semantic_nodes=0,
                relationships=0,
                files=0,
                symbols=0,
            )
            artifacts = CompilationArtifacts(
                semantic_nodes_db=target_workspace / "semantic_nodes.ks",
                relationships_db=target_workspace / "relationships.ks",
                dictionary_db=target_workspace / "dictionary.ks",
                manifest_json=target_workspace / "manifest.json",
            )
            return CompilationResult(
                success=False,
                project_name=project_name,
                profile_name=profile_name,
                metrics=metrics,
                artifacts=artifacts,
                error=str(e),
            )

        finally:
            cleanup_func()

    def status(self) -> EngineStatus:
        return EngineStatus(
            is_compiled=self._is_compiled,
            active_project=self._active_driver,
            cache_dir=self.base_workspace_dir,
        )