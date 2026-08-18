"""Provider lifecycle transition validation for the mock provider layer."""

from __future__ import annotations

from otp_verification.enums import ProviderLifecycleStatus
from otp_verification.exceptions import ValidationException

ALLOWED_PROVIDER_TRANSITIONS: dict[str, frozenset[str]] = {
    ProviderLifecycleStatus.INITIALIZED: frozenset(
        {
            ProviderLifecycleStatus.READY,
            ProviderLifecycleStatus.DISABLED,
        }
    ),
    ProviderLifecycleStatus.READY: frozenset(
        {
            ProviderLifecycleStatus.SENDING,
            ProviderLifecycleStatus.DISABLED,
        }
    ),
    ProviderLifecycleStatus.SENDING: frozenset(
        {
            ProviderLifecycleStatus.SUCCESS,
            ProviderLifecycleStatus.FAILED,
            ProviderLifecycleStatus.TIMEOUT,
            ProviderLifecycleStatus.READY,
        }
    ),
    ProviderLifecycleStatus.SUCCESS: frozenset({ProviderLifecycleStatus.READY}),
    ProviderLifecycleStatus.FAILED: frozenset({ProviderLifecycleStatus.READY}),
    ProviderLifecycleStatus.TIMEOUT: frozenset({ProviderLifecycleStatus.READY}),
    ProviderLifecycleStatus.DISABLED: frozenset({ProviderLifecycleStatus.READY}),
}


class ProviderLifecycle:
    """Validates mock-provider lifecycle transitions."""

    def __init__(self, *, initial: str = ProviderLifecycleStatus.INITIALIZED) -> None:
        self.status = initial

    def transition_to(self, next_status: str) -> str:
        """Apply a validated lifecycle transition and return the new status."""

        allowed = ALLOWED_PROVIDER_TRANSITIONS.get(self.status, frozenset())
        if next_status not in allowed:
            raise ValidationException(
                f"Invalid provider lifecycle transition from '{self.status}' to '{next_status}'."
            )
        self.status = next_status
        return self.status

    def assert_status(self, expected: str) -> None:
        if self.status != expected:
            raise ValidationException(
                f"Provider lifecycle expected '{expected}' but was '{self.status}'."
            )
