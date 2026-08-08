import subprocess


def get_audio():

    try:

        info = subprocess.check_output(
            [
                "system_profiler",
                "SPAudioDataType"
            ]
        ).decode()


        return f"""
Audio Information:

{info}
"""

    except Exception as e:

        return f"Audio information unavailable: {e}"
