from .scheduler_profile import SCHEDULER_PROFILE
from .vfs_profile import VFS_PROFILE
from .mm_profile import MM_PROFILE
from .net_profile import NET_PROFILE
from .block_profile import BLOCK_PROFILE
from .irq_profile import IRQ_PROFILE
from .workqueue_profile import WORKQUEUE_PROFILE

SCHED_KEYWORDS = {
    "sched",
    "scheduler",
    "task",
    "context switch",
    "runqueue",
}

VFS_KEYWORDS = {
    "vfs",
    "file",
    "filesystem",
    "read",
    "write",
    "inode",
    "dentry",
}

MM_KEYWORDS = {
    "mm",
    "memory",
    "page",
    "fault",
    "allocation",
    "allocator",
    "slab",
    "folio",
}

NET_KEYWORDS = {
    "net",
    "network",
    "tcp",
    "udp",
    "socket",
    "skb",
    "packet",
}

BLOCK_KEYWORDS = {
    "block",
    "bio",
    "request",
    "nvme",
    "disk",
    "storage",
}

IRQ_KEYWORDS = {
    "irq",
    "interrupt",
    "softirq",
    "hardirq",
}

WORKQUEUE_KEYWORDS = {
    "workqueue",
}

def determine_subsystem_profile(query: str):
    q = query.lower()

    if any(k in q for k in SCHED_KEYWORDS):
        return SCHEDULER_PROFILE

    if any(k in q for k in VFS_KEYWORDS):
        return VFS_PROFILE

    if any(k in q for k in IRQ_KEYWORDS):
        return IRQ_PROFILE
    elif any(k in q for k in NET_KEYWORDS):
        return NET_PROFILE
    elif any(k in q for k in BLOCK_KEYWORDS):
        return BLOCK_PROFILE
    elif any(k in q for k in MM_KEYWORDS):
        return MM_PROFILE
    elif any(k in q for k in WORKQUEUE_KEYWORDS):
        return WORKQUEUE_PROFILE
    else:
        return None