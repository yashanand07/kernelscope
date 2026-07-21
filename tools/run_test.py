from pathlib import Path
from semantic_runtime.engine.core import KernelScopeEngine
from semantic_runtime.engine.project import Project

# 1. Define the project pointing to your read-only Linux source
project = Project(
    name="linux-kernel",
    source_dir=Path("/home/yash/eternity/linux"),
)

# 2. Instantiate engine (defaults base_workspace_dir to ./workspace)
engine = KernelScopeEngine()

# 3. Trigger compilation
print("Starting KernelScope Engine Compilation...")
result = engine.compile(project=project, chunks_path="chunks.jsonl")

# 4. Print summary metrics
print("\n" + "=" * 50)
print(result.summary())
