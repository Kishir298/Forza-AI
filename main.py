import platform
import re
import sys
import time

from rich.console import Console

from app.app import Forza
from memory.database import create_tables, get_collector_history
from monitoring.controllers.audio_controller import mute, set_volume, unmute
from monitoring.hardware_monitor import get_component, get_system_snapshot
from tools.app_control import open_app
from tools.app_manager import AppManager
from tools.calculator import calculate
from tools.hardware.battery import get_battery
from tools.hardware.cpu import get_cpu
from tools.hardware.overview import get_overview
from tools.hardware.ram import get_ram
from tools.hardware.software import get_software
from tools.hardware.storage import get_storage as get_hardware_storage
from tools.registry import register_tool
from tools.storage_tool import get_storage as get_storage_tool
from tools.time_tool import get_time


console = Console()

# The current user message is stored here because the existing
# ToolRouter calls registered functions without passing arguments.
CURRENT_MESSAGE = ""

_APP_MANAGER = None


MONITOR_COMPONENTS = (
    "cpu",
    "ram",
    "storage",
    "battery",
    "processes",
    "network",
    "display",
    "software",
    "audio",
    "camera",
)


def current_message():
    return CURRENT_MESSAGE.lower().strip()


def extract_number(message):
    """
    Extract a volume percentage/number from a command.
    Examples:
        set volume to 50
        set volume to 50%
        volume 75
    """

    match = re.search(
        r"(?:volume|to|at)\s*(\d{1,3})",
        message.lower(),
    )

    if not match:
        match = re.search(
            r"\b(\d{1,3})\s*(?:%|percent)?\b",
            message.lower(),
        )

    if not match:
        return None

    return int(match.group(1))


def monitor_snapshot():
    """Collect the complete monitoring snapshot."""

    return str(get_system_snapshot())


def monitor_component():
    """Collect one specific monitoring component."""

    message = current_message()

    component = None

    for name in MONITOR_COMPONENTS:
        if name in message:
            component = name
            break

    if component is None:
        return (
            "Specify a monitoring component such as "
            "CPU, RAM, storage, battery, network, display, "
            "audio, camera, or processes."
        )

    try:
        return str(get_component(component))

    except Exception as error:
        return f"Unable to collect {component} monitoring data: {error}"


def monitor_history():
    """Return stored monitoring history for one component."""

    message = current_message()

    component = None

    for name in MONITOR_COMPONENTS:
        if name in message:
            component = name
            break

    if component is None:
        return (
            "Specify a component whose monitoring history "
            "you want."
        )

    try:
        history = get_collector_history(component)

        if not history:
            return f"No stored monitoring history exists for {component}."

        return str(history)

    except Exception as error:
        return f"Unable to retrieve {component} history: {error}"


def change_volume():
    """Set system output volume."""

    value = extract_number(current_message())

    if value is None:
        return (
            "Specify a volume percentage, for example: "
            "set volume to 50%."
        )

    return str(set_volume(value))


def open_application():
    """
    Use the repository's direct application controller.

    That implementation currently targets macOS.
    """

    if platform.system() != "Darwin":
        return (
            "The current direct application controller "
            "is implemented for macOS only."
        )

    return open_app(CURRENT_MESSAGE)


def fuzzy_open_application():
    """
    Use the repository's fuzzy application manager.

    The current AppManager implementation targets macOS
    application bundles.
    """

    global _APP_MANAGER

    if platform.system() != "Darwin":
        return (
            "The current fuzzy application launcher "
            "is implemented for macOS only."
        )

    if _APP_MANAGER is None:
        _APP_MANAGER = AppManager()

    message = CURRENT_MESSAGE.lower()

    for prefix in (
        "open",
        "launch",
        "start",
        "run",
    ):
        if message.startswith(prefix):
            message = message[len(prefix):].strip()
            break

    if not message:
        return "Tell me which application to open."

    matches = _APP_MANAGER.search(
        message,
        limit=1,
    )

    if not matches:
        return (
            f"I couldn't find an application named "
            f"'{message}'."
        )

    app, score = matches[0]

    if score < 60:
        return (
            f"I couldn't confidently match "
            f"'{message}' to an installed application."
        )

    try:
        _APP_MANAGER.launch(app)

        return f"Opening {app['name']}."

    except Exception as error:
        return (
            f"I found {app['name']}, but couldn't open it: "
            f"{error}"
        )


def load_tools():
    """
    Register every currently implemented callable
    feature that can be integrated with the existing
    ToolRouter interface.
    """

    # --------------------------------------------------
    # BASIC TOOLS
    # --------------------------------------------------

    register_tool(
        "calculator",
        "Performs basic arithmetic calculations.",
        [
            "calculate",
            "calculator",
            "calculate this",
            "do the math",
            "math calculation",
        ],
        lambda: calculate(CURRENT_MESSAGE),
    )

    register_tool(
        "time",
        "Returns the current local time and date.",
        [
            "what time is it",
            "current time",
            "current date",
            "what date is it",
            "today's date",
        ],
        get_time,
    )

    register_tool(
        "storage",
        "Shows root filesystem storage information.",
        [
            "storage left",
            "free storage",
            "free disk space",
            "disk space",
        ],
        get_storage_tool,
    )

    # --------------------------------------------------
    # HARDWARE INFORMATION
    # --------------------------------------------------

    register_tool(
        "hardware overview",
        "Shows the available hardware and software overview.",
        [
            "system overview",
            "hardware overview",
            "computer overview",
        ],
        get_overview,
    )

    register_tool(
        "cpu",
        "Returns CPU information.",
        [
            "cpu information",
            "cpu info",
            "processor information",
            "processor info",
        ],
        get_cpu,
    )

    register_tool(
        "ram",
        "Returns RAM information.",
        [
            "ram information",
            "ram info",
            "ram usage",
            "memory usage",
        ],
        get_ram,
    )

    register_tool(
        "hardware storage",
        "Returns detailed hardware storage information.",
        [
            "ssd information",
            "ssd info",
            "hardware storage",
            "drive usage",
        ],
        get_hardware_storage,
    )

    register_tool(
        "battery",
        "Returns battery information.",
        [
            "battery information",
            "battery info",
            "battery percentage",
            "battery status",
        ],
        get_battery,
    )

    register_tool(
        "software",
        "Returns operating system and software information.",
        [
            "software information",
            "software info",
            "os information",
            "operating system information",
            "python version",
        ],
        get_software,
    )

    # --------------------------------------------------
    # MONITORING
    # --------------------------------------------------

    register_tool(
        "monitor snapshot",
        "Collects a complete system monitoring snapshot.",
        [
            "system snapshot",
            "monitor snapshot",
            "full system monitoring",
            "monitor everything",
        ],
        monitor_snapshot,
    )

    register_tool(
        "monitor component",
        "Collects monitoring data for one component.",
        [
            "monitor cpu",
            "monitor ram",
            "monitor storage",
            "monitor battery",
            "monitor processes",
            "monitor network",
            "monitor display",
            "monitor software",
            "monitor audio",
            "monitor camera",
        ],
        monitor_component,
    )

    register_tool(
        "monitor history",
        "Returns stored monitoring history.",
        [
            "monitor history",
            "hardware history",
            "system history",
            "cpu history",
            "ram history",
            "battery history",
            "network history",
        ],
        monitor_history,
    )

    # --------------------------------------------------
    # AUDIO CONTROL
    # --------------------------------------------------

    # IMPORTANT:
    # "unmute" is registered before "mute" because the
    # existing registry uses substring matching.
    register_tool(
        "audio unmute",
        "Unmutes system audio.",
        [
            "unmute",
            "unmute audio",
            "unmute sound",
        ],
        unmute,
    )

    register_tool(
        "audio mute",
        "Mutes system audio.",
        [
            "mute",
            "mute audio",
            "mute sound",
        ],
        mute,
    )

    register_tool(
        "audio volume",
        "Sets system output volume.",
        [
            "set volume",
            "volume to",
            "volume at",
            "change volume",
        ],
        change_volume,
    )

    # --------------------------------------------------
    # APPLICATION CONTROL
    # --------------------------------------------------

    register_tool(
        "application launcher",
        "Launches an installed application.",
        [
            "open app",
            "open application",
            "launch app",
            "launch application",
            "start app",
            "start application",
        ],
        fuzzy_open_application,
    )

    register_tool(
        "application control",
        "Opens an application using the direct controller.",
        [
            "open",
            "launch",
            "start",
        ],
        open_application,
    )


def is_shutdown_command(message):
    """Detect explicit Forza shutdown commands."""

    message = message.lower().strip()

    commands = (
        "forza shutdown",
        "forza shut down",
        "shutdown forza",
        "shut down forza",
        "stop forza",
        "exit forza",
        "quit forza",
    )

    return any(
        command in message
        for command in commands
    )


def shutdown():
    """Shut down Forza cleanly."""

    console.print(
        "\n[cyan]Forza:[/cyan] "
        "Shutdown command received."
    )

    time.sleep(0.3)

    console.print(
        "[cyan]Forza:[/cyan] "
        "Closing systems. See you next time! 👋"
    )

    sys.exit(0)


def main():
    """Start the Forza assistant."""

    global CURRENT_MESSAGE

    create_tables()
    load_tools()

    console.print(
        "[bold cyan]FORZA AI Assistant Started[/bold cyan]"
    )

    console.print(
        "All currently implemented repository tools "
        "have been loaded."
    )

    console.print(
        "Type 'exit' or 'quit' to close Forza."
    )

    console.print(
        "Use an explicit 'Forza shutdown' command "
        "to shut Forza down.\n"
    )

    forza = Forza()

    while True:

        try:
            CURRENT_MESSAGE = input("You: ").strip()

            if not CURRENT_MESSAGE:
                continue

            if is_shutdown_command(CURRENT_MESSAGE):
                shutdown()

            if CURRENT_MESSAGE.lower() in {
                "exit",
                "quit",
            }:
                console.print(
                    "\n[cyan]Forza:[/cyan] "
                    "Goodbye! 👋"
                )
                break

            print(
                "\n[green]Forza:[/green] ",
                end="",
                flush=True,
            )

            try:
                for chunk in forza.process(
                    CURRENT_MESSAGE
                ):
                    print(
                        chunk,
                        end="",
                        flush=True,
                    )

            except KeyboardInterrupt:
                print("\n")

                console.print(
                    "[yellow]"
                    "Response interrupted."
                    "[/yellow]"
                )

            print("\n")

        except KeyboardInterrupt:
            print("\n")

            console.print(
                "[cyan]Ready.[/cyan]\n"
            )


if __name__ == "__main__":
    main()