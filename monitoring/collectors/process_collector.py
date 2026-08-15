import psutil


def get_processes(limit=10):
    """
    Return the processes currently using the most memory.

    Works across Windows, macOS, and Linux through psutil.
    """

    processes = []

    for process in psutil.process_iter(
        ["pid", "name", "cpu_percent", "memory_percent"]
    ):
        try:
            info = process.info

            processes.append(
                {
                    "pid": info["pid"],
                    "name": info["name"] or "Unknown",
                    "cpu_percent": round(info["cpu_percent"] or 0, 1),
                    "memory_percent": round(
                        info["memory_percent"] or 0,
                        2,
                    ),
                }
            )

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
            continue

    processes.sort(
        key=lambda process: process["memory_percent"],
        reverse=True,
    )

    return {
        "component": "Processes",
        "processes": processes[:limit],
    }