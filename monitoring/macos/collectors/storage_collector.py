import psutil


def _bytes_to_gb(value):
    if value is None:
        return None

    return round(value / (1024 ** 3), 2)


def get_storage():
    """
    Collect macOS storage information.

    Returns information about mounted filesystems while
    ignoring pseudo-filesystems and temporary system mounts.
    """

    try:
        drives = []

        seen_mounts = set()

        for partition in psutil.disk_partitions(
            all=False
        ):
            mount = partition.mountpoint

            if mount in seen_mounts:
                continue

            seen_mounts.add(mount)

            # Ignore temporary/system pseudo-filesystems.
            if mount.startswith(
                (
                    "/System/Volumes/VM",
                    "/System/Volumes/Preboot",
                    "/System/Volumes/Update",
                    "/private/var/vm",
                )
            ):
                continue

            try:
                usage = psutil.disk_usage(
                    mount
                )

            except Exception:
                continue

            drives.append(
                {
                    "mount": mount,
                    "filesystem": partition.fstype,
                    "total_bytes": usage.total,
                    "used_bytes": usage.used,
                    "free_bytes": usage.free,
                    "usage_percent": round(
                        usage.percent,
                        1,
                    ),
                    "total_gb": _bytes_to_gb(
                        usage.total
                    ),
                    "used_gb": _bytes_to_gb(
                        usage.used
                    ),
                    "free_gb": _bytes_to_gb(
                        usage.free
                    ),
                }
            )

        return {
            "component": "Storage",
            "available": bool(drives),
            "drives": drives,
        }

    except Exception as error:
        return {
            "component": "Storage",
            "available": False,
            "error": str(error),
            "drives": [],
        }
