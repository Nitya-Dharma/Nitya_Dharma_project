"""Storage adapters for the OTP engine."""

from otp_verification.storage.django_db import DjangoChallengeRepository
from otp_verification.storage.memory import InMemoryChallengeRepository
from otp_verification.storage.replay_db import DatabaseReplayProtection

__all__ = [
    "DatabaseReplayProtection",
    "DjangoChallengeRepository",
    "InMemoryChallengeRepository",
]
