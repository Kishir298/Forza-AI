import json
import platform
import re
import shutil
import subprocess
from pathlib import Path

import psutil


def _run_powershell(command, timeout=8):
    """
    Execute a PowerShell command and return parsed JSON.
    """

    try:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                command,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

        if result.returncode != 0:
            return None

        output = result.stdout.strip()

        if not output:
            return None

        return json.loads(output)

    except Exception:
        return None


def _normalize_list(value):
    """
    Normalize PowerShell JSON output.

    PowerShell returns:
    - dict for one object
    - list for multiple objects
    """

    if value is None:
        return []

    if isinstance(value, dict):
        return [value]

    if isinstance(value, list):
        return value

    return []


def _clean_string(value):
    """
    Clean strings returned by hardware APIs.
    """

    if value is None:
        return None

    value = str(value).strip()

    return value if value else None


def _get_partitions():
    """
    Get mounted filesystem partitions.
    """

    partitions = []

    try:
        for partition in psutil.disk_partitions(
            all=False
        ):
            try:
                usage = psutil.disk_usage(
                    partition.mountpoint
                )

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

            except (
                PermissionError,
                OSError,
            ):
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

        total, used, free = shutil.disk_usage(
            path
        )

        return {
            "path": path,
            "total_bytes": total,
            "used_bytes": used,
            "free_bytes": free,
            "usage_percent": (
                round(
                    (used / total) * 100,
                    1,
                )
                if total
                else None
            ),
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
    Get cumulative system disk I/O counters.
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


def _detect_manufacturer(model, manufacturer):
    """
    Determine the actual drive manufacturer.

    Windows sometimes reports '(Standard disk drives)'
    instead of the real manufacturer.

    We only use conservative model-name matching.
    """

    manufacturer = _clean_string(
        manufacturer
    )

    model = _clean_string(model)

    invalid_manufacturers = {
        "",
        "(standard disk drives)",
        "standard disk drives",
        "microsoft",
        "generic",
        "standard",
    }

    if (
        manufacturer
        and manufacturer.lower()
        not in invalid_manufacturers
    ):
        return manufacturer

    if not model:
        return None

    normalized = model.upper()

    known_manufacturers = [
        "KIOXIA",
        "TOSHIBA",
        "SAMSUNG",
        "WESTERN DIGITAL",
        "WDC",
        "SEAGATE",
        "CRUCIAL",
        "MICRON",
        "INTEL",
        "SK HYNIX",
        "HYNIX",
        "KINGSTON",
        "SANDISK",
        "ADATA",
        "CORSAIR",
        "SOLIDIGM",
        "LEXAR",
        "SILICON POWER",
        "TRANSCEND",
        "HP",
        "DELL",
        "LENOVO",
    ]

    for name in known_manufacturers:
        if name in normalized:
            return name

    # KIOXIA BG-series drives often contain KIOXIA
    # in the model string, but some firmware versions
    # omit it. Recognize common BG model prefixes.
    if normalized.startswith(
        (
            "KBG",
            "KCD",
            "KXG",
        )
    ):
        return "KIOXIA"

    return None


def _detect_interface(
    model,
    bus_type,
    interface_type,
):
    """
    Determine the physical storage interface.

    Important:
    Windows can report an NVMe drive as SCSI because
    NVMe storage is exposed through the Windows storage
    stack. Therefore SCSI must not automatically mean
    the physical drive is SCSI.
    """

    model = (
        _clean_string(model)
        or ""
    )

    bus = (
        _clean_string(bus_type)
        or ""
    )

    interface = (
        _clean_string(interface_type)
        or ""
    )

    combined = (
        f"{model} {bus} {interface}"
    ).upper()

    if (
        "NVME" in combined
        or "NVM EXPRESS" in combined
    ):
        return "NVMe"

    if (
        "PCIE" in combined
        or "PCI EXPRESS" in combined
    ):
        return "PCIe"

    if "SATA" in combined:
        return "SATA"

    if "USB" in combined:
        return "USB"

    if "SAS" in combined:
        return "SAS"

    if "SCSI" in combined:
        return "SCSI"

    if "IDE" in combined:
        return "IDE"

    if "ATA" in combined:
        return "ATA"

    return None


def _detect_media_type(
    media_type,
    model,
    interface,
    bus_type,
):
    """
    Determine SSD/HDD without making unsafe guesses.
    """

    model = (
        _clean_string(model)
        or ""
    )

    media = (
        _clean_string(media_type)
        or ""
    )

    interface = (
        _clean_string(interface)
        or ""
    )

    bus_type = (
        _clean_string(bus_type)
        or ""
    )

    combined = (
        f"{media} {model} "
        f"{interface} {bus_type}"
    ).upper()

    if any(
        token in combined
        for token in (
            "SSD",
            "SOLID STATE",
            "NVME",
            "NVM EXPRESS",
        )
    ):
        return "SSD"

    if any(
        token in combined
        for token in (
            "HDD",
            "HARD DISK",
            "ROTATIONAL",
        )
    ):
        return "HDD"

    return "Unknown"


def _get_windows_physical_drives():
    """
    Collect physical drives using Windows storage APIs.

    Sources:
    - Get-PhysicalDisk
    - Win32_DiskDrive
    """

    storage_disks = _normalize_list(
        _run_powershell(
            """
            Get-PhysicalDisk |
            Select-Object DeviceId,
                          FriendlyName,
                          Manufacturer,
                          SerialNumber,
                          MediaType,
                          BusType,
                          HealthStatus,
                          OperationalStatus,
                          Size |
            ConvertTo-Json -Compress
            """
        )
    )

    wmi_disks = _normalize_list(
        _run_powershell(
            """
            Get-CimInstance Win32_DiskDrive |
            Select-Object Index,
                          DeviceID,
                          Model,
                          Manufacturer,
                          SerialNumber,
                          InterfaceType,
                          MediaType,
                          Size,
                          Status |
            ConvertTo-Json -Compress
            """
        )
    )

    wmi_by_index = {}

    for disk in wmi_disks:
        index = disk.get("Index")

        if index is not None:
            wmi_by_index[
                str(index)
            ] = disk

    physical_drives = []

    for disk in storage_disks:
        device_id = disk.get(
            "DeviceId"
        )

        wmi_disk = wmi_by_index.get(
            str(device_id),
            {},
        )

        model = (
            _clean_string(
                disk.get("FriendlyName")
            )
            or _clean_string(
                wmi_disk.get("Model")
            )
        )

        manufacturer = _detect_manufacturer(
            model,
            (
                disk.get("Manufacturer")
                or wmi_disk.get(
                    "Manufacturer"
                )
            ),
        )

        bus_type = (
            disk.get("BusType")
            or ""
        )

        interface_type = (
            wmi_disk.get(
                "InterfaceType"
            )
            or ""
        )

        interface = _detect_interface(
            model,
            bus_type,
            interface_type,
        )

        media_type = _detect_media_type(
            disk.get("MediaType"),
            model,
            interface,
            bus_type,
        )

        size = (
            disk.get("Size")
            or wmi_disk.get("Size")
        )

        physical_drives.append(
            {
                "device": (
                    wmi_disk.get(
                        "DeviceID"
                    )
                    or (
                        f"\\\\.\\PHYSICALDRIVE"
                        f"{device_id}"
                    )
                ),
                "index": device_id,
                "model": model,
                "manufacturer": manufacturer,
                "serial_number": (
                    _clean_string(
                        disk.get(
                            "SerialNumber"
                        )
                    )
                    or _clean_string(
                        wmi_disk.get(
                            "SerialNumber"
                        )
                    )
                ),
                "media_type": media_type,
                "interface": interface,
                "size_bytes": size,
                "size_gb": (
                    round(
                        int(size)
                        / (1024 ** 3),
                        2,
                    )
                    if size
                    else None
                ),
                "health": {
                    "available": bool(
                        disk.get(
                            "HealthStatus"
                        )
                        or wmi_disk.get(
                            "Status"
                        )
                    ),
                    "status": (
                        disk.get(
                            "HealthStatus"
                        )
                        or wmi_disk.get(
                            "Status"
                        )
                    ),
                    "operational_status": disk.get(
                        "OperationalStatus"
                    ),
                },
            }
        )

    # Fallback if Get-PhysicalDisk was unavailable.
    if not physical_drives:
        for disk in wmi_disks:
            model = _clean_string(
                disk.get("Model")
            )

            interface = _detect_interface(
                model,
                None,
                disk.get(
                    "InterfaceType"
                ),
            )

            media_type = _detect_media_type(
                disk.get("MediaType"),
                model,
                interface,
                disk.get(
                    "InterfaceType"
                ),
            )

            size = disk.get("Size")

            physical_drives.append(
                {
                    "device": disk.get(
                        "DeviceID"
                    ),
                    "index": disk.get(
                        "Index"
                    ),
                    "model": model,
                    "manufacturer": _detect_manufacturer(
                        model,
                        disk.get(
                            "Manufacturer"
                        ),
                    ),
                    "serial_number": _clean_string(
                        disk.get(
                            "SerialNumber"
                        )
                    ),
                    "media_type": media_type,
                    "interface": interface,
                    "size_bytes": size,
                    "size_gb": (
                        round(
                            int(size)
                            / (1024 ** 3),
                            2,
                        )
                        if size
                        else None
                    ),
                    "health": {
                        "available": bool(
                            disk.get(
                                "Status"
                            )
                        ),
                        "status": disk.get(
                            "Status"
                        ),
                        "operational_status": None,
                    },
                }
            )

    return physical_drives


def _get_windows_temperature():
    """
    Get storage temperature through Windows Storage
    Reliability Counters where supported.
    """

    data = _normalize_list(
        _run_powershell(
            """
            Get-PhysicalDisk |
            Get-StorageReliabilityCounter |
            Select-Object DeviceId,
                          Temperature,
                          TemperatureMax |
            ConvertTo-Json -Compress
            """
        )
    )

    sensors = []

    for item in data:
        temperature = item.get(
            "Temperature"
        )

        maximum = item.get(
            "TemperatureMax"
        )

        try:
            temperature = (
                float(temperature)
                if temperature is not None
                else None
            )
        except (
            TypeError,
            ValueError,
        ):
            temperature = None

        try:
            maximum = (
                float(maximum)
                if maximum is not None
                else None
            )
        except (
            TypeError,
            ValueError,
        ):
            maximum = None

        if (
            temperature is None
            and maximum is None
        ):
            continue

        sensors.append(
            {
                "device_id": item.get(
                    "DeviceId"
                ),
                "temperature_c": (
                    round(
                        temperature,
                        1,
                    )
                    if temperature is not None
                    else None
                ),
                "maximum_temperature_c": (
                    round(
                        maximum,
                        1,
                    )
                    if maximum is not None
                    else None
                ),
            }
        )

    temperatures = [
        item["temperature_c"]
        for item in sensors
        if item["temperature_c"]
        is not None
    ]

    return {
        "available": bool(
            temperatures
        ),
        "temperature_c": (
            round(
                max(temperatures),
                1,
            )
            if temperatures
            else None
        ),
        "sensors": sensors,
        "source": (
            "Windows Storage Reliability Counters"
            if sensors
            else None
        ),
    }


def _get_windows_reliability():
    """
    Get Windows Storage Reliability Counters.

    Wear values are hardware-dependent and are not
    interpreted unless Windows exposes them.
    """

    data = _normalize_list(
        _run_powershell(
            """
            Get-PhysicalDisk |
            Get-StorageReliabilityCounter |
            Select-Object DeviceId,
                          Wear,
                          ReadErrorsTotal,
                          ReadErrorsCorrected,
                          WriteErrorsTotal,
                          WriteErrorsCorrected,
                          PowerOnHours,
                          Temperature,
                          TemperatureMax |
            ConvertTo-Json -Compress
            """
        )
    )

    results = []

    for item in data:
        results.append(
            {
                "device_id": item.get(
                    "DeviceId"
                ),
                "wear_percent": item.get(
                    "Wear"
                ),
                "read_errors_total": item.get(
                    "ReadErrorsTotal"
                ),
                "read_errors_corrected": item.get(
                    "ReadErrorsCorrected"
                ),
                "write_errors_total": item.get(
                    "WriteErrorsTotal"
                ),
                "write_errors_corrected": item.get(
                    "WriteErrorsCorrected"
                ),
                "power_on_hours": item.get(
                    "PowerOnHours"
                ),
                "temperature_c": item.get(
                    "Temperature"
                ),
                "maximum_temperature_c": item.get(
                    "TemperatureMax"
                ),
            }
        )

    return results


def _get_windows_health():
    """
    Get Windows physical-disk health status.
    """

    data = _normalize_list(
        _run_powershell(
            """
            Get-PhysicalDisk |
            Select-Object DeviceId,
                          FriendlyName,
                          HealthStatus,
                          OperationalStatus,
                          Usage,
                          MediaType |
            ConvertTo-Json -Compress
            """
        )
    )

    results = []

    for disk in data:
        results.append(
            {
                "device_id": disk.get(
                    "DeviceId"
                ),
                "name": disk.get(
                    "FriendlyName"
                ),
                "health_status": disk.get(
                    "HealthStatus"
                ),
                "operational_status": disk.get(
                    "OperationalStatus"
                ),
                "usage": disk.get(
                    "Usage"
                ),
                "media_type": disk.get(
                    "MediaType"
                ),
            }
        )

    return results


def _get_linux_physical_drives():
    """
    Collect Linux physical block devices.
    """

    drives = []

    root = Path(
        "/sys/class/block"
    )

    if not root.exists():
        return drives

    for device in root.iterdir():
        name = device.name

        # Ignore ordinary partitions.
        if (
            re.search(
                r"\d$",
                name,
            )
            and not name.startswith(
                "nvme"
            )
        ):
            continue

        try:
            sectors = int(
                (
                    device / "size"
                ).read_text().strip()
            )

            size_bytes = (
                sectors * 512
            )

            model = None
            vendor = None

            model_file = (
                device / "device/model"
            )

            vendor_file = (
                device / "device/vendor"
            )

            if model_file.exists():
                model = _clean_string(
                    model_file.read_text(
                        errors="ignore"
                    )
                )

            if vendor_file.exists():
                vendor = _clean_string(
                    vendor_file.read_text(
                        errors="ignore"
                    )
                )

            rotational_file = (
                device
                / "queue/rotational"
            )

            rotational = None

            if rotational_file.exists():
                rotational = (
                    rotational_file
                    .read_text()
                    .strip()
                    == "1"
                )

            if rotational is True:
                media_type = "HDD"

            elif rotational is False:
                media_type = "SSD"

            else:
                media_type = "Unknown"

            interface = (
                "NVMe"
                if name.startswith(
                    "nvme"
                )
                else None
            )

            drives.append(
                {
                    "device": f"/dev/{name}",
                    "index": None,
                    "model": model,
                    "manufacturer": vendor,
                    "serial_number": None,
                    "media_type": media_type,
                    "interface": interface,
                    "size_bytes": size_bytes,
                    "size_gb": round(
                        size_bytes
                        / (1024 ** 3),
                        2,
                    ),
                }
            )

        except Exception:
            continue

    return drives


def _get_linux_smart():
    """
    Collect SMART information through smartctl.
    """

    if shutil.which(
        "smartctl"
    ) is None:
        return []

    results = []

    try:
        scan = subprocess.run(
            [
                "smartctl",
                "--scan-open",
                "-j",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        try:
            scan_data = json.loads(
                scan.stdout
            )
        except Exception:
            return results

        for device in scan_data.get(
            "devices",
            [],
        ):
            name = device.get(
                "name"
            )

            if not name:
                continue

            result = subprocess.run(
                [
                    "smartctl",
                    "-a",
                    "-j",
                    name,
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            try:
                smart = json.loads(
                    result.stdout
                )
            except Exception:
                continue

            smart_status = smart.get(
                "smart_status",
                {}
            )

            temperature = None

            temperature_data = smart.get(
                "temperature",
                {}
            )

            if isinstance(
                temperature_data,
                dict,
            ):
                temperature = (
                    temperature_data.get(
                        "current"
                    )
                )

            nvme_health = smart.get(
                "nvme_smart_health_information_log",
                {},
            )

            if temperature is None:
                temperature = (
                    nvme_health.get(
                        "temperature"
                    )
                )

            wear = nvme_health.get(
                "percentage_used"
            )

            results.append(
                {
                    "device": name,
                    "available": True,
                    "smart_passed": smart_status.get(
                        "passed"
                    ),
                    "smart_status": smart_status,
                    "temperature_c": temperature,
                    "wear_percent": wear,
                }
            )

    except Exception:
        pass

    return results


def _get_macos_physical_drives():
    """
    Collect physical storage information on macOS.
    """

    drives = []

    try:
        import plistlib

        result = subprocess.run(
            [
                "diskutil",
                "list",
                "physical",
                "-plist",
            ],
            capture_output=True,
            timeout=5,
            check=False,
        )

        if result.returncode != 0:
            return drives

        data = plistlib.loads(
            result.stdout
        )

        for disk in data.get(
            "AllDisksAndPartitions",
            [],
        ):
            identifier = disk.get(
                "DeviceIdentifier"
            )

            if not identifier:
                continue

            info_result = subprocess.run(
                [
                    "diskutil",
                    "info",
                    "-plist",
                    identifier,
                ],
                capture_output=True,
                timeout=5,
                check=False,
            )

            try:
                info = plistlib.loads(
                    info_result.stdout
                )
            except Exception:
                continue

            size = info.get(
                "TotalSize"
            )

            solid_state = info.get(
                "SolidState"
            )

            if solid_state is True:
                media_type = "SSD"

            elif solid_state is False:
                media_type = "HDD"

            else:
                media_type = "Unknown"

            drives.append(
                {
                    "device": (
                        f"/dev/{identifier}"
                    ),
                    "index": None,
                    "model": _clean_string(
                        info.get(
                            "MediaName"
                        )
                    ),
                    "manufacturer": None,
                    "serial_number": None,
                    "media_type": media_type,
                    "interface": _clean_string(
                        info.get(
                            "Protocol"
                        )
                    ),
                    "size_bytes": size,
                    "size_gb": (
                        round(
                            size
                            / (1024 ** 3),
                            2,
                        )
                        if size
                        else None
                    ),
                }
            )

    except Exception:
        pass

    return drives


def _get_physical_drives():
    """
    Platform-specific physical drive detection.
    """

    system = platform.system()

    if system == "Windows":
        return _get_windows_physical_drives()

    if system == "Linux":
        return _get_linux_physical_drives()

    if system == "Darwin":
        return _get_macos_physical_drives()

    return []


def _get_temperature():
    """
    Platform-specific storage temperature.
    """

    system = platform.system()

    if system == "Windows":
        return _get_windows_temperature()

    if system == "Linux":
        smart = _get_linux_smart()

        sensors = [
            {
                "device": item.get(
                    "device"
                ),
                "temperature_c": item.get(
                    "temperature_c"
                ),
            }
            for item in smart
            if item.get(
                "temperature_c"
            ) is not None
        ]

        if sensors:
            values = [
                item["temperature_c"]
                for item in sensors
            ]

            return {
                "available": True,
                "temperature_c": round(
                    max(values),
                    1,
                ),
                "sensors": sensors,
                "source": "smartctl",
            }

    return {
        "available": False,
        "temperature_c": None,
        "sensors": [],
        "source": None,
    }


def _get_smart():
    """
    Platform-specific SMART health information.
    """

    system = platform.system()

    if system == "Linux":
        smart = _get_linux_smart()

        return {
            "available": bool(
                smart
            ),
            "drives": smart,
            "source": (
                "smartctl"
                if smart
                else None
            ),
        }

    if system == "Windows":
        health = _get_windows_health()

        return {
            "available": bool(
                health
            ),
            "drives": health,
            "source": (
                "Windows Storage Health"
                if health
                else None
            ),
        }

    return {
        "available": False,
        "drives": [],
        "source": None,
    }


def _get_ssd_life():
    """
    Platform-specific SSD/NVMe wear information.
    """

    system = platform.system()

    if system == "Windows":
        reliability = (
            _get_windows_reliability()
        )

        drives = []

        for item in reliability:
            wear = item.get(
                "wear_percent"
            )

            if wear is None:
                continue

            try:
                wear = float(
                    wear
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            # Windows Storage Reliability Counter
            # reports percentage of wear used.
            remaining = max(
                0.0,
                min(
                    100.0,
                    100.0 - wear,
                ),
            )

            drives.append(
                {
                    "device_id": item.get(
                        "device_id"
                    ),
                    "wear_percent": wear,
                    "remaining_percent": remaining,
                }
            )

        return {
            "available": bool(
                drives
            ),
            "drives": drives,
            "source": (
                "Windows Storage Reliability Counters"
                if drives
                else None
            ),
        }

    if system == "Linux":
        smart = _get_linux_smart()

        drives = []

        for item in smart:
            wear = item.get(
                "wear_percent"
            )

            if wear is None:
                continue

            try:
                wear = float(
                    wear
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            drives.append(
                {
                    "device": item.get(
                        "device"
                    ),
                    "wear_percent": wear,
                    "remaining_percent": max(
                        0.0,
                        min(
                            100.0,
                            100.0 - wear,
                        ),
                    ),
                }
            )

        return {
            "available": bool(
                drives
            ),
            "drives": drives,
            "source": (
                "smartctl"
                if drives
                else None
            ),
        }

    return {
        "available": False,
        "drives": [],
        "source": None,
    }


def get_storage():
    """
    Collect complete storage information.

    Existing objectives:
    - Total storage
    - Used storage
    - Free storage
    - Storage usage percentage
    - Individual drives
    - Disk read/write activity

    Hardware objectives:
    - SSD vs HDD
    - Drive model
    - Drive manufacturer
    - Drive interface/type
    - Drive temperature where supported
    - SMART health where supported
    - SSD life/health indicators where supported
    """

    try:
        partitions = _get_partitions()

        root = _get_root_storage()

        disk_io = _get_disk_io()

        physical_drives = (
            _get_physical_drives()
        )

        temperature = (
            _get_temperature()
        )

        smart = _get_smart()

        ssd_life = _get_ssd_life()

        return {
            "component": "Storage",
            "available": bool(
                partitions
                or physical_drives
            ),

            "system_storage": root,

            "partitions": partitions,

            "physical_drives": (
                physical_drives
            ),

            "temperature": temperature,

            "smart": smart,

            "ssd_life": ssd_life,

            "disk_io": disk_io,

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

            "physical_drives": [],

            "temperature": {
                "available": False,
                "temperature_c": None,
                "sensors": [],
                "source": None,
            },

            "smart": {
                "available": False,
                "drives": [],
                "source": None,
            },

            "ssd_life": {
                "available": False,
                "drives": [],
                "source": None,
            },

            "disk_io": None,

            "platform": platform.system(),
        }