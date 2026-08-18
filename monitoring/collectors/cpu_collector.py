import json
import os
import platform
import re
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

    except Exception:
        return None


def _powershell_json(command, timeout=5):
    """Run PowerShell and return decoded JSON."""
    output = _run_powershell(command, timeout)

    if not output:
        return None

    try:
        return json.loads(output)

    except Exception:
        return None


def _get_cpu_model():
    system = platform.system()

    if system == "Windows":
        try:
            data = _powershell_json(
                "Get-CimInstance Win32_Processor | "
                "Select-Object -First 1 Name | "
                "ConvertTo-Json -Compress"
            )

            if data:
                return data.get("Name") or None

        except Exception:
            pass

    if system == "Darwin":
        try:
            result = subprocess.run(
                [
                    "sysctl",
                    "-n",
                    "machdep.cpu.brand_string",
                ],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )

            if result.returncode == 0:
                return result.stdout.strip() or None

        except Exception:
            pass

    if system == "Linux":
        try:
            with open(
                "/proc/cpuinfo",
                "r",
                encoding="utf-8",
            ) as file:
                for line in file:
                    if line.lower().startswith("model name"):
                        return line.split(
                            ":",
                            1,
                        )[1].strip()

        except Exception:
            pass

    return platform.processor() or None


def _get_cpu_frequency():
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

    except Exception:
        return None

def _get_core_usage():
    try:
        values = psutil.cpu_percent(
            interval=0.5,
            percpu=True,
        )

        return [
            round(value, 1)
            for value in values
        ]

    except Exception:
        return []


def _get_cache_info():
    """
    Collect CPU cache information where the operating system
    exposes it.

    Windows:
        L2/L3 through Win32_Processor.

    Linux:
        /sys/devices/system/cpu/cpu0/cache.

    macOS:
        sysctl cache-size values where available.
    """

    system = platform.system()

    result = {
        "available": False,
        "l1_kb": None,
        "l2_kb": None,
        "l3_kb": None,
    }

    # ---------------------------------------------------------
    # Windows
    # ---------------------------------------------------------

    if system == "Windows":
        try:
            data = _powershell_json(
                "Get-CimInstance Win32_Processor | "
                "Select-Object -First 1 L2CacheSize,L3CacheSize | "
                "ConvertTo-Json -Compress"
            )

            if data:
                result["l2_kb"] = data.get(
                    "L2CacheSize"
                )

                result["l3_kb"] = data.get(
                    "L3CacheSize"
                )

                result["available"] = (
                    result["l2_kb"] is not None
                    or result["l3_kb"] is not None
                )

        except Exception:
            pass

        return result

    # ---------------------------------------------------------
    # Linux
    # ---------------------------------------------------------

    if system == "Linux":
        cache_root = "/sys/devices/system/cpu/cpu0/cache"

        cache_values = {
            "l1": [],
            "l2": [],
            "l3": [],
        }

        try:
            entries = os.listdir(cache_root)

            for entry in entries:
                if not entry.startswith("index"):
                    continue

                cache_path = os.path.join(
                    cache_root,
                    entry,
                )

                level_path = os.path.join(
                    cache_path,
                    "level",
                )

                type_path = os.path.join(
                    cache_path,
                    "type",
                )

                size_path = os.path.join(
                    cache_path,
                    "size",
                )

                with open(
                    level_path,
                    "r",
                    encoding="utf-8",
                ) as file:
                    level = file.read().strip()

                with open(
                    type_path,
                    "r",
                    encoding="utf-8",
                ) as file:
                    cache_type = file.read().strip()

                # Ignore instruction-only cache entries.
                if cache_type.lower() == "instruction":
                    continue

                with open(
                    size_path,
                    "r",
                    encoding="utf-8",
                ) as file:
                    size = file.read().strip().upper()

                match = re.match(
                    r"([0-9.]+)([KMG])",
                    size,
                )

                if not match:
                    continue

                number = float(match.group(1))
                unit = match.group(2)

                multiplier = {
                    "K": 1,
                    "M": 1024,
                    "G": 1024 * 1024,
                }[unit]

                size_kb = int(
                    number * multiplier
                )

                if level in ("1", "2", "3"):
                    cache_values[
                        f"l{level}"
                    ].append(size_kb)

            result["l1_kb"] = (
                max(cache_values["l1"])
                if cache_values["l1"]
                else None
            )

            result["l2_kb"] = (
                max(cache_values["l2"])
                if cache_values["l2"]
                else None
            )

            result["l3_kb"] = (
                max(cache_values["l3"])
                if cache_values["l3"]
                else None
            )

            result["available"] = any(
                cache_values.values()
            )

        except Exception:
            pass

        return result

    # ---------------------------------------------------------
    # macOS
    # ---------------------------------------------------------

    if system == "Darwin":
        sysctl_values = {
            "l1_kb": [
                "hw.l1dcachesize",
                "hw.l1icachesize",
            ],
            "l2_kb": [
                "hw.l2cachesize",
            ],
            "l3_kb": [
                "hw.l3cachesize",
            ],
        }

        for key, sysctl_names in sysctl_values.items():
            values = []

            for sysctl_name in sysctl_names:
                try:
                    result_data = subprocess.run(
                        [
                            "sysctl",
                            "-n",
                            sysctl_name,
                        ],
                        capture_output=True,
                        text=True,
                        timeout=3,
                        check=False,
                    )

                    if result_data.returncode != 0:
                        continue

                    value = result_data.stdout.strip()

                    if value.isdigit():
                        values.append(
                            int(value) // 1024
                        )

                except Exception:
                    continue

            if values:
                result[key] = max(values)

        result["available"] = (
            result["l1_kb"] is not None
            or result["l2_kb"] is not None
            or result["l3_kb"] is not None
        )

        return result

    return result


def _get_temperature_info():
    """
    Collect CPU temperature where the platform exposes
    a usable CPU-related temperature sensor.
    """

    system = platform.system()

    result = {
        "available": False,
        "cpu_temperature_c": None,
        "source": None,
    }

    # ---------------------------------------------------------
    # Windows
    # ---------------------------------------------------------

    if system == "Windows":
        try:
            data = _powershell_json(
                "Get-CimInstance "
                "-Namespace root/wmi "
                "-ClassName MSAcpi_ThermalZoneTemperature | "
                "Select-Object CurrentTemperature,InstanceName | "
                "ConvertTo-Json -Compress"
            )

            if isinstance(data, dict):
                data = [data]

            temperatures = []

            if data:
                for zone in data:
                    raw_temperature = zone.get(
                        "CurrentTemperature"
                    )

                    if raw_temperature is None:
                        continue

                    try:
                        celsius = (
                            float(raw_temperature)
                            / 10.0
                        ) - 273.15

                        if -20 <= celsius <= 150:
                            temperatures.append(
                                celsius
                            )

                    except (
                        TypeError,
                        ValueError,
                    ):
                        continue

            if temperatures:
                result["available"] = True
                result["cpu_temperature_c"] = round(
                    max(temperatures),
                    1,
                )
                result["source"] = (
                    "Windows ACPI thermal zone"
                )

        except Exception:
            pass

        return result

    # ---------------------------------------------------------
    # Linux
    # ---------------------------------------------------------

    if system == "Linux":
        thermal_root = "/sys/class/thermal"

        temperatures = []

        try:
            for entry in os.listdir(
                thermal_root
            ):
                if not entry.startswith(
                    "thermal_zone"
                ):
                    continue

                zone_path = os.path.join(
                    thermal_root,
                    entry,
                )

                type_path = os.path.join(
                    zone_path,
                    "type",
                )

                temp_path = os.path.join(
                    zone_path,
                    "temp",
                )

                with open(
                    type_path,
                    "r",
                    encoding="utf-8",
                ) as file:
                    zone_type = (
                        file.read()
                        .strip()
                        .lower()
                    )

                if not any(
                    name in zone_type
                    for name in (
                        "cpu",
                        "package",
                        "core",
                        "x86",
                    )
                ):
                    continue

                with open(
                    temp_path,
                    "r",
                    encoding="utf-8",
                ) as file:
                    temperature = (
                        float(
                            file.read().strip()
                        )
                        / 1000.0
                    )

                if -20 <= temperature <= 150:
                    temperatures.append(
                        temperature
                    )

        except Exception:
            pass

        if temperatures:
            result["available"] = True
            result["cpu_temperature_c"] = round(
                max(temperatures),
                1,
            )
            result["source"] = (
                "Linux thermal zone"
            )

        return result

    # ---------------------------------------------------------
    # macOS
    # ---------------------------------------------------------

    # macOS generally does not expose a reliable CPU
    # temperature through built-in sysctl interfaces.
    # Return unavailable instead of inventing a value.

    return result


def _get_power_info():
    """
    Collect CPU power/energy information where the operating
    system exposes a hardware energy counter.

    Linux:
        Intel RAPL energy counters where available.

    Windows/macOS:
        Returns unavailable unless a reliable native counter
        is exposed.
    """

    system = platform.system()

    result = {
        "available": False,
        "cpu_power_w": None,
        "energy_uj": None,
        "source": None,
    }

    # ---------------------------------------------------------
    # Linux Intel RAPL
    # ---------------------------------------------------------

    if system == "Linux":
        powercap_root = "/sys/class/powercap"

        energy_files = []

        try:
            for directory, _, files in os.walk(
                powercap_root
            ):
                if (
                    "energy_uj" in files
                    and "intel-rapl"
                    in directory.lower()
                ):
                    energy_files.append(
                        os.path.join(
                            directory,
                            "energy_uj",
                        )
                    )

        except Exception:
            pass

        total_energy_uj = 0

        for path in energy_files:
            try:
                with open(
                    path,
                    "r",
                    encoding="utf-8",
                ) as file:
                    total_energy_uj += int(
                        file.read().strip()
                    )

            except Exception:
                continue

        if total_energy_uj > 0:
            result["available"] = True
            result["energy_uj"] = (
                total_energy_uj
            )
            result["source"] = (
                "Linux RAPL energy counter"
            )

        return result

    # ---------------------------------------------------------
    # Windows
    # ---------------------------------------------------------

    # Standard Windows WMI CPU classes do not expose a
    # trustworthy live CPU package-power measurement.
    # Do not estimate power from unrelated values.

    if system == "Windows":
        return result

    # ---------------------------------------------------------
    # macOS
    # ---------------------------------------------------------

    # Apple Silicon power telemetry is not reliably available
    # through standard Python/OS APIs, so return unavailable.

    return result


def get_cpu():
    """
    Collect current CPU information.

    This collector only gathers raw/current CPU information.
    Historical averages and analysis belong to the processing layer.
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

        frequency = _get_cpu_frequency()
        core_usage = _get_core_usage()

        cache = _get_cache_info()
        temperature = _get_temperature_info()
        power = _get_power_info()

        return {
            "component": "CPU",
            "available": True,

            # Identification
            "model": _get_cpu_model(),
            "architecture": platform.machine(),

            # Core configuration
            "physical_cores": physical_cores,
            "logical_cores": logical_cores,

            # Current usage
            "usage_percent": round(
                usage_percent,
                1,
            ),

            "core_usage": core_usage,

            # Frequency
            "frequency": frequency,

            # Cache
            "cache": cache,

            # Temperature
            "temperature": temperature,

            # Power / energy
            "power": power,
        }

    except Exception as error:
        return {
            "component": "CPU",
            "available": False,
            "error": str(error),

            "model": None,
            "architecture": None,

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