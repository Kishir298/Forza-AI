import platform
import subprocess
import json

import psutil


def _get_basic_battery():
    """
    Get the common battery information exposed by psutil.
    """

    try:
        battery = psutil.sensors_battery()

        if battery is None:
            return None

        seconds_remaining = battery.secsleft

        # Windows commonly returns 4294967295 when the
        # remaining time is unknown.
        if seconds_remaining in (
            psutil.POWER_TIME_UNKNOWN,
            psutil.POWER_TIME_UNLIMITED,
            4294967295,
        ):
            seconds_remaining = None

        if seconds_remaining is not None and seconds_remaining < 0:
            seconds_remaining = None

        if battery.power_plugged:
            status = "Charging"
        else:
            status = "Discharging"

        return {
            "percentage": round(battery.percent, 1),
            "status": status,
            "charging": bool(battery.power_plugged),
            "power_plugged": bool(battery.power_plugged),
            "seconds_remaining": (
                int(seconds_remaining)
                if seconds_remaining is not None
                else None
            ),
        }

    except Exception:
        return None


def _get_windows_details():
    """
    Collect additional battery hardware information on Windows.
    """

    details = {
        "manufacturer": None,
        "model": None,
        "design_capacity_wh": None,
        "full_charge_capacity_wh": None,
        "cycle_count": None,
        "voltage_mv": None,
        "temperature_c": None,
    }

    if platform.system() != "Windows":
        return details

    try:
        command = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            """
            Get-CimInstance -Namespace root\\wmi -ClassName BatteryStaticData |
            Select-Object DesignedCapacity, FullChargedCapacity |
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

        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)

            if isinstance(data, list):
                data = data[0] if data else {}

            design = data.get("DesignedCapacity")
            full = data.get("FullChargedCapacity")

            if design:
                details["design_capacity_wh"] = round(
                    int(design) / 1000,
                    3,
                )

            if full:
                details["full_charge_capacity_wh"] = round(
                    int(full) / 1000,
                    3,
                )

    except Exception:
        pass

    return details


def _get_macos_details():
    """
    Collect additional battery information on macOS.
    """

    details = {
        "manufacturer": None,
        "model": None,
        "design_capacity_wh": None,
        "full_charge_capacity_wh": None,
        "cycle_count": None,
        "voltage_mv": None,
        "temperature_c": None,
    }

    if platform.system() != "Darwin":
        return details

    try:
        result = subprocess.run(
            ["system_profiler", "SPPowerDataType", "-json"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if result.returncode != 0:
            return details

        data = json.loads(result.stdout)

        power_data = data.get("SPPowerDataType", [])

        if not power_data:
            return details

        batteries = power_data[0].get(
            "sppower_battery_health_info",
            {},
        )

        details["cycle_count"] = batteries.get(
            "cycle_count"
        )

    except Exception:
        pass

    return details


def _get_linux_details():
    """
    Collect additional battery information on Linux
    through /sys/class/power_supply where available.
    """

    details = {
        "manufacturer": None,
        "model": None,
        "design_capacity_wh": None,
        "full_charge_capacity_wh": None,
        "cycle_count": None,
        "voltage_mv": None,
        "temperature_c": None,
    }

    if platform.system() != "Linux":
        return details

    try:
        import glob
        import os

        batteries = glob.glob(
            "/sys/class/power_supply/BAT*/"
        )

        if not batteries:
            return details

        battery = batteries[0]

        def read_file(filename):
            path = os.path.join(
                battery,
                filename,
            )

            try:
                with open(
                    path,
                    "r",
                    encoding="utf-8",
                ) as file:
                    return file.read().strip()

            except Exception:
                return None

        details["manufacturer"] = read_file(
            "manufacturer"
        )

        details["model"] = read_file(
            "model_name"
        )

        cycle_count = read_file(
            "cycle_count"
        )

        if cycle_count:
            try:
                details["cycle_count"] = int(
                    cycle_count
                )
            except ValueError:
                pass

        voltage = read_file(
            "voltage_now"
        )

        if voltage:
            try:
                details["voltage_mv"] = round(
                    int(voltage) / 1000,
                    2,
                )
            except ValueError:
                pass

        energy_full = read_file(
            "energy_full"
        )

        energy_design = read_file(
            "energy_full_design"
        )

        if energy_full:
            details["full_charge_capacity_wh"] = (
                round(
                    int(energy_full) / 1_000_000,
                    3,
                )
            )

        if energy_design:
            details["design_capacity_wh"] = (
                round(
                    int(energy_design) / 1_000_000,
                    3,
                )
            )

    except Exception:
        pass

    return details


def _calculate_health(
    design_capacity,
    full_charge_capacity,
):
    """
    Calculate battery health from design and full-charge
    capacity when both are available.
    """

    if (
        design_capacity is None
        or full_charge_capacity is None
        or design_capacity <= 0
    ):
        return None

    return round(
        (full_charge_capacity / design_capacity) * 100,
        1,
    )


def _format_time(seconds):
    if seconds is None:
        return None

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    return f"{hours}h {minutes}m"


def get_battery():
    """
    Collect current battery information.

    Historical discharge rate, charging history, downtime,
    optimal charging times and long-term battery analysis
    belong to the processor/memory layers.
    """

    battery = _get_basic_battery()

    if battery is None:
        return {
            "component": "Battery",
            "available": False,

            "percentage": None,
            "status": "Unavailable",
            "charging": None,
            "power_plugged": None,

            "seconds_remaining": None,
            "time_remaining": None,

            "estimated_seconds_remaining": None,
            "estimated_time_remaining": None,

            "manufacturer": None,
            "model": None,

            "design_capacity_wh": None,
            "full_charge_capacity_wh": None,
            "health_percent": None,

            "cycle_count": None,
            "voltage_mv": None,
            "temperature_c": None,
        }

    system = platform.system()

    if system == "Windows":
        details = _get_windows_details()

    elif system == "Darwin":
        details = _get_macos_details()

    elif system == "Linux":
        details = _get_linux_details()

    else:
        details = {
            "manufacturer": None,
            "model": None,
            "design_capacity_wh": None,
            "full_charge_capacity_wh": None,
            "cycle_count": None,
            "voltage_mv": None,
            "temperature_c": None,
        }

    health = _calculate_health(
        details["design_capacity_wh"],
        details["full_charge_capacity_wh"],
    )

    seconds_remaining = battery[
        "seconds_remaining"
    ]

    return {
        "component": "Battery",
        "available": True,

        # Current state
        "percentage": battery["percentage"],
        "status": battery["status"],
        "charging": battery["charging"],
        "power_plugged": battery["power_plugged"],

        # OS estimate
        "seconds_remaining": seconds_remaining,
        "time_remaining": _format_time(
            seconds_remaining
        ),

        # Calculated later from historical data
        "estimated_seconds_remaining": None,
        "estimated_time_remaining": None,

        # Hardware information
        "manufacturer": details["manufacturer"],
        "model": details["model"],

        "design_capacity_wh": details[
            "design_capacity_wh"
        ],

        "full_charge_capacity_wh": details[
            "full_charge_capacity_wh"
        ],

        "health_percent": health,

        "cycle_count": details[
            "cycle_count"
        ],

        "voltage_mv": details[
            "voltage_mv"
        ],

        "temperature_c": details[
            "temperature_c"
        ],
    }