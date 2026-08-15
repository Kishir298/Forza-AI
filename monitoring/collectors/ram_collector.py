import psutil


def get_ram():
    """Return system RAM and swap memory information."""

    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()

    return {
        "component": "RAM",
        "total_gb": round(memory.total / (1024 ** 3), 2),
        "used_gb": round(memory.used / (1024 ** 3), 2),
        "available_gb": round(memory.available / (1024 ** 3), 2),
        "usage_percent": round(memory.percent, 1),
        "free_gb": round(memory.available / (1024 ** 3), 2),
        "swap_total_gb": round(swap.total / (1024 ** 3), 2),
        "swap_used_gb": round(swap.used / (1024 ** 3), 2),
        "swap_usage_percent": round(swap.percent, 1),
    }