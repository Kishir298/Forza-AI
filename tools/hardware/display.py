import subprocess


def get_display():

    try:

        info = subprocess.check_output(
            [
                "system_profiler",
                "SPDisplaysDataType"
            ]
        ).decode()


        return f"""
Display Information:

{info}
"""

    except Exception as e:

        return f"Display information unavailable: {e}"
