import platform
import subprocess


def get_windows_cameras():
    """Detect cameras on Windows."""

    cameras = []

    try:
        command = (
            "Get-PnpDevice -Class Camera -Status OK | "
            "Select-Object -ExpandProperty FriendlyName"
        )

        result = subprocess.check_output(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                command,
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )

        cameras = [
            line.strip()
            for line in result.splitlines()
            if line.strip()
        ]

    except (OSError, subprocess.SubprocessError):
        pass

    return cameras


def get_macos_cameras():
    """Detect cameras on macOS."""

    cameras = []

    try:
        result = subprocess.check_output(
            [
                "system_profiler",
                "SPCameraDataType",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )

        for line in result.splitlines():
            line = line.strip()

            if line.startswith("Model ID:"):
                cameras.append(
                    line.split("Model ID:", 1)[1].strip()
                )

            elif line.startswith("Model:"):
                cameras.append(
                    line.split("Model:", 1)[1].strip()
                )

    except (OSError, subprocess.SubprocessError):
        pass

    return cameras


def get_linux_cameras():
    """Detect cameras on Linux."""

    cameras = []

    try:
        result = subprocess.check_output(
            [
                "v4l2-ctl",
                "--list-devices",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )

        for line in result.splitlines():
            if line and not line.startswith("\t"):
                cameras.append(line.strip().rstrip(":"))

    except (OSError, subprocess.SubprocessError):
        pass

    return cameras


def get_cameras():
    """
    Return detected camera information.

    Supports Windows, macOS, and Linux.
    """

    system = platform.system()

    if system == "Windows":
        cameras = get_windows_cameras()

    elif system == "Darwin":
        cameras = get_macos_cameras()

    elif system == "Linux":
        cameras = get_linux_cameras()

    else:
        cameras = []

    return {
        "component": "Camera",
        "available": bool(cameras),
        "camera_count": len(cameras),
        "cameras": cameras,
    }
