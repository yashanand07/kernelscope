
# ============================================================
# IR TEST HARNESS
# ============================================================
class RuntimeGraphPrinter:

    @staticmethod
    def print_graph(
        runtime_graph,
        semantic_graph
    ):

        print(
            "\n========== Runtime Execution Graph =========="
        )

        for edge in runtime_graph.edges:

            edge_type = "UNKNOWN"

            if edge.semantic_edge_id:

                semantic_edge = (
                    semantic_graph.semantic_edge_index.get(
                        edge.semantic_edge_id
                    )
                )

                if semantic_edge:
                    edge_type = (
                        semantic_edge.edge_type.value
                    )

            src_runtime_node = runtime_graph.nodes[
                edge.src_node_id
            ]

            dst_runtime_node = runtime_graph.nodes[
                edge.dst_node_id
            ]
            src_symbol = semantic_graph.lookup_symbol(
                src_runtime_node.symbol_id
            )

            dst_symbol = semantic_graph.lookup_symbol(
                dst_runtime_node.symbol_id
            )

            print(
                f"[{edge_type}] "
                f"{src_symbol.name}"
                f" -> "
                f"{dst_symbol.name}"
            )