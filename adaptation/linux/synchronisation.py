def get_linux_sync_profile() -> dict:
    return {
        "acquire": {
            "spin_lock": {"irqsave": False, "recursive": False},
            "raw_spin_lock": {"irqsave": False, "recursive": False},
            "mutex_lock": {"irqsave": False, "recursive": False},
            "spin_lock_irqsave": {"irqsave": True, "recursive": False},
            "rq_lock": {"irqsave": False, "recursive": False},
        },
        "release": {
            "spin_unlock": {"irqrestore": False},
            "raw_spin_unlock": {"irqrestore": False},
            "mutex_unlock": {"irqrestore": False},
            "spin_unlock_irqrestore": {"irqrestore": True},
            "raw_spin_rq_unlock_irq": {"irqrestore": True},
        },
        "interrupt": {
            "local_irq_disable": {"action": "disable"},
            "raw_local_irq_disable": {"action": "disable"},
            "local_irq_enable": {"action": "enable"},
            "raw_local_irq_enable": {"action": "enable"},
        }
    }