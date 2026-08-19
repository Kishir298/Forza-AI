import glob
import json
import os
import platform
import re
import subprocess
import tempfile
from html import unescape

import psutil


def _run_command(command, timeout=8):
    """
    Run a command and return stdout.

    Returns None if the command cannot be executed or fails.
    """

    try:
        result = subprocess.run(
            command,
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

        return output

    except Exception:
        return None


def _run_powershell(command, timeout=8):
    """
    Execute PowerShell and return parsed JSON.
    """

    if platform.system() != "Windows":
        return None

    output = _run_command(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ],
        timeout=timeout,
    )

    if not output:
        return None

    try:
        return json.loads(output)
    except Exception:
        return None


def _normalize_list(value):
    """
    Normalize PowerShell JSON output into a list.
    """

    if value is None:
        return []

    if isinstance(value, dict):
        return [value]

    if isinstance(value, list):
        return value

    return []


def _clean_string(value):
    """
    Normalize optional string values.
    """

    if value is None:
        return None

    value = str(value).strip()

    return value if value else None


def _safe_float(value):
    """
    Convert a value to float safely.
    """

    try:
        if value is None:
            return None

        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return None


def _safe_int(value):
    """
    Convert a value to int safely.
    """

    try:
        if value is None:
            return None

        return int(float(value))

    except (
        TypeError,
        ValueError,
    ):
        return None


def _empty_details():
    """
    Default battery hardware/telemetry structure.
    """

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

        "sources": [],
    }


def _get_basic_battery():
    """
    Get common battery state using psutil.
    """

    try:
        battery = psutil.sensors_battery()

        if battery is None:
            return None

        seconds_remaining = battery.secsleft

        unknown_values = {
            psutil.POWER_TIME_UNKNOWN,
            psutil.POWER_TIME_UNLIMITED,
            4294967295,
            -1,
            -2,
        }

        if seconds_remaining in unknown_values:
            seconds_remaining = None

        if (
            seconds_remaining is not None
            and seconds_remaining < 0
        ):
            seconds_remaining = None

        plugged = bool(
            battery.power_plugged
        )

        if plugged:
            status = "Charging"
        else:
            status = "Discharging"

        return {
            "percentage": round(
                float(battery.percent),
                1,
            ),
            "status": status,
            "charging": plugged,
            "power_plugged": plugged,
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
    Collect Windows battery static information.

    Uses several Windows WMI/ACPI classes because battery
    firmware does not expose every field consistently.
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

        designed = _safe_float(
            item.get(
                "DesignedCapacity"
            )
        )

        full_charge = _safe_float(
            item.get(
                "FullChargedCapacity"
            )
        )

        if (
            designed is not None
            and designed > 0
        ):
            details[
                "design_capacity_wh"
            ] = round(
                designed / 1000,
                3,
            )

        if (
            full_charge is not None
            and full_charge > 0
        ):
            details[
                "full_charge_capacity_wh"
            ] = round(
                full_charge / 1000,
                3,
            )

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

        details[
            "sources"
        ].append(
            "Windows BatteryStaticData"
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
        value = _safe_float(
            full_capacity_data[0].get(
                "FullChargedCapacity"
            )
        )

        if (
            value is not None
            and value > 0
        ):
            details[
                "full_charge_capacity_wh"
            ] = round(
                value / 1000,
                3,
            )

            if (
                "Windows BatteryFullChargedCapacity"
                not in details["sources"]
            ):
                details[
                    "sources"
                ].append(
                    "Windows BatteryFullChargedCapacity"
                )

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
        value = _safe_int(
            cycle_data[0].get(
                "CycleCount"
            )
        )

        # Zero is treated as unavailable because many
        # Windows firmware implementations expose 0 when
        # cycle telemetry is unsupported.
        if (
            value is not None
            and value > 0
        ):
            details[
                "cycle_count"
            ] = value

            details[
                "sources"
            ].append(
                "Windows BatteryCycleCount"
            )

    return details


def _get_windows_status_data():
    """
    Collect live Windows battery telemetry.

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
        "sources": [],
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

    voltage = _safe_float(
        item.get(
            "Voltage"
        )
    )

    if (
        voltage is not None
        and voltage > 0
    ):
        details[
            "voltage_mv"
        ] = round(
            voltage,
            2,
        )

    # ---------------------------------------------------------
    # Remaining capacity
    # ---------------------------------------------------------

    remaining_capacity = _safe_float(
        item.get(
            "RemainingCapacity"
        )
    )

    if (
        remaining_capacity is not None
        and remaining_capacity >= 0
    ):
        details[
            "capacity_wh"
        ] = round(
            remaining_capacity / 1000,
            3,
        )

    # ---------------------------------------------------------
    # Charge/discharge rate
    # ---------------------------------------------------------

    charge_rate = _safe_float(
        item.get(
            "ChargeRate"
        )
    )

    discharge_rate = _safe_float(
        item.get(
            "DischargeRate"
        )
    )

    power_mw = None

    if (
        charge_rate is not None
        and charge_rate > 0
    ):
        power_mw = charge_rate

    elif (
        discharge_rate is not None
        and discharge_rate > 0
    ):
        power_mw = -discharge_rate

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

    details[
        "sources"
    ].append(
        "Windows BatteryStatus"
    )

    return details


def _parse_battery_report_capacity(value):
    """
    Convert a battery-report capacity string to Wh.

    Examples:
    '48,670 mWh' -> 48.67
    '48,670mWh'  -> 48.67
    """

    if value is None:
        return None

    value = unescape(
        str(value)
    )

    match = re.search(
        r"([\d,.\s]+)\s*mWh",
        value,
        re.IGNORECASE,
    )

    if not match:
        return None

    raw = (
        match.group(1)
        .replace(",", "")
        .replace(" ", "")
    )

    try:
        return round(
            float(raw) / 1000,
            3,
        )

    except ValueError:
        return None


def _parse_battery_report_cycle_count(value):
    """
    Convert a battery-report cycle-count value to an integer.
    """

    if value is None:
        return None

    value = unescape(
        str(value)
    ).strip()

    match = re.search(
        r"(\d+)",
        value,
    )

    if not match:
        return None

    try:
        cycle_count = int(
            match.group(1)
        )

        if cycle_count <= 0:
            return None

        return cycle_count

    except ValueError:
        return None


def _extract_table_rows(html):
    """
    Extract simple table rows from Windows battery-report HTML.
    """

    rows = []

    for row in re.findall(
        r"<tr[^>]*>(.*?)</tr>",
        html,
        re.IGNORECASE | re.DOTALL,
    ):
        cells = re.findall(
            r"<t[dh][^>]*>(.*?)</t[dh]>",
            row,
            re.IGNORECASE | re.DOTALL,
        )

        cleaned = []

        for cell in cells:
            cell = re.sub(
                r"<[^>]+>",
                " ",
                cell,
            )

            cell = unescape(
                cell
            )

            cell = re.sub(
                r"\s+",
                " ",
                cell,
            ).strip()

            cleaned.append(cell)

        if cleaned:
            rows.append(cleaned)

    return rows


def _get_windows_battery_report():
    """
    Use Windows powercfg /batteryreport as a fallback
    telemetry source.

    This is particularly useful when WMI does not expose:
    - Design capacity
    - Full charge capacity
    - Cycle count
    """

    if platform.system() != "Windows":
        return _empty_details()

    details = _empty_details()

    temp_directory = tempfile.gettempdir()

    report_path = os.path.join(
        temp_directory,
        "forza_battery_report.html",
    )

    try:
        # Remove stale report first.
        try:
            if os.path.exists(
                report_path
            ):
                os.remove(
                    report_path
                )
        except Exception:
            pass

        result = subprocess.run(
            [
                "powercfg",
                "/batteryreport",
                "/output",
                report_path,
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

        if result.returncode != 0:
            return details

        if not os.path.exists(
            report_path
        ):
            return details

        with open(
            report_path,
            "r",
            encoding="utf-8",
            errors="ignore",
        ) as file:
            html = file.read()

        rows = _extract_table_rows(
            html
        )

        # -----------------------------------------------------
        # Parse battery information
        # -----------------------------------------------------

        for row in rows:
            if len(row) < 2:
                continue

            label = row[0].lower()

            value = row[1]

            # Design capacity
            if (
                "design capacity"
                in label
            ):
                capacity = (
                    _parse_battery_report_capacity(
                        value
                    )
                )

                if (
                    capacity is not None
                    and details[
                        "design_capacity_wh"
                    ] is None
                ):
                    details[
                        "design_capacity_wh"
                    ] = capacity

            # Full charge capacity
            elif (
                "full charge capacity"
                in label
            ):
                capacity = (
                    _parse_battery_report_capacity(
                        value
                    )
                )

                if (
                    capacity is not None
                    and details[
                        "full_charge_capacity_wh"
                    ] is None
                ):
                    details[
                        "full_charge_capacity_wh"
                    ] = capacity

            # Cycle count
            elif (
                "cycle count"
                in label
            ):
                cycle_count = (
                    _parse_battery_report_cycle_count(
                        value
                    )
                )

                if (
                    cycle_count is not None
                    and details[
                        "cycle_count"
                    ] is None
                ):
                    details[
                        "cycle_count"
                    ] = cycle_count

        # -----------------------------------------------------
        # Battery report may contain the information in
        # multiple battery sections. Scan the complete
        # document as a fallback.
        # -----------------------------------------------------

        if (
            details[
                "design_capacity_wh"
            ]
            is None
        ):
            matches = re.findall(
                r"Design Capacity.*?"
                r"([\d,.\s]+)\s*mWh",
                html,
                re.IGNORECASE | re.DOTALL,
            )

            for match in matches:
                capacity = (
                    _parse_battery_report_capacity(
                        match
                    )
                )

                if capacity is not None:
                    details[
                        "design_capacity_wh"
                    ] = capacity
                    break

        if (
            details[
                "full_charge_capacity_wh"
            ]
            is None
        ):
            matches = re.findall(
                r"Full Charge Capacity.*?"
                r"([\d,.\s]+)\s*mWh",
                html,
                re.IGNORECASE | re.DOTALL,
            )

            for match in matches:
                capacity = (
                    _parse_battery_report_capacity(
                        match
                    )
                )

                if capacity is not None:
                    details[
                        "full_charge_capacity_wh"
                    ] = capacity
                    break

        if (
            details[
                "cycle_count"
            ]
            is None
        ):
            matches = re.findall(
                r"Cycle Count.*?"
                r"(\d+)",
                html,
                re.IGNORECASE | re.DOTALL,
            )

            for match in matches:
                cycle_count = (
                    _parse_battery_report_cycle_count(
                        match
                    )
                )

                if cycle_count is not None:
                    details[
                        "cycle_count"
                    ] = cycle_count
                    break

        if (
            details[
                "design_capacity_wh"
            ]
            is not None
            or details[
                "full_charge_capacity_wh"
            ]
            is not None
            or details[
                "cycle_count"
            ]
            is not None
        ):
            details[
                "sources"
            ].append(
                "Windows Battery Report"
            )

        return details

    except Exception:
        return details

    finally:
        try:
            if os.path.exists(
                report_path
            ):
                os.remove(
                    report_path
                )
        except Exception:
            pass


def _get_windows_temperature():
    """
    Get battery temperature when Windows exposes a thermal
    zone explicitly associated with the battery.
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

        if (
            "battery" not in instance_name
            and "bat" not in instance_name
        ):
            continue

        temperature = _safe_float(
            item.get(
                "CurrentTemperature"
            )
        )

        if temperature is None:
            continue

        temperature_c = (
            temperature / 10
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

    if not temperatures:
        return None

    return round(
        max(temperatures),
        1,
    )


def _get_windows_details():
    """
    Complete Windows battery collector.

    Uses WMI/ACPI first and Windows Battery Report as
    a fallback for static battery health information.
    """

    details = _empty_details()

    static = _get_windows_static_data()
    status = _get_windows_status_data()

    # ---------------------------------------------------------
    # WMI static data
    # ---------------------------------------------------------

    for key in (
        "manufacturer",
        "model",
        "design_capacity_wh",
        "full_charge_capacity_wh",
        "cycle_count",
    ):
        if static.get(key) is not None:
            details[key] = static[key]

    # ---------------------------------------------------------
    # Live status
    # ---------------------------------------------------------

    for key in (
        "capacity_wh",
        "voltage_mv",
        "current_ma",
        "power_w",
    ):
        if status.get(key) is not None:
            details[key] = status[key]

    # ---------------------------------------------------------
    # Battery Report fallback
    # ---------------------------------------------------------

    report = _get_windows_battery_report()

    for key in (
        "design_capacity_wh",
        "full_charge_capacity_wh",
        "cycle_count",
    ):
        if (
            details.get(key) is None
            and report.get(key) is not None
        ):
            details[key] = report[key]

    # ---------------------------------------------------------
    # Sources
    # ---------------------------------------------------------

    details[
        "sources"
    ] = list(
        dict.fromkeys(
            static.get(
                "sources",
                []
            )
            + status.get(
                "sources",
                []
            )
            + report.get(
                "sources",
                []
            )
        )
    )

    # ---------------------------------------------------------
    # Temperature
    # ---------------------------------------------------------

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
            timeout=10,
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

        cycle_count = (
            health.get(
                "cycle_count"
            )
        )

        if cycle_count is not None:
            details[
                "cycle_count"
            ] = _safe_int(
                cycle_count
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
        ] = _safe_float(
            info.get(
                "sppower_battery_design_capacity"
            )
        )

        details[
            "full_charge_capacity_wh"
        ] = _safe_float(
            info.get(
                "sppower_battery_capacity"
            )
        )

        details[
            "voltage_mv"
        ] = _safe_float(
            info.get(
                "sppower_battery_voltage"
            )
        )

        details[
            "sources"
        ].append(
            "macOS system_profiler"
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
            cycle_value = _safe_int(
                cycle
            )

            if (
                cycle_value is not None
                and cycle_value > 0
            ):
                details[
                    "cycle_count"
                ] = cycle_value

        voltage = read_file(
            "voltage_now"
        )

        if voltage:
            voltage_value = _safe_float(
                voltage
            )

            if (
                voltage_value is not None
                and voltage_value > 0
            ):
                details[
                    "voltage_mv"
                ] = round(
                    voltage_value / 1000,
                    2,
                )

        current = read_file(
            "current_now"
        )

        if current:
            current_value = _safe_float(
                current
            )

            if current_value is not None:
                details[
                    "current_ma"
                ] = round(
                    current_value / 1000,
                    2,
                )

        if (
            details[
                "current_ma"
            ] is not None
            and details[
                "voltage_mv"
            ] is not None
        ):
            details[
                "power_w"
            ] = round(
                (
                    details[
                        "current_ma"
                    ] / 1000
                )
                * (
                    details[
                        "voltage_mv"
                    ] / 1000
                ),
                3,
            )

        # -----------------------------------------------------
        # Energy values
        # -----------------------------------------------------

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
            value = _safe_float(
                energy_now
            )

            if value is not None:
                details[
                    "capacity_wh"
                ] = round(
                    value / 1_000_000,
                    3,
                )

        if energy_full:
            value = _safe_float(
                energy_full
            )

            if value is not None:
                details[
                    "full_charge_capacity_wh"
                ] = round(
                    value / 1_000_000,
                    3,
                )

        if energy_design:
            value = _safe_float(
                energy_design
            )

            if value is not None:
                details[
                    "design_capacity_wh"
                ] = round(
                    value / 1_000_000,
                    3,
                )

        # -----------------------------------------------------
        # Battery temperature
        # -----------------------------------------------------

        temperature = read_file(
            "temp"
        )

        if temperature:
            value = _safe_float(
                temperature
            )

            if value is not None:
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

        details[
            "sources"
        ].append(
            "Linux power_supply sysfs"
        )

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
        or full_charge_capacity <= 0
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
    """
    Convert seconds to a human-readable duration.
    """

    if seconds is None:
        return None

    try:
        seconds = int(seconds)
    except (
        TypeError,
        ValueError,
    ):
        return None

    if seconds < 0:
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

    The collector preserves the existing output schema while
    adding more reliable Windows telemetry and fallbacks.
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

            "sources": [],
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

        # Existing battery state
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

        # Reserved analytics fields
        "estimated_seconds_remaining": None,
        "estimated_time_remaining": None,

        # Hardware identity
        "manufacturer": details[
            "manufacturer"
        ],
        "model": details[
            "model"
        ],

        # Battery capacity
        "capacity_wh": details[
            "capacity_wh"
        ],
        "design_capacity_wh": details[
            "design_capacity_wh"
        ],
        "full_charge_capacity_wh": details[
            "full_charge_capacity_wh"
        ],

        # Battery health
        "health_percent": health,
        "cycle_count": details[
            "cycle_count"
        ],

        # Electrical telemetry
        "voltage_mv": details[
            "voltage_mv"
        ],
        "current_ma": details[
            "current_ma"
        ],
        "power_w": details[
            "power_w"
        ],

        # Thermal telemetry
        "temperature_c": details[
            "temperature_c"
        ],

        # Telemetry provenance
        "sources": details[
            "sources"
        ],
    }