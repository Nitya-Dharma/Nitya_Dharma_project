"""Internal challenge records for the OTP engine.

ChallengeRecord retains the OTP hash for verification only. Public-facing
ChallengeView never exposes hashes or plaintext OTP values.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Mapping


@dataclass
class ChallengeRecord:
    """Mutable internal challenge state used by the OTP engine only."""

    id: str
    flow_type: str
    status: str
    otp_hash: str
    expires_at: datetime
    max_attempts: int
    attempt_count: int = 0
    context: Mapping[str, object] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    verified_at: datetime | None = None

    def copy_with(self, **changes) -> ChallengeRecord:
        """Return an updated copy of this challenge record."""

        return replace(self, **changes)


@dataclass(frozen=True)
class ChallengeView:
    """Safe external representation of a challenge (no secrets)."""

    id: str
    flow_type: str
    status: str
    expires_at: datetime
    attempt_count: int
    max_attempts: int
    created_at: datetime | None = None
    verified_at: datetime | None = None


@dataclass(frozen=True)
class ChallengeIssueResult:
    """Result of challenge creation.

    ``otp_code`` is returned only for transient provider handoff in later
    phases. It must never be persisted or logged.
    """

    challenge: ChallengeView
    otp_code: str


def to_challenge_view(record: ChallengeRecord) -> ChallengeView:
    """Project an internal record into a secret-free view."""

    return ChallengeView(
        id=record.id,
        flow_type=record.flow_type,
        status=record.status,
        expires_at=record.expires_at,
        attempt_count=record.attempt_count,
        max_attempts=record.max_attempts,
        created_at=record.created_at,
        verified_at=record.verified_at,
    )
