import time
import json
import sqlite3
import os

from semantic_runtime.main_runner import KernelScopeRunner
from semantic_runtime.compiler.identity.identity_manager import IdentityManager
from adaptation.linux.kit import LinuxAdaptationKit
from semantic_runtime.compiler.semantic_ir import SemanticCompiler
from semantic_runtime.compiler.persistence.semantic_store import SemanticStore


class ProfilingKernelScopeRunner(KernelScopeRunner):
    def run_pipeline(self, chunks_jsonl_path: str, symbol_db: dict):
        LIMIT_CHUNKS = 3000
        print(f"[*] Profiling first {LIMIT_CHUNKS} chunks to isolate runtime overhead...")

        functions_to_compile = []
        with open(chunks_jsonl_path, 'r') as f:
            for idx, line in enumerate(f):
                if idx >= LIMIT_CHUNKS: break
                if not line.strip(): continue
                chunk = json.loads(line)
                if "symbol_id" not in chunk and "symbol" in chunk:
                    chunk["symbol_id"] = f"func:{chunk['file']}:{chunk['symbol']}"
                functions_to_compile.append(chunk)



        class MockIndices: collections = {}
        indices = MockIndices()

        kit = LinuxAdaptationKit()
        semantic_compiler = SemanticCompiler(indices, kit)
        id_manager = IdentityManager(vocabulary_db=os.path.join(self.cache_dir, "dictionary.ks"))
        semantic_store = SemanticStore(db_path=os.path.join(self.cache_dir, "semantic_nodes.ks"))

        # Time Accumulators
        t_extraction = 0.0
        t_identity = 0.0
        t_persistence = 0.0

        for func in functions_to_compile:
            code_text = func.get("code") or func.get("content") or func.get("source") or ""

            # 1. Measure Extraction
            start = time.perf_counter()
            context = semantic_compiler.compile_function(
                symbol_id=func["symbol_id"], file_path=func["file"],
                code=code_text, start_line=func.get("start_line", 1), end_line=func.get("end_line", 1)
            )
            context.finalize()
            t_extraction += (time.perf_counter() - start)

            # 2. Measure Identity Generation vs Persistence
            semantic_store.begin()
            try:
                for construct in context.semantic_constructs:
                    domain_obj = getattr(construct, "domain", None)
                    domain = getattr(domain_obj, "value", "kernel") if domain_obj else "kernel"
                    loc = getattr(construct, "location", None)
                    file_path = getattr(loc, "file_path", None) or func["file"]
                    scope_coord = getattr(loc, "scope_coord", "global")
                    symbol_name = getattr(construct, "semantic_id", "")

                    try:
                        category_obj = getattr(construct, "category", None)
                        ontology_kind = getattr(category_obj, "value", "unknown") if category_obj else "unknown"
                    except:
                        ontology_kind = "unknown"

                    # Track Identity Generation strictly
                    id_start = time.perf_counter()
                    numeric_node_id = id_manager.derive_node_id(
                        domain=domain, file_path=file_path,
                        scope=scope_coord, symbol=symbol_name, kind=ontology_kind
                    )
                    t_identity += (time.perf_counter() - id_start)

                    # Track DB Node Writing strictly
                    db_start = time.perf_counter()
                    semantic_store.write_node(
                        node_id=numeric_node_id, ontology_kind=ontology_kind,
                        file_id=0, symbol_id=0, line=getattr(loc, "start_line", 1),
                        version=1, payload="{}"
                    )
                    t_persistence += (time.perf_counter() - db_start)

                semantic_store.commit()
            except Exception as e:
                semantic_store._conn.rollback()
                raise e

        print("\n================ PROFILE BREAKDOWN ================")
        print(f"  Extraction Phase  : {t_extraction:.4f} seconds")
        print(f"  Identity Phase    : {t_identity:.4f} seconds")
        print(f"  Persistence Phase : {t_persistence:.4f} seconds")
        print("===================================================")

runner = ProfilingKernelScopeRunner(cache_dir='ks_cache', verbosity=0)
runner.run_pipeline('chunks.jsonl', symbol_db={})
