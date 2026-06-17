# # Pseudo-code for your next step in dispatch_edge_builder.py
# raw_edges = extract_provider_dispatch_edges(LINUX_ROOT, VFS_PROFILE)

# for operation, concrete_func in raw_edges:
#     # Now you link them into your graph!
#     semantic_graph.add_edge(
#         src=operation, 
#         dst=concrete_func, 
#         edge_type=SemanticEdgeType.FUNCTION_POINTER_DISPATCH
#     )
#from pathlib import Path
#from semantic_runtime.provider_patterns import ProviderPattern
from .provider_extractor import extract_provider_dispatch_edges
from semantic_runtime.semantic_graph import SemanticGraph, SemanticEdgeType
#from profiles.vfs_profile import VFS_PROFILE
from config.config import app_config

def build_dispatch_edges(
    semantic_graph,
    profile,
    kernel_root
):
    raw_edges = (
        extract_provider_dispatch_edges(
            kernel_root,
            profile
        )
    )

    if app_config.runtime.debug_traversal:
        print(
            f"[DISPATCH] extracted "
            f"{len(raw_edges)} provider edges"
        )

    dispatch_count = 0

    for (
        provider_kind,  # e.g., "file_operations"
        provider_name,
        operation,
        concrete_func
    ) in raw_edges:

        matches = semantic_graph.resolve_symbols_by_name(
            concrete_func
        )

        if not matches:
            continue

        if len(matches) > 1:
            if app_config.runtime.debug_traversal:
                print(
                    f"[DISPATCH AMBIGUITY] "
                    f"{concrete_func} -> {len(matches)} matches"
                )
                for m in matches[:5]:
                    print(f"    {m.file_path}")

            continue
        
        dst_symbol = matches[0]
        

        if not dst_symbol:
            if app_config.runtime.debug_traversal:
                print(
                    f"[DISPATCH] unresolved implementation: "
                    f"{concrete_func}"
                )
            continue

        interface_id = (
            semantic_graph
            .resolve_or_create_interface(
                provider_kind=provider_kind,
                operation=operation
            )
        )

        semantic_graph.register_semantic_edge(
            src_symbol_id=interface_id,
            dst_symbol_id=dst_symbol.symbol_id,
            edge_type=SemanticEdgeType.FUNCTION_POINTER_DISPATCH,
            confidence=1.0,
            resolution_source="provider_extraction"
        )

        dispatch_count += 1

    if app_config.runtime.debug_traversal:
        print(
            f"[DISPATCH] registered "
            f"{dispatch_count} dispatch edges"
        )