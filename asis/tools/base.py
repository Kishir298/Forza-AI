"""
Base interface for A.S.I.S. tools.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from asis.permissions.models import PermissionLevel

from .result import ToolResult


@dataclass(frozen=True)
class ToolMetadata:
    """Metadata describing a tool."""

    name: str
    description: str
    category: str
    permission: PermissionLevel = PermissionLevel.SAFE
    tags: tuple[str, ...] = field(default_factory=tuple)


class Tool(ABC):
    """Abstract base class for every A.S.I.S. tool."""

    metadata: ToolMetadata

    @abstractmethod
    def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool."""
        raise NotImplementedError

    @property
    def name(self) -> str:
        """Return the tool's registered name."""
        return self.metadata.name

    @property
    def description(self) -> str:
        """Return the tool description."""
        return self.metadata.description

    @property
    def category(self) -> str:
        """Return the tool category."""
        return self.metadata.category

    @property
    def permission(self) -> PermissionLevel:
        """Return the required permission level."""
        return self.metadata.permission
