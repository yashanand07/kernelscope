import json
import os
import time
from typing import List, Dict, Any, Optional

def ks_json_encoder(obj):
    if hasattr(obj, '__dataclass_fields__'):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
    if hasattr(obj, 'value'):
        return obj.value
    return str(obj)

class PersistenceStoreV2:
    """
    Persistence Store v2: Lean telemetry wrapper.
    All concrete index database streams have been fully delegated to decoupled subsystem stores.
    """
    def __init__(self, cache_dir: str = "ks_cache"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

        # Track layout filenames exclusively for structural sizing measurements
        self.files = {
            "nodes": os.path.join(self.cache_dir, "semantic_nodes.ks"),
            "relationships": os.path.join(self.cache_dir, "relationships.ks"),
            "symbols": os.path.join(self.cache_dir, "symbols.ks"),
            "collections": os.path.join(self.cache_dir, "collections.ks"),
        }

        # Operational runtime telemetry counters
        self.counts = {
            "functions": 0,
            "semantic_nodes": 0,
            "relationships": 0,
            "symbols": 0,
            "collections": 0
        }

    def connect(self):
        """No-op: Database management delegated to specialized subsystem classes."""
        pass

    def persist_compiled_context(self, context) -> int:
        """Telemetry interceptor: Increments counters to maintain manifest tracking accuracy."""
        self.counts["functions"] += 1

        # Update metrics tracking based on processed arrays
        num_nodes = len(context.semantic_constructs) if hasattr(context, 'semantic_constructs') else 0
        num_rels = len(context.relationships) if hasattr(context, 'relationships') else 0

        self.counts["semantic_nodes"] += num_nodes
        self.counts["relationships"] += num_rels

        # Calculate approximate symbol metrics safely
        if hasattr(context, 'local_symbols'):
            for sym_list in context.local_symbols.values():
                self.counts["symbols"] += len(sym_list)

        return num_nodes + num_rels

    def persist_global_indices(self, indices):
        """Telemetry interceptor: Increments metrics for global collection tracking."""
        collection_source = []
        if hasattr(indices.collections, 'all'):
            res = indices.collections.all()
            collection_source = res.values() if hasattr(res, 'values') else res
        elif hasattr(indices.collections, '__iter__'):
            collection_source = indices.collections

        self.counts["collections"] += len(collection_source)

    def generate_manifest(self, runtime_seconds: float):
        """Assembles the final structural tracking manifest validation layout on disk."""
        manifest_path = os.path.join(self.cache_dir, "manifest.json")

        artifact_sizes = {}
        for name, path in self.files.items():
            if os.path.exists(path):
                artifact_sizes[f"{name}.ks"] = f"{os.path.getsize(path) / (1024*1024):.2f} MB"

        manifest_data = {
            "compiler_version": "2.0",
            "schema_version": 3,
            "compiled_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_compilation_time_s": round(runtime_seconds, 2),
            "metrics": self.counts,
            "artifacts_physical_size": artifact_sizes
        }

        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f, indent=2)

    def close(self):
        """No-op connection closure handler."""
        pass