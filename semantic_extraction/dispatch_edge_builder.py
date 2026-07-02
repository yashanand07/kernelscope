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
        file_path,
        operation,
        concrete_func
    ) in raw_edges:
        # print(
        #     f"\n[DISPATCH LOOKUP]"
        #     f"\n  func={concrete_func}"
        #     f"\n  provider_file={file_path}"
        # )
############################### uncomment
        # dst_symbol = semantic_graph.resolve_best_symbol( concrete_func, file_path)
        # if not dst_symbol:
        #     if app_config.runtime.debug_traversal:
        #         print(
        #             f"[DISPATCH DROPPED] "
        #             f"{concrete_func}"
        #         )
        #     continue
###############################

###############################comment
# --- TEMPORARY DEBUG BLOCK START ---
        # 1. Fetch raw matches first to see what we are working with
        raw_matches = semantic_graph.resolve_symbols_by_name(concrete_func)

        if raw_matches:
            # print(f"\n[DISPATCH DEBUG] Attempting to resolve '{concrete_func}'")
            # print(f"  Reference File (Provider context): {file_path}")
            # print(f"  Raw candidates found: {len(raw_matches)}")

            # 2. Replicate the scoring logic visually
            for m in raw_matches:
                score = 0
                if file_path and m.file_path == file_path:
                    score += 100
                if file_path:
                    score += 10 * semantic_graph.locality_rank(file_path, m.file_path)

                #print(f"    -> Candidate: {m.file_path} | Score: {score}")

            # 3. Call the actual method
            dst_symbol = semantic_graph.resolve_best_symbol(
                concrete_func,
                reference_file=file_path
            )

            # if not dst_symbol:
            #     print("  [!] RESULT: resolve_best_symbol returned None. Edge dropped.")
            # else:
            #     print(f"  [+] RESULT: Success. Chose {dst_symbol.file_path}")
        else:
            dst_symbol = None
        # --- TEMPORARY DEBUG BLOCK END ---

        if not dst_symbol:
            continue
###############################




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