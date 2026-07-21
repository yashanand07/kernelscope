import os
import sqlite3
from typing import Dict, Any, List
from semantic_runtime.compiler.working_set.query_context import QueryContext
from semantic_runtime.compiler.identity.formatter import IdentityFormatter

def to_signed_64(val: int) -> int:
    """Converts an unsigned 64-bit int to a signed 64-bit int for SQLite storage."""
    return val - 2**64 if val >= 2**63 else val

def to_unsigned_64(val: int) -> int:
    """Converts a signed 64-bit int back to an unsigned 64-bit int."""
    return val + 2**64 if val < 0 else val

class WorkingSetCoordinator:
    """
    The main coordinator for the Engineering Session Layer.
    Decoupled runtime traversal leveraging highly normalized binary index stores.
    """
    def __init__(self, dict_db: str, edge_db: str, node_db: str = "ks_cache/semantic_nodes.ks"):
        self.dict_db = dict_db
        self.edge_db = edge_db
        self.node_db = node_db

    def execute_session(self, target_node_id: int, context: QueryContext) -> Dict[str, Any]:
        """
        Executes a bounded relationship expansion over the binary stores
        using strict profile constraints. Returns a clean Localized Engineering Context.
        """
        discovered_edges = []
        visited_nodes = set()
        nodes_to_process = [(target_node_id, 0)] # Tuple of (NodeID, CurrentDepth)

        # 1. Traverse the binary edge adjacency matrix
        edge_conn = sqlite3.connect(self.edge_db)
        edge_cursor = edge_conn.cursor()
        try:
            while nodes_to_process:
                current_id, depth = nodes_to_process.pop(0)
                if current_id in visited_nodes or depth >= context.max_depth:
                    continue

                visited_nodes.add(current_id)
                db_key = to_signed_64(current_id)

                edge_cursor.execute("""
                    SELECT target_node_id, relationship_kind
                    FROM normalized_edges
                    WHERE source_node_id = ?;
                """, (db_key,))

                for signed_target_id, kind in edge_cursor.fetchall():
                    target_id = to_unsigned_64(signed_target_id)

                    if kind in context.allowed_relationships:
                        discovered_edges.append({
                            "source_id": current_id,
                            "target_id": target_id,
                            "relationship": kind
                        })
                        if len(visited_nodes) < context.max_nodes:
                            nodes_to_process.append((target_id, depth + 1))
        finally:
            edge_conn.close()

        # 2. Extract normalized ID keys (file_id, symbol_id) for all traversed nodes
        node_metadata = {}
        if visited_nodes:
            node_conn = sqlite3.connect(self.node_db)
            node_cursor = node_conn.cursor()
            try:
                signed_visited = [to_signed_64(nid) for nid in visited_nodes]
                placeholders = ",".join("?" for _ in signed_visited)

                # Fetch normalization attributes directly
                node_cursor.execute(f"""
                    SELECT node_id, file_id, symbol_id, ontology_kind
                    FROM semantic_records
                    WHERE node_id IN ({placeholders});
                """, signed_visited)

                for signed_nid, file_id, symbol_id, ontology_kind in node_cursor.fetchall():
                    unsigned_nid = to_unsigned_64(signed_nid)
                    node_metadata[unsigned_nid] = {
                        "file_id": file_id,
                        "symbol_id": symbol_id,
                        "kind": ontology_kind
                    }
            finally:
                node_conn.close()

        # 3. Batch resolve normalized identifiers using the dictionary registries
        resolved_files = {}
        resolved_symbols = {}

        if node_metadata:
            dict_conn = sqlite3.connect(self.dict_db)
            dict_cursor = dict_conn.cursor()
            try:
                # Gather unique IDs to minimize database queries
                unique_file_ids = list({meta["file_id"] for meta in node_metadata.values()})
                unique_sym_ids = list({meta["symbol_id"] for meta in node_metadata.values()})

                # Map file IDs
                if unique_file_ids:
                    file_placeholders = ",".join("?" for _ in unique_file_ids)
                    dict_cursor.execute(f"""
                        SELECT file_id, path_string FROM file_registry
                        WHERE file_id IN ({file_placeholders});
                    """, unique_file_ids)
                    resolved_files = dict(dict_cursor.fetchall())

                # Map symbol IDs
                if unique_sym_ids:
                    sym_placeholders = ",".join("?" for _ in unique_sym_ids)
                    dict_cursor.execute(f"""
                        SELECT symbol_id, name_string FROM symbol_registry
                        WHERE symbol_id IN ({sym_placeholders});
                    """, unique_sym_ids)
                    resolved_symbols = dict(dict_cursor.fetchall())
            finally:
                dict_conn.close()

        # 4. Construct the clean human-readable output graph map
        def get_readable_name(node_id: int) -> str:
            meta = node_metadata.get(node_id)
            if not meta:
                return IdentityFormatter.to_hex_str(node_id)

            path = resolved_files.get(meta["file_id"], "unknown_file")
            symbol = resolved_symbols.get(meta["symbol_id"], "unknown_symbol")
            return f"[{meta['kind']}] {path} ──► {symbol}"

        human_readable_graph = []
        for edge in discovered_edges:
            human_readable_graph.append({
                "source": get_readable_name(edge["source_id"]),
                "target": get_readable_name(edge["target_id"]),
                "relationship": edge["relationship"]
            })

        return {
            "session_profile": context.profile_name,
            "monitored_nodes_count": len(visited_nodes),
            "localized_graph": human_readable_graph
        }