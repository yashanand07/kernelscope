from profiles.subsystem_profile import SubsystemSemanticProfile
from semantic_runtime.provider_patterns import ProviderPattern

# =============================================================================
# 1. MEMORY MANAGEMENT (MM) PROFILE
# =============================================================================

MM_PROVIDER_PATTERNS = [
    ProviderPattern(
        suffix="_vm_ops",
        provider_kind="vm_operations",
        struct_type="vm_operations_struct",
        macro_name="" # Usually direct static const assignment
    )
]

MM_PROFILE = (
    SubsystemSemanticProfile(
        subsystem_name="mm",

        entrypoints=["handle_mm_fault", "do_page_fault", "__alloc_pages"],

        low_signal_calls={
            "page_get",
            "put_page",
            "folio_get",
            "folio_put",
            "SetPageDirty",
            "WARN_ON_ONCE",
            "pte_unmap_unlock",
            "rcu_read_lock",
            "rcu_read_unlock",
        },

        execution_spine_boost={
            "handle_mm_fault": 10.0,
            "__handle_mm_fault": 10.0,
            "handle_pte_fault": 10.0,
            "do_anonymous_page": 10.0,
            "do_fault": 10.0,
            "do_swap_page": 10.0,
            "__alloc_pages": 10.0,
            "get_page_from_freelist": 10.0,
        },

        high_value_transitions={
            ("handle_mm_fault", "__handle_mm_fault"): 20.0,
            ("__handle_mm_fault", "handle_pte_fault"): 20.0,
            ("handle_pte_fault", "do_pte_missing"): 20.0,
            ("do_pte_missing", "do_fault"): 30.0,
            ("do_pte_missing", "do_anonymous_page"): 20.0,
            ("__alloc_pages", "get_page_from_freelist"): 20.0,
        },

        synthetic_bridges={
            "do_fault": "vm_operations:fault",
            "do_page_mkwrite": "vm_operations:page_mkwrite",
        },

        associated_structs={
            "mm_struct",
            "vm_area_struct",
            "page",
            "folio",
            "vm_operations_struct",
            "zonelist",
            "zone",
        },

        dispatch_provider_files=[
            "mm/memory.c",
            "mm/filemap.c",
            "mm/shmem.c",
            "mm/huge_memory.c"
        ],

        provider_patterns=MM_PROVIDER_PATTERNS,

        valid_dispatch_operations={
            "fault",
            "page_mkwrite",
            "map_pages",
            "pfn_mkwrite",
        },

        runtime_depth_limit=16,
        terminal_symbols= {
            "filemap_fault",
            "shmem_fault",
            "do_swap_page",
            "do_anonymous_page",
        }
        # preferred_symbols={
        #     "do_pte_missing",
        #     "do_fault",
        # }
    )
)