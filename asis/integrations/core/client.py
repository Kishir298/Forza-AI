"""
C.O.R.E. (Communication, Organization and Resource Engine) interface.

A.S.I.S. will request capabilities through C.O.R.E. rather than
controlling subsystems directly. This interface is the contract; the
concrete adapter is provided by the C.O.R.E. project during integration.

For now A.S.I.S. runs with `MockCoreAdapter` (see `integrations.core.mock`).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CoreResponse:
    """Uniform result returned by C.O.R.E. client operations."""

    ok: bool
    data: Any = None
    error: str | None = None


@dataclass(frozen=True)
class ServiceRequest:
    """A service capability request routed through C.O.R.E."""

    service: str
    operation: str
    params: dict[str, Any] = field(default_factory=dict)


class CoreClient(ABC):
    """
    Interface to a C.O.R.E. instance.

    These methods mirror the eventual C.O.R.E. communication contract so
    that a real adapter can be dropped in without rewriting A.S.I.S.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the adapter name."""
        raise NotImplementedError

    @abstractmethod
    def send_message(self, recipient: str, payload: dict[str, Any]) -> CoreResponse:
        """Send a message through C.O.R.E."""
        raise NotImplementedError

    @abstractmethod
    def request_service(self, request: ServiceRequest) -> CoreResponse:
        """Request a capability through C.O.R.E."""
        raise NotImplementedError

    @abstractmethod
    def publish_event(
        self, event_type: str, data: dict[str, Any] | None = None
    ) -> None:
        """Publish an event into C.O.R.E."""
        raise NotImplementedError

    @abstractmethod
    def get_resource(self, name: str) -> CoreResponse:
        """Retrieve a resource handle/descriptor from C.O.R.E."""
        raise NotImplementedError

    @abstractmethod
    def register_component(
        self, component_id: str, metadata: dict[str, Any] | None = None
    ) -> CoreResponse:
        """Register an A.S.I.S. component with C.O.R.E."""
        raise NotImplementedError

    @abstractmethod
    def get_health(self) -> dict[str, Any]:
        """Return health information about C.O.R.E."""
        raise NotImplementedError
