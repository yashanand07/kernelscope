# =============================================================================
# 4. GENERIC PROFILE
# =============================================================================
from profiles.subsystem_profile import (
    SubsystemSemanticProfile
)
from semantic_runtime.provider_patterns import (
    ProviderPattern
)
GENERIC_PROVIDER_PATTERNS = [
    # Workqueues generally resolve directly to `work_struct->func` without 
    # a dedicated ops struct array, but we track the initialization macros.
    ProviderPattern(
        suffix="",
        provider_kind="",
        struct_type="",
        macro_name=""
    )
]

GENERIC_PROFILE = (
    SubsystemSemanticProfile(
        subsystem_name="generic",
        
        entrypoints=[], # This will be filled by the generic query once validated

        entrypoint_files=[], # This will be filled by the generic query once validated

        low_signal_calls={},
        
        execution_spine_boost={},
        
        high_value_transitions={},
        
        synthetic_bridges={},
        
        associated_structs={},
        
        dispatch_provider_files=[],
        
        provider_patterns=GENERIC_PROVIDER_PATTERNS,
        
        valid_dispatch_operations={},
        
        runtime_depth_limit=16,
        terminal_symbols={}
    )
)