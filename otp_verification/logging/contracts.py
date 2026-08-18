"""Logging value objects and backend contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class AuditEventPayload:
    """Immutable audit event payload for future logging backends."""

    event: str
    metadata: Mapping[str, object]


class LoggingBackend(ABC):
    """Abstract logging backend for OTP audit and operational events."""

    @abstractmethod
    def emit(self, payload: AuditEventPayload) -> None:
        """Emit a logging payload to the configured backend."""
