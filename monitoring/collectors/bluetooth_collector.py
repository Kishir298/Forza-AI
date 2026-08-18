import json
import platform
import subprocess


def _run_powershell(command):
    """Run PowerShell safely and return stdout."""

    try:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                command,
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        if result.returncode != 0:
            return None

        output = result.stdout.strip()

        return output if output else None

    except Exception:
        return None


def _powershell_json(command):
    """Run PowerShell and parse JSON output."""

    output = _run_powershell(command)

    if not output:
        return []

    try:
        data = json.loads(output)

        if isinstance(data, dict):
            return [data]

        if isinstance(data, list):
            return data

    except Exception:
        pass

    return []


def _get_windows_bluetooth_adapters():
    """
    Find actual Bluetooth radio/adapter hardware.

    Windows exposes the Bluetooth radio as a PnP device,
    commonly with names such as Intel Wireless Bluetooth.
    """

    command = r"""
Get-PnpDevice -PresentOnly |
Where-Object {
    $_.FriendlyName -match "Bluetooth"
} |
Select-Object FriendlyName, Status, Class, Manufacturer, InstanceId |
ConvertTo-Json -Compress
"""

    devices = _powershell_json(command)

    adapters = []

    for device in devices:

        name = device.get("FriendlyName")

        if not name:
            continue

        name_lower = name.lower()

        # Ignore individual Bluetooth peripherals.
        peripheral_keywords = (
            "headphone",
            "headset",
            "earbud",
            "speaker",
            "mouse",
            "keyboard",
            "controller",
            "gamepad",
            "phone",
            "audio",
        )

        if any(
            keyword in name_lower
            for keyword in peripheral_keywords
        ):
            continue

        adapters.append(
            {
                "name": name,
                "status": device.get(
                    "Status"
                ),
                "class": device.get(
                    "Class"
                ),
                "manufacturer": device.get(
                    "Manufacturer"
                ),
                "instance_id": device.get(
                    "InstanceId"
                ),
                "enabled": (
                    device.get("Status")
                    == "OK"
                ),
            }
        )

    return adapters


def _get_windows_bluetooth_devices():
    """
    Find Bluetooth peripherals known to Windows.
    """

    command = r"""
Get-PnpDevice -PresentOnly |
Where-Object {
    $_.InstanceId -like "BTHENUM\*" -or
    $_.InstanceId -like "BTHLEDEVICE\*"
} |
Select-Object FriendlyName, Status, Class, Manufacturer, InstanceId |
ConvertTo-Json -Compress
"""

    devices = _powershell_json(command)

    result = []

    for device in devices:

        name = device.get(
            "FriendlyName"
        )

        if not name:
            continue

        result.append(
            {
                "name": name,

                "status": device.get(
                    "Status"
                ),

                "class": device.get(
                    "Class"
                ),

                "manufacturer": device.get(
                    "Manufacturer"
                ),

                "instance_id": device.get(
                    "InstanceId"
                ),

                # PresentOnly means Windows currently
                # sees the device.
                "present": True,

                "connected": (
                    device.get("Status")
                    == "OK"
                ),
            }
        )

    return result


def _get_windows_bluetooth():
    """
    Complete Windows Bluetooth state.
    """

    adapters = (
        _get_windows_bluetooth_adapters()
    )

    devices = (
        _get_windows_bluetooth_devices()
    )

    return adapters, devices


def _get_linux_bluetooth():

    adapters = []
    devices = []

    try:

        result = subprocess.run(
            [
                "bluetoothctl",
                "list",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if result.returncode == 0:

            for line in result.stdout.splitlines():

                line = line.strip()

                if line.startswith(
                    "Controller "
                ):

                    parts = line.split(
                        " ",
                        2,
                    )

                    if len(parts) >= 3:

                        adapters.append(
                            {
                                "name": parts[2],
                                "address": parts[1],
                                "enabled": True,
                                "status": "OK",
                                "manufacturer": None,
                                "driver_version": None,
                            }
                        )

        result = subprocess.run(
            [
                "bluetoothctl",
                "devices",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if result.returncode == 0:

            for line in result.stdout.splitlines():

                parts = line.split(
                    " ",
                    2,
                )

                if len(parts) >= 3:

                    devices.append(
                        {
                            "name": parts[2],
                            "address": parts[1],
                            "present": True,
                            "connected": False,
                        }
                    )

    except Exception:
        pass

    return adapters, devices


def _get_macos_bluetooth():

    adapters = []
    devices = []

    try:

        result = subprocess.run(
            [
                "system_profiler",
                "SPBluetoothDataType",
                "-json",
            ],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )

        if result.returncode != 0:
            return adapters, devices

        data = json.loads(
            result.stdout
        )

        sections = data.get(
            "SPBluetoothDataType",
            [],
        )

        for section in sections:

            if not isinstance(
                section,
                dict,
            ):
                continue

            for name, info in section.items():

                if not isinstance(
                    info,
                    dict,
                ):
                    continue

                adapters.append(
                    {
                        "name": name,
                        "enabled": True,
                        "status": "OK",
                        "manufacturer": info.get(
                            "controller_manufacturer"
                        ),
                        "driver_version": info.get(
                            "controller_firmware_version"
                        ),
                    }
                )

    except Exception:
        pass

    return adapters, devices


def _get_platform_bluetooth():

    system = platform.system()

    if system == "Windows":
        return _get_windows_bluetooth()

    if system == "Linux":
        return _get_linux_bluetooth()

    if system == "Darwin":
        return _get_macos_bluetooth()

    return [], []


def get_bluetooth():

    """
    Collect Bluetooth hardware and connection state.

    Returns:
        available
        enabled
        adapter information
        known/present Bluetooth devices
        connected device count
    """

    try:

        adapters, devices = (
            _get_platform_bluetooth()
        )

        available = bool(
            adapters
        )

        enabled = any(
            adapter.get(
                "enabled",
                False,
            )
            for adapter in adapters
        )

        connected_devices = [
            device
            for device in devices
            if device.get(
                "connected",
                False,
            )
        ]

        return {
            "component": "Bluetooth",

            "available": available,

            "enabled": enabled,

            "adapter_count": len(
                adapters
            ),

            "adapters": adapters,

            "device_count": len(
                devices
            ),

            "connected_device_count": len(
                connected_devices
            ),

            "connected_devices": (
                connected_devices
            ),

            "devices": devices,

            "platform": platform.system(),
        }

    except Exception as error:

        return {
            "component": "Bluetooth",

            "available": False,

            "enabled": False,

            "adapter_count": 0,

            "adapters": [],

            "device_count": 0,

            "connected_device_count": 0,

            "connected_devices": [],

            "devices": [],

            "platform": platform.system(),

            "error": str(error),
        }