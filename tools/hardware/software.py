import platform
import subprocess


def get_software():

    try:

        macos = subprocess.check_output(
            [
                "sw_vers",
                "-productVersion"
            ]
        ).decode().strip()


        python = platform.python_version()


        shell = subprocess.check_output(
            [
                "echo",
                "$SHELL"
            ]
        ).decode().strip()


        return f"""
Software Information:

macOS Version:
{macos}

Python Version:
{python}

Architecture:
{platform.machine()}

Operating System:
{platform.system()}

"""
    
    except Exception as e:

        return f"Software information unavailable: {e}"
