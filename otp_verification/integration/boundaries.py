"""Stable-system integration boundaries for future OTP phases.

These adapters intentionally contain no runtime integration logic in Task 1.
They preserve a strict isolation boundary from registration, referral, email
verification, approval, authentication, and transaction ownership.
"""


class RegistrationGateway:
    """Future adapter for existing registration entry points."""

    def begin_verified_registration(self, *, flow_type: str, token: str) -> object:
        raise NotImplementedError("Registration integration is implemented in a later phase.")


class AuthenticationGateway:
    """Future adapter for authentication/session ownership boundaries."""

    def complete_login_transition(self, *, user_id: int) -> None:
        raise NotImplementedError("Authentication integration is implemented later.")


class ReferralGateway:
    """Future adapter for stable referral validation and application logic."""

    def apply_referral_context(self, *, payload: object) -> object:
        raise NotImplementedError("Referral integration is implemented in a later phase.")


class EmailVerificationGateway:
    """Future adapter for existing email verification flows."""

    def trigger_verification(self, *, user_id: int) -> None:
        raise NotImplementedError("Email verification integration is implemented later.")


class ApprovalGateway:
    """Future adapter for existing admin approval workflow boundaries."""

    def enqueue_for_approval(self, *, user_id: int) -> None:
        raise NotImplementedError("Approval integration is implemented in a later phase.")


class TransactionGateway:
    """Future adapter for existing registration transaction ownership."""

    def run_atomic_registration(self, callback):
        raise NotImplementedError("Transaction integration is implemented in a later phase.")
