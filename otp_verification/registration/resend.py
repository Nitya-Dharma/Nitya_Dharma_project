"""Registration OTP resend service (Task 7B) — no provider/transport knowledge."""

from __future__ import annotations

import logging
from typing import Any

from otp_verification.config import OTPConfiguration, get_configuration
from otp_verification.enums import AuditEvent, ChallengeStatus
from otp_verification.registration.contracts import RegistrationOTPResendResult
from otp_verification.registration.exceptions import (
    RegistrationOTPCooldownActive,
    RegistrationOTPDeliveryFailed,
    RegistrationOTPDisabled,
    RegistrationOTPError,
    RegistrationOTPExpired,
    RegistrationOTPLocked,
    RegistrationOTPNotFound,
    RegistrationOTPReplay,
    RegistrationOTPResendLimitReached,
    RegistrationOTPSessionExpired,
    RegistrationOTPValidationError,
)
from otp_verification.registration.service import RegistrationOTPService
from otp_verification.registration.session import (
    assert_otp_generation_available,
    bind_pending_to_new_challenge,
    bind_phone_challenge_to_new_challenge,
    cooldown_remaining_seconds,
    get_completed_registration,
    get_pending_resend_count,
    is_registration_otp_verified,
    record_successful_otp_generation,
    remaining_otp_generations,
    resolve_otp_resend_session,
)
from otp_verification.services.factory import OTPProviderRuntime, build_otp_provider_runtime

logger = logging.getLogger(__name__)


class RegistrationOTPResendService:
    """Issues a replacement challenge for an active OTP session.

    Resolves either real pending registration or phone_challenge session.
    Strategy (Task 7A): create a **new** challenge via existing deliver_otp,
    then rebind the session to the new challenge_id. Does not modify
    ChallengeManager, providers, or transport.
    """

    def __init__(
        self,
        *,
        runtime: OTPProviderRuntime | None = None,
        configuration: OTPConfiguration | None = None,
        otp_service: RegistrationOTPService | None = None,
    ) -> None:
        self._runtime = runtime
        self._configuration = configuration
        self._otp_service = otp_service

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

    def _get_otp_service(self) -> RegistrationOTPService:
        if self._otp_service is None:
            self._otp_service = RegistrationOTPService(
                runtime=self._get_runtime(),
                configuration=self._config(),
            )
        return self._otp_service

    def resend(
        self,
        request,
        *,
        posted_challenge_id: str | None = None,
    ) -> RegistrationOTPResendResult:
        """Validate session/ownership/state, deliver a new OTP challenge, rebind session."""

        config = self._config()
        if not config.enabled:
            raise RegistrationOTPDisabled("SMS OTP verification is not enabled.")

        completed = get_completed_registration(request)
        if completed:
            logger.info("event=%s reason=already_completed", AuditEvent.RESEND_DENIED)
            raise RegistrationOTPReplay("Registration already completed for this session.")

        try:
            source, session = resolve_otp_resend_session(request, enforce_ttl=True)
        except RegistrationOTPSessionExpired:
            logger.info("event=%s reason=session_expired", AuditEvent.RESEND_DENIED)
            raise

        if not session:
            logger.info("event=%s reason=invalid_session", AuditEvent.RESEND_DENIED)
            raise RegistrationOTPValidationError(
                "No pending registration OTP found. Please register again."
            )

        pending = session
        flow_type = str(pending.get("flow_type") or "")
        challenge_id = str(pending.get("challenge_id") or "")
        destination = str(pending.get("destination") or "").strip()
        posted = (posted_challenge_id or "").strip()

        logger.info(
            "event=%s flow=%s challenge=%s",
            AuditEvent.RESEND_REQUESTED,
            flow_type,
            challenge_id,
        )

        if not posted or posted != challenge_id:
            logger.info(
                "event=%s flow=%s reason=ownership_failure",
                AuditEvent.RESEND_DENIED,
                flow_type,
            )
            raise RegistrationOTPValidationError(
                "Invalid resend request. Please restart registration."
            )

        if is_registration_otp_verified(
            request,
            flow_type=flow_type,
            challenge_id=challenge_id,
        ):
            logger.info(
                "event=%s flow=%s reason=already_verified",
                AuditEvent.RESEND_BLOCKED,
                flow_type,
            )
            raise RegistrationOTPReplay(
                "OTP already verified. Continue registration without resending."
            )

        if flow_type not in config.enabled_flows:
            raise RegistrationOTPDisabled(
                "SMS OTP verification is not enabled for this registration flow."
            )

        self._assert_challenge_eligible(challenge_id=challenge_id, flow_type=flow_type)
        assert_otp_generation_available(request, flow_type=flow_type)
        self._assert_cooldown(pending=pending, config=config, flow_type=flow_type)

        if not destination:
            raise RegistrationOTPValidationError("Phone number is missing from the pending session.")

        try:
            runtime = self._get_runtime()
            delivery = runtime.orchestrator.deliver_otp(
                flow_type=flow_type,
                destination=destination,
                context={
                    "resume_path": pending.get("resume_path"),
                    "email": (pending.get("payload") or {}).get("email"),
                    "resend": True,
                },
            )
        except RegistrationOTPError:
            logger.info(
                "event=%s flow=%s challenge=%s",
                AuditEvent.RESEND_FAILED,
                flow_type,
                challenge_id,
            )
            raise
        except Exception as exc:  # noqa: BLE001
            logger.info(
                "event=%s flow=%s challenge=%s",
                AuditEvent.RESEND_FAILED,
                flow_type,
                challenge_id,
            )
            from otp_verification.registration.adapters import map_exception

            mapped = map_exception(exc)
            if isinstance(mapped, RegistrationOTPDeliveryFailed):
                raise mapped from exc
            raise RegistrationOTPDeliveryFailed(
                "Unable to send verification code. Please try again later."
            ) from exc

        new_challenge = delivery.challenge
        if new_challenge.flow_type != flow_type:
            raise RegistrationOTPValidationError("Resend challenge flow mismatch.")

        record_successful_otp_generation(request, flow_type=flow_type)
        if source == "phone_challenge":
            updated = bind_phone_challenge_to_new_challenge(
                request,
                challenge_id=new_challenge.id,
            )
        else:
            updated = bind_pending_to_new_challenge(request, challenge_id=new_challenge.id)
        resend_count = get_pending_resend_count(updated)
        remaining = remaining_otp_generations(request, flow_type=flow_type)

        logger.info(
            "event=%s flow=%s challenge=%s previous=%s resend_count=%s",
            AuditEvent.RESEND_SENT,
            flow_type,
            new_challenge.id,
            challenge_id,
            resend_count,
        )

        return RegistrationOTPResendResult(
            challenge_id=new_challenge.id,
            flow_type=new_challenge.flow_type,
            status=new_challenge.status,
            expires_at=new_challenge.expires_at,
            resend_count=resend_count,
            remaining_attempts=remaining,
            cooldown_seconds=int(config.resend_cooldown_seconds),
        )

    def _assert_challenge_eligible(self, *, challenge_id: str, flow_type: str) -> None:
        service = self._get_otp_service()
        try:
            status = service.get_challenge_status(challenge_id=challenge_id)
        except RegistrationOTPNotFound:
            # In-memory loss / expired-and-purged: allow issuing a replacement.
            return
        except RegistrationOTPExpired:
            # Task 7A: expired challenge may be replaced when session is valid.
            return

        if status.flow_type != flow_type:
            logger.info(
                "event=%s flow=%s reason=flow_mismatch",
                AuditEvent.RESEND_DENIED,
                flow_type,
            )
            raise RegistrationOTPValidationError(
                "Invalid resend request. Please restart registration."
            )

        if status.status == ChallengeStatus.LOCKED:
            logger.info(
                "event=%s flow=%s reason=locked",
                AuditEvent.RESEND_DENIED,
                flow_type,
            )
            raise RegistrationOTPLocked("Too many incorrect attempts. OTP verification is locked.")

        if status.status in {
            ChallengeStatus.VERIFIED,
            ChallengeStatus.CONSUMED,
            ChallengeStatus.CANCELLED,
            ChallengeStatus.ARCHIVED,
        }:
            logger.info(
                "event=%s flow=%s reason=terminal_status",
                AuditEvent.RESEND_DENIED,
                flow_type,
            )
            raise RegistrationOTPReplay("This OTP challenge can no longer be used.")

        # VERIFY_PENDING / EXPIRED / INITIATED / OTP_SENT → eligible

    def _assert_cooldown(
        self,
        *,
        pending: dict[str, Any],
        config: OTPConfiguration,
        flow_type: str,
    ) -> None:
        remaining = cooldown_remaining_seconds(
            pending,
            cooldown_seconds=int(config.resend_cooldown_seconds),
        )
        if remaining > 0:
            logger.info(
                "event=%s flow=%s remaining_seconds=%s",
                AuditEvent.RESEND_COOLDOWN,
                flow_type,
                remaining,
            )
            raise RegistrationOTPCooldownActive(
                f"Please wait {remaining} seconds before requesting another code.",
                remaining_seconds=remaining,
            )

    def _assert_resend_limit(
        self,
        *,
        pending: dict[str, Any],
        config: OTPConfiguration,
        flow_type: str,
    ) -> None:
        used = get_pending_resend_count(pending)
        max_resends = int(config.max_resends)
        if used >= max_resends:
            logger.info(
                "event=%s flow=%s resend_count=%s",
                AuditEvent.RESEND_LIMIT_REACHED,
                flow_type,
                used,
            )
            raise RegistrationOTPResendLimitReached(
                "Maximum resend attempts reached. Please restart registration.",
                remaining_attempts=0,
            )
