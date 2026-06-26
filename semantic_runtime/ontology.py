# ============================================================
# ENUMS
# ============================================================
# Defining semantic edge types to capture different kinds of
# relationships in the kernel's execution flow.
# | -------------------------------- | ------------------------- |
# | Layer                            | Meaning                   |
# | -------------------------------- | ------------------------- |
# | Control-flow semantics           | DIRECT_CALL               |
# | Dispatch semantics               | FUNCTION_POINTER_DISPATCH |
# | Runtime reconstruction semantics | SYNTHETIC_CONTINUATION    |
# | Concurrency semantics            | ASYNC_WAKEUP              |
# | Context semantics                | INTERRUPT_ENTRY           |
# | State semantics                  | STATE_MUTATION            |
# | Synchronization semantics        | LOCK_*                    |
from enum import Enum

class SemanticEdgeType(Enum):
    DIRECT_CALL = "DIRECT_CALL" # schedule() -> __schedule()
    FUNCTION_POINTER_DISPATCH = "FUNCTION_POINTER_DISPATCH" # p->sched_class->enqueue_task(...) -> enqueue_task_fair
    SYNTHETIC_CONTINUATION  = "SYNTHETIC_CONTINUATION" # pick_next_task_fair -> context_switch
    ASYNC_WAKEUP = "ASYNC_WAKEUP" # try_to_wake_up -> ttwu_do_activate
    INTERRUPT_ENTRY = "INTERRUPT_ENTRY" # Hardware interrupt -> do_IRQ
    INTERRUPT_EXIT = "INTERRUPT_EXIT" # irq_exit -> schedule
    STATE_MUTATION = "STATE_MUTATION" # set_current_state(TASK_INTERRUPTIBLE)
    LOCK_ACQUIRE = "LOCK_ACQUIRE" # raw_spin_lock_irqsave(&rq->lock, flags)
    LOCK_RELEASE = "LOCK_RELEASE" # raw_spin_unlock_irqrestore(&rq->lock, flags)
    WORKQUEUE_QUEUE = "WORKQUEUE_QUEUE" # queue_work(system_wq, &my_work)
    WORKQUEUE_EXECUTE = "WORKQUEUE_EXECUTE" # Worker thread execution -> my_work_func
    MACRO_ALIAS = "MACRO_ALIAS"
    # Add more edge types as needed for richer semantics

    @property
    def is_runtime_traversable(
        self
    ) -> bool:
        return self in {
            SemanticEdgeType.DIRECT_CALL,
            SemanticEdgeType.FUNCTION_POINTER_DISPATCH,
            SemanticEdgeType.SYNTHETIC_CONTINUATION,
            SemanticEdgeType.ASYNC_WAKEUP,
            SemanticEdgeType.INTERRUPT_ENTRY,
            SemanticEdgeType.INTERRUPT_EXIT,
            SemanticEdgeType.WORKQUEUE_EXECUTE
        }

    @property
    def expands_execution_paths(self) -> bool:
        return self in {
            SemanticEdgeType.FUNCTION_POINTER_DISPATCH,
            SemanticEdgeType.ASYNC_WAKEUP
        }

    @property
    def changes_execution_context(
        self
    ) -> bool:

        return self in {
            SemanticEdgeType.INTERRUPT_ENTRY,
            SemanticEdgeType.INTERRUPT_EXIT
        }

    @property
    def is_interrupt(self) -> bool:
        """Represents hardware/ISR boundary crossings."""
        return self in {
            SemanticEdgeType.INTERRUPT_ENTRY,
            SemanticEdgeType.INTERRUPT_EXIT
        }

    @property
    def is_state_mutation(self) -> bool:
        """Represents internal state/lock changes rather than logic jumps."""
        return self in {
            SemanticEdgeType.STATE_MUTATION,
            SemanticEdgeType.LOCK_ACQUIRE,
            SemanticEdgeType.LOCK_RELEASE
        }

    @property
    def is_synchronization(self) -> bool:

        return self in {
            SemanticEdgeType.LOCK_ACQUIRE,
            SemanticEdgeType.LOCK_RELEASE
        }

