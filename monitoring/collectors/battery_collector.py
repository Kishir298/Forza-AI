import glob
import json
import os
import platform
import subprocess

import psutil


def _run_powershell(command, timeout=6):
    """
    Execute PowerShell and return parsed JSON.
    """

    if platform.system() != "Windows":
        return None

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
            timeout=timeout,
            check=False,
        )

        if result.returncode != 0:
            return None

        output = result.stdout.strip()

        if not output:
            return None

        return json.loads(output)

    except Exception:
        return None


def _normalize_list(value):
    if value is None:
        return []

    if isinstance(value, dict):
        return [value]

    if isinstance(value, list):
        return value

    return []


def _clean_string(value):
    if value is None:
        return None

    value = str(value).strip()

    return value if value else None


def _empty_details():
    return {
        "manufacturer": None,
        "model": None,

        "capacity_wh": None,
        "design_capacity_wh": None,
        "full_charge_capacity_wh": None,

        "health_percent": None,
        "cycle_count": None,

        "voltage_mv": None,
        "current_ma": None,
        "power_w": None,

        "temperature_c": None,
    }


def _get_basic_battery():
    """
    Common battery state from psutil.
    """

    try:
        battery = psutil.sensors_battery()

        if battery is None:
            return None

        seconds_remaining = battery.secsleft

        if seconds_remaining in (
            psutil.POWER_TIME_UNKNOWN,
            psutil.POWER_TIME_UNLIMITED,
            4294967295,
        ):
            seconds_remaining = None

        if (
            seconds_remaining is not None
            and seconds_remaining < 0
        ):
            seconds_remaining = None

        if battery.power_plugged:
            status = "Charging"
        else:
            status = "Discharging"

        return {
            "percentage": round(
                battery.percent,
                1,
            ),
            "status": status,
            "charging": bool(
                battery.power_plugged
            ),
            "power_plugged": bool(
                battery.power_plugged
            ),
            "seconds_remaining": (
                int(seconds_remaining)
                if seconds_remaining is not None
                else None
            ),
        }

    except Exception:
        return None


def _get_windows_static_data():
    """
    Get static battery information.

    Different Windows firmware exposes different subsets
    of these WMI classes, so each class is queried separately.
    """

    details = _empty_details()

    # ---------------------------------------------------------
    # BatteryStaticData
    # ---------------------------------------------------------

    static_data = _normalize_list(
        _run_powershell(
            """
            Get-CimInstance `
                -Namespace root\\wmi `
                -ClassName BatteryStaticData `
                -ErrorAction SilentlyContinue |
            Select-Object `
                DesignedCapacity,
                FullChargedCapacity,
                ManufactureName,
                DeviceName |
            ConvertTo-Json -Compress
            """
        )
    )

    if static_data:
        item = static_data[0]

        designed = item.get(
            "DesignedCapacity"
        )

        full_charge = item.get(
            "FullChargedCapacity"
        )

        if designed is not None:
            try:
                details[
                    "design_capacity_wh"
                ] = round(
                    float(designed) / 1000,
                    3,
                )
            except (
                TypeError,
                ValueError,
            ):
                pass

        if full_charge is not None:
            try:
                details[
                    "full_charge_capacity_wh"
                ] = round(
                    float(full_charge) / 1000,
                    3,
                )
            except (
                TypeError,
                ValueError,
            ):
                pass

        details[
            "manufacturer"
        ] = _clean_string(
            item.get(
                "ManufactureName"
            )
        )

        details[
            "model"
        ] = _clean_string(
            item.get(
                "DeviceName"
            )
        )

    # ---------------------------------------------------------
    # BatteryFullChargedCapacity
    # ---------------------------------------------------------

    full_capacity_data = _normalize_list(
        _run_powershell(
            """
            Get-CimInstance `
                -Namespace root\\wmi `
                -ClassName BatteryFullChargedCapacity `
                -ErrorAction SilentlyContinue |
            Select-Object FullChargedCapacity |
            ConvertTo-Json -Compress
            """
        )
    )

    if full_capacity_data:
        value = full_capacity_data[0].get(
            "FullChargedCapacity"
        )

        if value is not None:
            try:
                details[
                    "full_charge_capacity_wh"
                ] = round(
                    float(value) / 1000,
                    3,
                )
            except (
                TypeError,
                ValueError,
            ):
                pass

    # ---------------------------------------------------------
    # BatteryCycleCount
    # ---------------------------------------------------------

    cycle_data = _normalize_list(
        _run_powershell(
            """
            Get-CimInstance `
                -Namespace root\\wmi `
                -ClassName BatteryCycleCount `
                -ErrorAction SilentlyContinue |
            Select-Object CycleCount |
            ConvertTo-Json -Compress
            """
        )
    )

    if cycle_data:
        value = cycle_data[0].get(
            "CycleCount"
        )

        if value is not None:
            try:
                details[
                    "cycle_count"
                ] = int(value)
            except (
                TypeError,
                ValueError,
            ):
                pass

    return details


def _get_windows_status_data():
    """
    Get dynamic battery information.

    BatteryStatus provides:
    - Voltage
    - ChargeRate
    - DischargeRate
    - RemainingCapacity
    """

    details = {
        "capacity_wh": None,
        "voltage_mv": None,
        "current_ma": None,
        "power_w": None,
    }

    data = _normalize_list(
        _run_powershell(
            """
            Get-CimInstance `
                -Namespace root\\wmi `
                -ClassName BatteryStatus `
                -ErrorAction SilentlyContinue |
            Select-Object `
                Voltage,
                ChargeRate,
                DischargeRate,
                RemainingCapacity,
                Active,
                Critical,
                PowerOnline |
            ConvertTo-Json -Compress
            """
        )
    )

    if not data:
        return details

    item = data[0]

    # ---------------------------------------------------------
    # Voltage
    # ---------------------------------------------------------

    voltage = item.get(
        "Voltage"
    )

    if voltage is not None:
        try:
            details[
                "voltage_mv"
            ] = round(
                float(voltage),
                2,
            )
        except (
            TypeError,
            ValueError,
        ):
            pass

    # ---------------------------------------------------------
    # Current capacity
    # ---------------------------------------------------------

    remaining_capacity = item.get(
        "RemainingCapacity"
    )

    if remaining_capacity is not None:
        try:
            details[
                "capacity_wh"
            ] = round(
                float(
                    remaining_capacity
                ) / 1000,
                3,
            )
        except (
            TypeError,
            ValueError,
        ):
            pass

    # ---------------------------------------------------------
    # Charge/discharge power
    # ---------------------------------------------------------
    #
    # Windows exposes both ChargeRate and DischargeRate.
    # We select whichever one is actually non-zero.
    #
    # This avoids reporting 0 W while the machine is
    # visibly discharging.
    # ---------------------------------------------------------

    charge_rate = item.get(
        "ChargeRate"
    )

    discharge_rate = item.get(
        "DischargeRate"
    )

    power_mw = None

    try:
        if (
            charge_rate is not None
            and float(charge_rate) > 0
        ):
            power_mw = float(
                charge_rate
            )

        elif (
            discharge_rate is not None
            and float(discharge_rate) > 0
        ):
            power_mw = -float(
                discharge_rate
            )

    except (
        TypeError,
        ValueError,
    ):
        power_mw = None

    if power_mw is not None:
        details[
            "power_w"
        ] = round(
            power_mw / 1000,
            3,
        )

    # ---------------------------------------------------------
    # Current
    # ---------------------------------------------------------

    if (
        details["power_w"] is not None
        and details["voltage_mv"] is not None
        and details["voltage_mv"] > 0
    ):
        voltage_v = (
            details["voltage_mv"]
            / 1000
        )

        details[
            "current_ma"
        ] = round(
            (
                abs(
                    details["power_w"]
                )
                / voltage_v
            )
            * 1000,
            2,
        )

    return details


def _get_windows_temperature():
    """
    Get battery temperature only when Windows explicitly
    identifies an ACPI thermal zone as battery-related.
    """

    temperatures = []

    data = _normalize_list(
        _run_powershell(
            """
            Get-CimInstance `
                -Namespace root\\wmi `
                -ClassName MSAcpi_ThermalZoneTemperature `
                -ErrorAction SilentlyContinue |
            Select-Object `
                InstanceName,
                CurrentTemperature |
            ConvertTo-Json -Compress
            """
        )
    )

    for item in data:
        instance_name = (
            _clean_string(
                item.get(
                    "InstanceName"
                )
            )
            or ""
        ).lower()

        if "battery" not in instance_name:
            continue

        temperature = item.get(
            "CurrentTemperature"
        )

        try:
            temperature_c = (
                float(temperature)
                / 10
                - 273.15
            )

            if (
                -40
                <= temperature_c
                <= 100
            ):
                temperatures.append(
                    temperature_c
                )

        except (
            TypeError,
            ValueError,
        ):
            continue

    if not temperatures:
        return None

    return round(
        max(temperatures),
        1,
    )


def _get_windows_details():
    """
    Complete Windows battery hardware collector.
    """

    details = _empty_details()

    static = _get_windows_static_data()
    status = _get_windows_status_data()

    details.update(static)
    details.update(status)

    details[
        "temperature_c"
    ] = _get_windows_temperature()

    return details


def _get_macos_details():
    """
    Collect additional battery information on macOS.
    """

    details = _empty_details()

    if platform.system() != "Darwin":
        return details

    try:
        result = subprocess.run(
            [
                "system_profiler",
                "SPPowerDataType",
                "-json",
            ],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )

        if result.returncode != 0:
            return details

        data = json.loads(
            result.stdout
        )

        power_data = data.get(
            "SPPowerDataType",
            [],
        )

        if not power_data:
            return details

        info = power_data[0]

        health = info.get(
            "sppower_battery_health_info",
            {},
        )

        details[
            "cycle_count"
        ] = health.get(
            "cycle_count"
        )

        details[
            "manufacturer"
        ] = _clean_string(
            info.get(
                "sppower_battery_manufacturer"
            )
        )

        details[
            "model"
        ] = _clean_string(
            info.get(
                "sppower_battery_model_name"
            )
        )

        details[
            "design_capacity_wh"
        ] = info.get(
            "sppower_battery_design_capacity"
        )

        details[
            "full_charge_capacity_wh"
        ] = info.get(
            "sppower_battery_capacity"
        )

        details[
            "voltage_mv"
        ] = info.get(
            "sppower_battery_voltage"
        )

    except Exception:
        pass

    return details


def _get_linux_details():
    """
    Collect battery information from Linux sysfs.
    """

    details = _empty_details()

    if platform.system() != "Linux":
        return details

    try:
        batteries = glob.glob(
            "/sys/class/power_supply/BAT*/"
        )

        if not batteries:
            return details

        battery = batteries[0]

        def read_file(name):
            path = os.path.join(
                battery,
                name,
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

        details[
            "manufacturer"
        ] = read_file(
            "manufacturer"
        )

        details[
            "model"
        ] = read_file(
            "model_name"
        )

        cycle = read_file(
            "cycle_count"
        )

        if cycle:
            try:
                details[
                    "cycle_count"
                ] = int(cycle)
            except ValueError:
                pass

        voltage = read_file(
            "voltage_now"
        )

        if voltage:
            try:
                details[
                    "voltage_mv"
                ] = round(
                    int(voltage) / 1000,
                    2,
                )
            except ValueError:
                pass

        current = read_file(
            "current_now"
        )

        if current:
            try:
                details[
                    "current_ma"
                ] = round(
                    int(current) / 1000,
                    2,
                )
            except ValueError:
                pass

        if (
            details["current_ma"]
            is not None
            and details["voltage_mv"]
            is not None
        ):
            details[
                "power_w"
            ] = round(
                (
                    details["current_ma"]
                    / 1000
                )
                * (
                    details["voltage_mv"]
                    / 1000
                ),
                3,
            )

        energy_now = read_file(
            "energy_now"
        )

        energy_full = read_file(
            "energy_full"
        )

        energy_design = read_file(
            "energy_full_design"
        )

        if energy_now:
            details[
                "capacity_wh"
            ] = round(
                int(energy_now)
                / 1_000_000,
                3,
            )

        if energy_full:
            details[
                "full_charge_capacity_wh"
            ] = round(
                int(energy_full)
                / 1_000_000,
                3,
            )

        if energy_design:
            details[
                "design_capacity_wh"
            ] = round(
                int(energy_design)
                / 1_000_000,
                3,
            )

        temperature = read_file(
            "temp"
        )

        if temperature:
            try:
                value = float(
                    temperature
                )

                if abs(value) > 200:
                    value /= 10

                if (
                    -40
                    <= value
                    <= 100
                ):
                    details[
                        "temperature_c"
                    ] = round(
                        value,
                        1,
                    )

            except ValueError:
                pass

    except Exception:
        pass

    return details


def _calculate_health(
    design_capacity,
    full_charge_capacity,
):
    """
    Calculate battery health from capacity degradation.
    """

    if (
        design_capacity is None
        or full_charge_capacity is None
        or design_capacity <= 0
    ):
        return None

    health = (
        full_charge_capacity
        / design_capacity
    ) * 100

    return round(
        max(
            0,
            min(
                100,
                health,
            ),
        ),
        1,
    )


def _format_time(seconds):
    if seconds is None:
        return None

    hours = seconds // 3600
    minutes = (
        seconds % 3600
    ) // 60

    return (
        f"{hours}h {minutes}m"
    )


def get_battery():
    """
    Collect complete battery information.
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

            "capacity_wh": None,
            "design_capacity_wh": None,
            "full_charge_capacity_wh": None,

            "health_percent": None,
            "cycle_count": None,

            "voltage_mv": None,
            "current_ma": None,
            "power_w": None,

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
        details = _empty_details()

    health = _calculate_health(
        details[
            "design_capacity_wh"
        ],
        details[
            "full_charge_capacity_wh"
        ],
    )

    seconds_remaining = battery[
        "seconds_remaining"
    ]

    return {
        "component": "Battery",
        "available": True,

        # Existing objectives
        "percentage": battery[
            "percentage"
        ],
        "status": battery[
            "status"
        ],
        "charging": battery[
            "charging"
        ],
        "power_plugged": battery[
            "power_plugged"
        ],

        "seconds_remaining": (
            seconds_remaining
        ),
        "time_remaining": (
            _format_time(
                seconds_remaining
            )
        ),

        # Analytics-layer estimates
        "estimated_seconds_remaining": None,
        "estimated_time_remaining": None,

        # Hardware
        "manufacturer": details[
            "manufacturer"
        ],
        "model": details[
            "model"
        ],

        # Capacity
        "capacity_wh": details[
            "capacity_wh"
        ],
        "design_capacity_wh": details[
            "design_capacity_wh"
        ],
        "full_charge_capacity_wh": details[
            "full_charge_capacity_wh"
        ],

        # Health
        "health_percent": health,
        "cycle_count": details[
            "cycle_count"
        ],

        # Electrical
        "voltage_mv": details[
            "voltage_mv"
        ],
        "current_ma": details[
            "current_ma"
        ],
        "power_w": details[
            "power_w"
        ],

        # Thermal
        "temperature_c": details[
            "temperature_c"
        ],
    }