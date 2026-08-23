"""
Tool routing for Forza.
"""

from __future__ import annotations

from typing import Any

from core.logging.logger import get_logger

from .executor import ToolExecutor
from .registry import ToolRegistry
from .result import ToolResult


class ToolRouter:
    """Routes tool requests to registered tools."""

    def __init__(
        self,
        registry: ToolRegistry,
        executor: ToolExecutor | None = None,
    ) -> None:
        self._logger = get_logger("tools.router")
        self.registry = registry
        self.executor = executor or ToolExecutor()

    def execute(
        self,
        tool_name: str,
        **kwargs: Any,
    ) -> ToolResult:
        """Route a tool request."""

        tool = self.registry.get(tool_name)

        if tool is None:
            self._logger.warning(
                "Unknown tool requested: %s",
                tool_name,
            )

            return ToolResult.failure(
                error=f"Tool not found: {tool_name}",
                tool_name=tool_name,
            )

        return self.executor.execute(
            tool,
            **kwargs,
        )
