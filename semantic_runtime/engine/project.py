"""Project domain model for KernelScope Engine."""

from dataclasses import dataclass, field
from pathlib import Path
import json
from typing import Dict, Any, Optional


@dataclass
class Project:
    name: str
    source_dir: Path
    workspace_dir: Optional[Path] = None
    profile_name: str = "linux"
    config: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.source_dir = Path(self.source_dir).resolve()
        if self.workspace_dir:
            self.workspace_dir = Path(self.workspace_dir).resolve()

    @property
    def intermediate_dir(self) -> Path:
        """Directory for ephemeral artifacts (ctags, raw chunks, etc.)."""
        if not self.workspace_dir:
            raise ValueError("workspace_dir must be resolved before accessing intermediate_dir")
        path = self.workspace_dir / "intermediate"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def manifest_path(self) -> Path:
        if not self.workspace_dir:
            raise ValueError("workspace_dir must be resolved before accessing manifest_path")
        return self.workspace_dir / "manifest.json"

    def save_manifest(self, metadata: Dict[str, Any]) -> None:
        """Persists project metadata to project root workspace."""
        payload = {
            "name": self.name,
            "source_dir": str(self.source_dir),
            "profile_name": self.profile_name,
            "config": self.config,
            **metadata,
        }
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    @classmethod
    def load(cls, workspace_dir: Path) -> "Project":
        """Loads an existing project configuration from a workspace directory."""
        workspace = Path(workspace_dir).resolve()
        manifest_file = workspace / "manifest.json"

        if not manifest_file.exists():
            raise FileNotFoundError(f"No KernelScope project found at {workspace}")

        with open(manifest_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls(
            name=data.get("name", workspace.name),
            source_dir=Path(data["source_dir"]),
            workspace_dir=workspace,
            profile_name=data.get("profile_name", "linux"),
            config=data.get("config", {}),
        )