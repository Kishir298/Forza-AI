import os
import re

import psutil


def _get_cpu_model():
    """Get the Linux CPU model from /proc/cpuinfo."""
    try:
        with open(
            "/proc/cpuinfo",
            "r",
            encoding="utf-8",
        ) as file:
            for line in file:
                if line.lower().startswith("model name"):
                    parts = line.split(
                        ":",
                        1,
                    )

                    if len(parts) == 2:
                        return parts[1].strip() or None

    except (
        FileNotFoundError,
        PermissionError,
        OSError,
    ):
        pass

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
                round(
                    current_mhz / 1000,
                    2,
                )
                if current_mhz is not None
                else None
            ),
            "min_mhz": min_mhz,
            "min_ghz": (
                round(
                    min_mhz / 1000,
                    2,
                )
                if min_mhz is not None
                else None
            ),
            "max_mhz": max_mhz,
            "max_ghz": (
                round(
                    max_mhz / 1000,
                    2,
                )
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
    """Get current utilisation for every logical CPU."""
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
    """
    Read CPU cache information from Linux sysfs.

    Uses the first CPU's cache topology exposed through:
        /sys/devices/system/cpu/cpu0/cache
    """
    result = {
        "available": False,
        "l1_kb": None,
        "l2_kb": None,
        "l3_kb": None,
    }

    cache_root = (
        "/sys/devices/system/cpu/cpu0/cache"
    )

    cache_values = {
        "l1": [],
        "l2": [],
        "l3": [],
    }

    try:
        entries = os.listdir(
            cache_root
        )

    except (
        FileNotFoundError,
        PermissionError,
        OSError,
    ):
        return result

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

        try:
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

            # Ignore instruction-only caches.
            if cache_type.lower() == "instruction":
                continue

            with open(
                size_path,
                "r",
                encoding="utf-8",
            ) as file:
                size = file.read().strip().upper()

        except (
            FileNotFoundError,
            PermissionError,
            OSError,
        ):
            continue

        match = re.fullmatch(
            r"([0-9.]+)\s*([KMG])",
            size,
        )

        if not match:
            continue

        try:
            number = float(
                match.group(1)
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

        unit = match.group(2)

        multiplier = {
            "K": 1,
            "M": 1024,
            "G": 1024 * 1024,
        }.get(unit)

        if multiplier is None:
            continue

        size_kb = int(
            number * multiplier
        )

        if level in (
            "1",
            "2",
            "3",
        ):
            cache_values[
                f"l{level}"
            ].append(
                size_kb
            )

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

    return result


def _get_temperature_info():
    """
    Get CPU-related temperature from Linux thermal zones.

    Only thermal zones whose names indicate CPU/package/core/x86
    hardware are considered.
    """
    result = {
        "available": False,
        "cpu_temperature_c": None,
        "source": None,
    }

    thermal_root = "/sys/class/thermal"

    temperatures = []

    try:
        entries = os.listdir(
            thermal_root
        )

    except (
        FileNotFoundError,
        PermissionError,
        OSError,
    ):
        return result

    for entry in entries:
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

        try:
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

        except (
            FileNotFoundError,
            PermissionError,
            OSError,
            ValueError,
            TypeError,
        ):
            continue

        if -20 <= temperature <= 150:
            temperatures.append(
                temperature
            )

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


def _get_power_info():
    """
    Read Intel RAPL energy counters where available.

    RAPL exposes cumulative energy, not an instantaneous power
    value. Therefore cpu_power_w remains unavailable here unless
    a future sampling layer calculates it from energy deltas.
    """
    result = {
        "available": False,
        "cpu_power_w": None,
        "energy_uj": None,
        "source": None,
    }

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

    except (
        FileNotFoundError,
        PermissionError,
        OSError,
    ):
        return result

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

        except (
            FileNotFoundError,
            PermissionError,
            OSError,
            ValueError,
        ):
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


def get_cpu():
    """
    Collect current Linux CPU information.

    This collector only gathers raw/current CPU information.
    Historical averages and analysis belong in the analytics layer.
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
            "architecture": os.uname().machine,

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
