import math

import psutil


def format_time(seconds):
    """Convert seconds into a readable battery time string."""

    if seconds is None:
        return None

    if not isinstance(seconds, (int, float)):
        return None

    if not math.isfinite(seconds):
        return None

    if seconds <= 0:
        return None

    # Ignore clearly invalid OS estimates.
    # 7 days is already an extremely generous upper bound.
    if seconds > 7 * 24 * 60 * 60:
        return None

    minutes = int(seconds // 60)

    hours = minutes // 60
    remaining_minutes = minutes % 60

    if hours > 0:
        return f"{hours}h {remaining_minutes}m"

    return f"{remaining_minutes}m"


def get_battery():
    """Return battery information across Windows, macOS, and Linux."""

    battery = psutil.sensors_battery()

    if battery is None:
        return {
            "component": "Battery",
            "available": False,
            "percentage": None,
            "status": "No battery detected",
            "time_remaining": None,
        }

    percentage = round(battery.percent, 1)

    if battery.power_plugged:
        status = "Charging"
    else:
        status = "Not Charging"

    time_remaining = format_time(battery.secsleft)

    return {
        "component": "Battery",
        "available": True,
        "percentage": percentage,
        "status": status,
        "time_remaining": time_remaining,
    }