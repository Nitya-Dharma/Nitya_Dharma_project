"""Registration OTP Service — sole facade used by registration modules."""

from __future__ import annotations

from typing import Mapping

from otp_verification.config import OTPConfiguration, get_configuration
from otp_verification.registration.adapters import (
    adapt_issue_request,
    adapt_issue_result,
    adapt_status_result,
    adapt_verify_result,
    map_exception,
)
from otp_verification.registration.contracts import (
    RegistrationOTPIssueResult,
    RegistrationOTPStatusResult,
    RegistrationOTPVerifyResult,
)
from otp_verification.registration.exceptions import (
    RegistrationOTPDisabled,
    RegistrationOTPError,
)
from otp_verification.services.factory import OTPProviderRuntime, build_otp_provider_runtime


class RegistrationOTPService:
    """Business-facing OTP API for all registration modules.

    Responsibilities:
    - start verification (issue + deliver via orchestrator)
    - verify submitted OTP via ChallengeManager
    - expose challenge status
    - map internal failures to registration-safe exceptions

    Non-responsibilities:
    - user/profile creation, approval, referral, authentication
    - provider/transport/MSG91 knowledge
    """

    def __init__(
        self,
        *,
        runtime: OTPProviderRuntime | None = None,
        configuration: OTPConfiguration | None = None,
    ) -> None:
        self._runtime = runtime
        self._configuration = configuration

    def _config(self) -> OTPConfiguration:
        if self._configuration is not None:
            return self._configuration
        if self._runtime is not None:
            return self._runtime.configuration
        return get_configuration()

    def _get_runtime(self) -> OTPProviderRuntime:
        if self._runtime is None:
            self._runtime = build_otp_provider_runtime(configuration=self._config())
        return self._runtime

    def is_enabled_for_flow(self, flow_type: str) -> bool:
        """Return True when OTP gating should apply for this registration flow."""

        config = self._config()
        if not config.enabled:
            return False
        return flow_type in config.enabled_flows

    def start_verification(
        self,
        *,
        flow_type: str,
        destination: str,
        context: Mapping[str, object] | None = None,
    ) -> RegistrationOTPIssueResult:
        """Issue an OTP challenge and deliver it through the provider runtime."""

        if not self.is_enabled_for_flow(flow_type):
            raise RegistrationOTPDisabled(
                "SMS OTP verification is not enabled for this registration flow."
            )
        try:
            validated_flow, phone, safe_context = adapt_issue_request(
                flow_type=flow_type,
                destination=destination,
                context=context,
            )
            runtime = self._get_runtime()
            delivery = runtime.orchestrator.deliver_otp(
                flow_type=validated_flow,
                destination=phone,
                context=safe_context,
            )
            return adapt_issue_result(delivery)
        except RegistrationOTPError:
            raise
        except Exception as exc:  # noqa: BLE001 - mapped immediately
            raise map_exception(exc) from exc

    def verify_challenge(
        self,
        *,
        challenge_id: str,
        submitted_otp: str,
    ) -> RegistrationOTPVerifyResult:
        """Verify a submitted OTP against an existing challenge."""

        if not challenge_id or not str(challenge_id).strip():
            from otp_verification.registration.exceptions import RegistrationOTPValidationError

            raise RegistrationOTPValidationError("Challenge id is required.")
        if not submitted_otp or not str(submitted_otp).strip():
            from otp_verification.registration.exceptions import RegistrationOTPValidationError

            raise RegistrationOTPValidationError("OTP code is required.")
        try:
            runtime = self._get_runtime()
            challenge = runtime.engine.challenge_manager.verify_challenge(
                challenge_id=str(challenge_id).strip(),
                submitted_otp=str(submitted_otp).strip(),
            )
            return adapt_verify_result(challenge)
        except RegistrationOTPError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise map_exception(exc) from exc

    def get_challenge_status(self, *, challenge_id: str) -> RegistrationOTPStatusResult:
        """Return a secret-free challenge status for registration UI/state checks."""

        if not challenge_id or not str(challenge_id).strip():
            from otp_verification.registration.exceptions import RegistrationOTPValidationError

            raise RegistrationOTPValidationError("Challenge id is required.")
        try:
            runtime = self._get_runtime()
            challenge = runtime.engine.challenge_manager.get_challenge(
                str(challenge_id).strip()
            )
            return adapt_status_result(challenge)
        except RegistrationOTPError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise map_exception(exc) from exc
