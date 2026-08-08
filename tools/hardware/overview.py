from tools.hardware.cpu import get_cpu
from tools.hardware.ram import get_ram
from tools.hardware.storage import get_storage
from tools.hardware.battery import get_battery
from tools.hardware.software import get_software


def get_overview():

    return f"""

========== FORZA SYSTEM OVERVIEW ==========


{get_cpu()}


{get_ram()}


{get_storage()}


{get_battery()}


{get_software()}


===========================================

"""
