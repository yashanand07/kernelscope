def reconstruct_runtime_spine(
    runtime_engine,
    profile,
    start_symbol_id,
    cpu,
    max_depth=16
):
    print(f"Reconstructing Runtime Spine for Symbol: {start_symbol_id} on CPU: {cpu}")
    print(f"Using Profile: {profile.subsystem_name}")
    print(f"Max Depth: {max_depth}\n")
    print("But I called reconstruct_implementation_path for spine construction...\n")
    return reconstruct_implementation_path(
        runtime_engine,
        profile,
        start_symbol_id,
        cpu,
        max_depth
    )

# def reconstruct_runtime_spine(
#     runtime_engine,
#     profile,
#     start_symbol_id: str,
#     cpu: int,
#     max_depth: int = 16
# ) -> RuntimeExecutionGraph:

#     runtime_graph = RuntimeExecutionGraph()

#     # Prevent cycles and redundant traversal.
#     visited_symbols = set()

#     current_symbol_id = start_symbol_id
#     previous_node_id = None

#     # Tracks the edge that produced the current node.
#     incoming_edge = None

#     for depth in range(max_depth):

#         # Cycle Prevention
#         if current_symbol_id in visited_symbols:
#             break

#         visited_symbols.add(current_symbol_id)

#         # Create Current Execution Node
#         node_id = runtime_engine.generate_execution_node_id(
#             symbol_id=current_symbol_id,
#             cpu=cpu,
#             depth=depth + 1,  # Depth starts at 1 for better readability
#             context="process_context"
#         )

#         node = ExecutionNode(
#             node_id=node_id,

#             symbol_id=current_symbol_id,

#             cpu=cpu,

#             context="process_context",

#             timestamp=None,

#             depth=depth + 1,
#         )

#         runtime_graph.add_node(node)

#         if previous_node_id is not None and incoming_edge is not None:
#             runtime_graph.add_edge(incoming_edge)

#         # Determine Next Symbol to Traverse
#         next_symbol_id = runtime_engine.get_next_symbol_in_execution_spine(
#             current_symbol_id=current_symbol_id,
#             profile=profile
#         )

#         if next_symbol_id is None:
#             break

#         # Prepare for Next Iteration
#         incoming_edge = ExecutionEdge(
#             source_node_id=node.node_id,
#             target_node_id=None,  # To be filled in the next iteration
#             edge_type=SemanticEdgeType.EXECUTION_FLOW
#         )

#         previous_node_id = node.node_id
#         current_symbol_id = next_symbol_id

#     return runtime_graph