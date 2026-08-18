"""Policy services for OTP attempt tracking and deferred safeguards."""

from __future__ import annotations

from datetime import datetime, timezone

from otp_verification.domain.lifecycle import ChallengeLifecycle
from otp_verification.enums import ChallengeStatus
from otp_verification.exceptions import ChallengeLockedException, ConfigurationException
from otp_verification.interfaces import BaseAttemptTracker, BaseCooldownManager
from otp_verification.interfaces import BaseChallengeRepository, BaseLockoutManager


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AttemptTracker(BaseAttemptTracker):
    """Persists verification attempt counts on challenge records."""

    def __init__(self, *, repository: BaseChallengeRepository | None = None) -> None:
        self.repository = repository

    def record_attempt(self, *, challenge_id: str, successful: bool) -> None:
        """Record an OTP verification attempt.

        Failed attempts increment the counter. Successful attempts do not.
        """

        if self.repository is None:
            raise ConfigurationException("AttemptTracker requires a repository.")
        record = self.repository.get_by_id(challenge_id)
        if successful:
            return
        updated = record.copy_with(
            attempt_count=record.attempt_count + 1,
            updated_at=_utcnow(),
        )
        self.repository.update(challenge_id, payload={"record": updated})


class CooldownManager(BaseCooldownManager):
    """Resend cooldown remains deferred (Task 2 explicitly excludes it)."""

    def __init__(self, *, repository=None, configuration=None) -> None:
        self.repository = repository
        self.configuration = configuration

    def ensure_available(self, *, challenge_id: str) -> None:
        raise NotImplementedError("Cooldown enforcement is implemented in a later OTP phase.")


class LockoutManager(BaseLockoutManager):
    """Checks challenge LOCKED state produced by max-attempt enforcement.

    Duration-based lockout windows remain deferred to later phases.
    """

    def __init__(
        self,
        *,
        repository: BaseChallengeRepository | None = None,
        configuration=None,
    ) -> None:
        self.repository = repository
        self.configuration = configuration

    def ensure_available(self, *, challenge_id: str) -> None:
        """Raise when the challenge has entered the LOCKED lifecycle state."""

        if self.repository is None:
            raise ConfigurationException("LockoutManager requires a repository.")
        record = self.repository.get_by_id(challenge_id)
        if record.status == ChallengeStatus.LOCKED:
            raise ChallengeLockedException("OTP challenge is locked.")
        if ChallengeLifecycle.is_replay_blocked(record.status) and record.status != ChallengeStatus.LOCKED:
            # Expired/verified challenges are handled by replay/expiry paths.
            return


class DuplicatePhonePolicy:
    """Duplicate-phone policy remains deferred to later phases."""

    def __init__(self, *, adapters=None) -> None:
        self.adapters = adapters or ()

    def evaluate(self, *, canonical_phone: str, flow_type: str) -> object:
        raise NotImplementedError("Duplicate-phone policy is implemented in a later OTP phase.")
