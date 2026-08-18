"""OTP engine services and dependency-injection factory.

Heavy factory/provider imports are lazy to avoid circular import cycles with
the mock provider module.
"""

from otp_verification.services.core import ChallengeManager, OTPGenerator, OTPHasher
from otp_verification.services.core import OTPValidator, TokenManager
from otp_verification.services.orchestration import ProviderDeliveryResult, ProviderOrchestrator
from otp_verification.services.policies import AttemptTracker, CooldownManager
from otp_verification.services.policies import DuplicatePhonePolicy, LockoutManager
from otp_verification.services.support import AuditLogger, RegistrationContextBuilder

__all__ = [
    "AttemptTracker",
    "AuditLogger",
    "ChallengeManager",
    "CooldownManager",
    "DuplicatePhonePolicy",
    "LockoutManager",
    "OTPEngine",
    "OTPGenerator",
    "OTPHasher",
    "OTPProviderRuntime",
    "OTPValidator",
    "ProviderDeliveryResult",
    "ProviderOrchestrator",
    "RegistrationContextBuilder",
    "TokenManager",
    "build_otp_engine",
    "build_otp_provider_runtime",
]


def __getattr__(name: str):
    if name in {"OTPEngine", "OTPProviderRuntime", "build_otp_engine", "build_otp_provider_runtime"}:
        from otp_verification.services import factory as factory_module

        return getattr(factory_module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
