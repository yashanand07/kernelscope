# =============================================================================
# 3. BLOCK IO (BLOCK) PROFILE
# =============================================================================
from profiles.subsystem_profile import (
    SubsystemSemanticProfile
)
from semantic_runtime.provider_patterns import (
    ProviderPattern
)
BLOCK_PROVIDER_PATTERNS = [
    ProviderPattern(
        suffix="_mq_ops",
        provider_kind="blk_mq_ops",
        struct_type="blk_mq_ops",
        macro_name=""
    )
]

BLOCK_PROFILE = (
    SubsystemSemanticProfile(
        subsystem_name="block",
        
        entrypoints=["submit_bio", "blk_mq_submit_bio", "blk_mq_dispatch_rq_list"],

        entrypoint_files=[
            "block/blk-core.c"
        ],

        low_signal_calls = {
            "should_fail_bio",
            "should_fail_request",
            "should_fail",
            "should_fail_ex",
            "fail_stacktrace",
        },
        
        execution_spine_boost={
            "submit_bio": 10.0,
            "submit_bio_noacct": 10.0,
            "submit_bio_noacct_nocheck": 10.0,
            "blk_mq_submit_bio": 10.0,
        },
        
        high_value_transitions = {
            ("submit_bio", "submit_bio_noacct"): 20.0,
            ("submit_bio_noacct", "submit_bio_noacct_nocheck"): 20.0,
            ("submit_bio_noacct_nocheck", "__submit_bio_noacct"): 20.0,
            ("__submit_bio_noacct", "__submit_bio"): 20.0,
            ("__submit_bio", "blk_mq_submit_bio"): 20.0,
        },
        
        synthetic_bridges={
            "__blk_mq_issue_directly": "blk_mq_ops:queue_rq",
            "blk_mq_dispatch_rq_list": "blk_mq_ops:queue_rq",
        },
        
        associated_structs={
            "bio",
            "request",
            "request_queue",
            "blk_mq_hw_ctx",
            "blk_mq_ops",
            "gendisk",
        },
        
        dispatch_provider_files=[
            "block/blk-core.c",
            "block/blk-mq.c",
            "block/blk-mq-sched.c"
        ],
        
        provider_patterns=BLOCK_PROVIDER_PATTERNS,
        
        valid_dispatch_operations={
            "queue_rq",
            "commit_rqs",
            "complete",
        },
        
        runtime_depth_limit=16,
        terminal_symbols={
            "bio_endio",
            "blk_mq_end_request"
        }
    )
)