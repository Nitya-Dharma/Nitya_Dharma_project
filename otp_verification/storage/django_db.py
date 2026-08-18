"""Django ORM challenge repository for durable multi-worker OTP storage."""

from __future__ import annotations

import logging
from typing import Mapping

from django.db import IntegrityError, OperationalError, transaction
from django.db.utils import DatabaseError

from otp_verification.domain.challenge import ChallengeRecord
from otp_verification.domain.lifecycle import ChallengeLifecycle
from otp_verification.enums import ChallengeStatus
from otp_verification.exceptions import (
    ChallengeNotFoundException,
    ReplayAttackException,
    RepositoryUnavailableException,
    ValidationException,
)
from otp_verification.interfaces.storage import BaseChallengeRepository
from otp_verification.models import OTPChallenge

logger = logging.getLogger(__name__)

_TERMINAL_STATUSES = frozenset(
    {
        ChallengeStatus.VERIFIED,
        ChallengeStatus.CONSUMED,
        ChallengeStatus.EXPIRED,
        ChallengeStatus.LOCKED,
        ChallengeStatus.CANCELLED,
        ChallengeStatus.ARCHIVED,
    }
)


def _row_to_record(row: OTPChallenge) -> ChallengeRecord:
    return ChallengeRecord(
        id=row.challenge_id,
        flow_type=row.flow_type,
        status=row.status,
        otp_hash=row.otp_hash,
        expires_at=row.expires_at,
        max_attempts=row.max_attempts,
        attempt_count=row.attempt_count,
        context=dict(row.context or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
        verified_at=row.verified_at,
    )


def _apply_record_to_row(row: OTPChallenge, record: ChallengeRecord) -> None:
    row.flow_type = record.flow_type
    row.status = record.status
    row.otp_hash = record.otp_hash
    row.expires_at = record.expires_at
    row.max_attempts = record.max_attempts
    row.attempt_count = record.attempt_count
    row.context = dict(record.context or {})
    row.created_at = record.created_at
    row.updated_at = record.updated_at
    row.verified_at = record.verified_at


class DjangoChallengeRepository(BaseChallengeRepository):
    """Database-backed BaseChallengeRepository implementation."""

    def create(self, *, payload: Mapping[str, object]) -> ChallengeRecord:
        """Persist a new challenge record."""

        record = payload.get("record")
        if not isinstance(record, ChallengeRecord):
            raise TypeError("payload['record'] must be a ChallengeRecord.")
        try:
            with transaction.atomic():
                OTPChallenge.objects.create(
                    challenge_id=record.id,
                    flow_type=record.flow_type,
                    status=record.status,
                    otp_hash=record.otp_hash,
                    expires_at=record.expires_at,
                    max_attempts=record.max_attempts,
                    attempt_count=record.attempt_count,
                    context=dict(record.context or {}),
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                    verified_at=record.verified_at,
                )
        except IntegrityError as exc:
            raise ValidationException(f"Challenge '{record.id}' already exists.") from exc
        except (OperationalError, DatabaseError) as exc:
            logger.warning("otp.challenge.repository.create_failed")
            raise RepositoryUnavailableException(
                "Challenge storage is temporarily unavailable."
            ) from exc
        return self.get_by_id(record.id)

    def get_by_id(self, challenge_id: str) -> ChallengeRecord:
        """Load a challenge record by identifier."""

        try:
            row = OTPChallenge.objects.get(challenge_id=challenge_id)
        except OTPChallenge.DoesNotExist as exc:
            raise ChallengeNotFoundException(
                f"Challenge '{challenge_id}' was not found."
            ) from exc
        except (OperationalError, DatabaseError) as exc:
            logger.warning("otp.challenge.repository.get_failed")
            raise RepositoryUnavailableException(
                "Challenge storage is temporarily unavailable."
            ) from exc
        return _row_to_record(row)

    def update(self, challenge_id: str, *, payload: Mapping[str, object]) -> ChallengeRecord:
        """Persist challenge state changes with concurrency-safe status transitions.

        Terminal transitions (VERIFIED / LOCKED / EXPIRED / …) use a compare-and-set
        UPDATE so concurrent workers cannot both complete the same challenge even on
        databases that do not enforce ``select_for_update`` (e.g. SQLite).
        """

        record = payload.get("record")
        if not isinstance(record, ChallengeRecord):
            raise TypeError("payload['record'] must be a ChallengeRecord.")
        if record.id != challenge_id:
            raise ValidationException("Challenge id mismatch during update.")

        try:
            with transaction.atomic():
                try:
                    row = (
                        OTPChallenge.objects.select_for_update()
                        .get(challenge_id=challenge_id)
                    )
                except OTPChallenge.DoesNotExist as exc:
                    raise ChallengeNotFoundException(
                        f"Challenge '{challenge_id}' was not found."
                    ) from exc

                self._assert_update_allowed(current_status=row.status, incoming=record)

                if (
                    record.status in _TERMINAL_STATUSES
                    and row.status != record.status
                ):
                    expected_from = row.status
                    updated = OTPChallenge.objects.filter(
                        challenge_id=challenge_id,
                        status=expected_from,
                    ).update(
                        flow_type=record.flow_type,
                        status=record.status,
                        otp_hash=record.otp_hash,
                        expires_at=record.expires_at,
                        max_attempts=record.max_attempts,
                        attempt_count=record.attempt_count,
                        context=dict(record.context or {}),
                        created_at=record.created_at,
                        updated_at=record.updated_at,
                        verified_at=record.verified_at,
                    )
                    if updated != 1:
                        raise ReplayAttackException(
                            "OTP challenge is no longer reusable."
                        )
                    return self.get_by_id(challenge_id)

                _apply_record_to_row(row, record)
                row.save()
                return _row_to_record(row)
        except (ChallengeNotFoundException, ValidationException, ReplayAttackException):
            raise
        except (OperationalError, DatabaseError) as exc:
            logger.warning("otp.challenge.repository.update_failed")
            raise RepositoryUnavailableException(
                "Challenge storage is temporarily unavailable."
            ) from exc

    def _assert_update_allowed(self, *, current_status: str, incoming: ChallengeRecord) -> None:
        """Reject stale writes that would corrupt terminal or concurrent verify state."""

        if current_status in _TERMINAL_STATUSES:
            if incoming.status == current_status:
                # Idempotent rewrite of same terminal state (e.g. verified_at stamp).
                return
            if ChallengeLifecycle.is_replay_blocked(current_status):
                raise ReplayAttackException("OTP challenge is no longer reusable.")
            raise ValidationException(
                f"Challenge cannot transition from terminal status '{current_status}'."
            )

        if incoming.status == ChallengeStatus.VERIFIED and current_status != ChallengeStatus.VERIFY_PENDING:
            raise ReplayAttackException("OTP challenge is no longer reusable.")

    def clear(self) -> None:
        """Remove all challenge rows (tests only)."""

        OTPChallenge.objects.all().delete()
