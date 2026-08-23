"""
Runtime component interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .context import RuntimeContext


class RuntimeComponent(ABC):
    """
    Base class for components managed by the Forza runtime.

    Components should contain their own startup and shutdown logic.
    """

    name: str = "unnamed"

    @abstractmethod
    def start(self, context: RuntimeContext) -> None:
        """Start the component."""
        raise NotImplementedError

    @abstractmethod
    def stop(self, context: RuntimeContext) -> None:
        """Stop the component."""
        raise NotImplementedError
