import psutil


def get_battery():

    battery = psutil.sensors_battery()

    if battery is None:
        return "Battery information unavailable."

    percent = battery.percent

    charging = "Charging" if battery.power_plugged else "Not charging"

    remaining = battery.secsleft

    if remaining == psutil.POWER_TIME_UNLIMITED:
        time_left = "Unlimited (plugged in)"

    elif remaining == psutil.POWER_TIME_UNKNOWN:
        time_left = "Unknown"

    else:
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        time_left = f"{hours}h {minutes}m"


    return f"""
Battery Information:

Current Percentage:
{percent}%

Status:
{charging}

Estimated Remaining Time:
{time_left}
"""
