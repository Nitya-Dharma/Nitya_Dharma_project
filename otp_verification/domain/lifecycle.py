"""Challenge lifecycle transitions for the internal OTP engine.

Lifecycle mapping onto Task 1 ChallengeStatus values:
- Created  -> INITIATED
- Active   -> VERIFY_PENDING
- Verified -> VERIFIED
- Expired  -> EXPIRED
- Locked   -> LOCKED
"""

from __future__ import annotations

from otp_verification.enums import ChallengeStatus
from otp_verification.exceptions import ValidationException

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    ChallengeStatus.INITIATED: frozenset(
        {
            ChallengeStatus.VERIFY_PENDING,
            ChallengeStatus.EXPIRED,
            ChallengeStatus.LOCKED,
            ChallengeStatus.CANCELLED,
        }
    ),
    ChallengeStatus.VERIFY_PENDING: frozenset(
        {
            ChallengeStatus.VERIFIED,
            ChallengeStatus.EXPIRED,
            ChallengeStatus.LOCKED,
            ChallengeStatus.CANCELLED,
        }
    ),
    ChallengeStatus.OTP_SENT: frozenset(
        {
            ChallengeStatus.VERIFY_PENDING,
            ChallengeStatus.VERIFIED,
            ChallengeStatus.EXPIRED,
            ChallengeStatus.LOCKED,
            ChallengeStatus.CANCELLED,
        }
    ),
    ChallengeStatus.VERIFIED: frozenset({ChallengeStatus.CONSUMED, ChallengeStatus.ARCHIVED}),
    ChallengeStatus.EXPIRED: frozenset({ChallengeStatus.ARCHIVED}),
    ChallengeStatus.LOCKED: frozenset({ChallengeStatus.ARCHIVED}),
    ChallengeStatus.FAILED: frozenset({ChallengeStatus.ARCHIVED, ChallengeStatus.CANCELLED}),
    ChallengeStatus.CANCELLED: frozenset({ChallengeStatus.ARCHIVED}),
    ChallengeStatus.CONSUMED: frozenset({ChallengeStatus.ARCHIVED}),
    ChallengeStatus.ARCHIVED: frozenset(),
}

ACTIVE_STATUSES = frozenset(
    {
        ChallengeStatus.INITIATED,
        ChallengeStatus.OTP_SENT,
        ChallengeStatus.VERIFY_PENDING,
    }
)

TERMINAL_REPLAY_STATUSES = frozenset(
    {
        ChallengeStatus.VERIFIED,
        ChallengeStatus.CONSUMED,
        ChallengeStatus.EXPIRED,
        ChallengeStatus.LOCKED,
        ChallengeStatus.CANCELLED,
        ChallengeStatus.ARCHIVED,
    }
)


class ChallengeLifecycle:
    """Validates and documents allowed challenge state transitions."""

    @staticmethod
    def assert_transition(current_status: str, next_status: str) -> None:
        """Raise when a lifecycle transition is invalid."""

        allowed = ALLOWED_TRANSITIONS.get(current_status, frozenset())
        if next_status not in allowed:
            raise ValidationException(
                f"Invalid challenge transition from '{current_status}' to '{next_status}'."
            )

    @staticmethod
    def is_active(status: str) -> bool:
        """Return whether the challenge can still accept verification."""

        return status in ACTIVE_STATUSES

    @staticmethod
    def is_replay_blocked(status: str) -> bool:
        """Return whether the challenge is no longer reusable."""

        return status in TERMINAL_REPLAY_STATUSES
