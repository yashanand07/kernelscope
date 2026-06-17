import hashlib
from dataclasses import dataclass, asdict
from typing import Dict, List, Set, Optional, Any
from .ontology import SemanticEdgeType
from utils.subsystem_derivation import derive_subsystem
from .symbol_type import SymbolKind

# --------------------------------------------------------
# Exceptions & Core Identity Layer
# --------------------------------------------------------

class AmbiguousSymbolError(Exception):
    """Raised when a name-only lookup resolves to multiple distinct symbols."""
    pass

@dataclass(frozen=True)
class SymbolKey:
    """The canonical, composite identity of a kernel symbol."""
    file_path: str
    symbol_name: str

    def __str__(self):
        return f"{self.file_path}::{self.symbol_name}"

@dataclass(frozen=True, slots=True)
class SymbolIdentity:
    """The metadata payload for a resolved symbol."""
    key: SymbolKey
    line: int
    kind: SymbolKind
    signature: Optional[str]
    subsystem: str
    is_static: bool = False

    # Convenience properties to maintain compatibility
    @property
    def name(self) -> str:
        return self.key.symbol_name

    @property
    def file_path(self) -> str:
        return self.key.file_path

    # ----------------------------------------------------
    # Strangler Pattern: Derived ID and Convenience Props
    # ----------------------------------------------------
    @property
    def symbol_id(self) -> str:
        # means: symbol_id == file_path::symbol_name and not: symbol_id == hash
        # Symbol IDs are intentionally human-readable and
        # derived directly from SymbolKey.
        # Do not assume hashed UUID semantics.
        return str(self.key)  # Yields: "fs/open.c::do_sys_open"


# --------------------------------------------------------
# Semantic Edge Layer
# --------------------------------------------------------

@dataclass(slots=True)
class SemanticEdge:
    edge_id: str
    src_symbol_id: str
    dst_symbol_id: str
    edge_type: SemanticEdgeType
    confidence: float
    subsystem: str
    resolution_source: str
    is_deterministic: bool = True

# --------------------------------------------------------
# Central Semantic Graph
# --------------------------------------------------------

class SemanticGraph:

    def __init__(self):

        # ----------------------------------------------------
        # Primary Identity Registries
        # ----------------------------------------------------
        self.symbol_db_by_key: Dict[SymbolKey, SymbolIdentity] = {}
        self.symbol_db_by_id: Dict[str, SymbolIdentity] = {}
        
        # Secondary Indexes (Using Sets to prevent duplicates)
        self.symbol_db_by_name: Dict[str, Set[SymbolKey]] = {}
        self.symbol_db_by_file: Dict[str, Set[SymbolKey]] = {}

        # ----------------------------------------------------
        # Edge Registries
        # ----------------------------------------------------
        self.semantic_edge_index: Dict[str, SemanticEdge] = {}
        self.semantic_edges_by_src: Dict[str, List[SemanticEdge]] = {}
        self.semantic_edges_by_dst: Dict[str, List[SemanticEdge]] = {}

        # ----------------------------------------------------
        # Telemetry
        # ----------------------------------------------------
        self.legacy_name_lookups: Dict[str, Dict[str, Any]] = {}

    # --------------------------------------------------------
    # Edge ID Generation (Only Edges use Hashlib now)
    # --------------------------------------------------------

    @staticmethod
    def generate_edge_id(
        src_symbol_id: str,
        dst_symbol_id: str,
        edge_type: SemanticEdgeType
    ) -> str:
        edge_seed = f"{src_symbol_id}:{dst_symbol_id}:{edge_type.value}"
        return hashlib.sha1(edge_seed.encode()).hexdigest()

    # --------------------------------------------------------
    # Symbol Registration & Synthetic Creation
    # --------------------------------------------------------

    def resolve_or_create_interface(
        self,
        provider_kind: str,
        operation: str
    ) -> str:
        interface_name = f"{provider_kind}:{operation}"
        file_path = f"<{provider_kind}_interface>"
        key = SymbolKey(file_path=file_path, symbol_name=interface_name)

        if key in self.symbol_db_by_key:
            return self.symbol_db_by_key[key].symbol_id

        sym_identity = SymbolIdentity(
            key=key,
            line=0,
            kind=SymbolKind.INTERFACE,
            signature=None,
            subsystem=provider_kind
        )
        
        self.symbol_db_by_key[key] = sym_identity
        self.symbol_db_by_id[sym_identity.symbol_id] = sym_identity
        self.symbol_db_by_name.setdefault(interface_name, set()).add(key)
        self.symbol_db_by_file.setdefault(file_path, set()).add(key)

        return sym_identity.symbol_id

    # --------------------------------------------------------
    # Symbol Registration
    # --------------------------------------------------------

    def register_symbol(
        self,
        name: str,
        file_path: str,
        line: int,
        kind: SymbolKind,
        signature: Optional[str] = None,
        is_static: bool = False
    ) -> str:

        key = SymbolKey(file_path=file_path, symbol_name=name)

        if key in self.symbol_db_by_key:
            return self.symbol_db_by_key[key].symbol_id

        subsystem = derive_subsystem(file_path)

        sym_identity = SymbolIdentity(
            key=key,
            line=line,
            kind=kind,
            signature=signature,
            subsystem=subsystem,
            is_static=is_static
        )

        self.symbol_db_by_key[key] = sym_identity
        self.symbol_db_by_id[sym_identity.symbol_id] = sym_identity
        self.symbol_db_by_name.setdefault(name, set()).add(key)
        self.symbol_db_by_file.setdefault(file_path, set()).add(key)

        return sym_identity.symbol_id

    # --------------------------------------------------------
    # Deterministic Lookups
    # ---------------------------------------------------------
    def get_symbol(self, key: SymbolKey) -> Optional[SymbolIdentity]:
        """O(1) lookup using a pre-constructed SymbolKey."""
        return self.symbol_db_by_key.get(key)

    def resolve_symbol_by_key(self, file_path: str, name: str) -> Optional[SymbolIdentity]:
        """Strict resolution using the composite key components."""
        key = SymbolKey(file_path, name)
        return self.symbol_db_by_key.get(key)

    def lookup_symbol(self, symbol_id: str) -> Optional[SymbolIdentity]:
        """O(1) reverse lookup by ID."""
        return self.symbol_db_by_id.get(symbol_id)

    def resolve_fq_name(self, file_path: str, symbol_name: str) -> Optional[str]:
        """Legacy helper for fully qualified name string resolution."""
        key = SymbolKey(file_path, symbol_name)
        identity = self.symbol_db_by_key.get(key)
        return identity.symbol_id if identity else None

    # ---------------------------------------------------------
    # Discovery & Resolution (Ambiguity Handling)
    # ---------------------------------------------------------
    def resolve_symbols_by_name(self, name: str) -> List[SymbolIdentity]:
        """Returns all matching SymbolIdentities deterministically sorted by file_path."""
        keys = self.symbol_db_by_name.get(name, set())
        return [self.symbol_db_by_key[k] for k in sorted(keys, key=lambda x: x.file_path)]

    def get_symbols_in_file(self, file_path: str) -> List[SymbolIdentity]:
        """Returns all SymbolIdentities in a file deterministically sorted by symbol_name."""
        keys = self.symbol_db_by_file.get(file_path, set())
        return [self.symbol_db_by_key[k] for k in sorted(keys, key=lambda x: x.symbol_name)]

    def has_ambiguous_name(self, name: str) -> bool:
        """Helper to check if a symbol name is overloaded in the kernel tree."""
        return len(self.symbol_db_by_name.get(name, set())) > 1

    def resolve_symbol_by_name(self, name: str, caller: str = "unknown") -> Optional[SymbolIdentity]:
        """
        Legacy compatibility layer.
        Pass `caller` manually to track where legacy lookups are originating.
        """
        if caller not in self.legacy_name_lookups:
            self.legacy_name_lookups[caller] = {"count": 0, "symbols": set()}
            
        self.legacy_name_lookups[caller]["count"] += 1
        self.legacy_name_lookups[caller]["symbols"].add(name)
        
        keys = self.symbol_db_by_name.get(name)
        if not keys:
            return None
            
        if len(keys) == 1:
            return self.symbol_db_by_key[next(iter(keys))]
            
        sorted_keys = sorted(keys, key=lambda x: x.file_path)
        raise AmbiguousSymbolError(
            f"Ambiguous lookup: '{name}' resolved to {len(keys)} distinct symbols. "
            f"Files involved: {[k.file_path for k in sorted_keys]}. "
            f"Use resolve_symbols_by_name() or resolve_symbol_by_key() instead."
        )

    def resolve_entrypoint_symbol(self, symbol_name: str, profile) -> Optional[str]:
        """Resolves an entrypoint name, preferring files defined in the profile."""
        files = getattr(profile, "entrypoint_files", [])
        
        if files:
            for file_path in files:
                key = SymbolKey(file_path, symbol_name)
                if key in self.symbol_db_by_key:
                    return self.symbol_db_by_key[key].symbol_id
        
        # Fallback to ambiguity-aware lookup
        matches = self.resolve_symbols_by_name(
            symbol_name
        )

        if len(matches) == 1:
            return matches[0].symbol_id

        return None

    def get_legacy_lookup_stats(self) -> Dict[str, Dict[str, Any]]:
        """Returns structured telemetry data for the presentation layer."""
        return self.legacy_name_lookups

    # --------------------------------------------------------
    # Edge Registration
    # --------------------------------------------------------

    def register_semantic_edge(
        self,
        src_symbol_id: str,
        dst_symbol_id: str,
        edge_type: SemanticEdgeType,
        confidence: float,
        resolution_source: str,
        is_deterministic: bool = True
    ) -> str:

        src_symbol = self.lookup_symbol(src_symbol_id)
        if not src_symbol:
            raise ValueError(f"Unknown source symbol: {src_symbol_id}")

        edge_id = self.generate_edge_id(src_symbol_id, dst_symbol_id, edge_type)

        edge = SemanticEdge(
            edge_id=edge_id,
            src_symbol_id=src_symbol_id,
            dst_symbol_id=dst_symbol_id,
            edge_type=edge_type,
            confidence=confidence,
            subsystem=src_symbol.subsystem,
            resolution_source=resolution_source,
            is_deterministic=is_deterministic
        )

        existing = self.semantic_edges_by_src.get(src_symbol_id, [])
        for e in existing:
            if e.edge_id == edge_id:
                return edge_id

        # Forward Index
        self.semantic_edges_by_src.setdefault(src_symbol_id, []).append(edge)
        # Reverse Index
        self.semantic_edges_by_dst.setdefault(dst_symbol_id, []).append(edge)
        # Edge Lookup Index
        self.semantic_edge_index[edge.edge_id] = edge

        # Deterministic Traversal Ordering
        self.semantic_edges_by_src[src_symbol_id].sort(
            key=lambda e: (e.confidence, e.is_deterministic),
            reverse=True
        )

        return edge_id

    # --------------------------------------------------------
    # Graph Traversal
    # --------------------------------------------------------

    def get_outgoing_edges(self, symbol_id: str) -> List[SemanticEdge]:
        return self.semantic_edges_by_src.get(symbol_id, [])

    def get_incoming_edges(self, symbol_id: str) -> List[SemanticEdge]:
        return self.semantic_edges_by_dst.get(symbol_id, [])

    def rebuild_indexes(self):
        self.semantic_edges_by_dst = {}
        for src_id, edges in self.semantic_edges_by_src.items():
            for edge in edges:
                self.semantic_edges_by_dst.setdefault(edge.dst_symbol_id, []).append(edge)
                self.semantic_edge_index[edge.edge_id] = edge

    # --------------------------------------------------------
    # Stats & Telemetry
    # --------------------------------------------------------

    def number_of_edges(self):
        return sum(len(edges) for edges in self.semantic_edges_by_src.values())

    def dispatch_edges(self):
        count = sum(
            1 for edges in self.semantic_edges_by_src.values() 
            for edge in edges if edge.edge_type == SemanticEdgeType.FUNCTION_POINTER_DISPATCH
        )
        if app_config.debug_traversal:
            print(f"Dispatch edges reconstructed: {count}")
        return count

    def synthetic_edges(self):
        count = sum(
            1 for edges in self.semantic_edges_by_src.values() 
            for edge in edges if edge.edge_type == SemanticEdgeType.SYNTHETIC_CONTINUATION
        )
        if app_config.debug_traversal:
            print(f"Synthetic edges reconstructed: {count}")
        return count

    def semantic_ir_stats(self):
        return {
            "symbols": len(self.symbol_db_by_key),
            "edges": self.number_of_edges(),
            "dispatch_edges": self.dispatch_edges(),
            "synthetic_edges": self.synthetic_edges()
        }

    # --------------------------------------------------------
    # Serialization & Debugging
    # --------------------------------------------------------

    def export_json(self) -> dict:
        return {
            "symbols": {
                # Because `@property` fields are ignored by dataclass.asdict, 
                # we explicitly inject `symbol_id`, `name`, and `file_path`.
                v.symbol_id: {
                    **asdict(v),
                    "symbol_id": v.symbol_id,
                    "name": v.name,
                    "file_path": v.file_path,
                    "key": str(v.key)
                }
                for v in self.symbol_db_by_key.values()
            },
            "semantic_edges_by_src": {
                k: [
                    {**asdict(e), "edge_type": e.edge_type.value}
                    for e in v
                ]
                for k, v in self.semantic_edges_by_src.items()
            },
            "name_to_keys": {
                k: [str(key) for key in v] 
                for k, v in self.symbol_db_by_name.items()
            }
        }

    def dump_symbol_edges(self, symbol_id: str, profile=None):
        outgoing = self.get_outgoing_edges(symbol_id)
        sym = self.lookup_symbol(symbol_id)
        sym_name = sym.name if sym else symbol_id
        
        print(
            f"Outgoing edges for "
            f"{sym.file_path}::{sym.name} "
            f"({len(outgoing)})"
        )
        for edge in outgoing:
            dst_symbol = self.lookup_symbol(edge.dst_symbol_id)
            dst_name = dst_symbol.name if dst_symbol else edge.dst_symbol_id
            print(f"  - {edge.edge_type.name} --> {dst_name} (confidence={edge.confidence})")
        print("\n\n")