import psutil


def get_ram():

    memory = psutil.virtual_memory()

    swap = psutil.swap_memory()


    total = round(
        memory.total / (1024 ** 3),
        2
    )

    used = round(
        memory.used / (1024 ** 3),
        2
    )

    available = round(
        memory.available / (1024 ** 3),
        2
    )


    return {

        "component": "RAM",

        "total_gb": total,

        "used_gb": used,

        "available_gb": available,

        "usage_percent": memory.percent,

        "free_gb": available,

        "swap_total_gb": round(
            swap.total / (1024 ** 3),
            2
        ),

        "swap_used_gb": round(
            swap.used / (1024 ** 3),
            2
        )

    }
