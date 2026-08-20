import json
import subprocess

import psutil


def _run_powershell(command, timeout=5):
    """Run a PowerShell command safely on Windows."""
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

        return output if output else None

    except (
        subprocess.TimeoutExpired,
        FileNotFoundError,
        OSError,
        ValueError,
    ):
        return None


def _powershell_json(command, timeout=5):
    """Run PowerShell and return decoded JSON."""
    output = _run_powershell(command, timeout)

    if not output:
        return None

    try:
        return json.loads(output)

    except (
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ):
        return None


def _get_cpu_model():
    """Get the Windows CPU model through WMI/CIM."""
    data = _powershell_json(
        "Get-CimInstance Win32_Processor | "
        "Select-Object -First 1 Name | "
        "ConvertTo-Json -Compress"
    )

    if isinstance(data, dict):
        return data.get("Name") or None

    return None


def _get_cpu_frequency():
    """Get current, minimum, and maximum CPU frequency."""
    try:
        frequency = psutil.cpu_freq()

        if frequency is None:
            return None

        current_mhz = (
            round(frequency.current, 2)
            if frequency.current
            else None
        )

        min_mhz = (
            round(frequency.min, 2)
            if frequency.min
            else None
        )

        max_mhz = (
            round(frequency.max, 2)
            if frequency.max
            else None
        )

        return {
            "current_mhz": current_mhz,
            "current_ghz": (
                round(current_mhz / 1000, 2)
                if current_mhz is not None
                else None
            ),
            "min_mhz": min_mhz,
            "min_ghz": (
                round(min_mhz / 1000, 2)
                if min_mhz is not None
                else None
            ),
            "max_mhz": max_mhz,
            "max_ghz": (
                round(max_mhz / 1000, 2)
                if max_mhz is not None
                else None
            ),
        }

    except (
        OSError,
        ValueError,
        TypeError,
    ):
        return None


def _get_core_usage():
    """Get current CPU utilisation for every logical CPU."""
    try:
        values = psutil.cpu_percent(
            interval=0.5,
            percpu=True,
        )

        return [
            round(
                max(
                    0.0,
                    float(value),
                ),
                1,
            )
            for value in values
        ]

    except (
        OSError,
        ValueError,
        TypeError,
    ):
        return []


def _get_cache_info():
    """Get CPU L2/L3 cache information through Windows CIM."""
    result = {
        "available": False,
        "l1_kb": None,
        "l2_kb": None,
        "l3_kb": None,
    }

    data = _powershell_json(
        "Get-CimInstance Win32_Processor | "
        "Select-Object -First 1 L2CacheSize,L3CacheSize | "
        "ConvertTo-Json -Compress"
    )

    if not isinstance(data, dict):
        return result

    l2_cache = data.get("L2CacheSize")
    l3_cache = data.get("L3CacheSize")

    try:
        if l2_cache is not None:
            result["l2_kb"] = int(l2_cache)
    except (
        TypeError,
        ValueError,
    ):
        pass

    try:
        if l3_cache is not None:
            result["l3_kb"] = int(l3_cache)
    except (
        TypeError,
        ValueError,
    ):
        pass

    result["available"] = (
        result["l2_kb"] is not None
        or result["l3_kb"] is not None
    )

    return result


def _get_temperature_info():
    """
    Get CPU-related thermal zone information through Windows ACPI.

    Windows does not expose a reliable CPU package temperature on
    every machine through this interface, so unavailable data is
    explicitly reported instead of being guessed.
    """
    result = {
        "available": False,
        "cpu_temperature_c": None,
        "source": None,
    }

    data = _powershell_json(
        "Get-CimInstance "
        "-Namespace root/wmi "
        "-ClassName MSAcpi_ThermalZoneTemperature | "
        "Select-Object CurrentTemperature,InstanceName | "
        "ConvertTo-Json -Compress"
    )

    if isinstance(data, dict):
        data = [data]

    if not isinstance(data, list):
        return result

    temperatures = []

    for zone in data:
        if not isinstance(zone, dict):
            continue

        raw_temperature = zone.get(
            "CurrentTemperature"
        )

        if raw_temperature is None:
            continue

        try:
            celsius = (
                float(raw_temperature) / 10.0
            ) - 273.15

        except (
            TypeError,
            ValueError,
        ):
            continue

        if -20 <= celsius <= 150:
            temperatures.append(celsius)

    if temperatures:
        result["available"] = True
        result["cpu_temperature_c"] = round(
            max(temperatures),
            1,
        )
        result["source"] = (
            "Windows ACPI thermal zone"
        )

    return result


def _get_power_info():
    """
    Return Windows CPU power telemetry.

    Standard Windows WMI/CIM CPU classes do not provide a
    consistently reliable live CPU package-power measurement.
    Therefore this collector does not fabricate one.
    """
    return {
        "available": False,
        "cpu_power_w": None,
        "energy_uj": None,
        "source": None,
    }


def get_cpu():
    """
    Collect current Windows CPU information.

    This collector gathers raw/current hardware information.
    Historical analysis belongs in the analytics layer.
    """
    try:
        physical_cores = psutil.cpu_count(
            logical=False
        )

        logical_cores = psutil.cpu_count(
            logical=True
        )

        usage_percent = psutil.cpu_percent(
            interval=0.5
        )

        if usage_percent is None:
            usage_percent = 0.0

        return {
            "component": "CPU",
            "available": True,

            "model": _get_cpu_model(),
            "architecture": "Windows",

            "physical_cores": physical_cores,
            "logical_cores": logical_cores,

            "usage_percent": round(
                max(
                    0.0,
                    float(usage_percent),
                ),
                1,
            ),

            "core_usage": _get_core_usage(),

            "frequency": _get_cpu_frequency(),

            "cache": _get_cache_info(),

            "temperature": _get_temperature_info(),

            "power": _get_power_info(),
        }

    except Exception as error:
        return {
            "component": "CPU",
            "available": False,
            "error": str(error),

            "model": None,
            "architecture": "Windows",

            "physical_cores": None,
            "logical_cores": None,

            "usage_percent": None,
            "core_usage": [],

            "frequency": None,

            "cache": {
                "available": False,
                "l1_kb": None,
                "l2_kb": None,
                "l3_kb": None,
            },

            "temperature": {
                "available": False,
                "cpu_temperature_c": None,
                "source": None,
            },

            "power": {
                "available": False,
                "cpu_power_w": None,
                "energy_uj": None,
                "source": None,
            },
        }
