"""
Main Forza runtime controller.
"""

from __future__ import annotations

from collections.abc import Iterable

from core.logging.logger import get_logger

from .component import RuntimeComponent
from .context import RuntimeContext
from .lifecycle import LifecycleManager
from .state import RuntimeState


class ForzaRuntime:
    """Central lifecycle controller for Forza."""

    def __init__(
        self,
        components: Iterable[RuntimeComponent] | None = None,
    ) -> None:
        self.logger = get_logger("runtime")

        self.state = RuntimeState.CREATED

        self.context = RuntimeContext()
        self.lifecycle = LifecycleManager()

        if components is not None:
            self.lifecycle.register_many(components)

    @property
    def is_running(self) -> bool:
        """Return whether the runtime is currently running."""

        return self.state == RuntimeState.RUNNING

    def register(
        self,
        component: RuntimeComponent,
    ) -> None:
        """Register a component."""

        if self.state not in {
            RuntimeState.CREATED,
            RuntimeState.STOPPED,
        }:
            raise RuntimeError(
                "Components cannot be registered while "
                "the runtime is active."
            )

        self.lifecycle.register(component)

    def start(self) -> None:
        """Start the Forza runtime."""

        if self.state == RuntimeState.RUNNING:
            return

        if self.state == RuntimeState.STARTING:
            raise RuntimeError(
                "Runtime is already starting."
            )

        self.logger.info("Starting Forza runtime.")

        self.state = RuntimeState.STARTING

        try:
            self.lifecycle.start_all(self.context)

            self.state = RuntimeState.RUNNING

            self.logger.info(
                "Forza runtime is running."
            )

        except Exception:
            self.state = RuntimeState.FAILED

            self.logger.exception(
                "Forza runtime startup failed."
            )

            raise

    def stop(self) -> None:
        """Stop the Forza runtime."""

        if self.state in {
            RuntimeState.CREATED,
            RuntimeState.STOPPED,
        }:
            return

        self.logger.info("Stopping Forza runtime.")

        self.state = RuntimeState.STOPPING

        try:
            self.lifecycle.stop_all(self.context)

            self.context.clear()

            self.state = RuntimeState.STOPPED

            self.logger.info(
                "Forza runtime stopped."
            )

        except Exception:
            self.state = RuntimeState.FAILED

            self.logger.exception(
                "Forza runtime shutdown failed."
            )

            raise

    def restart(self) -> None:
        """Restart the Forza runtime."""

        self.stop()
        self.start()

    def component_names(self) -> list[str]:
        """Return names of registered components."""

        return self.lifecycle.list_components()
