# ============================================================
# IR TEST HARNESS
# ============================================================
class RuntimeGraphPrinter:

    @staticmethod
    def print_graph(
        runtime_graph,
        semantic_graph
    ):

        print("\n@@========== Runtime Execution Graph ==========@@\n")

        # Sort nodes by depth to print the trace chronologically
        nodes_by_depth = sorted(
            runtime_graph.nodes.values(),
            key=lambda n: n.depth
        )

        for node in nodes_by_depth:

            src_symbol = semantic_graph.lookup_symbol(node.symbol_id)

            # 1. Print the primary execution node
            print(f"[Depth={node.depth}] {src_symbol.name}")

            # 2. Print Semantic Annotations (Locks, State changes, etc.)
            if hasattr(node, 'semantic_annotations') and node.semantic_annotations:
                for annotation in node.semantic_annotations:
                    ann_symbol = semantic_graph.lookup_symbol(annotation.dst_symbol_id)
                    ann_name = ann_symbol.name if ann_symbol else annotation.dst_symbol_id
                    print(f"    ├── [{annotation.edge_type.name}] {ann_name}")

            # 3. Print the outgoing runtime edge
            outgoing_edge = next(
                (e for e in runtime_graph.edges if e.src_node_id == node.node_id),
                None
            )

            if outgoing_edge:
                edge_type_name = "UNKNOWN"
                if outgoing_edge.semantic_edge_id:
                    semantic_edge = semantic_graph.semantic_edge_index.get(
                        outgoing_edge.semantic_edge_id
                    )
                    if semantic_edge:
                        edge_type_name = semantic_edge.edge_type.name

                dst_node = runtime_graph.nodes[outgoing_edge.dst_node_id]
                dst_symbol = semantic_graph.lookup_symbol(dst_node.symbol_id)
                dst_name = dst_symbol.name if dst_symbol else dst_node.symbol_id

                print(f"    └── ➔ [{edge_type_name}] {dst_name}")
        print("===================================================\n")