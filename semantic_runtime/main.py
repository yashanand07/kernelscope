"""
Main CLI entry point for KernelScope Engine.

Usage:
    python -m semantic_runtime.main --source-dir /home/yash/eternity/linux --name linux-kernel
"""

import argparse
import sys
from pathlib import Path

from semantic_runtime.engine.core import KernelScopeEngine
from semantic_runtime.engine.project import Project


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kernelscope",
        description="KernelScope Semantic Runtime — High-Performance Kernel AST & Symbol Extraction Engine",
    )
    parser.add_argument(
        "--source-dir",
        "-s",
        type=Path,
        required=True,
        help="Path to the target kernel source tree (Read-Only target)",
    )
    parser.add_argument(
        "--name",
        "-n",
        type=str,
        default=None,
        help="Project name identifier (defaults to directory name)",
    )
    parser.add_argument(
        "--workspace",
        "-w",
        type=Path,
        default=None,
        help="Root workspace path (defaults to ./workspace inside KernelScope root)",
    )
    parser.add_argument(
        "--driver",
        "-d",
        type=str,
        choices=["linux", "mock"],
        default="linux",
        help="Execution driver backend ('linux' or 'mock')",
    )
    parser.add_argument(
        "--chunks",
        type=str,
        default="chunks.jsonl",
        help="Path to AST/symbol input chunks file",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    source_dir = args.source_dir.resolve()
    if not source_dir.exists():
        print(f"Error: Source directory does not exist: {source_dir}")
        return 1

    project_name = args.name or source_dir.name

    print("=" * 60)
    print("  KernelScope Engine CLI")
    print("=" * 60)
    print(f" Target Source : {source_dir}")
    print(f" Project Name  : {project_name}")
    print(f" Driver Backend: {args.driver}")
    print("=" * 60 + "\n")

    # 1. Initialize Read-Only Project Model
    project = Project(
        name=project_name,
        source_dir=source_dir,
    )

    # 2. Instantiate Engine (Targeting KernelScope execution root)
    engine = KernelScopeEngine(workspace_dir=args.workspace)

    # 3. Execute Build Pipeline
    print("Initiating KernelScope extraction pipeline...\n")
    result = engine.compile(
        project=project,
        driver=args.driver,
        chunks_path=args.chunks,
    )

    # 4. Telemetry Output
    print("\n" + "=" * 60)
    if result.success:
        print(" Compilation Succeeded!")
        print(f"Output Directory: {result.artifacts.semantic_nodes_db.parent}")
        print("-" * 60)
        print(result.summary())
        return 0
    else:
        print(f"Compilation Failed: {result.error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())