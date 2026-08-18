"""Storage and repository contracts for future OTP persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Mapping


class BaseChallengeRepository(ABC):
    """Abstract persistence boundary for future challenge storage."""

    @abstractmethod
    def create(self, *, payload: Mapping[str, object]) -> object:
        """Persist a challenge record."""

    @abstractmethod
    def get_by_id(self, challenge_id: str) -> object:
        """Load a challenge record by identifier."""

    @abstractmethod
    def update(self, challenge_id: str, *, payload: Mapping[str, object]) -> object:
        """Persist challenge state changes."""
