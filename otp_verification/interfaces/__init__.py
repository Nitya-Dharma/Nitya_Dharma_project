"""Contracts for all replaceable OTP components."""

from otp_verification.interfaces.phone import BasePhoneFormatter, BasePhoneNormalizer
from otp_verification.interfaces.phone import BasePhoneParser, BasePhoneValidator
from otp_verification.interfaces.providers import BaseOTPProvider
from otp_verification.interfaces.security import BaseAuditLogger, BaseHasher
from otp_verification.interfaces.security import BaseLockoutManager, BaseReplayProtector
from otp_verification.interfaces.security import BaseTokenManager
from otp_verification.interfaces.services import BaseAttemptTracker, BaseChallengeManager
from otp_verification.interfaces.services import BaseCooldownManager, BaseOTPGenerator
from otp_verification.interfaces.services import BaseOTPValidator
from otp_verification.interfaces.storage import BaseChallengeRepository

__all__ = [
    "BaseAuditLogger",
    "BaseAttemptTracker",
    "BaseChallengeManager",
    "BaseChallengeRepository",
    "BaseCooldownManager",
    "BaseHasher",
    "BaseLockoutManager",
    "BaseOTPGenerator",
    "BaseOTPProvider",
    "BaseOTPValidator",
    "BasePhoneFormatter",
    "BasePhoneNormalizer",
    "BasePhoneParser",
    "BasePhoneValidator",
    "BaseReplayProtector",
    "BaseTokenManager",
]
