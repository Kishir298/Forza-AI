import platform
import re
import subprocess


def get_windows_display():
    """Get display information on Windows."""

    displays = []

    try:
        command = (
            "Get-CimInstance -Namespace root\\wmi "
            "-ClassName WmiMonitorBasicDisplayParams | "
            "ForEach-Object { "
            "$size = [math]::Sqrt("
            "$_.MaxHorizontalImageSize * $_.MaxHorizontalImageSize + "
            "$_.MaxVerticalImageSize * $_.MaxVerticalImageSize"
            "); "
            "[PSCustomObject]@{"
            "WidthCM=$_.MaxHorizontalImageSize;"
            "HeightCM=$_.MaxVerticalImageSize;"
            "Active=$_.Active"
            "} "
            "} | ConvertTo-Csv -NoTypeInformation"
        )

        result = subprocess.check_output(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                command,
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )

        lines = result.strip().splitlines()

        if len(lines) > 1:
            headers = [
                value.strip('"')
                for value in lines[0].split(",")
            ]

            for line in lines[1:]:
                values = [
                    value.strip('"')
                    for value in line.split(",")
                ]

                if len(values) != len(headers):
                    continue

                data = dict(zip(headers, values))

                displays.append(
                    {
                        "width_cm": int(float(data["WidthCM"])),
                        "height_cm": int(float(data["HeightCM"])),
                        "active": data["Active"].lower() == "true",
                    }
                )

    except (
        OSError,
        subprocess.SubprocessError,
        ValueError,
        KeyError,
    ):
        pass

    return displays


def get_macos_display():
    """Get display information on macOS."""

    displays = []

    try:
        result = subprocess.check_output(
            [
                "system_profiler",
                "SPDisplaysDataType",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )

        for line in result.splitlines():
            line = line.strip()

            if "Resolution:" in line:
                resolution = line.split(
                    "Resolution:",
                    1,
                )[1].strip()

                displays.append(
                    {
                        "resolution": resolution,
                    }
                )

    except (
        OSError,
        subprocess.SubprocessError,
    ):
        pass

    return displays


def get_linux_display():
    """Get display information on Linux."""

    displays = []

    try:
        result = subprocess.check_output(
            [
                "xrandr",
                "--query",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )

        for line in result.splitlines():

            if " connected" not in line:
                continue

            match = re.search(
                r"(\d+)x(\d+)\+\d+\+\d+",
                line,
            )

            if match:
                displays.append(
                    {
                        "width": int(match.group(1)),
                        "height": int(match.group(2)),
                    }
                )

    except (
        OSError,
        subprocess.SubprocessError,
    ):
        pass

    return displays


def get_display():
    """
    Return display information.

    Supports Windows, macOS, and Linux.
    """

    system = platform.system()

    if system == "Windows":
        displays = get_windows_display()

    elif system == "Darwin":
        displays = get_macos_display()

    elif system == "Linux":
        displays = get_linux_display()

    else:
        displays = []

    return {
        "component": "Display",
        "available": bool(displays),
        "display_count": len(displays),
        "displays": displays,
    }