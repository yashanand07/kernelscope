# =============================================================================
# 4. WORKQUEUE PROFILE
# =============================================================================
from profiles.subsystem_profile import (
    SubsystemSemanticProfile
)
from semantic_runtime.provider_patterns import (
    ProviderPattern
)
WORKQUEUE_PROVIDER_PATTERNS = [
    # Workqueues generally resolve directly to `work_struct->func` without
    # a dedicated ops struct array, but we track the initialization macros.
    ProviderPattern(
        suffix="",
        provider_kind="work_func",
        struct_type="work_struct",
        macro_name="INIT_WORK"
    )
]

WORKQUEUE_PROFILE = (
    SubsystemSemanticProfile(
        subsystem_name="kernel/workqueue",

        entrypoints=[
            "queue_work_on",
            "worker_thread",
        ],

        # entrypoints=[
        #     "worker_thread"
        # ],
        entrypoint_files=[
            "kernel/workqueue.c"
        ],

        low_signal_calls={
            "local_irq_save",
            "local_irq_restore",
            "spin_lock_irq",
            "spin_unlock_irq",
            "lock_map_acquire",
            "lock_map_release",
            "debug_work_activate",
            "debug_object_activate",
            "debug_objects_fill_pool",
            "pool_should_refill",
            "pool_count",
        },

        execution_spine_boost={
            "queue_work": 10.0,
            "queue_work_on": 10.0,
            "__queue_work": 10.0,
            "insert_work": 10.0,
            "worker_thread": 10.0,
            "process_one_work": 10.0,
            #"set_work_pwq": 10.0,
            #"get_pwq": 10.0,
            "process_scheduled_works": 10.0,
            "process_one_work": 10.0,
            "process_scheduled_works": 10.0,
            "process_one_work": 10.0,
        },

        high_value_transitions={
            ("insert_work", "set_work_pwq"): 20.0,
            ("queue_work", "queue_work_on"): 20.0,
            ("queue_work_on", "__queue_work"): 20.0,
            ("__queue_work", "insert_work"): 20.0,
            ("worker_thread", "process_one_work"): 20.0,
            ("worker_thread", "process_scheduled_works"): 20.0,
            ("process_scheduled_works", "process_one_work"): 20.0,
        },

        synthetic_bridges={
            "process_one_work": "work_struct:func",
        },

        associated_structs={
            "work_struct",
            "workqueue_struct",
            "worker",
            "worker_pool",
            "pool_workqueue",
        },

        dispatch_provider_files=[
            "kernel/workqueue.c"
        ],

        provider_patterns=WORKQUEUE_PROVIDER_PATTERNS,

        valid_dispatch_operations={
            "func",
        },

        runtime_depth_limit=12,
        terminal_symbols={
            "work_struct:func"
        }
    )
)