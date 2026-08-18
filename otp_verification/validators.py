"""Configuration-focused validators for the OTP foundation package."""

from otp_verification import constants
from otp_verification.exceptions import ConfigurationException


def validate_provider_name(provider_name: str) -> str:
    """Validate a configured provider identifier."""

    if provider_name not in constants.PROVIDER_CHOICES:
        raise ConfigurationException(
            f"Unsupported OTP provider '{provider_name}'. Allowed: {constants.PROVIDER_CHOICES}."
        )
    return provider_name


def validate_enabled_flow(flow_name: str) -> str:
    """Validate a configured registration flow identifier."""

    if flow_name not in constants.FLOW_CHOICES:
        raise ConfigurationException(
            f"Unsupported OTP flow '{flow_name}'. Allowed: {constants.FLOW_CHOICES}."
        )
    return flow_name


def validate_positive_setting(name: str, value: int, *, minimum: int = 0) -> int:
    """Validate a numeric OTP configuration value."""

    try:
        numeric_value = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigurationException(f"{name} must be an integer.") from exc
    if numeric_value < minimum:
        raise ConfigurationException(f"{name} must be >= {minimum}.")
    return numeric_value
