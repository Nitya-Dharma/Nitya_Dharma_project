"""Structured exception hierarchy for the OTP foundation package."""


class OTPException(Exception):
    """Base exception for the OTP package."""


class ConfigurationException(OTPException):
    """Raised when OTP configuration is missing or invalid."""


class ProviderException(OTPException):
    """Raised for provider resolution or provider contract failures."""


class ProviderNotFoundException(ProviderException):
    """Raised when a configured provider cannot be found in the registry."""


class ProviderUnavailableException(ProviderException):
    """Raised when a provider reports an unavailable state."""


class ProviderTimeoutException(ProviderException):
    """Raised when a provider send operation times out."""


class ProviderFailureException(ProviderException):
    """Raised when a provider reports a delivery failure."""


class InvalidProviderResponseException(ProviderException):
    """Raised when a provider response fails validation."""


class ProviderDisabledException(ProviderException):
    """Raised when provider execution is disabled by configuration."""


class ProviderAuthenticationException(ProviderException):
    """Raised when provider authentication fails."""


class ValidationException(OTPException):
    """Raised when OTP-layer validation fails."""


class OTPExpiredException(OTPException):
    """Raised when a submitted OTP is expired."""


class ChallengeExpiredException(OTPException):
    """Raised when an OTP challenge is no longer active."""


class ChallengeLockedException(OTPException):
    """Raised when a challenge is locked by policy."""


class ChallengeNotFoundException(OTPException):
    """Raised when a challenge cannot be located."""


class RepositoryUnavailableException(OTPException):
    """Raised when durable challenge storage is temporarily unavailable."""


class InvalidOTPException(OTPException):
    """Raised when a submitted OTP does not match the active challenge."""


class InvalidPhoneException(OTPException):
    """Raised when a phone number cannot be accepted."""


class TokenException(OTPException):
    """Raised when a verified registration token is invalid."""


class ReplayAttackException(OTPException):
    """Raised when a one-time token or challenge is replayed."""


class SecurityException(OTPException):
    """Raised for OTP-related security policy violations."""


class RateLimitException(OTPException):
    """Raised when a request is blocked by rate limits."""


class CooldownException(OTPException):
    """Raised when a resend or retry cooldown is active."""
