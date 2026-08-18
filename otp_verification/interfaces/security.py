"""Security and token contracts for the OTP foundation package."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Mapping


class BaseHasher(ABC):
    """Abstract hashing boundary for OTP secrets."""

    @abstractmethod
    def hash_value(self, raw_value: str) -> str:
        """Return a hashed representation of a sensitive value."""

    @abstractmethod
    def verify_value(self, raw_value: str, hashed_value: str) -> bool:
        """Return whether ``raw_value`` matches ``hashed_value`` using secure comparison."""


class BaseTokenManager(ABC):
    """Abstract token management boundary."""

    @abstractmethod
    def issue(self, *, context: Mapping[str, object]) -> str:
        """Issue a future verification token."""

    @abstractmethod
    def consume(self, token: str) -> Mapping[str, object]:
        """Consume and return verified token context."""


class BaseAuditLogger(ABC):
    """Abstract audit logging boundary."""

    @abstractmethod
    def record(self, *, event: str, payload: Mapping[str, object]) -> None:
        """Record an OTP audit event."""


class BaseLockoutManager(ABC):
    """Abstract lockout policy boundary."""

    @abstractmethod
    def ensure_available(self, *, challenge_id: str) -> None:
        """Raise if the challenge is locked."""


class BaseReplayProtector(ABC):
    """Abstract replay protection boundary."""

    @abstractmethod
    def assert_not_replayed(self, *, token: str) -> None:
        """Raise when a token replay is detected."""
