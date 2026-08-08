import psutil
import subprocess


def get_cpu_model():

    try:
        model = subprocess.check_output(
            [
                "sysctl",
                "-n",
                "machdep.cpu.brand_string"
            ]
        ).decode().strip()

        return model

    except Exception:
        return "Unknown"



def get_cpu():

    cpu_usage = psutil.cpu_percent(interval=1)

    per_core = psutil.cpu_percent(
        interval=0.5,
        percpu=True
    )


    frequency = psutil.cpu_freq()

    if frequency:
        current_frequency = round(
            frequency.current,
            2
        )
    else:
        current_frequency = "Unknown"


    cores = psutil.cpu_count(
        logical=False
    )

    threads = psutil.cpu_count(
        logical=True
    )


    return {

        "component": "CPU",

        "model": get_cpu_model(),

        "physical_cores": cores,

        "threads": threads,

        "usage_percent": cpu_usage,

        "core_usage": per_core,

        "frequency_mhz": current_frequency

    }
