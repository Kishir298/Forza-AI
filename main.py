from tools.load_tools import load_tools
from memory.database import create_tables
from app.app import Forza
from rich.console import Console
import sys
import time
import re


console = Console()


def shutdown():
    console.print("\n[cyan]Forza:[/cyan] Shutdown command received.")
    time.sleep(0.5)
    console.print("[cyan]Forza:[/cyan] Closing systems. See you next time! 👋")
    time.sleep(1)
    sys.exit(0)


def is_shutdown_command(message):
    """
    Detects different ways the user can ask Forza to shut down.
    """

    message = message.lower()

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
        "stop forza"
    ]

    for word in shutdown_words:
        if word in message:
            return True

    return False


def main():
   
    
    create_tables()
    load_tools()
    

    console.print("[bold cyan]FORZA AI Assistant Started[/bold cyan]")
    console.print("Type 'exit' to close Forza.")
    console.print("Say 'Forza shutdown' or similar commands to fully stop.\n")

    forza = Forza()

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if is_shutdown_command(user_input):
                shutdown()

            if user_input.lower() in ["exit", "quit"]:
                console.print(
                    "\n[cyan]Forza:[/cyan] Goodbye! 👋"
                )
                break

            print("\n[green]Forza:[/green] ", end="", flush=True)

            try:
                for chunk in forza.process(user_input):
                    print(chunk, end="", flush=True)

            except KeyboardInterrupt:
                print("\n")
                console.print(
                    "[yellow]Response interrupted.[/yellow]"
                )

            print("\n")

        except KeyboardInterrupt:
            print("\n")
            console.print("[cyan]Ready.[/cyan]\n")


if __name__ == "__main__":
    main()
