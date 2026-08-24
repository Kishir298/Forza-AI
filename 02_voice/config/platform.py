from __future__ import annotations

import platform


def get_platform() -> str:
    """Return the normalized operating system name."""

    system = platform.system()

    if system == "Windows":
        return "windows"

    if system == "Darwin":
        return "macos"

    if system == "Linux":
        return "linux"

    return "unknown"


def is_supported_platform() -> bool:
    """Return whether the current platform is supported."""

    return get_platform() in {"windows", "macos", "linux"}
