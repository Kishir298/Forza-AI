from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"


def get_venv_python() -> Path:
    if platform.system() == "Windows":
        return VENV / "Scripts" / "python.exe"

    return VENV / "bin" / "python"


def create_venv() -> None:
    print("Creating Forza AI virtual environment...")

    subprocess.check_call(
        [sys.executable, "-m", "venv", str(VENV)]
    )


def main() -> None:
    system = platform.system()

    if system not in {"Windows", "Darwin", "Linux"}:
        print(f"Unsupported operating system: {system}")
        sys.exit(1)

    print(f"Detected OS: {system}")

    python_path = get_venv_python()

    if python_path.exists():
        print("Virtual environment already exists.")
    else:
        create_venv()

    print()
    print("Forza AI virtual environment: READY")
    print(f"Python: {python_path}")

    print()
    print("Activate it with:")

    if system == "Windows":
        print(r"  .venv\Scripts\activate")
    else:
        print("  source .venv/bin/activate")

    print()
    print("Or run Python directly with:")
    print(f"  {python_path}")


if __name__ == "__main__":
    main()
