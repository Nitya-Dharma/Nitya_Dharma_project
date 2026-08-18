"""Durable replay protection backed by the application database."""

from __future__ import annotations

import logging

from django.db import IntegrityError, OperationalError, transaction
from django.db.utils import DatabaseError
from django.utils import timezone

from otp_verification.exceptions import (
    ReplayAttackException,
    RepositoryUnavailableException,
    SecurityException,
)
from otp_verification.interfaces.security import BaseReplayProtector
from otp_verification.models import OTPReplayToken

logger = logging.getLogger(__name__)


class DatabaseReplayProtection(BaseReplayProtector):
    """Cross-worker replay protection using durable consumed-token rows."""

    def assert_not_replayed(self, *, token: str) -> None:
        """Raise when a challenge/token identifier has already been consumed."""

        if not token:
            raise SecurityException("Replay protection requires a token.")
        try:
            if OTPReplayToken.objects.filter(token=token).exists():
                raise ReplayAttackException("OTP challenge replay blocked.")
        except ReplayAttackException:
            raise
        except (OperationalError, DatabaseError) as exc:
            logger.warning("otp.replay.repository.assert_failed")
            raise RepositoryUnavailableException(
                "Challenge storage is temporarily unavailable."
            ) from exc

    def mark_consumed(self, *, token: str) -> None:
        """Mark a challenge/token as consumed after successful verification."""

        if not token:
            raise SecurityException("Cannot mark an empty token as consumed.")
        try:
            with transaction.atomic():
                OTPReplayToken.objects.get_or_create(
                    token=token,
                    defaults={"consumed_at": timezone.now()},
                )
        except IntegrityError:
            # Concurrent insert of the same token is acceptable — already consumed.
            return
        except (OperationalError, DatabaseError) as exc:
            logger.warning("otp.replay.repository.mark_failed")
            raise RepositoryUnavailableException(
                "Challenge storage is temporarily unavailable."
            ) from exc

    def clear(self) -> None:
        """Clear consumed tokens (intended for tests)."""

        OTPReplayToken.objects.all().delete()
