import psutil


def get_ram():
    """
    Collect current RAM information on Windows.

    Returns raw/current RAM information.
    Historical analysis belongs to the processing layer.
    """

    try:
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        return {
            "component": "RAM",
            "available": True,

            "total_bytes": memory.total,
            "used_bytes": memory.used,
            "available_bytes": memory.available,
            "free_bytes": memory.free,
            "usage_percent": round(
                memory.percent,
                1,
            ),

            "swap": {
                "total_bytes": swap.total,
                "used_bytes": swap.used,
                "free_bytes": swap.free,
                "usage_percent": round(
                    swap.percent,
                    1,
                ),
            },
        }

    except Exception as error:
        return {
            "component": "RAM",
            "available": False,
            "error": str(error),

            "total_bytes": None,
            "used_bytes": None,
            "available_bytes": None,
            "free_bytes": None,
            "usage_percent": None,

            "swap": {
                "total_bytes": None,
                "used_bytes": None,
                "free_bytes": None,
                "usage_percent": None,
            },
        }
