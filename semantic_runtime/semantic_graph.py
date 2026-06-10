from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from .ontology import SemanticEdgeType
from utils.subsystem_derivation import derive_subsystem
from .symbol_type import (
    SymbolKind
)
from hashlib import sha1
# --------------------------------------------------------
# Symbol Identity Layer
# --------------------------------------------------------

DEBUG = True
@dataclass(slots=True)
class SymbolIdentity:
    symbol_id: str

    name: str
    file_path: str

    line: int

    kind: SymbolKind

    signature: Optional[str]

    subsystem: str


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

@dataclass
class SemanticGraph:

    def __init__(self):

        # ----------------------------------------------------
        # Symbol Registries
        # ----------------------------------------------------

        self.symbol_table: Dict[str, SymbolIdentity] = {}

        self.fq_name_to_id: Dict[str, str] = {}

        self.name_to_symbol_id = {}

        self.semantic_edge_index = {}

        # ----------------------------------------------------
        # Edge Registries
        # ----------------------------------------------------

        self.semantic_edges_by_src: Dict[
            str,
            List[SemanticEdge]
        ] = {}

        self.semantic_edges_by_dst: Dict[
            str,
            List[SemanticEdge]
        ] = {}

    # --------------------------------------------------------
    # Identity Generation (using hashing for stable IDs)
    # --------------------------------------------------------

    @staticmethod
    def generate_symbol_id(
        file_path: str,
        symbol: str,
        signature: Optional[str],
    ) -> str:

        identity_seed = (
            f"{file_path}:{symbol}:{signature}"
        )

        return sha1(identity_seed.encode()).hexdigest()

    @staticmethod
    def generate_edge_id(
        src_symbol_id: str,
        dst_symbol_id: str,
        edge_type: SemanticEdgeType
    ) -> str:

        edge_seed = (
            f"{src_symbol_id}:"
            f"{dst_symbol_id}:"
            f"{edge_type.value}"
        )

        return sha1(edge_seed.encode()).hexdigest()

    def resolve_or_create_interface(
        self,
        provider_kind,
        operation
    ):
        # Takes in ("file_operations", "read_iter")
        # and returns file_operations.read_iter as a synthetic symbol ID
        # creating it if it doesn't exist
        # reusing it if present
    
        interface_name = f"{provider_kind}:{operation}"

        symbol_id = self.name_to_symbol_id.get(
            interface_name
        )

        if symbol_id:
            return symbol_id

        # Create a synthetic symbol for this interface
        symbol_id = self.generate_symbol_id(
            file_path=f"<{provider_kind}_interface>",
            symbol=interface_name,
            signature=None
        )
        symbol = SymbolIdentity(
            symbol_id=symbol_id,
            name=interface_name,
            file_path=f"<{provider_kind}_interface>",
            line=0,
            kind=SymbolKind.INTERFACE,
            signature=None,
            subsystem=provider_kind
        )
        self.symbol_table[symbol_id] = symbol

        self.name_to_symbol_id[interface_name] = symbol_id

        return symbol_id

    # --------------------------------------------------------
    # Symbol Registration
    # --------------------------------------------------------

    def register_symbol(
        self,
        name: str,
        file_path: str,
        line: int,
        kind: SymbolKind,
        signature: Optional[str] = None
    ) -> str:

        subsystem = derive_subsystem(file_path)

        symbol_id = self.generate_symbol_id(
            file_path=file_path,
            symbol=name,
            signature=signature
        )

        if symbol_id in self.symbol_table:
            return symbol_id

        symbol = SymbolIdentity(
            symbol_id=symbol_id,
            name=name,
            file_path=file_path,
            line=line,
            kind=kind,
            signature=signature,
            subsystem=subsystem
        )

        self.symbol_table[symbol_id] = symbol

        fq_name = f"{file_path}:{name}"

        self.fq_name_to_id[fq_name] = symbol_id

        self.name_to_symbol_id[name] = symbol_id

        return symbol_id

    # --------------------------------------------------------
    # Symbol Lookup and Resolution
    # --------------------------------------------------------

    def lookup_symbol(
        self,
        symbol_id: str
    ) -> Optional[SymbolIdentity]:

        return self.symbol_table.get(symbol_id)

    def resolve_fq_name(
        self,
        file_path: str,
        symbol_name: str
    ) -> Optional[str]:

        fq_name = f"{file_path}:{symbol_name}"

        return self.fq_name_to_id.get(fq_name)

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
            raise ValueError(
                f"Unknown source symbol: {src_symbol_id}"
            )

        edge_id = self.generate_edge_id(
            src_symbol_id,
            dst_symbol_id,
            edge_type
        )

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

        # To solve the problem of duplicate edges being created due to
        # multiple regex matches or overlapping heuristics,
        # we first check if an identical edge already exists before
        # registering a new one. This ensures that the graph remains
        # clean and prevents bloat from redundant edges.
        existing = self.semantic_edges_by_src.get(
            src_symbol_id,
            []
        )

        for e in existing:
            if e.edge_id == edge_id:
                return edge_id
        # ----------------------------------------------------
        # Forward Index
        # ----------------------------------------------------

        self.semantic_edges_by_src.setdefault(
            src_symbol_id,
            []
        ).append(edge)

        # ----------------------------------------------------
        # Reverse Index
        # ----------------------------------------------------

        self.semantic_edges_by_dst.setdefault(
            dst_symbol_id,
            []
        ).append(edge)

        # ----------------------------------------------------
        # Edge Lookup Index
        # ----------------------------------------------------

        self.semantic_edge_index[
            edge.edge_id
        ] = edge

        # ----------------------------------------------------
        # Deterministic Traversal Ordering
        # ----------------------------------------------------

        self.semantic_edges_by_src[src_symbol_id].sort(
            key=lambda e: (
                e.confidence,
                e.is_deterministic
            ),
            reverse=True
        )

        return edge_id

    # --------------------------------------------------------
    # Graph Traversal - Outgoing and Incoming Edges
    # --------------------------------------------------------

    def get_outgoing_edges(
        self,
        symbol_id: str
    ) -> List[SemanticEdge]:

        return self.semantic_edges_by_src.get(
            symbol_id,
            []
        )

    def get_incoming_edges(
        self,
        symbol_id: str
    ) -> List[SemanticEdge]:

        return self.semantic_edges_by_dst.get(
            symbol_id,
            []
        )


    def rebuild_indexes(self):


        self.semantic_edges_by_dst = {}

        for src_id, edges in (
            self.semantic_edges_by_src.items()
        ):

            for edge in edges:

                self.semantic_edges_by_dst.setdefault(
                    edge.dst_symbol_id,
                    []
                ).append(edge)

                self.semantic_edge_index[
                    edge.edge_id
                ] = edge

    def number_of_edges(self):
        count = 0
        for edges in self.semantic_edges_by_src.values():
            count += len(edges)
        return count

    def dispatch_edges(self):
        count = 0
        for edges in self.semantic_edges_by_src.values():
            for edge in edges:
                if edge.edge_type == SemanticEdgeType.FUNCTION_POINTER_DISPATCH:
                    count += 1
        dispatch_edge_count = count
        if DEBUG:
            print(
                f"Dispatch edges reconstructed: "
                f"{dispatch_edge_count}"
            )

        return count

    def synthetic_edges(self):
        count = 0
        for edges in self.semantic_edges_by_src.values():
            for edge in edges:
                if edge.edge_type == SemanticEdgeType.SYNTHETIC_CONTINUATION :
                    count += 1
        if DEBUG:
            print(
                f"Synthetic edges reconstructed: "
                f"{count}"
            )
        return count

    def semantic_ir_stats(self):

        return {
            "symbols": len(self.symbol_table),

            "edges": self.number_of_edges(),

            "dispatch_edges":
                self.dispatch_edges(),

            "synthetic_edges":
                self.synthetic_edges()
        }
    # --------------------------------------------------------
    # Serialization for Debugging and Visualization
    # --------------------------------------------------------

    def export_json(self) -> dict:

        return {
            "symbols": {
                k: asdict(v)
                for k, v in self.symbol_table.items()
            },

            "semantic_edges_by_src": {
                k: [
                    {
                        **asdict(e),
                        "edge_type": e.edge_type.value
                    }
                    for e in v
                ]

                for k, v in self.semantic_edges_by_src.items()
            },

            "fq_name_to_id": self.fq_name_to_id,

            "name_to_symbol_id": self.name_to_symbol_id,
        }

    # --------------------------------------------------------
    # Helper for symbol resolution by name
    # --------------------------------------------------------

    def resolve_symbol_by_name(
        self,
        symbol_name: str
    ):

        return self.name_to_symbol_id.get(
            symbol_name
        )

    def dump_symbol_edges(self, symbol_id: str):

        outgoing = self.get_outgoing_edges(symbol_id)

        print(
            f"Outgoing edges for {self.resolve_symbol_by_name(symbol_id)} ({symbol_id[:8]}) ({len(outgoing)}):"
        )

        for edge in outgoing:
            dst_symbol = self.lookup_symbol(edge.dst_symbol_id)
            dst_name = dst_symbol.name if dst_symbol else edge.dst_symbol_id
            print(
                f"  - {edge.edge_type.name} --> "
                f"{dst_name} (confidence={edge.confidence})"
            )
        print("\n\n")