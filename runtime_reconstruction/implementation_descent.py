#--------------------------------------------------------
# Reconstructs a plausible execution path starting from a
# given symbol, using the semantic graph and heuristics.
#--------------------------------------------------------
from semantic_runtime.runtime_graph import (
    RuntimeExecutionGraph,
    ExecutionNode,
    ExecutionEdge
)
from semantic_runtime.ontology import (
    SemanticEdgeType
)
from profiles.subsystem_profile import (
    SubsystemSemanticProfile
)
DEBUG = False
def reconstruct_implementation_path(
    runtime_engine,
    profile,
    start_symbol_id: str,
    cpu: int,
    max_depth: int = 16
) -> RuntimeExecutionGraph:

    print(f"Reconstructing Implementation Path for Symbol: {start_symbol_id}")

    runtime_graph = RuntimeExecutionGraph()

    # Prevent cycles and redundant traversal.
    visited_symbols = set()

    current_symbol_id = start_symbol_id
    previous_node_id = None

    # Tracks the edge that produced the current node.
    incoming_edge = None
    max_depth_profile = (
        profile.runtime_depth_limit
        if profile.runtime_depth_limit is not None
        else max_depth
    )
    profile_terminal_symbol = profile.terminal_symbols

    for depth in range(max_depth_profile):

        # Cycle Prevention
        if current_symbol_id in visited_symbols:
            break

        visited_symbols.add(current_symbol_id)

        # Create Current Execution Node
        node_id = runtime_engine.generate_execution_node_id(
            symbol_id=current_symbol_id,
            cpu=cpu,
            depth=depth,
            context="process_context"
        )

        node = ExecutionNode(
            node_id=node_id,

            symbol_id=current_symbol_id,

            cpu=cpu,

            context="process_context",

            timestamp=None,

            depth=depth,

            # Semantic annotations attached to this
            # execution point (locks, state changes, etc.)
            semantic_annotations=[]
        )

        runtime_graph.nodes[node_id] = node

        # Link Previous Node -> Current Node
        if (
            previous_node_id is not None
            and incoming_edge is not None
        ):

            runtime_graph.edges.append(
                ExecutionEdge(
                    src_node_id=previous_node_id,

                    dst_node_id=node_id,

                    semantic_edge_id=incoming_edge.edge_id,

                    execution_context="runtime_flow"
                )
            )

        symbol = runtime_engine.semantic_graph.lookup_symbol(
            current_symbol_id
        )

        symbol_name = (
            symbol.name
            if symbol
            else current_symbol_id
        )

        if symbol_name in profile.terminal_symbols:
            print(
                f"[TRACE COMPLETE] {symbol_name}"
            )
            break

        # Pull Semantic Transitions
        outgoing_edges = (
            runtime_engine.semantic_graph.get_outgoing_edges(
                current_symbol_id
            )
        )

        if not outgoing_edges:
            break

        # Separate Runtime Traversal Edges
        # From Semantic Annotations
        traversable_edges = []

        for edge in outgoing_edges:

            #
            # Runtime traversal edges participate
            # in execution flow reconstruction.
            #
            if edge.edge_type.is_runtime_traversable:

                traversable_edges.append(edge)

            #
            # Non-traversable edges become semantic
            # annotations attached to the node.
            #
            else:

                node.semantic_annotations.append(edge)

        # No Forward Runtime Flow
        if not traversable_edges:
            break
        symbol = runtime_engine.semantic_graph.lookup_symbol(
            current_symbol_id
        )

        symbol_name = (
            symbol.name
            if symbol
            else current_symbol_id
        )
        print(
            f"\n[DEBUG] CURRENT SYMBOL: "
            f"{symbol_name}"
            f" ({current_symbol_id[:8]})"
        )

        for edge in traversable_edges:

            dst_symbol = runtime_engine.semantic_graph.lookup_symbol(
                edge.dst_symbol_id
            )

            dst_name = (
                dst_symbol.name
                if dst_symbol
                else edge.dst_symbol_id
            )

            print(
                f"    "
                f"{edge.edge_type.name}"
                f" -> "
                f"{dst_name}"
            )
        # ------------------------------------------------
        # Runtime Edge Selection
        #
        # NOTE:
        # Currently selects a dominant execution path.
        #
        # Future work:
        # - multi-path expansion
        # - async branching
        # - dispatch fanout traversal
        # ------------------------------------------------

        # 1. FILTER VISITED NODES EARLY
        # Prevent the engine from selecting edges that loop backwards
        valid_edges = [
            edge for edge in traversable_edges
            if edge.dst_symbol_id not in visited_symbols
        ]

        if not valid_edges:
            break

        next_edges = []

        # Prefer deterministic SYNTHETIC_CONTINUATION edges first.
        synth_edges = [
            edge
            for edge in valid_edges
            if edge.edge_type in {
                SemanticEdgeType.SYNTHETIC_CONTINUATION,
            }
        ]
        # Print the results we just filtered
        if DEBUG:
            dst_symbol = runtime_engine.semantic_graph.lookup_symbol(
                edge.dst_symbol_id
            )

            dst_name = (
                dst_symbol.name
                if dst_symbol
                else edge.dst_symbol_id
            )

            print(
                f"[DEBUG] Found SYNTHETIC_CONTINUATION:"
                f" {edge.edge_type.name}"
                f" -> {dst_name}"
            )

        if synth_edges:
            # Sort by confidence to ensure we pick the strongest path
            synth_edges.sort(key=lambda e: getattr(e, 'confidence', 0), reverse=True)
            next_edges = [synth_edges[0]]
        else:
            # Fall back to dispatch reconstruction.
            dispatch_edges = [
                edge
                for edge in valid_edges
                if (
                    edge.edge_type ==
                    SemanticEdgeType.FUNCTION_POINTER_DISPATCH
                )
            ]

            if dispatch_edges:

                #
                # NOTE:
                # Future runtime graph expansion will
                # traverse ALL dispatch candidates.
                #
                #next_edges = [dispatch_edges[0]]
                dispatch_edges.sort(key=lambda e: getattr(e, 'confidence', 0), reverse=True)
                next_edges = [dispatch_edges[0]]
            else:

                direct_edges = [
                    edge
                    for edge in valid_edges
                    if (
                        edge.edge_type ==
                        SemanticEdgeType.DIRECT_CALL
                    )
                ]

                if direct_edges:

                    direct_edges.sort(
                        key=lambda e: getattr(
                            e,
                            "confidence",
                            0
                        ),
                        reverse=True
                    )

                    next_edges = [direct_edges[0]]

        # Final fallback.
        if not next_edges:

            next_edges = [traversable_edges[0]]

        # Advance Traversal
        selected_edge = next_edges[0]

        previous_node_id = node_id

        incoming_edge = selected_edge

        current_symbol_id = (
            selected_edge.dst_symbol_id
        )

    return runtime_graph
