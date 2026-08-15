import platform
import socket
import sys


def get_software():
    """Return operating-system and runtime information."""

    return {
        "component": "Software",
        "os": platform.system(),
        "os_version": platform.version(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "hostname": socket.gethostname(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "system": platform.system(),
        "kernel": platform.release(),
        "processor": platform.processor(),
        "runtime_executable": sys.executable,
    }