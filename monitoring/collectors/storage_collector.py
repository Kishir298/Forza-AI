import psutil


def get_storage():
    """Return storage information for the main system drive."""

    partitions = psutil.disk_partitions(all=False)

    system_partition = None

    for partition in partitions:
        mountpoint = partition.mountpoint

        if mountpoint:
            system_partition = partition
            break

    if system_partition is None:
        return {
            "component": "Storage",
            "total_gb": None,
            "used_gb": None,
            "free_gb": None,
            "usage_percent": None,
            "mountpoint": None,
            "filesystem": None,
        }

    try:
        usage = psutil.disk_usage(system_partition.mountpoint)

        return {
            "component": "Storage",
            "total_gb": round(usage.total / (1024 ** 3), 2),
            "used_gb": round(usage.used / (1024 ** 3), 2),
            "free_gb": round(usage.free / (1024 ** 3), 2),
            "usage_percent": round(usage.percent, 1),
            "mountpoint": system_partition.mountpoint,
            "filesystem": system_partition.fstype or None,
        }

    except (PermissionError, OSError):
        return {
            "component": "Storage",
            "total_gb": None,
            "used_gb": None,
            "free_gb": None,
            "usage_percent": None,
            "mountpoint": system_partition.mountpoint,
            "filesystem": system_partition.fstype or None,
        }