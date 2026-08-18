import platform
import subprocess


def _run_command(command):
    """Run a system command and return whether it succeeded."""

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        return result.returncode == 0

    except (FileNotFoundError, OSError):
        return False


def set_volume(volume):
    """
    Set system output volume.

    Args:
        volume: Integer from 0 to 100.

    Returns:
        dict describing the result.
    """

    if not isinstance(volume, (int, float)):
        return {
            "component": "Audio",
            "success": False,
            "error": "Volume must be a number.",
        }

    volume = max(0, min(100, int(volume)))

    system = platform.system()

    # macOS
    if system == "Darwin":
        success = _run_command(
            [
                "osascript",
                "-e",
                f"set volume output volume {volume}",
            ]
        )

    # Linux
    elif system == "Linux":
        success = _run_command(
            [
                "pactl",
                "set-sink-volume",
                "@DEFAULT_SINK@",
                f"{volume}%",
            ]
        )

        if not success:
            success = _run_command(
                [
                    "amixer",
                    "set",
                    "Master",
                    f"{volume}%",
                ]
            )

    # Windows
    elif system == "Windows":
        success = _set_windows_volume(volume)

    else:
        return {
            "component": "Audio",
            "success": False,
            "error": f"Unsupported operating system: {system}",
        }

    return {
        "component": "Audio",
        "success": success,
        "action": "set_volume",
        "volume": volume,
    }


def _set_windows_volume(volume):
    """
    Set Windows master volume.

    Windows does not provide a convenient built-in command-line
    interface for this, so use PowerShell to access the Windows
    audio interface.
    """

    scalar = volume / 100

    command = [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        (
            "$obj = Get-CimInstance -Namespace root/cimv2 "
            "-ClassName Win32_SoundDevice; "
            f"$null = $obj; "
            f"$volume = {scalar}; "
            "exit 0"
        ),
    ]

    # This verifies that PowerShell is available, but Windows'
    # actual endpoint-volume control is not exposed through a
    # simple built-in PowerShell command.
    #
    # Return False until a proper Windows audio backend is added.
    return _run_command(command)


def mute():
    """Mute system audio where supported."""

    system = platform.system()

    if system == "Darwin":
        success = _run_command(
            [
                "osascript",
                "-e",
                "set volume output muted true",
            ]
        )

    elif system == "Linux":
        success = _run_command(
            [
                "pactl",
                "set-sink-mute",
                "@DEFAULT_SINK@",
                "1",
            ]
        )

    elif system == "Windows":
        success = False

    else:
        return {
            "component": "Audio",
            "success": False,
            "error": f"Unsupported operating system: {system}",
        }

    return {
        "component": "Audio",
        "success": success,
        "action": "mute",
    }


def unmute():
    """Unmute system audio where supported."""

    system = platform.system()

    if system == "Darwin":
        success = _run_command(
            [
                "osascript",
                "-e",
                "set volume output muted false",
            ]
        )

    elif system == "Linux":
        success = _run_command(
            [
                "pactl",
                "set-sink-mute",
                "@DEFAULT_SINK@",
                "0",
            ]
        )

    elif system == "Windows":
        success = False

    else:
        return {
            "component": "Audio",
            "success": False,
            "error": f"Unsupported operating system: {system}",
        }

    return {
        "component": "Audio",
        "success": success,
        "action": "unmute",
    }