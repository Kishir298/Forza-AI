import contextlib
import io
import json
import platform
import subprocess






def _get_windows_device_inventory():
    """
    Query Windows for camera-related imaging devices.

    This is useful for detecting devices such as:
    - RGB webcams
    - IR cameras
    - Windows Hello cameras
    """

    devices = []

    if platform.system() != "Windows":
        return devices

    command = r"""
Get-PnpDevice |
Where-Object {
    $_.Class -in @("Camera", "Image", "Sensor") -or
    $_.FriendlyName -match "camera|webcam|infrared|infra-red|IR|Windows Hello"
} |
Select-Object FriendlyName, Class, Status, InstanceId |
ConvertTo-Json -Compress
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
            timeout=8,
            check=False,
        )

        if result.returncode != 0:
            return devices

        output = result.stdout.strip()

        if not output:
            return devices

        data = json.loads(output)

        if isinstance(data, dict):
            data = [data]

        for device in data:

            name = device.get(
                "FriendlyName"
            )

            if not name:
                continue

            name_lower = name.lower()

            is_ir = any(
                keyword in name_lower
                for keyword in (
                    "infrared",
                    "infra-red",
                    " ir ",
                    "windows hello",
                    "ir camera",
                )
            )

            devices.append(
                {
                    "name": name,
                    "class": device.get(
                        "Class"
                    ),
                    "status": device.get(
                        "Status"
                    ),
                    "instance_id": device.get(
                        "InstanceId"
                    ),
                    "infrared": is_ir,
                }
            )

    except Exception:
        pass

    return devices


def _get_windows_cameras():
    """
    Detect Windows camera devices through Windows PnP.

    Windows device inventory is the authoritative source for
    camera detection. This avoids noisy DirectShow probing.
    """

    cameras = []

    if platform.system() != "Windows":
        return cameras

    devices = _get_windows_device_inventory()

    for index, device in enumerate(devices):

        device_class = device.get("class")

        if device_class not in (
            "Camera",
            "Image",
        ):
            continue

        name = device.get("name")

        if not name:
            continue

        # IR cameras are recorded separately.
        if device.get("infrared"):
            continue

        cameras.append(
            {
                "index": index,
                "name": name,
                "backend": "Windows PnP",
                "available": (
                    device.get("status") == "OK"
                ),
                "device_class": device_class,
            }
        )

    return cameras

def _get_linux_cameras():
    """
    Detect V4L2 camera devices on Linux.
    """

    cameras = []

    if platform.system() != "Linux":
        return cameras

    try:

        result = subprocess.run(
            [
                "bash",
                "-c",
                "ls /dev/video* 2>/dev/null",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if result.returncode != 0:
            return cameras

        devices = result.stdout.split()

        for index, device in enumerate(
            devices
        ):

            cameras.append(
                {
                    "index": index,
                    "name": device,
                    "device": device,
                    "backend": "V4L2",
                    "available": True,
                }
            )

    except Exception:
        pass

    return cameras


def _get_macos_cameras():
    """
    Detect cameras on macOS.
    """

    cameras = []

    if platform.system() != "Darwin":
        return cameras

    try:

        result = subprocess.run(
            [
                "system_profiler",
                "SPCameraDataType",
                "-json",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if result.returncode != 0:
            return cameras

        data = json.loads(
            result.stdout
        )

        devices = data.get(
            "SPCameraDataType",
            [],
        )

        for index, device in enumerate(
            devices
        ):

            cameras.append(
                {
                    "index": index,
                    "name": device.get(
                        "_name"
                    ),
                    "model": device.get(
                        "_name"
                    ),
                    "backend": "AVFoundation",
                    "available": True,
                }
            )

    except Exception:
        pass

    return cameras


def _get_platform_cameras():
    system = platform.system()

    if system == "Windows":
        return _get_windows_cameras()

    if system == "Darwin":
        return _get_macos_cameras()

    if system == "Linux":
        return _get_linux_cameras()

    return []


def _get_camera_capabilities(camera):
    """
    Return camera hardware information.

    Windows PnP is used for detection. Camera streaming/
    capability probing is intentionally handled elsewhere.
    """

    camera["accessible"] = (
        camera.get("status") == "OK"
        if "status" in camera
        else None
    )

    camera["width"] = None
    camera["height"] = None
    camera["resolution"] = None
    camera["fps"] = None

    return camera

def _merge_windows_ir_devices(
    cameras,
    windows_devices,
):
    """
    Add Windows device-inventory information to the camera
    list and separately identify IR cameras.
    """

    infrared_devices = []

    for device in windows_devices:

        if not device.get(
            "infrared"
        ):
            continue

        infrared_devices.append(
            {
                "name": device.get(
                    "name"
                ),
                "class": device.get(
                    "class"
                ),
                "status": device.get(
                    "status"
                ),
                "instance_id": device.get(
                    "instance_id"
                ),
                "available": (
                    device.get("status")
                    == "OK"
                ),
            }
        )

    return cameras, infrared_devices


def get_camera():
    """
    Collect camera hardware information.

    Detects:
    - Standard cameras/webcams
    - Windows IR/Hello cameras
    - Camera resolution
    - FPS where available
    - Camera backend
    - Camera accessibility

    Does NOT:
    - record video
    - save images
    - process camera frames
    """

    try:

        cameras = _get_platform_cameras()

        processed_cameras = []

        for camera in cameras:

            processed_cameras.append(
                _get_camera_capabilities(
                    camera
                )
            )

        infrared_cameras = []

        if platform.system() == "Windows":

            windows_devices = (
                _get_windows_device_inventory()
            )

            (
                processed_cameras,
                infrared_cameras,
            ) = _merge_windows_ir_devices(
                processed_cameras,
                windows_devices,
            )

        return {
            "component": "Camera",

            "available": bool(
                processed_cameras
                or infrared_cameras
            ),

            "camera_count": len(
                processed_cameras
            ),

            "cameras": processed_cameras,

            "infrared_camera_count": len(
                infrared_cameras
            ),

            "infrared_cameras": (
                infrared_cameras
            ),

            "platform": platform.system(),
        }

    except Exception as error:

        return {
            "component": "Camera",
            "available": False,

            "camera_count": 0,
            "cameras": [],

            "infrared_camera_count": 0,
            "infrared_cameras": [],

            "platform": platform.system(),

            "error": str(error),
        }