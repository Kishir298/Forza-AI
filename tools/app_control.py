import subprocess



ALIASES = {

    "minecraft education": "minecraft-edu",

    "minecraft": "minecraft-edu"

}



def get_installed_apps():

    apps = {}


    try:

        result = subprocess.run(
            [
                "mdfind",
                "kMDItemContentType == 'com.apple.application-bundle'"
            ],
            capture_output=True,
            text=True
        )


        for path in result.stdout.splitlines():

            if path.endswith(".app"):

                name = path.split("/")[-1].replace(".app", "")

                apps[name.lower()] = path



    except Exception:

        pass


    return apps




def open_app(message):

    apps = get_installed_apps()


    text = message.lower()


    for word in [
        "open",
        "launch",
        "start"
    ]:

        text = text.replace(word, "")


    search = text.strip()



    # Convert common names into real app names

    if search in ALIASES:

        search = ALIASES[search]



    # Exact match

    for name, path in apps.items():

        if search == name:

            return launch(path)



    return f"I couldn't find an application named '{search}'."



def launch(path):

    try:

        subprocess.run(
            [
                "open",
                path
            ],
            timeout=5
        )


        app_name = path.split("/")[-1].replace(".app", "")

        return f"Opening {app_name}."



    except subprocess.TimeoutExpired:

        return "The app took too long to open."


    except Exception:

        return "I couldn't open that application."
