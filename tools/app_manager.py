from pathlib import Path
from rapidfuzz import process, fuzz
import subprocess


APP_DIRS = [
    "/Applications",
    "/System/Applications",
    str(Path.home() / "Applications")
]


ALIASES = {
    "vscode": "visual studio code",
    "vs code": "visual studio code",
    "code": "visual studio code",

    "mc": "minecraft",
    "minecraft edu": "minecraft education",
    "minecraft education": "minecraft education",

    "zoom": "zoom.us",

    "chrome": "google chrome",

    "word": "microsoft word",
    "excel": "microsoft excel",
    "powerpoint": "microsoft powerpoint",

    "photos": "photos",
    "calendar": "calendar",
    "settings": "system settings",
}


class AppManager:

    def __init__(self):

        self.apps = []

        self.scan_apps()


    def clean_name(self, name):

        return (
            name.lower()
            .replace("-", " ")
            .replace("_", " ")
            .replace(".", " ")
        )


    def scan_apps(self):

        self.apps.clear()

        for folder in APP_DIRS:

            folder = Path(folder)

            if not folder.exists():
                continue

            for app in folder.rglob("*.app"):

                self.apps.append(
                    {
                        "name": app.stem,
                        "clean": self.clean_name(app.stem),
                        "path": str(app)
                    }
                )


    def search(self, query, limit=5):

        query = self.clean_name(query)

        query = ALIASES.get(query, query)

        scored = []

        for app in self.apps:

            score = fuzz.WRatio(query, app["clean"])

            if query in app["clean"]:
                score += 20

            if app["clean"] == query:
                score += 100

            scored.append(
                (
                    app,
                    score
                )
            )

        scored.sort(
            key=lambda x: x[1],
            reverse=True
        )

        return scored[:limit]


    def launch(self, app):

        subprocess.Popen(
            [
                "open",
                app["path"]
            ]
        )
