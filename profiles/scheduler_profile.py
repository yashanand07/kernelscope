from profiles.subsystem_profile import (
    SubsystemSemanticProfile
)
from semantic_runtime.provider_patterns import (
    ProviderPattern
)

SCHEDULER_PROVIDER_PATTERNS = [
    ProviderPattern(
        suffix="_sched_class",
        provider_kind="scheduler_class",
        macro_name="DEFINE_SCHED_CLASS"
    )
]

SCHEDULER_PROFILE = (
    SubsystemSemanticProfile(
        subsystem_name="kernel/sched",

        entrypoints=["schedule", "try_to_wake_up", "wake_up_process"],

        low_signal_calls = {
            "lockdep_assert",
            "task_is_running",
            "schedstat_inc",
            "trace_sched_switch",
            "rcu_note_context_switch",
            "might_sleep",
            "preempt_disable",
            "preempt_enable",
            "WARN_ON",
        },

        execution_spine_boost = {
            "schedule": 10.0,
            "__schedule": 10.0,
            "pick_next_task": 10.0,
            "__pick_next_task": 10.0,
            #"pick_next_task_fair": 10.0,
            "context_switch": 10.0,
            "__switch_to": 10.0,
            "finish_task_switch": 10.0,
            "__schedule_loop": 10.0,
        },

        high_value_transitions = {
            ("schedule", "__schedule"): 20.0,
            ("__schedule", "pick_next_task"): 20.0,
            ("pick_next_task", "__pick_next_task"): 20.0,
            ("context_switch", "__switch_to"): 20.0,
            ("__switch_to", "finish_task_switch"): 20.0,
            ("schedule", "__schedule_loop"): 20.0,
            ("__schedule_loop", "__schedule"): 20.0,
        },

        # These are manually curated edges that we know exist but are not easily
        # detectable through regex parsing due to indirect calls, function pointer
        # dispatches, or complex control flow. They help bridge gaps in the semantic
        # graph and enable more complete execution path reconstruction.
        synthetic_bridges = {
            "pick_next_task_fair": "context_switch",
            "pick_next_task_rt": "context_switch",
            "pick_next_task_idle": "context_switch",
            "context_switch": "__switch_to",
            "__switch_to": "finish_task_switch",
        },
        associated_structs={
            "task_struct",
            "rq",
            "sched_class",
            "sched_entity",
            "cfs_rq",
            "rt_rq",
            "dl_rq"
        },
        dispatch_provider_files=[
            "kernel/sched/fair.c",
            "kernel/sched/rt.c",
            "kernel/sched/idle.c",
            "kernel/sched/deadline.c"
        ],
        provider_patterns = SCHEDULER_PROVIDER_PATTERNS,
        valid_dispatch_operations = {
            "pick_next_task",
            "pick_task",
            "enqueue_task",
            "dequeue_task",
            "check_preempt_curr",
            "yield_task",
            "wakeup_preempt",
        }
    )
)