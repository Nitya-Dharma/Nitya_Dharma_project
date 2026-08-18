"""Registration-friendly exceptions (no provider/transport leakage)."""

from __future__ import annotations


class RegistrationOTPError(Exception):
    """Base registration OTP integration error."""


class RegistrationOTPValidationError(RegistrationOTPError):
    """Invalid registration OTP request (phone, flow, empty fields)."""


class RegistrationOTPInvalid(RegistrationOTPError):
    """Submitted OTP does not match the challenge."""


class RegistrationOTPReplay(RegistrationOTPError):
    """Challenge was already verified or otherwise consumed; replay blocked."""


class RegistrationOTPExpired(RegistrationOTPError):
    """Challenge or OTP has expired."""


class RegistrationOTPLocked(RegistrationOTPError):
    """Challenge locked after too many failed attempts."""


class RegistrationOTPRateLimited(RegistrationOTPError):
    """Too many OTP-related requests."""


class RegistrationOTPDeliveryFailed(RegistrationOTPError):
    """OTP could not be delivered (provider/transport abstracted)."""


class RegistrationOTPNotFound(RegistrationOTPError):
    """Challenge could not be located."""


class RegistrationOTPDisabled(RegistrationOTPError):
    """OTP registration gate is disabled or flow not enabled."""


class RegistrationOTPSessionExpired(RegistrationOTPError):
    """Pending registration session TTL has elapsed; registration must restart."""


class RegistrationOTPCooldownActive(RegistrationOTPError):
    """Resend rejected because cooldown has not elapsed."""

    def __init__(self, message: str, *, remaining_seconds: int) -> None:
        super().__init__(message)
        self.remaining_seconds = max(0, int(remaining_seconds))


class RegistrationOTPResendLimitReached(RegistrationOTPError):
    """Resend rejected because maximum resend attempts were used."""

    def __init__(self, message: str, *, remaining_attempts: int = 0) -> None:
        super().__init__(message)
        self.remaining_attempts = max(0, int(remaining_attempts))


class RegistrationOTPGenerationLimitReached(RegistrationOTPError):
    """OTP generation rejected because this session context used its total quota."""

    def __init__(self, message: str, *, remaining_attempts: int = 0) -> None:
        super().__init__(message)
        self.remaining_attempts = max(0, int(remaining_attempts))


class RegistrationOTPServiceError(RegistrationOTPError):
    """Unexpected registration OTP service failure."""
