"""
Tool permission handling.
"""

from __future__ import annotations

from core.security.confirmation import request_confirmation
from core.security.permissions import PermissionLevel

from .base import Tool


def authorize(tool: Tool) -> bool:
    """
    Determine whether a tool is authorized to execute.

    Safe and low-risk tools can proceed automatically.
    High-risk tools require explicit confirmation.
    """
    return request_confirmation(
        action=tool.name,
        level=tool.permission,
    )


def permission_name(level: PermissionLevel) -> str:
    """Return a human-readable permission name."""
    return level.name
