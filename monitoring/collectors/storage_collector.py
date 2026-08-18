import platform
import shutil

import psutil


def _get_partitions():
    """
    Get mounted storage partitions across Windows, macOS and Linux.
    """

    partitions = []

    try:
        for partition in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(partition.mountpoint)

                partitions.append(
                    {
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "filesystem": partition.fstype,
                        "total_bytes": usage.total,
                        "used_bytes": usage.used,
                        "free_bytes": usage.free,
                        "usage_percent": round(
                            usage.percent,
                            1,
                        ),
                    }
                )

            except (PermissionError, OSError):
                continue

    except Exception:
        pass

    return partitions


def _get_root_storage():
    """
    Get storage information for the main system filesystem.
    """

    try:
        path = (
            "C:\\"
            if platform.system() == "Windows"
            else "/"
        )

        total, used, free = shutil.disk_usage(path)

        return {
            "path": path,
            "total_bytes": total,
            "used_bytes": used,
            "free_bytes": free,
            "usage_percent": round(
                (used / total) * 100,
                1,
            ) if total else None,
        }

    except Exception:
        return {
            "path": None,
            "total_bytes": None,
            "used_bytes": None,
            "free_bytes": None,
            "usage_percent": None,
        }


def _get_disk_io():
    """
    Get cumulative disk I/O counters.

    These values are useful later for determining which
    processes and activities are using storage.
    """

    try:
        io = psutil.disk_io_counters()

        if io is None:
            return None

        return {
            "read_bytes": io.read_bytes,
            "write_bytes": io.write_bytes,
            "read_count": io.read_count,
            "write_count": io.write_count,
            "read_time_ms": io.read_time,
            "write_time_ms": io.write_time,
        }

    except Exception:
        return None


def get_storage():
    """
    Collect current storage information.

    This collector does NOT calculate:
    - daily storage changes
    - SSD lifetime
    - SSD health
    - storage usage by individual process

    Those require historical data or hardware-specific APIs.
    """

    try:
        partitions = _get_partitions()
        root = _get_root_storage()
        disk_io = _get_disk_io()

        return {
            "component": "Storage",
            "available": bool(partitions),

            # Main system storage
            "system_storage": root,

            # All mounted storage
            "partitions": partitions,

            # Current cumulative disk activity
            "disk_io": disk_io,

            # Platform
            "platform": platform.system(),
        }

    except Exception as error:
        return {
            "component": "Storage",
            "available": False,
            "error": str(error),

            "system_storage": {
                "path": None,
                "total_bytes": None,
                "used_bytes": None,
                "free_bytes": None,
                "usage_percent": None,
            },

            "partitions": [],
            "disk_io": None,
            "platform": platform.system(),
        }