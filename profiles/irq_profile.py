# =============================================================================
# 5. INTERRUPTS (IRQ) PROFILE
# =============================================================================
from profiles.subsystem_profile import (
    SubsystemSemanticProfile
)
from semantic_runtime.provider_patterns import (
    ProviderPattern
)
IRQ_PROVIDER_PATTERNS = [
    ProviderPattern(
        suffix="_chip",
        provider_kind="irq_chip",
        struct_type="irq_chip",
        macro_name=""
    ),
    ProviderPattern(
        suffix="_action",
        provider_kind="irqaction",
        struct_type="irqaction",
        macro_name=""
    )
]

IRQ_PROFILE = (
    SubsystemSemanticProfile(
        subsystem_name="kernel/irq",
        
        entrypoints=["handle_irq_event", "__do_softirq", "irq_exit"],

        entrypoint_files=[
            "kernel/irq/handle.c"
        ],

        low_signal_calls={
            "irq_state_set",
            "irqd_irq_disabled",
            "local_irq_enable",
            "local_irq_disable",
            "rcu_irq_enter",
            "rcu_irq_exit",
        },
        
        execution_spine_boost={
            "handle_irq_event": 10.0,
            "handle_irq_event_percpu": 10.0,
            "__handle_irq_event_percpu": 10.0,
            "do_softirq": 10.0,
            "__do_softirq": 10.0,
            "irq_exit": 10.0,
            "irq_exit_rcu": 10.0,
        },
        
        high_value_transitions={
            ("handle_irq_event", "handle_irq_event_percpu"): 20.0,
            ("handle_irq_event_percpu", "__handle_irq_event_percpu"): 20.0,
            ("irq_exit", "irq_exit_rcu"): 20.0,
            ("irq_exit_rcu", "__do_softirq"): 15.0, # Softirqs often trigger on hard IRQ exit
        },
        
        synthetic_bridges={
            "__handle_irq_event_percpu": "irqaction:handler",
            "__do_softirq": "softirq_action:action",
            "mask_irq": "irq_chip:irq_mask",
            "unmask_irq": "irq_chip:irq_unmask",
            "ack_irq": "irq_chip:irq_ack",
        },
        
        associated_structs={
            "irq_desc",
            "irqaction",
            "irq_chip",
            "irq_data",
            "softirq_action",
        },
        
        dispatch_provider_files=[
            "kernel/irq/handle.c",
            "kernel/irq/chip.c",
            "kernel/softirq.c",
            "kernel/irq/spurious.c"
        ],
        
        provider_patterns=IRQ_PROVIDER_PATTERNS,
        
        valid_dispatch_operations={
            "handler",
            "action",
            "irq_mask",
            "irq_unmask",
            "irq_ack",
            "irq_eoi",
        },
        
        runtime_depth_limit=14,
        terminal_symbols={  #yashtbd
            # "note_interrupt",
            # "wake_up_process"
        }
    )
)