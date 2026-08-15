import psutil


def get_network():
    """
    Return current network interface statistics.

    Works across Windows, macOS, and Linux through psutil.
    """

    counters = psutil.net_io_counters()

    if counters is None:
        return {
            "component": "Network",
            "available": False,
            "bytes_sent": None,
            "bytes_received": None,
            "packets_sent": None,
            "packets_received": None,
            "errors_in": None,
            "errors_out": None,
            "dropped_in": None,
            "dropped_out": None,
        }

    return {
        "component": "Network",
        "available": True,
        "bytes_sent": counters.bytes_sent,
        "bytes_received": counters.bytes_recv,
        "packets_sent": counters.packets_sent,
        "packets_received": counters.packets_recv,
        "errors_in": counters.errin,
        "errors_out": counters.errout,
        "dropped_in": counters.dropin,
        "dropped_out": counters.dropout,
    }