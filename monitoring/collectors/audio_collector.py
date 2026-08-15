import platform
import subprocess
import re


def get_windows_audio():
    """Get audio devices, volume, and mute state on Windows."""

    devices = []

    try:
        command = (
            "Get-CimInstance Win32_SoundDevice | "
            "Where-Object {$_.Status -eq 'OK'} | "
            "Select-Object -ExpandProperty Name"
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

        devices = [
            line.strip()
            for line in result.splitlines()
            if line.strip()
        ]

    except (OSError, subprocess.SubprocessError):
        pass

    volume = None
    muted = None

    try:
        volume_command = (
            "[AudioManager]::GetMasterVolume()"
        )

        # Windows doesn't provide a simple built-in PowerShell
        # command for master volume, so this is intentionally
        # left unavailable until we add the Windows audio API.
        _ = volume_command

    except Exception:
        pass

    return devices, volume, muted


def get_macos_audio():
    """Get audio devices, volume, and mute state on macOS."""

    devices = []
    volume = None
    muted = None

    try:
        result = subprocess.check_output(
            [
                "system_profiler",
                "SPAudioDataType",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )

        for line in result.splitlines():
            line = line.strip()

            if line.startswith("Device:"):
                devices.append(
                    line.split("Device:", 1)[1].strip()
                )

    except (OSError, subprocess.SubprocessError):
        pass

    try:
        result = subprocess.check_output(
            [
                "osascript",
                "-e",
                "output volume of (get volume settings)",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )

        volume = int(result.strip())

    except (OSError, subprocess.SubprocessError, ValueError):
        pass

    try:
        result = subprocess.check_output(
            [
                "osascript",
                "-e",
                "output muted of (get volume settings)",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )

        muted = result.strip().lower() == "true"

    except (OSError, subprocess.SubprocessError):
        pass

    return devices, volume, muted


def get_linux_audio():
    """Get audio devices, volume, and mute state on Linux."""

    devices = []
    volume = None
    muted = None

    try:
        result = subprocess.check_output(
            [
                "pactl",
                "list",
                "short",
                "sinks",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )

        for line in result.splitlines():
            parts = line.split("\t")

            if len(parts) >= 2:
                devices.append(parts[1])

    except (OSError, subprocess.SubprocessError):
        pass

    try:
        result = subprocess.check_output(
            [
                "pactl",
                "get-sink-volume",
                "@DEFAULT_SINK@",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )

        match = re.search(r"(\d+)%", result)

        if match:
            volume = int(match.group(1))

    except (OSError, subprocess.SubprocessError, ValueError):
        pass

    try:
        result = subprocess.check_output(
            [
                "pactl",
                "get-sink-mute",
                "@DEFAULT_SINK@",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )

        muted = "yes" in result.lower()

    except (OSError, subprocess.SubprocessError):
        pass

    return devices, volume, muted


def get_audio():
    """
    Return current audio information.

    Supports Windows, macOS, and Linux.
    """

    system = platform.system()

    if system == "Windows":
        devices, volume, muted = get_windows_audio()

    elif system == "Darwin":
        devices, volume, muted = get_macos_audio()

    elif system == "Linux":
        devices, volume, muted = get_linux_audio()

    else:
        devices = []
        volume = None
        muted = None

    return {
        "component": "Audio",
        "available": bool(devices),
        "device_count": len(devices),
        "devices": devices,
        "volume_percent": volume,
        "muted": muted,
    }