# -----------------------------
# Mermaid call graph export
# -----------------------------
# LEGACY - Will convert toMermaidGraphExporter which is the semantic graph exporter - yashtbd
from datetime import datetime
from semantic_runtime.ontology import (
    SemanticEdgeType
)
import os

class MermaidGraphExporter:

    @staticmethod
    def export_runtime_graph(
        runtime_graph,
        semantic_graph,
        profile,
        output_dir="exports"
    ):

        os.makedirs(
            output_dir,
            exist_ok=True
        )

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        subsystem = (
            profile.subsystem_name
            .replace("/", "_")
        )

        output_file = os.path.join(
            output_dir,
            f"{subsystem}_runtime_{timestamp}.mmd"
        )

        lines = [
            "graph TD\n"
        ]
        content = "graph TD\n"

        for edge in runtime_graph.edges:

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

            semantic_edge = semantic_graph.semantic_edge_index.get(
                edge.semantic_edge_id
            )
            if semantic_edge.edge_type == SemanticEdgeType.MACRO_ALIAS:
                link_style = f"-. {semantic_edge.edge_type.name} .->"
            elif semantic_edge.edge_type == SemanticEdgeType.FUNCTION_POINTER_DISPATCH:
                link_style = f"== {semantic_edge.edge_type.name} ==>"
            else:
                link_style = f"-- {semantic_edge.edge_type.name} -->"

            content += (
                f"    {src_symbol.name}"
                f"{link_style}"
                f"{dst_symbol.name}\n"
            )
        with open(output_file, "w") as f:
            f.write(content)

        print(
            f" Mermaid graph exported to "
            f"{output_file}"
        )