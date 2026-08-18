import platform
import psutil


def _get_cpu_model():
    system = platform.system()

    if system == "Windows":
        return platform.processor() or None

    if system == "Darwin":
        try:
            import subprocess

            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
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
            with open("/proc/cpuinfo", "r", encoding="utf-8") as file:
                for line in file:
                    if line.lower().startswith("model name"):
                        return line.split(":", 1)[1].strip()

        except Exception:
            pass

    return platform.processor() or None


def _get_cpu_frequency():
    try:
        frequency = psutil.cpu_freq()

        if frequency is None:
            return None

        return {
            "current_mhz": round(frequency.current, 2)
            if frequency.current
            else None,

            "min_mhz": round(frequency.min, 2)
            if frequency.min
            else None,

            "max_mhz": round(frequency.max, 2)
            if frequency.max
            else None,
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


def get_cpu():
    """
    Collect current CPU information.

    This collector only gathers raw/current CPU information.
    Historical averages and analysis belong to the processing layer.
    """

    try:
        physical_cores = psutil.cpu_count(logical=False)
        logical_cores = psutil.cpu_count(logical=True)

        usage_percent = psutil.cpu_percent(interval=0.5)

        frequency = _get_cpu_frequency()
        core_usage = _get_core_usage()

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
        }