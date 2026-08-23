import os
import string

import psutil


def _bytes_to_gb(value):
    if value is None:
        return None

    return round(value / (1024 ** 3), 2)


def _get_windows_drives():
    drives = []

    for letter in string.ascii_uppercase:
        drive = f"{letter}:\\"

        if not os.path.exists(drive):
            continue

        try:
            usage = psutil.disk_usage(drive)

            drives.append(
                {
                    "mount": drive,
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

        except Exception:
            continue

    return drives


def get_storage():
    """
    Collect Windows storage information.

    Returns information about every mounted Windows drive.
    """

    try:
        drives = _get_windows_drives()

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
