"""Provider contracts for future OTP delivery backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ProviderRequest:
    """Immutable provider request payload for future delivery implementations."""

    destination: str
    message: str
    channel: str
    metadata: Mapping[str, object]


@dataclass(frozen=True)
class ProviderResponse:
    """Immutable provider response contract for future delivery implementations."""

    accepted: bool
    provider_name: str
    provider_reference: str | None = None
    metadata: Mapping[str, object] | None = None


class BaseOTPProvider(ABC):
    """Abstract delivery provider contract."""

    provider_name: str

    @abstractmethod
    def send(self, request: ProviderRequest) -> ProviderResponse:
        """Send an outbound OTP delivery request."""
