import platform
import subprocess

import psutil


def get_cpu_model():
    """Detect the CPU model on Windows, macOS, and Linux."""

    system = platform.system()

    try:
        if system == "Windows":
            result = subprocess.check_output(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "(Get-CimInstance Win32_Processor).Name",
                ],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()

            if result:
                return result

        elif system == "Darwin":
            result = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()

            if result:
                return result

        elif system == "Linux":
            with open("/proc/cpuinfo", "r", encoding="utf-8") as file:
                for line in file:
                    if line.lower().startswith("model name"):
                        return line.split(":", 1)[1].strip()

    except (OSError, subprocess.SubprocessError, FileNotFoundError):
        pass

    return platform.processor() or "Unknown"


def get_cpu():
    """Return CPU information."""

    model = get_cpu_model()

    physical_cores = psutil.cpu_count(logical=False)
    threads = psutil.cpu_count(logical=True)

    usage_percent = psutil.cpu_percent(interval=0.2)

    core_usage = psutil.cpu_percent(
        interval=0.2,
        percpu=True,
    )

    frequency = psutil.cpu_freq()

    frequency_mhz = None

    if frequency:
        frequency_mhz = round(frequency.current, 1)

    return {
        "component": "CPU",
        "model": model,
        "physical_cores": physical_cores,
        "threads": threads,
        "usage_percent": round(usage_percent, 1),
        "core_usage": [round(value, 1) for value in core_usage],
        "frequency_mhz": frequency_mhz,
    }
