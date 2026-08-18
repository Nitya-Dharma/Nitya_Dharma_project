"""Phone parsing and normalization contracts for future phases."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BasePhoneNormalizer(ABC):
    """Canonicalizes user-supplied phone numbers."""

    @abstractmethod
    def normalize(self, raw_phone: str) -> str:
        """Return a canonical phone number representation."""


class BasePhoneFormatter(ABC):
    """Formats canonical phone values for display or providers."""

    @abstractmethod
    def format(self, canonical_phone: str) -> str:
        """Return a formatted phone number."""


class BasePhoneValidator(ABC):
    """Validates phone numbers for future OTP flows."""

    @abstractmethod
    def validate(self, raw_phone: str) -> None:
        """Raise if the provided phone number is invalid."""


class BasePhoneParser(ABC):
    """Parses raw phone numbers into structured components."""

    @abstractmethod
    def parse(self, raw_phone: str) -> object:
        """Return a structured phone representation."""
