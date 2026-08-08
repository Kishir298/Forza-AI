import shutil


def get_storage():

    total, used, free = shutil.disk_usage("/")


    total = round(total/(1024**3),2)
    used = round(used/(1024**3),2)
    free = round(free/(1024**3),2)


    percentage = round((used/total)*100,2)


    return f"""
SSD Storage:

Total:
{total} GB

Used:
{used} GB

Free:
{free} GB

Usage:
{percentage}%
"""