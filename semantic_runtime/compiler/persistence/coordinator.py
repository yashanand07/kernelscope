import os
import json
from typing import Dict, Any, Iterable
from semantic_runtime.compiler.identity.identity_manager import IdentityManager
from semantic_runtime.compiler.persistence.semantic_store import SemanticStore
from semantic_runtime.compiler.persistence.relationship_store import RelationshipStore
from semantic_runtime.compiler.persistence.collection_store import CollectionStore
from semantic_runtime.compiler.persistence.symbol_store import SymbolStore
from semantic_runtime.compiler.identity.vocabulary import VocabularyManager
from semantic_runtime.compiler.persistence_store import ks_json_encoder

class PersistenceCoordinator:
    """
    Facade controller orchestrating lifecycle, transactional boundaries,
    and streaming data ingestion for all KernelScope SQLite persistence engines.
    """
    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir

        # Instantiate localized storage engines
        self.semantic_store = SemanticStore(db_path=os.path.join(cache_dir, "semantic_nodes.ks"))
        self.relationship_store = RelationshipStore(db_path=os.path.join(cache_dir, "relationships.ks"))
        self.collection_store = CollectionStore(db_path=os.path.join(cache_dir, "collections.ks"))
        self.symbol_store = SymbolStore(db_path=os.path.join(cache_dir, "symbols.ks"))
        self.vocab_store = VocabularyManager(os.path.join(cache_dir, "dictionary.ks"))

        # Operational transactional stores group
        self._tx_stores = [self.semantic_store, self.relationship_store, self.symbol_store, self.vocab_store]

    def begin(self):
        """Initializes an isolated transaction block across all transactional storage layers."""
        for store in self._tx_stores:
            store.begin()

    def commit(self):
        """Commits all staged mutations safely to their respective SQLite endpoints."""
        for store in self._tx_stores:
            store.commit()

    def rollback_and_close(self):
        """Safely rolls back pending transactions and tears down active connections on error."""
        for store in self._tx_stores:
            try:
                if getattr(store, '_conn', None):
                    store._conn.rollback()
                    store._conn.close()
                    store._conn = None
                    store._cursor = None
            except Exception:
                pass

    def ingest_function_context(self, context: Any, func_meta: Dict[str, Any]):
        """
        Processes a fully compiled function semantic context, maps internal
        structures to deterministic integer identities, and streams them to database targets.
        """
        uri_to_id_map = {}
        current_file = func_meta["file"]
        current_symbol_id = func_meta["symbol_id"]

        # 1. Map and write Semantic Nodes
        for construct in context.semantic_constructs:
            domain_obj = getattr(construct, "domain", None)
            domain = getattr(domain_obj, "value", "kernel") if domain_obj else "kernel"

            loc = getattr(construct, "location", None)
            file_path = getattr(loc, "file_path", None) or current_file
            scope_coord = getattr(loc, "scope_coord", "global")
            symbol_name = getattr(construct, "semantic_id", "")

            try:
                category_obj = getattr(construct, "category", None)
                ontology_kind = getattr(category_obj, "value", "unknown") if category_obj else "unknown"
            except NotImplementedError:
                ontology_kind = "unknown"

            numeric_node_id = IdentityManager.generate_node_id(
                domain=domain, file_path=file_path, scope_coord=scope_coord,
                symbol_name=symbol_name, entity_kind=ontology_kind
            )
            setattr(construct, "node_id", numeric_node_id)

            uri_to_id_map[symbol_name] = numeric_node_id

            file_id = self.vocab_store.intern_file(file_path)

            #  SAFE TOKEN EXTRACTION: Tries explicit attributes first, falls back to splitting semantic_id
            raw_name = (
                getattr(construct, "target_name", None)
                or getattr(construct, "target_function", None)
                or getattr(construct, "clean_expr", None)
                or getattr(construct, "primitive", None)
                or getattr(construct, "macro_name", None)
                or getattr(construct, "token", None)
                or getattr(construct, "symbol", None)
            )
            if not raw_name and symbol_name:
                raw_name = symbol_name.split(":")[-1]

            symbol_id = self.vocab_store.intern_symbol(raw_name or "unknown")
            line_number = getattr(loc, "start_line", 1)

            payload_dict = {"symbol": symbol_name, "scope_coord": scope_coord, "domain": domain}

            self.semantic_store.write_node(
                node_id=numeric_node_id, ontology_kind=ontology_kind,
                file_id=file_id, symbol_id=symbol_id,
                line=line_number, version=1, payload=json.dumps(payload_dict)
            )

        # 2. Translate and write Normalized Relationship Edges
        for rel in context.relationships:
            source_uri = getattr(rel, "source_semantic_id", None)
            target_uri = getattr(rel, "target_semantic_id", None)

            source_id = uri_to_id_map.get(source_uri)
            target_id = uri_to_id_map.get(target_uri)

            if target_uri and target_id is None and target_uri.startswith("sym:"):
                target_id = IdentityManager.generate_node_id(
                    domain="symbol", file_path=current_file, scope_coord=current_symbol_id,
                    symbol_name=target_uri, entity_kind="local"
                )

            rel_type = getattr(rel, "relationship_type", None)
            edge_kind = rel_type.value if rel_type else "dependency"

            if source_id is not None and target_id is not None:
                self.relationship_store.write_edge(source_id=source_id, target_id=target_id, kind=edge_kind)

        # 3. Stream Local Variable Registrations (Normalized)
        #  SANITIZED SCOPE NAME: Ensures scope name is stripped of func:file: prefixes
        raw_scope_name = func_meta.get("symbol") or current_symbol_id.split(":")[-1]

        current_file_id = self.vocab_store.intern_file(current_file)
        current_scope_id = self.vocab_store.intern_symbol(raw_scope_name)

        for name, sym_list in context.local_symbols.items():
            for sym in sym_list:
                sym_key = f"{current_file}:{current_symbol_id}:{name}:{id(sym)}"

                self.symbol_store.write_symbol(
                    symbol_key=sym_key,
                    name=name,
                    type_str=getattr(sym, 'type_str', 'unknown'),
                    scope_id=current_scope_id,
                    file_id=current_file_id
                )

    def ingest_global_collections(self, collections_source: Iterable[Any]):
        """Writes out Phase 0 collected indices to the non-transactional collection repository."""
        self.collection_store.begin()
        try:
            for col in collections_source:
                col_id = getattr(col, 'collection_id', None) or getattr(col, 'name', str(id(col)))
                raw_data = col.__dict__ if hasattr(col, '__dict__') else str(col)
                self.collection_store.write_collection(
                    collection_id=col_id, family=getattr(col, 'family', 'generic'),
                    raw_descriptor=json.dumps(raw_data, default=ks_json_encoder)
                )
            self.collection_store.commit()
        except Exception as e:
            if self.collection_store._conn:
                self.collection_store._conn.rollback()
                self.collection_store._conn.close()
            raise e