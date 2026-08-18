import json
import platform
import subprocess

import psutil


WINDOWS_MEMORY_TYPES = {
    20: "DDR",
    21: "DDR2",
    22: "DDR2 FB-DIMM",
    24: "DDR3",
    26: "DDR4",
    27: "DDR4",
    28: "LPDDR",
    29: "LPDDR2",
    30: "LPDDR3",
    31: "LPDDR4",
    32: "LPDDR5",
    34: "DDR5",
    35: "LPDDR5",
}


def _get_memory_type():
    """
    Get the physical RAM type when the operating system exposes it.
    """

    if platform.system() != "Windows":
        return None

    try:
        command = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            """
            Get-CimInstance Win32_PhysicalMemory |
            Select-Object -First 1 SMBIOSMemoryType |
            ConvertTo-Json -Compress
            """,
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )

        if result.returncode != 0 or not result.stdout.strip():
            return None

        data = json.loads(result.stdout)

        memory_type = data.get("SMBIOSMemoryType")

        if memory_type is None:
            return None

        return WINDOWS_MEMORY_TYPES.get(
            int(memory_type),
            f"Unknown ({memory_type})",
        )

    except Exception:
        return None


def _get_ram_modules():
    """
    Get physical RAM module information on Windows.

    Returns an empty list when the platform does not expose
    physical module information through this interface.
    """

    if platform.system() != "Windows":
        return []

    modules = []

    try:
        command = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            """
            Get-CimInstance Win32_PhysicalMemory |
            Select-Object Manufacturer, PartNumber, Capacity,
                          Speed, ConfiguredClockSpeed, DeviceLocator |
            ConvertTo-Json -Compress
            """,
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if result.returncode != 0 or not result.stdout.strip():
            return modules

        data = json.loads(result.stdout)

        if isinstance(data, dict):
            data = [data]

        for module in data:
            capacity = module.get("Capacity")

            manufacturer = module.get("Manufacturer")
            part_number = module.get("PartNumber")
            slot = module.get("DeviceLocator")

            modules.append(
                {
                    "manufacturer": (
                        manufacturer.strip()
                        if isinstance(manufacturer, str)
                        else manufacturer
                    ),

                    "part_number": (
                        part_number.strip()
                        if isinstance(part_number, str)
                        else part_number
                    ),

                    "capacity_gb": (
                        round(
                            int(capacity) / (1024 ** 3),
                            2,
                        )
                        if capacity
                        else None
                    ),

                    "speed_mhz": module.get("Speed"),

                    "configured_speed_mhz": module.get(
                        "ConfiguredClockSpeed"
                    ),

                    "slot": (
                        slot.strip()
                        if isinstance(slot, str)
                        else slot
                    ),
                }
            )

    except Exception:
        pass

    return modules


def _get_swap():
    """
    Collect swap/page-file information.
    """

    try:
        swap = psutil.swap_memory()

        return {
            "total_bytes": swap.total,
            "total_gb": round(
                swap.total / (1024 ** 3),
                2,
            ),

            "used_bytes": swap.used,
            "used_gb": round(
                swap.used / (1024 ** 3),
                2,
            ),

            "free_bytes": (
                swap.total - swap.used
                if swap.total
                else None
            ),

            "free_gb": (
                round(
                    (swap.total - swap.used)
                    / (1024 ** 3),
                    2,
                )
                if swap.total
                else None
            ),

            "usage_percent": round(
                swap.percent,
                1,
            ),
        }

    except Exception:
        return {
            "total_bytes": None,
            "total_gb": None,
            "used_bytes": None,
            "used_gb": None,
            "free_bytes": None,
            "free_gb": None,
            "usage_percent": None,
        }


def get_ram():
    """
    Collect current RAM information.

    Collectors only gather current/raw system information.
    Historical averages, RAM-heavy activities and RAM-life
    calculations belong to the processing/memory layers.
    """

    try:
        memory = psutil.virtual_memory()

        return {
            "component": "RAM",
            "available": True,

            # Total physical RAM
            "total_bytes": memory.total,

            "total_gb": round(
                memory.total / (1024 ** 3),
                2,
            ),

            # Currently used RAM
            "used_bytes": memory.used,

            "used_gb": round(
                memory.used / (1024 ** 3),
                2,
            ),

            "usage_percent": round(
                memory.percent,
                1,
            ),

            # Available RAM
            "available_bytes": memory.available,

            "available_gb": round(
                memory.available / (1024 ** 3),
                2,
            ),

            # Technically unused RAM
            "free_bytes": memory.free,

            "free_gb": round(
                memory.free / (1024 ** 3),
                2,
            ),

            # Hardware information
            "memory_type": _get_memory_type(),

            "modules": _get_ram_modules(),

            # Swap/page file
            "swap": _get_swap(),
        }

    except Exception as error:
        return {
            "component": "RAM",
            "available": False,
            "error": str(error),

            "total_bytes": None,
            "total_gb": None,

            "used_bytes": None,
            "used_gb": None,
            "usage_percent": None,

            "available_bytes": None,
            "available_gb": None,

            "free_bytes": None,
            "free_gb": None,

            "memory_type": None,
            "modules": [],

            "swap": {
                "total_bytes": None,
                "total_gb": None,
                "used_bytes": None,
                "used_gb": None,
                "free_bytes": None,
                "free_gb": None,
                "usage_percent": None,
            },
        }