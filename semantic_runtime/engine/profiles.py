"""Compiler profiles encapsulating language & system indexing strategies."""

from abc import ABC, abstractmethod
from pathlib import Path
import os
import subprocess
from typing import Dict, Type

from semantic_runtime.engine.project import Project


class CompilerProfile(ABC):
    """Abstract strategy owning symbol discovery and semantic unit extraction rules."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable display name of the profile."""
        ...

    @abstractmethod
    def discover_symbols(self, project: Project) -> Path:
        """
        Runs symbol indexing (e.g. ctags, tree-sitter, or Clang AST).
        Returns path to the intermediate symbol index file.
        """
        ...

    @abstractmethod
    def extract_semantic_units(self, project: Project, symbol_index_path: Path) -> Path:
        """
        Extracts structural code chunks/semantic units based on discovered symbols.
        Returns path to the generated chunks file (e.g., jsonl).
        """
        ...


class LinuxCompilerProfile(CompilerProfile):
    """Compilation profile tailored for C and C/Assembly kernel source trees."""

    @property
    def name(self) -> str:
        return "Linux Kernel (C/Assembly)"

    def discover_symbols(self, project: Project) -> Path:
        """Discovers C symbols across the source root into intermediate tags."""
        tags_out = project.intermediate_dir / "tags"

        # If pre-existing tags file exists in source root or workspace, reuse or build
        source_tags = project.source_root / "tags"
        if source_tags.exists():
            return source_tags

        # Default fallback to driver symbol indexer
        from semantic_runtime.drivers.linux_driver import LinuxDriver
        driver = LinuxDriver(driver_source_path=str(project.source_root))
        driver.build_symbol_table(output_tags=tags_out)

        return tags_out

    def extract_semantic_units(self, project: Project, symbol_index_path: Path) -> Path:
        """Extracts C code block units into JSONL line chunks."""
        chunks_out = project.intermediate_dir / "chunks.jsonl"

        # If pre-existing chunks file exists in source root or workspace, reuse
        source_chunks = project.source_root / "chunks.jsonl"
        if source_chunks.exists():
            return source_chunks

        from semantic_runtime.drivers.linux_driver import LinuxDriver
        driver = LinuxDriver(driver_source_path=str(project.source_root))
        driver.extract_code_units(tags_path=symbol_index_path, output_chunks=chunks_out)

        return chunks_out


class ProfileRegistry:
    """Registry mapping profile names to their implementation strategy."""

    _registry: Dict[str, Type[CompilerProfile]] = {
        "linux": LinuxCompilerProfile,
    }

    @classmethod
    def get(cls, profile_name: str) -> CompilerProfile:
        if profile_name not in cls._registry:
            raise ValueError(
                f"Unknown compiler profile '{profile_name}'. "
                f"Available profiles: {list(cls._registry.keys())}"
            )
        return cls._registry[profile_name]()

    @classmethod
    def register(cls, name: str, profile_cls: Type[CompilerProfile]) -> None:
        cls._registry[name] = profile_cls