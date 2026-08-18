import platform
import socket

import psutil


def _get_interface_details():
    """
    Get network interface state and link information.
    """

    interfaces = {}

    try:
        stats = psutil.net_if_stats()

        for name, stat in stats.items():
            interfaces[name] = {
                "name": name,
                "is_up": bool(stat.isup),
                "speed_mbps": (
                    stat.speed
                    if stat.speed > 0
                    else None
                ),
                "duplex": (
                    str(stat.duplex)
                    if stat.duplex is not None
                    else None
                ),
                "mtu": stat.mtu,
            }

    except Exception:
        pass

    return interfaces


def _get_addresses():
    """
    Get IPv4, IPv6 and MAC addresses for interfaces.
    """

    addresses = {}

    try:
        interface_addresses = psutil.net_if_addrs()

        for name, addr_list in interface_addresses.items():

            ipv4 = []
            ipv6 = []
            mac = None

            for address in addr_list:

                if address.family == socket.AF_INET:
                    ipv4.append(address.address)

                elif address.family == socket.AF_INET6:
                    ipv6.append(address.address)

                elif (
                    hasattr(psutil, "AF_LINK")
                    and address.family == psutil.AF_LINK
                ):
                    mac = address.address

            addresses[name] = {
                "ipv4": ipv4,
                "ipv6": ipv6,
                "mac": mac,
            }

    except Exception:
        pass

    return addresses


def _get_wifi_interfaces(interfaces):
    """
    Identify interfaces that appear to be Wi-Fi adapters.

    This is intentionally conservative. Actual Wi-Fi SSID,
    signal and link-speed information requires OS-specific
    APIs and is handled separately.
    """

    wifi = []

    for name, interface in interfaces.items():

        name_lower = name.lower()

        if any(
            keyword in name_lower
            for keyword in (
                "wi-fi",
                "wifi",
                "wireless",
                "wlan",
            )
        ):
            wifi.append(name)

    return wifi


def _get_windows_wifi():
    """
    Get Windows Wi-Fi information using netsh.
    """

    if platform.system() != "Windows":
        return {
            "connected": False,
            "ssid": None,
            "signal_percent": None,
            "link_speed_mbps": None,
            "adapter": None,
        }

    result_data = {
        "connected": False,
        "ssid": None,
        "signal_percent": None,
        "link_speed_mbps": None,
        "adapter": None,
    }

    try:
        import subprocess

        result = subprocess.run(
            [
                "netsh",
                "wlan",
                "show",
                "interfaces",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if result.returncode != 0:
            return result_data

        for raw_line in result.stdout.splitlines():

            line = raw_line.strip()

            if ":" not in line:
                continue

            key, value = line.split(
                ":",
                1,
            )

            key = key.strip().lower()
            value = value.strip()

            if key == "state":
                result_data["connected"] = (
                    value.lower() == "connected"
                )

            elif key == "ssid":
                result_data["ssid"] = value

            elif key == "signal":

                try:
                    result_data[
                        "signal_percent"
                    ] = int(
                        value.replace("%", "")
                        .strip()
                    )
                except ValueError:
                    pass

            elif key in (
                "receive rate (mbps)",
                "transmit rate (mbps)",
            ):
                try:
                    speed = float(
                        value.split()[0]
                    )

                    if (
                        result_data[
                            "link_speed_mbps"
                        ]
                        is None
                    ):
                        result_data[
                            "link_speed_mbps"
                        ] = speed

                except ValueError:
                    pass

            elif key == "name":
                result_data["adapter"] = value

    except Exception:
        pass

    return result_data


def _get_linux_wifi():
    """
    Try NetworkManager's nmcli on Linux.
    """

    if platform.system() != "Linux":
        return {
            "connected": False,
            "ssid": None,
            "signal_percent": None,
            "link_speed_mbps": None,
            "adapter": None,
        }

    result_data = {
        "connected": False,
        "ssid": None,
        "signal_percent": None,
        "link_speed_mbps": None,
        "adapter": None,
    }

    try:
        import subprocess

        result = subprocess.run(
            [
                "nmcli",
                "-t",
                "-f",
                "DEVICE,TYPE,STATE,CONNECTION,SIGNAL",
                "device",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if result.returncode != 0:
            return result_data

        for line in result.stdout.splitlines():

            parts = line.split(":")

            if len(parts) < 5:
                continue

            device, device_type, state, connection, signal = (
                parts[:5]
            )

            if device_type != "wifi":
                continue

            result_data["adapter"] = device

            result_data["connected"] = (
                state == "connected"
            )

            if result_data["connected"]:
                result_data["ssid"] = connection

            try:
                result_data[
                    "signal_percent"
                ] = int(signal)

            except ValueError:
                pass

            break

    except Exception:
        pass

    return result_data


def _get_wifi():
    system = platform.system()

    if system == "Windows":
        return _get_windows_wifi()

    if system == "Linux":
        return _get_linux_wifi()

    # macOS gets its own backend later if needed.
    return {
        "connected": False,
        "ssid": None,
        "signal_percent": None,
        "link_speed_mbps": None,
        "adapter": None,
    }


def _get_network_counters():
    """
    Get cumulative network traffic counters.
    """

    try:
        counters = psutil.net_io_counters()

        return {
            "bytes_sent": counters.bytes_sent,
            "bytes_received": counters.bytes_recv,

            "packets_sent": counters.packets_sent,
            "packets_received": counters.packets_recv,

            "errors_in": counters.errin,
            "errors_out": counters.errout,

            "dropped_in": counters.dropin,
            "dropped_out": counters.dropout,
        }

    except Exception:
        return {
            "bytes_sent": None,
            "bytes_received": None,
            "packets_sent": None,
            "packets_received": None,
            "errors_in": None,
            "errors_out": None,
            "dropped_in": None,
            "dropped_out": None,
        }


def get_network():
    """
    Collect current network information.

    Historical bandwidth usage and per-process network
    activity belong to the processing/history layer.
    """

    try:
        interfaces = _get_interface_details()
        addresses = _get_addresses()

        wifi = _get_wifi()

        return {
            "component": "Network",
            "available": bool(interfaces),

            "hostname": socket.gethostname(),

            "wifi": wifi,

            "interfaces": interfaces,

            "addresses": addresses,

            "traffic": _get_network_counters(),
        }

    except Exception as error:
        return {
            "component": "Network",
            "available": False,
            "error": str(error),

            "hostname": None,

            "wifi": {
                "connected": False,
                "ssid": None,
                "signal_percent": None,
                "link_speed_mbps": None,
                "adapter": None,
            },

            "interfaces": {},
            "addresses": {},

            "traffic": _get_network_counters(),
        }