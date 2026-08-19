import json
import platform
import subprocess
from pathlib import Path

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


RAM_SENSOR_KEYWORDS = (
    "memory",
    "ram",
    "dimm",
    "dram",
)


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


def _is_ram_sensor_name(name):
    """
    Determine whether a hardware-monitoring sensor name appears
    to refer specifically to RAM/DIMM/memory rather than CPU,
    motherboard, chipset, or another thermal zone.
    """

    if not isinstance(name, str):
        return False

    normalized = name.strip().lower()

    return any(
        keyword in normalized
        for keyword in RAM_SENSOR_KEYWORDS
    )


def _get_windows_ram_temperature():
    """
    Attempt to retrieve RAM temperature from optional hardware
    monitoring applications on Windows.

    Supported sources:
    - LibreHardwareMonitor
    - OpenHardwareMonitor

    These applications are optional. If neither is installed or
    neither exposes a RAM/DIMM temperature sensor, this returns
    unavailable rather than incorrectly using a CPU or motherboard
    temperature.
    """

    namespaces = (
        "root/LibreHardwareMonitor",
        "root/OpenHardwareMonitor",
    )

    for namespace in namespaces:
        try:
            command = [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                f"""
                Get-CimInstance -Namespace "{namespace}" -ClassName Sensor |
                Where-Object {{
                    $_.SensorType -eq "Temperature"
                }} |
                Select-Object Name, Identifier, Value, SensorType |
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
                continue

            data = json.loads(result.stdout)

            if isinstance(data, dict):
                data = [data]

            sensors = []

            for sensor in data:
                name = sensor.get("Name")
                identifier = sensor.get("Identifier")

                if not _is_ram_sensor_name(name) and not _is_ram_sensor_name(
                    identifier
                ):
                    continue

                value = sensor.get("Value")

                try:
                    temperature = float(value)
                except (TypeError, ValueError):
                    continue

                sensors.append(
                    {
                        "name": name,
                        "identifier": identifier,
                        "temperature_c": round(
                            temperature,
                            1,
                        ),
                    }
                )

            if sensors:
                temperatures = [
                    sensor["temperature_c"]
                    for sensor in sensors
                ]

                return {
                    "available": True,
                    "temperature_c": round(
                        max(temperatures),
                        1,
                    ),
                    "sensors": sensors,
                    "source": (
                        "LibreHardwareMonitor"
                        if "LibreHardwareMonitor" in namespace
                        else "OpenHardwareMonitor"
                    ),
                }

        except Exception:
            continue

    return {
        "available": False,
        "temperature_c": None,
        "sensors": [],
        "source": None,
    }


def _get_linux_ram_temperature():
    """
    Attempt to retrieve RAM/DIMM temperature from Linux hwmon
    sensors.

    Only sensors whose labels identify them as memory, RAM,
    DRAM, or DIMM are accepted.
    """

    sensors = []

    try:
        hwmon_root = Path("/sys/class/hwmon")

        if not hwmon_root.exists():
            return {
                "available": False,
                "temperature_c": None,
                "sensors": [],
                "source": None,
            }

        for hwmon in hwmon_root.glob("hwmon*"):
            sensor_labels = {}

            for label_file in hwmon.glob("temp*_label"):
                try:
                    label = label_file.read_text(
                        encoding="utf-8",
                        errors="ignore",
                    ).strip()

                    sensor_labels[
                        label_file.stem.replace(
                            "_label",
                            "",
                        )
                    ] = label

                except Exception:
                    continue

            for input_file in hwmon.glob("temp*_input"):
                sensor_key = input_file.stem

                label = sensor_labels.get(
                    sensor_key,
                    "",
                )

                if not _is_ram_sensor_name(label):
                    continue

                try:
                    millidegrees = int(
                        input_file.read_text(
                            encoding="utf-8",
                            errors="ignore",
                        ).strip()
                    )

                    temperature_c = millidegrees / 1000.0

                except (ValueError, OSError):
                    continue

                sensors.append(
                    {
                        "name": label,
                        "temperature_c": round(
                            temperature_c,
                            1,
                        ),
                        "device": hwmon.name,
                    }
                )

        if sensors:
            temperatures = [
                sensor["temperature_c"]
                for sensor in sensors
            ]

            return {
                "available": True,
                "temperature_c": round(
                    max(temperatures),
                    1,
                ),
                "sensors": sensors,
                "source": "Linux hwmon",
            }

    except Exception:
        pass

    return {
        "available": False,
        "temperature_c": None,
        "sensors": [],
        "source": None,
    }


def _get_ram_temperature():
    """
    Get RAM temperature where the operating system or an
    installed hardware-monitoring interface exposes it.

    The collector deliberately avoids substituting CPU,
    motherboard, chipset, or generic ACPI thermal-zone
    temperatures for RAM temperature.
    """

    system = platform.system()

    if system == "Windows":
        return _get_windows_ram_temperature()

    if system == "Linux":
        return _get_linux_ram_temperature()

    return {
        "available": False,
        "temperature_c": None,
        "sensors": [],
        "source": None,
    }


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

            # RAM temperature
            "temperature": _get_ram_temperature(),

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

            "temperature": {
                "available": False,
                "temperature_c": None,
                "sensors": [],
                "source": None,
            },

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