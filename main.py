from app.app import Forza
from memory.database import create_tables
from tools.registry import register_tool
from tools.storage_tool import get_storage

from rich.console import Console

import sys
import time


console = Console()


def load_available_tools():
    """Register tools that currently exist in the repository."""

    register_tool(
        "storage",
        "Shows SSD storage and free space.",
        [
            "storage",
            "ssd",
            "ssd storage",
            "ssd disk",
            "disk",
            "drive",
            "space",
            "free space",
            "storage left",
            "how much storage",
            "how much space",
        ],
        get_storage,
    )


def shutdown():
    """Shut down Forza cleanly."""

    console.print(
        "\n[cyan]Forza:[/cyan] Shutdown command received."
    )

    time.sleep(0.5)

    console.print(
        "[cyan]Forza:[/cyan] Closing systems. See you next time! 👋"
    )

    time.sleep(1)

    sys.exit(0)


def is_shutdown_command(message):
    """Detect commands intended to shut down Forza."""

    message = message.lower().strip()

    shutdown_words = [
        "shutdown",
        "shut down",
        "turn off",
        "close yourself",
        "go offline",
        "power off",
        "terminate",
        "exit forza",
        "quit forza",
        "stop forza",
    ]

    return any(
        word in message
        for word in shutdown_words
    )


def main():
    """Start the Forza assistant."""

    create_tables()
    load_available_tools()

    console.print(
        "[bold cyan]FORZA AI Assistant Started[/bold cyan]"
    )

    console.print(
        "Type 'exit' or 'quit' to close Forza."
    )

    console.print(
        "Say 'Forza shutdown' or a similar command to fully stop.\n"
    )

    forza = Forza()

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if is_shutdown_command(user_input):
                shutdown()

            if user_input.lower() in {"exit", "quit"}:
                console.print(
                    "\n[cyan]Forza:[/cyan] Goodbye! 👋"
                )
                break

            print(
                "\n[green]Forza:[/green] ",
                end="",
                flush=True,
            )

            try:
                for chunk in forza.process(user_input):
                    print(
                        chunk,
                        end="",
                        flush=True,
                    )

            except KeyboardInterrupt:
                print("\n")

                console.print(
                    "[yellow]Response interrupted.[/yellow]"
                )

            print("\n")

        except KeyboardInterrupt:
            print("\n")

            console.print(
                "[cyan]Ready.[/cyan]\n"
            )


if __name__ == "__main__":
    main()