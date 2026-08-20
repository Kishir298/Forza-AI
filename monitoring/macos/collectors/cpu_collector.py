import platform
import subprocess

import psutil


def _run_command(command, timeout=3):
    """Run a macOS system command safely."""
    try:
        result = subprocess.run(
            command,
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


def _get_cpu_model():
    """Get the CPU model reported by macOS."""
    output = _run_command(
        [
            "sysctl",
            "-n",
            "machdep.cpu.brand_string",
        ]
    )

    if output:
        return output

    # Apple Silicon may expose useful information through
    # sysctl even when the traditional brand string is absent.
    output = _run_command(
        [
            "sysctl",
            "-n",
            "hw.model",
        ]
    )

    return output


def _get_cpu_architecture():
    """Get the CPU architecture reported by macOS."""
    output = _run_command(
        [
            "uname",
            "-m",
        ]
    )

    if output:
        return output

    return platform.machine() or None


def _get_cpu_frequency():
    """
    Get CPU frequency information where macOS exposes it.

    Apple Silicon does not expose a simple universal live
    frequency through standard sysctl interfaces, so unavailable
    values are returned as None rather than estimated.
    """
    result = {
        "current_mhz": None,
        "current_ghz": None,
        "min_mhz": None,
        "min_ghz": None,
        "max_mhz": None,
        "max_ghz": None,
        "available": False,
    }

    frequency = psutil.cpu_freq()

    if frequency is None:
        return result

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

    result.update(
        {
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
            "available": (
                current_mhz is not None
                or min_mhz is not None
                or max_mhz is not None
            ),
        }
    )

    return result


def _get_core_usage():
    """Get current utilization for every logical CPU."""
    try:
        values = psutil.cpu_percent(
            interval=0.5,
            percpu=True,
        )

        return [
            round(value, 1)
            for value in values
        ]

    except (
        psutil.Error,
        OSError,
        ValueError,
    ):
        return []


def _get_cache_info():
    """
    Get CPU cache sizes from macOS sysctl.

    macOS may expose separate instruction/data L1 caches.
    We report the largest exposed L1 cache value so the
    returned structure stays consistent.
    """
    result = {
        "available": False,
        "l1_kb": None,
        "l2_kb": None,
        "l3_kb": None,
    }

    cache_sources = {
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

    for key, sysctl_names in cache_sources.items():
        values = []

        for sysctl_name in sysctl_names:
            output = _run_command(
                [
                    "sysctl",
                    "-n",
                    sysctl_name,
                ]
            )

            if output is None:
                continue

            try:
                value = int(output)

            except ValueError:
                continue

            if value >= 0:
                values.append(
                    value // 1024
                )

        if values:
            result[key] = max(values)

    result["available"] = any(
        value is not None
        for key, value in result.items()
        if key != "available"
    )

    return result


def _get_temperature_info():
    """
    Return CPU temperature information.

    macOS does not provide a reliable CPU temperature through
    standard built-in Python/sysctl interfaces. Do not invent
    a temperature from unrelated sensors.
    """
    return {
        "available": False,
        "cpu_temperature_c": None,
        "source": None,
    }


def _get_power_info():
    """
    Return CPU power information.

    Standard macOS APIs do not provide a reliable universal
    process-independent CPU package power reading, especially
    across Intel Macs and Apple Silicon. Return unavailable
    rather than estimating.
    """
    return {
        "available": False,
        "cpu_power_w": None,
        "energy_uj": None,
        "source": None,
    }


def get_cpu():
    """
    Collect macOS CPU information.

    This collector is intentionally macOS-specific.
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

        return {
            "component": "CPU",
            "available": True,

            "model": _get_cpu_model(),
            "architecture": _get_cpu_architecture(),

            "physical_cores": physical_cores,
            "logical_cores": logical_cores,

            "usage_percent": round(
                usage_percent,
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

            "frequency": {
                "available": False,
                "current_mhz": None,
                "current_ghz": None,
                "min_mhz": None,
                "min_ghz": None,
                "max_mhz": None,
                "max_ghz": None,
            },

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