import shutil


def get_storage():

    total, used, free = shutil.disk_usage("/")

    gb = 1024 ** 3

    return f"""
Storage Information:

Total: {total / gb:.1f} GB
Used: {used / gb:.1f} GB
Free: {free / gb:.1f} GB
"""
