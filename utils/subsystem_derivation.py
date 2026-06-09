# =================================================================
# Convert filesystem paths into canonical semantic subsystem names.
# =================================================================
from typing import Dict

# ============================================================
# SUBSYSTEM DETECTION
# ============================================================

SUBSYSTEM_MAP = {
    "kernel/sched": "scheduler",
    "kernel/irq": "interrupts",
    "kernel/softirq": "softirq",
    "fs": "vfs",
    "mm": "memory_management",
    "block": "block_layer",
    "net": "networking",
    "drivers": "drivers",
}

def derive_subsystem(file_path: str) -> str:

    normalized = file_path.strip("/")

    for prefix, subsystem in SUBSYSTEM_MAP.items():
        if normalized.startswith(prefix):
            return subsystem

    return "kernel_core"