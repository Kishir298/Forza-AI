import psutil


def _bytes_to_gb(value):
    if value is None:
        return None

    return round(value / (1024 ** 3), 2)


def get_storage():
    """
    Collect Linux storage information.

    Returns information about mounted physical and
    persistent filesystems while avoiding duplicate mounts.
    """

    try:
        drives = []

        seen_devices = set()
        seen_mounts = set()

        for partition in psutil.disk_partitions(
            all=False
        ):
            device = partition.device
            mount = partition.mountpoint

            if (
                device in seen_devices
                or mount in seen_mounts
            ):
                continue

            seen_devices.add(device)
            seen_mounts.add(mount)

            # Ignore pseudo-filesystems.
            if partition.fstype.lower() in {
                "tmpfs",
                "devtmpfs",
                "proc",
                "sysfs",
                "cgroup",
                "cgroup2",
                "overlay",
                "squashfs",
            }:
                continue

            try:
                usage = psutil.disk_usage(
                    mount
                )

            except Exception:
                continue

            drives.append(
                {
                    "device": device,
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
