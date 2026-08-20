import psutil


def get_battery():
    """
    Collect battery information on Windows.
    """

    try:
        battery = psutil.sensors_battery()

        if battery is None:
            return {
                "component": "Battery",
                "available": False,
                "percent": None,
                "charging": None,
                "time_left_seconds": None,
            }

        return {
            "component": "Battery",
            "available": True,
            "percent": round(battery.percent, 1),
            "charging": battery.power_plugged,
            "time_left_seconds": (
                battery.secsleft
                if battery.secsleft >= 0
                else None
            ),
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
