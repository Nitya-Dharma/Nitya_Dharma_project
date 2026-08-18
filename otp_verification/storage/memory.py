"""In-memory challenge repository for the internal OTP engine.

This keeps Task 2 free of Django models and migrations while still providing a
real BaseChallengeRepository implementation for lifecycle and verification.
"""

from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Mapping

from otp_verification.domain.challenge import ChallengeRecord
from otp_verification.exceptions import ChallengeNotFoundException, ValidationException
from otp_verification.interfaces.storage import BaseChallengeRepository


class InMemoryChallengeRepository(BaseChallengeRepository):
    """Thread-safe process-local challenge store."""

    def __init__(self) -> None:
        self._records: dict[str, ChallengeRecord] = {}
        self._lock = RLock()

    def create(self, *, payload: Mapping[str, object]) -> ChallengeRecord:
        """Persist a new challenge record."""

        record = payload.get("record")
        if not isinstance(record, ChallengeRecord):
            raise TypeError("payload['record'] must be a ChallengeRecord.")
        with self._lock:
            if record.id in self._records:
                raise ValidationException(f"Challenge '{record.id}' already exists.")
            self._records[record.id] = deepcopy(record)
            return deepcopy(self._records[record.id])

    def get_by_id(self, challenge_id: str) -> ChallengeRecord:
        """Load a challenge record by identifier."""

        with self._lock:
            try:
                return deepcopy(self._records[challenge_id])
            except KeyError as exc:
                raise ChallengeNotFoundException(
                    f"Challenge '{challenge_id}' was not found."
                ) from exc

    def update(self, challenge_id: str, *, payload: Mapping[str, object]) -> ChallengeRecord:
        """Persist challenge state changes."""

        with self._lock:
            if challenge_id not in self._records:
                raise ChallengeNotFoundException(
                    f"Challenge '{challenge_id}' was not found."
                )
            record = payload.get("record")
            if not isinstance(record, ChallengeRecord):
                raise TypeError("payload['record'] must be a ChallengeRecord.")
            if record.id != challenge_id:
                raise ValidationException("Challenge id mismatch during update.")
            self._records[challenge_id] = deepcopy(record)
            return deepcopy(self._records[challenge_id])

    def clear(self) -> None:
        """Remove all records (intended for tests)."""

        with self._lock:
            self._records.clear()
