from tools.registry import register_tool

from tools.memory_tool import get_memory
from tools.system_info import get_system_info, get_battery
from tools.storage_tool import get_storage


def load_tools():

    register_tool(
        "memory",
         "Shows RAM usage and available memory.",
        [
            "ram",
            "memory",
            "available memory",
            "free memory",
            "memory left",
            "how much ram",
            "ram usage",
            "how much memory"
        ],
        get_memory
    )


    register_tool(
        "system",
        "Shows computer hardware specifications.",
        [
            "system info",
            "system specs",
            "system specifications",
            "laptop specs",
            "laptop specifications",
            "computer specs",
            "computer specifications",
            "hardware",
            "processor",
            "cpu"
        ],
        get_system_info
    )


    register_tool(
        "battery",
        "Shows battery percentage and charging status.",
        [
            "battery",
            "charge",
            "power"
        ],
        get_battery
    )


    register_tool(
        "storage",
        "Shows SSD storage and free space.",
        [
            "storage",
            "ssd",
            "ssd storage",
            "ssd disk",
            "disk",
            "drive",
            "space",
            "free space",
            "storage left",
            "how much storage",
            "how much space"
        ],
        get_storage
    )