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
        
        low_signal_calls={
            "bio_get",
            "bio_put",
            "blk_queue_enter",
            "blk_queue_exit",
            "rcu_read_lock",
            "spin_lock_irqsave",
        },
        
        execution_spine_boost={
            "submit_bio": 10.0,
            "submit_bio_noacct": 10.0,
            "blk_mq_submit_bio": 10.0,
            "__blk_mq_issue_directly": 10.0,
            "blk_mq_dispatch_rq_list": 10.0,
            "blk_mq_sched_insert_request": 10.0,
        },
        
        high_value_transitions={
            ("submit_bio", "submit_bio_noacct"): 20.0,
            ("submit_bio_noacct", "blk_mq_submit_bio"): 20.0,
            ("blk_mq_submit_bio", "__blk_mq_issue_directly"): 20.0,
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