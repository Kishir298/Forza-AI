from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def get_venv_path() -> Path:
    system = platform.system()

    if system == "Windows":
        return ROOT / ".venv-windows"

    if system == "Linux":
        return ROOT / ".venv-linux"

    if system == "Darwin":
        return ROOT / ".venv-macos"

    raise RuntimeError(f"Unsupported operating system: {system}")


def get_python_path(venv: Path) -> Path:
    if platform.system() == "Windows":
        return venv / "Scripts" / "python.exe"

    return venv / "bin" / "python"


def create_venv(venv: Path) -> None:
    print(f"Creating virtual environment: {venv.name}")
    subprocess.check_call(
        [sys.executable, "-m", "venv", str(venv)]
    )


def main() -> None:
    system = platform.system()
    venv = get_venv_path()
    python = get_python_path(venv)

    print(f"Detected OS: {system}")
    print(f"Environment: {venv.name}")

    if python.exists():
        print("Virtual environment already exists.")
    else:
        create_venv(venv)

    print()
    print("Forza AI virtual environment: READY")
    print(f"Python: {python}")

    print()
    print("Activate it with:")

    if system == "Windows":
        print(f"  source {venv.name}/Scripts/activate")
    else:
        print(f"  source {venv.name}/bin/activate")


if __name__ == "__main__":
    main()
