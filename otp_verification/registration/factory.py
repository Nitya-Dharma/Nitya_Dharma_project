"""Factory helpers for the Registration OTP Service."""

from __future__ import annotations

from otp_verification.config import OTPConfiguration, get_configuration
from otp_verification.registration.resend import RegistrationOTPResendService
from otp_verification.registration.service import RegistrationOTPService
from otp_verification.services.factory import OTPProviderRuntime, build_otp_provider_runtime


def build_registration_otp_service(
    *,
    runtime: OTPProviderRuntime | None = None,
    configuration: OTPConfiguration | None = None,
) -> RegistrationOTPService:
    """Resolve RegistrationOTPService through the existing OTP DI factory."""

    config = configuration or (runtime.configuration if runtime else get_configuration())
    provider_runtime = runtime or build_otp_provider_runtime(configuration=config)
    return RegistrationOTPService(runtime=provider_runtime, configuration=config)


def build_registration_otp_resend_service(
    *,
    runtime: OTPProviderRuntime | None = None,
    configuration: OTPConfiguration | None = None,
) -> RegistrationOTPResendService:
    """Resolve RegistrationOTPResendService through the existing OTP DI factory."""

    config = configuration or (runtime.configuration if runtime else get_configuration())
    provider_runtime = runtime or build_otp_provider_runtime(configuration=config)
    otp_service = build_registration_otp_service(
        runtime=provider_runtime,
        configuration=config,
    )
    return RegistrationOTPResendService(
        runtime=provider_runtime,
        configuration=config,
        otp_service=otp_service,
    )


def is_registration_otp_required(flow_type: str) -> bool:
    """Configuration gate used by registration views (no service instantiation required)."""

    config = get_configuration()
    return bool(config.enabled and flow_type in config.enabled_flows)
