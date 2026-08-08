import psutil


def get_battery():

    battery = psutil.sensors_battery()


    if battery is None:

        return {

            "component": "Battery",

            "status": "Unavailable"

        }


    percent = battery.percent


    if battery.power_plugged:

        status = "Charging"

    else:

        status = "Not Charging"


    seconds = battery.secsleft


    if seconds == psutil.POWER_TIME_UNLIMITED:

        time_left = "Unlimited (plugged in)"

    elif seconds == psutil.POWER_TIME_UNKNOWN:

        time_left = "Unknown"

    else:

        hours = seconds // 3600

        minutes = (seconds % 3600) // 60

        time_left = f"{hours}h {minutes}m"


    return {


        "component": "Battery",

        "percentage": percent,

        "status": status,

        "time_remaining": time_left

    }
    