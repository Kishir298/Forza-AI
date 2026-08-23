"""
Runtime state definitions for Forza.
"""

from __future__ import annotations

from enum import StrEnum


class RuntimeState(StrEnum):
    """Lifecycle states of the Forza runtime."""

    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
