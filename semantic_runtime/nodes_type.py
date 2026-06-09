class RuntimeNodeKind(Enum):
    FUNCTION = "FUNCTION"
    INTERFACE = "INTERFACE"
    IMPLEMENTATION = "IMPLEMENTATION"
    LOCK = "LOCK"
    STATE = "STATE"
    IRQ = "IRQ"
    WORKQUEUE = "WORKQUEUE"


# RuntimeNode(
#     node_id,
#     symbol_id,
#     depth
# )

# class RuntimeContext(Enum):
#     PROCESS
#     IRQ
#     SOFTIRQ
#     WORKQUEUE
#     TIMER
#     KTHREAD