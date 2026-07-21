import os
from typing import List, Dict, Any

# [Surgical Reference Blueprint Imports]
from semantic_runtime.compiler.identity.manager import IdentityManager
from semantic_runtime.compiler.identity.formatter import IdentityFormatter

class KernelScopeRunner:
    """
    Orchestrates compilation execution, persistence, and session indexing.
    Acts as a pure pipeline coordinator.
    """
    def __init__(self, cache_dir: str = "ks_cache"):
        # Enforce Step 1 Layout Standardization: Replaces legacy cache names
        self.cache_dir = cache_dir

        # Canonical binary indices configurations
        self.dict_db = os.path.join(self.cache_dir, "dictionary.ks")
        self.semantic_db = os.path.join(self.cache_dir, "semantic_nodes.ks")
        self.relationship_db = os.path.join(self.cache_dir, "relationships.ks")

        # Ensure the structural cache container exists locally
        os.makedirs(self.cache_dir, exist_ok=True)

    def run_pipeline(self, chunks_path: str):
        """
        Executes the compilation pipeline passes incrementally.
        """
        # ----------------------------------------------------------------------
        # Phase 0 & Phase 1: Ingestion & Extraction Core
        # ──► ✓ KEEP: High-speed JSONL loading and AST parsing are frozen.
        # ----------------------------------------------------------------------
        print("[✓ Phase 0] Loading source abstraction layers...")
        raw_chunks = self._phase0_load_chunks(chunks_path)

        print("[✓ Phase 1] Extracting concrete syntax elements...")
        semantic_objects = self._phase1_extract_ontologies(raw_chunks)

# ----------------------------------------------------------------------
        # ──► GATE A INTEGRATION: Identity Context Interception (Aligned Signature)
        # ----------------------------------------------------------------------
        print("[Gate A] Instantiating Identity Context Layer...")

        id_manager = IdentityManager(vocabulary_db=self.dict_db)
        processed_nodes: List[Dict[str, Any]] = []

        for obj in semantic_objects:
            # Extract parameters exactly matching the names used by the parser output
            domain = obj.get("domain", "kernel")
            file_path = obj.get("file_path", "unknown.c")
            scope_coord = obj.get("scope_coord", "global")
            symbol_name = obj.get("symbol", "")
            ontology_kind = obj.get("kind", "unknown")

            # ✓ Pass positionally or map keyword pairs directly to the exact method signature:
            # derive_node_id(self, domain: str, file_path: str, scope: str, symbol: str, kind: str)
            numeric_node_id = id_manager.derive_node_id(
                domain=domain,
                file_path=file_path,
                scope=scope_coord,    # Maps parser scope_coord to contract scope
                symbol=symbol_name,   # Maps parser symbol to contract symbol
                kind=ontology_kind    # Maps parser kind to contract kind
            )

            # Enrich and track
            obj["node_id"] = numeric_node_id

            # Print explicit diagnostic metric via hex formatter
            hex_id = IdentityFormatter.to_hex_str(numeric_node_id)
            print(f"  [Identity Mapped] {symbol_name:<25} ──► {hex_id}")

            processed_nodes.append(obj)

        # ----------------------------------------------------------------------
        # Gate B: Split Persistence Store Layer
        # ──► TODO: Replace this legacy temporary path next in our timeline.
        # ----------------------------------------------------------------------
        print("[Gate B Bridge] Forwarding nodes to legacy persistence layout...")
        self._legacy_write_monolith(processed_nodes)

        print("\n[✓ COMPILER RUN STATUS] Gate A Integration Pipeline Complete.")