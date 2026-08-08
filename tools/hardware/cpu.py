import subprocess


def get_cpu():

    try:

        model = subprocess.check_output(
            [
                "sysctl",
                "-n",
                "machdep.cpu.brand_string"
            ]
        ).decode().strip()


        cores = subprocess.check_output(
            [
                "sysctl",
                "-n",
                "machdep.cpu.core_count"
            ]
        ).decode().strip()


        threads = subprocess.check_output(
            [
                "sysctl",
                "-n",
                "machdep.cpu.thread_count"
            ]
        ).decode().strip()


        return f"""
CPU Information:

Model:
{model}

Physical Cores:
{cores}

Threads:
{threads}
"""


    except Exception as e:

        return f"CPU information unavailable: {e}"