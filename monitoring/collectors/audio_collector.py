import json
import platform
import subprocess

import psutil


def _run_powershell(command):
    """
    Run a PowerShell command on Windows.
    """

    try:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                command,
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if result.returncode != 0:
            return None

        output = result.stdout.strip()

        if not output:
            return None

        return output

    except Exception:
        return None


def _get_windows_audio():
    """
    Get Windows audio endpoint information.

    Uses Windows PowerShell/CIM information where available.
    """

    result = {
        "outputs": [],
        "inputs": [],
    }

    if platform.system() != "Windows":
        return result

    try:
        output = _run_powershell(
            """
            Get-CimInstance Win32_SoundDevice |
            Select-Object Name, Manufacturer, Status, DeviceID |
            ConvertTo-Json -Compress
            """
        )

        if output:
            devices = json.loads(output)

            if isinstance(devices, dict):
                devices = [devices]

            for device in devices:
                name = device.get("Name")

                if not name:
                    continue

                result["outputs"].append(
                    {
                        "name": name,
                        "manufacturer": device.get(
                            "Manufacturer"
                        ),
                        "status": device.get(
                            "Status"
                        ),
                        "device_id": device.get(
                            "DeviceID"
                        ),
                    }
                )

    except Exception:
        pass

    return result


def _get_macos_audio():
    """
    Get macOS audio devices through system_profiler.
    """

    result = {
        "outputs": [],
        "inputs": [],
    }

    if platform.system() != "Darwin":
        return result

    try:
        completed = subprocess.run(
            [
                "system_profiler",
                "SPAudioDataType",
                "-json",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if completed.returncode != 0:
            return result

        data = json.loads(
            completed.stdout
        )

        for section in data.get(
            "SPAudioDataType",
            [],
        ):
            for device_name, device_data in section.items():

                if not isinstance(
                    device_data,
                    dict,
                ):
                    continue

                result["outputs"].append(
                    {
                        "name": device_name,
                        "manufacturer": device_data.get(
                            "coreaudio_device_manufacturer"
                        ),
                        "status": None,
                        "device_id": None,
                    }
                )

    except Exception:
        pass

    return result


def _get_linux_audio():
    """
    Get Linux audio devices through PulseAudio/PipeWire
    using pactl when available.
    """

    result = {
        "outputs": [],
        "inputs": [],
    }

    if platform.system() != "Linux":
        return result

    try:
        completed = subprocess.run(
            [
                "pactl",
                "list",
                "short",
                "sinks",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if completed.returncode == 0:

            for line in completed.stdout.splitlines():

                parts = line.split(
                    "\t"
                )

                if len(parts) >= 2:

                    result["outputs"].append(
                        {
                            "name": parts[1],
                            "manufacturer": None,
                            "status": "available",
                            "device_id": parts[0],
                        }
                    )

    except Exception:
        pass

    return result


def _get_platform_audio():
    system = platform.system()

    if system == "Windows":
        return _get_windows_audio()

    if system == "Darwin":
        return _get_macos_audio()

    if system == "Linux":
        return _get_linux_audio()

    return {
        "outputs": [],
        "inputs": [],
    }


def _get_volume():
    """
    Get current master volume where a reliable cross-platform
    interface is available.

    Windows volume control will be handled by the controller
    layer, so this collector only attempts basic state reading.
    """

    if platform.system() != "Windows":
        return {
            "available": False,
            "percent": None,
            "muted": None,
        }

    # Windows does not expose the endpoint volume cleanly
    # through standard Python libraries. Keep the collector
    # safe rather than pretending we have data.
    return {
        "available": False,
        "percent": None,
        "muted": None,
    }


def get_audio():
    """
    Collect current audio hardware information.

    Audio control belongs to the controller layer.
    """

    try:
        devices = _get_platform_audio()

        return {
            "component": "Audio",
            "available": bool(
                devices["outputs"]
                or devices["inputs"]
            ),

            "outputs": devices["outputs"],
            "inputs": devices["inputs"],

            "volume": _get_volume(),

            "platform": platform.system(),
        }

    except Exception as error:
        return {
            "component": "Audio",
            "available": False,
            "error": str(error),

            "outputs": [],
            "inputs": [],

            "volume": {
                "available": False,
                "percent": None,
                "muted": None,
            },

            "platform": platform.system(),
        }