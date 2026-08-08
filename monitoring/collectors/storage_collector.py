import psutil


def get_storage():

    disk = psutil.disk_usage("/")


    total = round(
        disk.total / (1024 ** 3),
        2
    )

    used = round(
        disk.used / (1024 ** 3),
        2
    )

    free = round(
        disk.free / (1024 ** 3),
        2
    )


    return {

        "component": "SSD Storage",

        "total_gb": total,

        "used_gb": used,

        "free_gb": free,

        "usage_percent": disk.percent

    }
