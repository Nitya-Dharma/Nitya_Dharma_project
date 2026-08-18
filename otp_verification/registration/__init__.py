"""Registration OTP integration layer (Task 5 + Task 7 resend).

Registration modules must import from this package only — never from
providers, transport, or engine internals.
"""

from otp_verification.registration.contracts import (
    RegistrationOTPIssueRequest,
    RegistrationOTPIssueResult,
    RegistrationOTPResendResult,
    RegistrationOTPStatusResult,
    RegistrationOTPVerifyRequest,
    RegistrationOTPVerifyResult,
)
from otp_verification.registration.exceptions import (
    RegistrationOTPCooldownActive,
    RegistrationOTPDeliveryFailed,
    RegistrationOTPDisabled,
    RegistrationOTPError,
    RegistrationOTPExpired,
    RegistrationOTPInvalid,
    RegistrationOTPLocked,
    RegistrationOTPNotFound,
    RegistrationOTPRateLimited,
    RegistrationOTPReplay,
    RegistrationOTPResendLimitReached,
    RegistrationOTPServiceError,
    RegistrationOTPSessionExpired,
    RegistrationOTPValidationError,
)
from otp_verification.registration.factory import (
    build_registration_otp_resend_service,
    build_registration_otp_service,
    is_registration_otp_required,
)
from otp_verification.registration.resend import RegistrationOTPResendService
from otp_verification.registration.service import RegistrationOTPService
from otp_verification.registration.session import (
    cancel_pending_registration,
    clear_pending_registration,
    finalize_registration_session,
    get_pending_registration,
    is_registration_otp_verified,
    mark_registration_otp_verified,
    minimize_registration_payload,
    store_pending_registration,
)

__all__ = [
    "RegistrationOTPCooldownActive",
    "RegistrationOTPDeliveryFailed",
    "RegistrationOTPDisabled",
    "RegistrationOTPError",
    "RegistrationOTPExpired",
    "RegistrationOTPInvalid",
    "RegistrationOTPIssueRequest",
    "RegistrationOTPIssueResult",
    "RegistrationOTPLocked",
    "RegistrationOTPNotFound",
    "RegistrationOTPRateLimited",
    "RegistrationOTPReplay",
    "RegistrationOTPResendLimitReached",
    "RegistrationOTPResendResult",
    "RegistrationOTPResendService",
    "RegistrationOTPService",
    "RegistrationOTPServiceError",
    "RegistrationOTPSessionExpired",
    "RegistrationOTPStatusResult",
    "RegistrationOTPValidationError",
    "RegistrationOTPVerifyRequest",
    "RegistrationOTPVerifyResult",
    "build_registration_otp_resend_service",
    "build_registration_otp_service",
    "cancel_pending_registration",
    "clear_pending_registration",
    "finalize_registration_session",
    "get_pending_registration",
    "is_registration_otp_required",
    "is_registration_otp_verified",
    "mark_registration_otp_verified",
    "minimize_registration_payload",
    "store_pending_registration",
]
