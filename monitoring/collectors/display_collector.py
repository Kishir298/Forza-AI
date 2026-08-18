import json
import platform
import subprocess

import screeninfo


def _get_monitors():
    """
    Get basic physical/logical monitor information using screeninfo.
    """

    try:
        monitors = screeninfo.get_monitors()

        return [
            {
                "name": monitor.name,
                "x": monitor.x,
                "y": monitor.y,
                "width": monitor.width,
                "height": monitor.height,
                "is_primary": bool(
                    getattr(monitor, "is_primary", False)
                ),
            }
            for monitor in monitors
        ]

    except Exception:
        return []


def _get_windows_details():
    """
    Get Windows display/GPU information.
    """

    details = []

    if platform.system() != "Windows":
        return details

    try:
        command = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            """
            Get-CimInstance Win32_VideoController |
            Select-Object Name, AdapterRAM, DriverVersion,
                          VideoModeDescription, CurrentRefreshRate,
                          CurrentHorizontalResolution,
                          CurrentVerticalResolution |
            ConvertTo-Json -Compress
            """,
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if result.returncode != 0 or not result.stdout.strip():
            return details

        data = json.loads(result.stdout)

        if isinstance(data, dict):
            data = [data]

        for gpu in data:
            adapter_ram = gpu.get("AdapterRAM")

            details.append(
                {
                    "gpu": gpu.get("Name"),
                    "driver_version": gpu.get(
                        "DriverVersion"
                    ),

                    "vram_bytes": adapter_ram,

                    "resolution": gpu.get(
                        "VideoModeDescription"
                    ),

                    "refresh_rate_hz": gpu.get(
                        "CurrentRefreshRate"
                    ),

                    "horizontal_resolution": gpu.get(
                        "CurrentHorizontalResolution"
                    ),

                    "vertical_resolution": gpu.get(
                        "CurrentVerticalResolution"
                    ),
                }
            )

    except Exception:
        pass

    return details


def _get_macos_details():
    """
    Get display information from macOS system_profiler.
    """

    details = []

    if platform.system() != "Darwin":
        return details

    try:
        result = subprocess.run(
            [
                "system_profiler",
                "SPDisplaysDataType",
                "-json",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if result.returncode != 0:
            return details

        data = json.loads(result.stdout)

        for gpu in data.get(
            "SPDisplaysDataType",
            [],
        ):
            gpu_name = gpu.get(
                "sppci_model"
            )

            vram = gpu.get(
                "sppci_vram"
            )

            for display in gpu.get(
                "spdisplays_ndrvs",
                [],
            ):
                details.append(
                    {
                        "gpu": gpu_name,
                        "model": display.get(
                            "_name"
                        ),

                        "vram": vram,

                        "resolution": display.get(
                            "_spdisplays_resolution"
                        ),

                        "retina": display.get(
                            "spdisplays_retina"
                        ),
                    }
                )

    except Exception:
        pass

    return details


def _get_linux_details():
    """
    Get display information through xrandr where available.
    """

    details = []

    if platform.system() != "Linux":
        return details

    try:
        result = subprocess.run(
            ["xrandr", "--query"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if result.returncode != 0:
            return details

        for line in result.stdout.splitlines():

            if " connected" not in line:
                continue

            parts = line.split()

            name = parts[0]

            resolution = None
            refresh_rate = None

            for part in parts:

                if "x" in part:
                    resolution_candidate = (
                        part.split("+")[0]
                    )

                    if (
                        resolution_candidate
                        .replace("x", "")
                        .isdigit()
                    ):
                        resolution = (
                            resolution_candidate
                        )

                if part.endswith("*"):
                    try:
                        refresh_rate = float(
                            part.rstrip("*+")
                        )
                    except ValueError:
                        pass

            details.append(
                {
                    "name": name,
                    "resolution": resolution,
                    "refresh_rate_hz": refresh_rate,
                }
            )

    except Exception:
        pass

    return details


def _get_platform_details():
    system = platform.system()

    if system == "Windows":
        return _get_windows_details()

    if system == "Darwin":
        return _get_macos_details()

    if system == "Linux":
        return _get_linux_details()

    return []


def get_display():
    """
    Collect current display information.

    This collector only reports display state/specifications.

    Brightness changing, screen mirroring, AirPlay and other
    display controls belong to the controller layer.
    """

    monitors = _get_monitors()
    platform_details = _get_platform_details()

    displays = []

    for index, monitor in enumerate(monitors):

        width = monitor.get("width")
        height = monitor.get("height")

        orientation = None

        if width and height:

            if width > height:
                orientation = "landscape"

            elif height > width:
                orientation = "portrait"

            else:
                orientation = "square"

        display = {
            "index": index,

            "name": monitor.get("name"),
            "model": None,
            "manufacturer": None,

            "width": width,
            "height": height,

            "resolution": (
                f"{width}x{height}"
                if width and height
                else None
            ),

            "refresh_rate_hz": None,

            "orientation": orientation,

            "is_primary": monitor.get(
                "is_primary",
                False,
            ),

            "scaling": None,
            "brightness_percent": None,
            "hdr": None,

            "connection_type": None,

            "gpu": None,
            "gpu_driver": None,
            "vram_bytes": None,
        }

        if index < len(platform_details):

            details = platform_details[index]

            display["gpu"] = details.get(
                "gpu"
            )

            display["gpu_driver"] = details.get(
                "driver_version"
            )

            display["vram_bytes"] = details.get(
                "vram_bytes"
            )

            refresh_rate = details.get(
                "refresh_rate_hz"
            )

            if refresh_rate:
                display["refresh_rate_hz"] = (
                    refresh_rate
                )

            model = details.get(
                "model"
            )

            if model:
                display["model"] = model

        displays.append(display)

    return {
        "component": "Display",
        "available": bool(displays),
        "display_count": len(displays),
        "displays": displays,
    }