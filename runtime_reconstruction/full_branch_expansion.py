from collections import deque
from typing import Set, Tuple, Dict, Any
import os
from collections import defaultdict

from semantic_runtime.ontology import SemanticEdgeType

from profiles.subsystem_profile import (
    SubsystemSemanticProfile
)
from config.config import app_config
from semantic_runtime.runtime_graph import (
    RuntimeExecutionGraph,
    ExecutionNode,
    ExecutionEdge
)
from semantic_runtime.semantic_graph import (
    SemanticGraph,
    SymbolIdentity,
    SemanticEdge
)
class FullBranchExplorer:
    """
    Explores all semantically significant branches within a bounded execution horizon.
    Constructs a strict DAG RuntimeExecutionGraph and tracks truncation telemetry.
    """

    ALLOWED_EDGE_TYPES = {
        SemanticEdgeType.SYNTHETIC_CONTINUATION,
        SemanticEdgeType.FUNCTION_POINTER_DISPATCH,
        SemanticEdgeType.DIRECT_CALL
    }

    EDGE_PRIORITIES = {
        SemanticEdgeType.SYNTHETIC_CONTINUATION: 3,
        SemanticEdgeType.FUNCTION_POINTER_DISPATCH: 2,
        SemanticEdgeType.DIRECT_CALL: 1
    }
    TERMINAL_NOISE = {
        "printk",
        "pr_info",
        "pr_warn",
        "pr_debug",
        "fprintf",
        "vfprintf",
        "sprintf",
        "snprintf",
        "seq_printf",
        "printf",
        "scnprintf",
    }
    NOISE_PATH_PREFIXES = {
        "tools/",
        "samples/",
        "Documentation/",
    }
    UTILITY_NOISE = {
        "strlen",
        "strcmp",
        "strncmp",
        "memcmp",
        "memcpy",
        "memset",
    }
    SYNC_NOISE = {
        "mutex_lock",
        "mutex_unlock",
        "spin_lock",
        "spin_unlock",
        "mutex_init",
    }
    SEMANTIC_WEIGHT = 10
    PROFILE_WEIGHT = 10
    CONFIDENCE_WEIGHT = 1
    MIN_SCORE_THRESHOLD = 0

    def __init__(
        self,
        semantic_graph,
        max_depth: int = 8,
        max_branches_per_node: int = 5,
        max_total_nodes: int = 75
    ):
        self.semantic_graph = semantic_graph
        self.max_depth = max_depth
        self.max_branches = max_branches_per_node
        self.max_total_nodes = max_total_nodes
        self.root_file = None

    def reconstruct_full_branch_path(
        self,
        runtime_engine,
        profile,
        start_symbol_id: str,
        cpu,
        max_depth) -> Tuple['RuntimeExecutionGraph', Dict[str, Any]]:
        start_symbol = self.semantic_graph.lookup_symbol(start_symbol_id)
        if not start_symbol:
            raise ValueError(f"Start symbol ID {start_symbol_id} not found in graph.")

        self.root_file = start_symbol.file_path

        # ---------------------------------------------------------
        # Initialization
        # ---------------------------------------------------------
        exec_graph = RuntimeExecutionGraph()

        # Add root node (DAG property: node_id == symbol_id)
        exec_graph.nodes[start_symbol_id] = ExecutionNode(
            node_id=start_symbol_id,
            symbol_id=start_symbol_id,
            cpu=None,
            context="FullBranch",
            timestamp=None,
            depth=0
        )

        # Visited Nodes
        expanded_nodes: Set[str] = set()
        runtime_edges_set: Set[str] = set()

        # New: Track how many incoming edges have successfully targeted a node
        node_visit_count = defaultdict(int)

        truncated_branches = 0

        # Queue stores (symbol_id, current_depth)
        queue = deque([(start_symbol_id, 0)])

        # ---------------------------------------------------------
        # Bounded Traversal Loop
        # ---------------------------------------------------------
        while queue and len(exec_graph.nodes) < self.max_total_nodes:
            current_id, current_depth = queue.popleft()

            # 1. Hard depth limit
            if current_depth >= self.max_depth:
                continue

            # 2. DAG Path Uniqueness
            if current_id in expanded_nodes:
                continue
            expanded_nodes.add(current_id)

            # 3. Fetch and filter outgoing edges
            raw_edges = self.semantic_graph.get_outgoing_edges(current_id)
            valid_edges = [
                e for e in raw_edges
                if e.edge_type in self.ALLOWED_EDGE_TYPES
            ]

            # 4. Telemetry: Track branches dropped due to budget
            omitted = max(0, len(valid_edges) - self.max_branches)
            truncated_branches += omitted

            # 5. Branch Selection: Rank by (Priority, Confidence)
            def calculate_edge_rank(edge):
                edge_priority = self.EDGE_PRIORITIES.get(
                    edge.edge_type,
                    0
                )

                noise_penalty = 0
                locality_rank = 0
                boost = 0

                dst_name = ""
                dst_symbol = self.semantic_graph.lookup_symbol(
                    edge.dst_symbol_id
                )
                if dst_symbol:
                    dst_name = dst_symbol.name

                # Apply boost if a profile exists and has the attribute
                if (
                    profile
                    and profile.subsystem_name != "generic"
                    and dst_symbol
                ):
                    boost = profile.execution_spine_boost.get(
                        dst_symbol.name,
                        0
                    )
                if dst_name in self.TERMINAL_NOISE:
                    noise_penalty = -50

                if dst_symbol:
                    if any(
                        dst_symbol.file_path.startswith(prefix)
                        for prefix in self.NOISE_PATH_PREFIXES
                    ):
                        noise_penalty -= 100

                if dst_name in self.UTILITY_NOISE:
                    noise_penalty -= 5

                if dst_name in self.SYNC_NOISE:
                    noise_penalty -= 10

                # --- NEW: Dynamic Revisit Penalty ---
                revisits = node_visit_count[edge.dst_symbol_id]
                revisit_penalty = revisits * 25

                graph_rank = edge.confidence        # confidence
                profile_rank = boost                # hints
                semantic_rank = edge_priority       # dispatch > direct

                # same directory Later implementation yashtbd
                if dst_symbol:
                    locality_rank = self.semantic_graph.locality_rank(
                        self.root_file,
                        dst_symbol.file_path
                    )

                score = (
                    self.SEMANTIC_WEIGHT * semantic_rank +
                    self.PROFILE_WEIGHT * profile_rank +
                    self.CONFIDENCE_WEIGHT * graph_rank +
                    noise_penalty +
                    locality_rank -
                    revisit_penalty
                )

                # Future:
                #   directory proximity
                #   subsystem proximity
                #   provider ownership
                #   CONFIG ownership
                if app_config.runtime.debug_traversal:
                    print(
                        f"score={score:.2f} "
                        f"semantic={semantic_rank} "
                        f"profile={profile_rank} "
                        f"graph={graph_rank} "
                        f"locality={locality_rank} "
                        f"penalty={noise_penalty}"
                    )
                return (
                    score
                    #dst_name
                )

            ranked_edges = sorted(
                valid_edges,
                key=calculate_edge_rank,
                reverse=True
            )

            top_branches = [
                e for e in ranked_edges
                if calculate_edge_rank(e) >= self.MIN_SCORE_THRESHOLD
            ][:self.max_branches]

            if app_config.runtime.debug_traversal:
                current_symbol = self.semantic_graph.lookup_symbol(
                    current_id
                )
                print(
                    f"\nTop branches from "
                    f"{current_symbol.file_path}::{current_symbol.name}"
                )

                for edge in top_branches:
                    dst_symbol = self.semantic_graph.lookup_symbol(
                        edge.dst_symbol_id
                    )

                    print(
                        edge.edge_type.name,
                        dst_symbol.name if dst_symbol else "UNKNOWN",
                        calculate_edge_rank(edge)
                    )

            # 6. Graph Expansion
            for edge in top_branches:
                dst_id = edge.dst_symbol_id

                # 1. NODE CREATION (Guarantee existence before linking)
                if dst_id not in exec_graph.nodes:
                    if len(exec_graph.nodes) >= self.max_total_nodes:
                        break  # Node budget exhausted, do not create this node OR edge

                    dst_symbol = self.semantic_graph.lookup_symbol(dst_id)
                    if not dst_symbol:
                        continue  # Invalid symbol, skip node and edge

                    exec_graph.nodes[dst_id] = ExecutionNode(
                        node_id=dst_id,
                        symbol_id=dst_id,
                        cpu=None,
                        context="FullBranch",
                        timestamp=None,
                        depth=current_depth + 1
                    )

                    # Queue for future exploration
                    queue.append((dst_id, current_depth + 1))

                # 2. TELEMETRY
                # Increment the visit count only if the node actually exists
                node_visit_count[dst_id] += 1

                # 3. EDGE CREATION
                # We only reach this point if dst_id is safely inside exec_graph.nodes
                edge_sig = f"{current_id}->{dst_id}:{edge.edge_type.name}"
                if edge_sig not in runtime_edges_set:
                    runtime_edges_set.add(edge_sig)

                    exec_edge = ExecutionEdge(
                        src_node_id=current_id,
                        dst_node_id=dst_id,
                        semantic_edge_id=edge.edge_id,
                        execution_context=edge.edge_type.name
                    )
                    exec_graph.edges.append(exec_edge)

        # ---------------------------------------------------------
        # Package and Return
        # ---------------------------------------------------------
        stats = {
            "max_depth_reached": self.max_depth,
            "total_nodes": len(exec_graph.nodes),
            "total_edges": len(exec_graph.edges),
            "hit_node_limit": len(exec_graph.nodes) >= self.max_total_nodes,
            "truncated_branches": truncated_branches
        }
        # assert edge.src_node_id in exec_graph.nodes, (
        #     f"Missing src node: {edge.src_node_id}"
        # )

        # assert edge.dst_node_id in exec_graph.nodes, (
        #     f"Missing dst node: {edge.dst_node_id}"
        # )

        return exec_graph, stats