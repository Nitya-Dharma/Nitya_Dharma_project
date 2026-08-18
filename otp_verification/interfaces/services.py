"""Service-layer contracts for the OTP foundation package."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Mapping


class BaseChallengeManager(ABC):
    """Coordinates future challenge lifecycle operations."""

    @abstractmethod
    def create_challenge(self, *, flow_type: str, context: Mapping[str, object]) -> object:
        """Create a new challenge boundary object."""


class BaseOTPGenerator(ABC):
    """Generates OTP material in future phases."""

    @abstractmethod
    def generate(self, *, length: int) -> str:
        """Return a new OTP string."""


class BaseOTPValidator(ABC):
    """Validates submitted OTPs in future phases."""

    @abstractmethod
    def validate(self, *, submitted_otp: str, context: Mapping[str, object]) -> bool:
        """Return whether a submitted OTP is valid."""


class BaseAttemptTracker(ABC):
    """Tracks verification attempts in future phases."""

    @abstractmethod
    def record_attempt(self, *, challenge_id: str, successful: bool) -> None:
        """Record an OTP verification attempt."""


class BaseCooldownManager(ABC):
    """Applies resend cooldown policy in future phases."""

    @abstractmethod
    def ensure_available(self, *, challenge_id: str) -> None:
        """Raise if a resend action is still cooling down."""
