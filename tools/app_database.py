from pathlib import Path

APP_DIRS = [
    "/Applications",
    "/System/Applications",
    str(Path.home() / "Applications")
]


def scan_apps():

    apps = []

    for folder in APP_DIRS:

        p = Path(folder)

        if not p.exists():
            continue

        for app in p.rglob("*.app"):

            apps.append(
                {
                    "name": app.stem,
                    "path": str(app)
                }
            )

    return apps
