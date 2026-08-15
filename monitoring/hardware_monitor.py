from monitoring.collectors.audio_collector import get_audio
from monitoring.collectors.battery_collector import get_battery
from monitoring.collectors.camera_collector import get_cameras
from monitoring.collectors.cpu_collector import get_cpu
from monitoring.collectors.display_collector import get_display
from monitoring.collectors.network_collector import get_network
from monitoring.collectors.process_collector import get_processes
from monitoring.collectors.ram_collector import get_ram
from monitoring.collectors.software_collector import get_software
from monitoring.collectors.storage_collector import get_storage


def get_system_snapshot():
    """
    Collect a complete snapshot of the current system.

    Each collector is isolated so a failure in one component
    does not prevent the remaining monitoring data from being
    collected.
    """

    collectors = {
        "cpu": get_cpu,
        "ram": get_ram,
        "storage": get_storage,
        "battery": get_battery,
        "processes": get_processes,
        "network": get_network,
        "display": get_display,
        "software": get_software,
        "audio": get_audio,
        "camera": get_cameras,
    }

    snapshot = {}

    for name, collector in collectors.items():
        try:
            snapshot[name] = collector()

        except Exception as error:
            snapshot[name] = {
                "component": name.capitalize(),
                "available": False,
                "error": str(error),
            }

    return snapshot


def get_component(component):
    """
    Collect data for one specific component.

    Example:
        get_component("cpu")
    """

    collectors = {
        "cpu": get_cpu,
        "ram": get_ram,
        "storage": get_storage,
        "battery": get_battery,
        "processes": get_processes,
        "network": get_network,
        "display": get_display,
        "software": get_software,
        "audio": get_audio,
        "camera": get_cameras,
    }

    collector = collectors.get(
        component.lower()
    )

    if collector is None:
        raise ValueError(
            f"Unknown monitoring component: {component}"
        )

    return collector()