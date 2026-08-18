"""Centralized configuration access for the OTP foundation package."""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from otp_verification import constants
from otp_verification.enums import ProviderType, RegistrationFlow, SimulationMode
from otp_verification.exceptions import ConfigurationException


def _coerce_int(value, *, setting_name: str, minimum: int) -> int:
    try:
        value = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigurationException(f"{setting_name} must be an integer.") from exc
    if value < minimum:
        raise ConfigurationException(f"{setting_name} must be >= {minimum}.")
    return value


def _coerce_bool(value, *, setting_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise ConfigurationException(f"{setting_name} must be a boolean.")


def _coerce_str(value, *, setting_name: str, allow_empty: bool = False) -> str:
    text = "" if value is None else str(value).strip()
    if not text and not allow_empty:
        raise ConfigurationException(f"{setting_name} is required.")
    return text


@dataclass(frozen=True)
class OTPConfiguration:
    """Read-only OTP configuration snapshot for engine and provider consumers."""

    enabled: bool
    mode: str
    provider: str
    enabled_flows: tuple[str, ...]
    otp_expiry_seconds: int
    resend_cooldown_seconds: int
    otp_length: int
    max_attempts: int
    max_resends: int
    provider_enabled: bool = constants.DEFAULT_PROVIDER_ENABLED
    mock_simulation_mode: str = constants.DEFAULT_MOCK_SIMULATION_MODE
    mock_execution_delay_ms: int = constants.DEFAULT_MOCK_EXECUTION_DELAY_MS
    mock_allow_random: bool = constants.DEFAULT_MOCK_ALLOW_RANDOM
    provider_audit_enabled: bool = constants.DEFAULT_PROVIDER_AUDIT_ENABLED
    provider_metrics_enabled: bool = constants.DEFAULT_PROVIDER_METRICS_ENABLED
    msg91_auth_key: str = ""
    msg91_base_url: str = constants.DEFAULT_MSG91_BASE_URL
    msg91_flow_id: str = ""
    msg91_sender_id: str = ""
    msg91_template_variable: str = constants.DEFAULT_MSG91_TEMPLATE_VARIABLE
    msg91_country_code: str = constants.DEFAULT_MSG91_COUNTRY_CODE
    msg91_timeout_seconds: int = constants.DEFAULT_MSG91_TIMEOUT_SECONDS
    registration_pending_ttl_seconds: int = (
        constants.DEFAULT_REGISTRATION_PENDING_TTL_SECONDS
    )
    registration_completed_ttl_seconds: int = (
        constants.DEFAULT_REGISTRATION_COMPLETED_TTL_SECONDS
    )


def get_mode() -> str:
    mode = getattr(settings, constants.FEATURE_FLAG_MODE, constants.MODE_MOCK)
    if mode not in constants.MODE_CHOICES:
        raise ConfigurationException(
            f"{constants.FEATURE_FLAG_MODE} must be one of {constants.MODE_CHOICES}."
        )
    return mode


def get_provider() -> str:
    provider = getattr(settings, constants.FEATURE_FLAG_PROVIDER, constants.PROVIDER_MOCK_SMS)
    if provider not in constants.PROVIDER_CHOICES:
        raise ConfigurationException(
            f"{constants.FEATURE_FLAG_PROVIDER} must be one of {constants.PROVIDER_CHOICES}."
        )
    return provider


def get_enabled_flows() -> tuple[str, ...]:
    configured = getattr(settings, constants.FEATURE_FLAG_ENABLED_FLOWS, constants.FLOW_CHOICES)
    if isinstance(configured, str):
        configured = [item.strip() for item in configured.split(",") if item.strip()]
    if not isinstance(configured, (list, tuple, set)):
        raise ConfigurationException(
            f"{constants.FEATURE_FLAG_ENABLED_FLOWS} must be a list, tuple, set, or CSV string."
        )

    validated: list[str] = []
    for flow in configured:
        flow_value = str(flow).strip()
        try:
            validated.append(RegistrationFlow(flow_value).value)
        except ValueError as exc:
            raise ConfigurationException(
                f"Unknown OTP flow '{flow_value}'. Allowed values: {constants.FLOW_CHOICES}."
            ) from exc
    return tuple(validated)


def get_mock_simulation_mode() -> str:
    mode = getattr(
        settings,
        "OTP_MOCK_SIMULATION_MODE",
        constants.DEFAULT_MOCK_SIMULATION_MODE,
    )
    try:
        return SimulationMode(str(mode).strip()).value
    except ValueError as exc:
        raise ConfigurationException(
            "OTP_MOCK_SIMULATION_MODE must be one of "
            f"{constants.SIMULATION_MODE_CHOICES}."
        ) from exc


def get_configuration() -> OTPConfiguration:
    """Build and validate a configuration snapshot for the OTP package."""

    provider = get_provider()
    config = OTPConfiguration(
        enabled=bool(getattr(settings, constants.FEATURE_FLAG_ENABLED, False)),
        mode=get_mode(),
        provider=provider,
        enabled_flows=get_enabled_flows(),
        otp_expiry_seconds=_coerce_int(
            getattr(settings, "OTP_EXPIRY_SECONDS", constants.DEFAULT_OTP_EXPIRY_SECONDS),
            setting_name="OTP_EXPIRY_SECONDS",
            minimum=1,
        ),
        resend_cooldown_seconds=_coerce_int(
            getattr(
                settings,
                "OTP_RESEND_COOLDOWN_SECONDS",
                constants.DEFAULT_RESEND_COOLDOWN_SECONDS,
            ),
            setting_name="OTP_RESEND_COOLDOWN_SECONDS",
            minimum=0,
        ),
        otp_length=_coerce_int(
            getattr(settings, "OTP_LENGTH", constants.DEFAULT_OTP_LENGTH),
            setting_name="OTP_LENGTH",
            minimum=1,
        ),
        max_attempts=_coerce_int(
            getattr(settings, "OTP_MAX_ATTEMPTS", constants.DEFAULT_MAX_ATTEMPTS),
            setting_name="OTP_MAX_ATTEMPTS",
            minimum=1,
        ),
        max_resends=_coerce_int(
            getattr(settings, "OTP_MAX_RESENDS", constants.DEFAULT_MAX_RESENDS),
            setting_name="OTP_MAX_RESENDS",
            minimum=0,
        ),
        provider_enabled=_coerce_bool(
            getattr(settings, "OTP_PROVIDER_ENABLED", constants.DEFAULT_PROVIDER_ENABLED),
            setting_name="OTP_PROVIDER_ENABLED",
        ),
        mock_simulation_mode=get_mock_simulation_mode(),
        mock_execution_delay_ms=_coerce_int(
            getattr(
                settings,
                "OTP_MOCK_EXECUTION_DELAY_MS",
                constants.DEFAULT_MOCK_EXECUTION_DELAY_MS,
            ),
            setting_name="OTP_MOCK_EXECUTION_DELAY_MS",
            minimum=0,
        ),
        mock_allow_random=_coerce_bool(
            getattr(settings, "OTP_MOCK_ALLOW_RANDOM", constants.DEFAULT_MOCK_ALLOW_RANDOM),
            setting_name="OTP_MOCK_ALLOW_RANDOM",
        ),
        provider_audit_enabled=_coerce_bool(
            getattr(
                settings,
                "OTP_PROVIDER_AUDIT_ENABLED",
                constants.DEFAULT_PROVIDER_AUDIT_ENABLED,
            ),
            setting_name="OTP_PROVIDER_AUDIT_ENABLED",
        ),
        provider_metrics_enabled=_coerce_bool(
            getattr(
                settings,
                "OTP_PROVIDER_METRICS_ENABLED",
                constants.DEFAULT_PROVIDER_METRICS_ENABLED,
            ),
            setting_name="OTP_PROVIDER_METRICS_ENABLED",
        ),
        msg91_auth_key=_coerce_str(
            getattr(settings, "MSG91_AUTH_KEY", ""),
            setting_name="MSG91_AUTH_KEY",
            allow_empty=True,
        ),
        msg91_base_url=_coerce_str(
            getattr(settings, "MSG91_BASE_URL", constants.DEFAULT_MSG91_BASE_URL),
            setting_name="MSG91_BASE_URL",
        ),
        msg91_flow_id=_coerce_str(
            getattr(settings, "MSG91_FLOW_ID", ""),
            setting_name="MSG91_FLOW_ID",
            allow_empty=True,
        ),
        msg91_sender_id=_coerce_str(
            getattr(settings, "MSG91_SENDER_ID", ""),
            setting_name="MSG91_SENDER_ID",
            allow_empty=True,
        ),
        msg91_template_variable=_coerce_str(
            getattr(
                settings,
                "MSG91_TEMPLATE_VARIABLE",
                constants.DEFAULT_MSG91_TEMPLATE_VARIABLE,
            ),
            setting_name="MSG91_TEMPLATE_VARIABLE",
        ),
        msg91_country_code=_coerce_str(
            getattr(settings, "MSG91_COUNTRY_CODE", constants.DEFAULT_MSG91_COUNTRY_CODE),
            setting_name="MSG91_COUNTRY_CODE",
        ),
        msg91_timeout_seconds=_coerce_int(
            getattr(
                settings,
                "MSG91_TIMEOUT_SECONDS",
                constants.DEFAULT_MSG91_TIMEOUT_SECONDS,
            ),
            setting_name="MSG91_TIMEOUT_SECONDS",
            minimum=1,
        ),
        registration_pending_ttl_seconds=_coerce_int(
            getattr(
                settings,
                "OTP_REGISTRATION_PENDING_TTL_SECONDS",
                constants.DEFAULT_REGISTRATION_PENDING_TTL_SECONDS,
            ),
            setting_name="OTP_REGISTRATION_PENDING_TTL_SECONDS",
            minimum=60,
        ),
        registration_completed_ttl_seconds=_coerce_int(
            getattr(
                settings,
                "OTP_REGISTRATION_COMPLETED_TTL_SECONDS",
                constants.DEFAULT_REGISTRATION_COMPLETED_TTL_SECONDS,
            ),
            setting_name="OTP_REGISTRATION_COMPLETED_TTL_SECONDS",
            minimum=60,
        ),
    )
    return config


def validate_msg91_configuration(config: OTPConfiguration) -> None:
    """Fail fast when MSG91 is selected but required settings are missing."""

    if config.provider != constants.PROVIDER_MSG91:
        return
    missing = []
    if not config.msg91_auth_key:
        missing.append("MSG91_AUTH_KEY")
    if not config.msg91_base_url:
        missing.append("MSG91_BASE_URL")
    if not config.msg91_flow_id:
        missing.append("MSG91_FLOW_ID")
    if not config.msg91_sender_id:
        missing.append("MSG91_SENDER_ID")
    if not config.msg91_template_variable:
        missing.append("MSG91_TEMPLATE_VARIABLE")
    if not config.msg91_country_code:
        missing.append("MSG91_COUNTRY_CODE")
    if config.msg91_timeout_seconds < 1:
        missing.append("MSG91_TIMEOUT_SECONDS")
    if not str(config.msg91_base_url).lower().startswith("https://"):
        raise ConfigurationException("MSG91_BASE_URL must use HTTPS.")
    if missing:
        raise ConfigurationException(
            "MSG91 provider configuration incomplete: " + ", ".join(missing)
        )


def validate_configuration() -> OTPConfiguration:
    """Validate OTP configuration without activating OTP runtime behavior."""

    config = get_configuration()
    ProviderType(config.provider)
    SimulationMode(config.mock_simulation_mode)
    validate_msg91_configuration(config)
    return config
