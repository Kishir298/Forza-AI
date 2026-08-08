import psutil


def get_ram():

    memory = psutil.virtual_memory()

    total = round(memory.total / (1024**3), 2)
    used = round(memory.used / (1024**3), 2)
    available = round(memory.available / (1024**3), 2)
    percent = memory.percent


    return f"""
RAM Information:

Total:
{total} GB

Used:
{used} GB

Available:
{available} GB

Usage:
{percent}%
"""