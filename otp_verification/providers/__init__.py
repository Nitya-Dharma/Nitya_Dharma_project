"""Provider registry and resolution helpers.

MockOTPProvider is imported lazily from ``otp_verification.providers.mock`` to
avoid circular imports with the services factory.
"""

from otp_verification.providers.base import ProviderDescriptor
from otp_verification.providers.lifecycle import ProviderLifecycle
from otp_verification.providers.metrics import ProviderMetrics, ProviderMetricsSnapshot
from otp_verification.providers.registry import OTPProviderRegistry
from otp_verification.providers.resolver import ProviderResolver, load_provider_class
from otp_verification.providers.results import ProviderResult, provider_result_from_response
from otp_verification.providers.results import validate_provider_result
from otp_verification.providers.simulation import MockSimulationEngine, SimulationOutcome

__all__ = [
    "MockOTPProvider",
    "Msg91SmsProvider",
    "MockSimulationEngine",
    "OTPProviderRegistry",
    "ProviderDescriptor",
    "ProviderLifecycle",
    "ProviderMetrics",
    "ProviderMetricsSnapshot",
    "ProviderResolver",
    "ProviderResult",
    "SimulationOutcome",
    "load_provider_class",
    "provider_result_from_response",
    "validate_provider_result",
]


def __getattr__(name: str):
    if name == "MockOTPProvider":
        from otp_verification.providers.mock import MockOTPProvider

        return MockOTPProvider
    if name == "Msg91SmsProvider":
        from otp_verification.providers.msg91 import Msg91SmsProvider

        return Msg91SmsProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
