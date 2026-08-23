"""
Tool execution engine.
"""

from __future__ import annotations

from typing import Any

from core.logging.logger import get_logger

from .base import Tool
from .permissions import authorize
from .result import ToolResult


class ToolExecutor:
    """Executes registered Forza tools safely."""

    def __init__(self) -> None:
        self._logger = get_logger("tools.executor")

    def execute(
        self,
        tool: Tool,
        **kwargs: Any,
    ) -> ToolResult:
        """Execute a tool after authorization."""

        if not authorize(tool):
            self._logger.warning(
                "Tool execution denied: %s",
                tool.name,
            )

            return ToolResult.failure(
                error="Tool execution denied.",
                tool_name=tool.name,
            )

        try:
            self._logger.info(
                "Executing tool: %s",
                tool.name,
            )

            result = tool.execute(**kwargs)

            if not isinstance(result, ToolResult):
                return ToolResult.ok(
                    data=result,
                    tool_name=tool.name,
                )

            return result

        except Exception as exc:
            self._logger.exception(
                "Tool execution failed: %s",
                tool.name,
            )

            return ToolResult.failure(
                error=str(exc),
                tool_name=tool.name,
            )
