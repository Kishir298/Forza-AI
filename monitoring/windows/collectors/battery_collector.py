import ctypes
import ctypes.wintypes


class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.wintypes.BYTE),
        ("BatteryFlag", ctypes.wintypes.BYTE),
        ("BatteryLifePercent", ctypes.wintypes.BYTE),
        ("Reserved", ctypes.wintypes.BYTE),
        ("BatteryLifeTime", ctypes.wintypes.DWORD),
        ("BatteryFullLifeTime", ctypes.wintypes.DWORD),
    ]


def _get_windows_power_status():
    """
    Get battery information directly from the native
    Windows GetSystemPowerStatus API.
    """

    status = SYSTEM_POWER_STATUS()

    try:
        result = ctypes.windll.kernel32.GetSystemPowerStatus(
            ctypes.byref(status)
        )

    except Exception:
        return None

    if not result:
        return None

    return status


def _normalize_time_left(seconds):
    """
    Convert the Windows battery lifetime value into a
    usable number of seconds.

    Windows uses 0xFFFFFFFF when the remaining time
    is unknown.
    """

    if seconds is None:
        return None

    seconds = int(seconds)

    if seconds == 0xFFFFFFFF:
        return None

    if seconds < 0:
        return None

    return seconds


def get_battery():
    """
    Collect battery information using the native
    Windows power-management API.

    Returns:
        dict containing:

        - component
        - available
        - percent
        - charging
        - time_left_seconds
    """

    try:
        status = _get_windows_power_status()

        if status is None:
            return {
                "component": "Battery",
                "available": False,
                "percent": None,
                "charging": None,
                "time_left_seconds": None,
            }

        battery_percent = int(
            status.BatteryLifePercent
        )

        # 255 means the battery percentage is unknown.
        if battery_percent == 255:
            battery_percent = None

        ac_status = int(
            status.ACLineStatus
        )

        if ac_status == 1:
            charging = True

        elif ac_status == 0:
            charging = False

        else:
            charging = None

        time_left = _normalize_time_left(
            status.BatteryLifeTime
        )

        return {
            "component": "Battery",
            "available": (
                battery_percent is not None
                or charging is not None
                or time_left is not None
            ),
            "percent": battery_percent,
            "charging": charging,
            "time_left_seconds": time_left,
        }

    except Exception as error:
        return {
            "component": "Battery",
            "available": False,
            "error": str(error),
            "percent": None,
            "charging": None,
            "time_left_seconds": None,
        }
