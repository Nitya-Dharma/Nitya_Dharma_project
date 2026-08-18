"""Orchestration connecting the OTP engine to providers via interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from otp_verification.config import OTPConfiguration, get_configuration
from otp_verification.domain.challenge import ChallengeIssueResult, ChallengeView
from otp_verification.enums import AuditEvent, DeliveryChannel, ProviderResultStatus
from otp_verification.exceptions import (
    ProviderDisabledException,
    ProviderException,
    ProviderFailureException,
    ProviderTimeoutException,
    ProviderUnavailableException,
    ValidationException,
)
from otp_verification.interfaces import BaseAuditLogger, BaseChallengeManager
from otp_verification.interfaces.providers import BaseOTPProvider, ProviderRequest
from otp_verification.providers.results import ProviderResult, provider_result_from_response
from otp_verification.providers.resolver import ProviderResolver


@dataclass(frozen=True)
class ProviderDeliveryResult:
    """Secret-free orchestration result for challenge + provider execution."""

    challenge: ChallengeView
    provider_result: ProviderResult


class ProviderOrchestrator:
    """Coordinates challenge creation and provider delivery.

    Does not generate/hash/verify OTPs or implement provider logic itself.
    """

    def __init__(
        self,
        *,
        challenge_manager: BaseChallengeManager,
        provider_resolver: ProviderResolver,
        audit_logger: BaseAuditLogger,
        configuration: OTPConfiguration | None = None,
    ) -> None:
        self.challenge_manager = challenge_manager
        self.provider_resolver = provider_resolver
        self.audit_logger = audit_logger
        self.configuration = configuration

    def _config(self) -> OTPConfiguration:
        return self.configuration or get_configuration()

    def _audit(self, event: str, payload: Mapping[str, object]) -> None:
        config = self._config()
        if not config.provider_audit_enabled:
            return
        safe_payload = {
            key: value
            for key, value in payload.items()
            if key
            not in {
                "otp",
                "otp_code",
                "otp_hash",
                "hash",
                "salt",
                "message",
                "plaintext_otp",
                "api_key",
                "credentials",
            }
        }
        self.audit_logger.record(event=event, payload=safe_payload)

    def _resolve_provider(self) -> BaseOTPProvider:
        config = self._config()
        provider_name = config.provider
        self._audit(
            AuditEvent.PROVIDER_SELECTED,
            {"provider_name": provider_name},
        )
        return self.provider_resolver.resolve(provider_name)

    def deliver_otp(
        self,
        *,
        flow_type: str,
        destination: str,
        context: Mapping[str, object] | None = None,
        channel: str = DeliveryChannel.SMS,
    ) -> ProviderDeliveryResult:
        """Create a challenge and hand the transient OTP to the resolved provider."""

        if not destination:
            raise ValidationException("destination is required for provider delivery.")
        config = self._config()
        if not config.provider_enabled:
            self._audit(
                AuditEvent.PROVIDER_DISABLED,
                {"provider_name": config.provider},
            )
            raise ProviderDisabledException("OTP provider delivery is disabled.")

        issued: ChallengeIssueResult = self.challenge_manager.create_challenge(
            flow_type=flow_type,
            context=context or {},
        )
        # Challenge-created audit is emitted by ChallengeManager; do not re-log OTP.
        otp_code = issued.otp_code
        provider = self._resolve_provider()

        request = ProviderRequest(
            destination=destination,
            message=otp_code,  # transient handoff only; never audited/persisted here
            channel=channel,
            metadata={
                "challenge_id": issued.challenge.id,
                "flow_type": issued.challenge.flow_type,
            },
        )
        # Drop local reference after request construction intent: keep variable until send.
        try:
            self._audit(
                AuditEvent.PROVIDER_EXECUTION_STARTED,
                {
                    "provider_name": getattr(provider, "provider_name", config.provider),
                    "challenge_id": issued.challenge.id,
                    "destination_present": True,
                    "channel": channel,
                },
            )
            response = provider.send(request)
            result = provider_result_from_response(response)
            self._audit(
                AuditEvent.PROVIDER_COMPLETED,
                {
                    "provider_name": result.provider_name,
                    "provider_reference": result.provider_reference,
                    "status": result.status,
                    "challenge_id": issued.challenge.id,
                },
            )
            if result.status == ProviderResultStatus.SUCCESS:
                self._audit(
                    AuditEvent.OTP_SENT,
                    {
                        "provider_name": result.provider_name,
                        "provider_reference": result.provider_reference,
                        "challenge_id": issued.challenge.id,
                    },
                )
            return ProviderDeliveryResult(
                challenge=issued.challenge,
                provider_result=result,
            )
        except (
            ProviderTimeoutException,
            ProviderUnavailableException,
            ProviderFailureException,
            ProviderDisabledException,
            ProviderException,
        ) as exc:
            self._audit(
                AuditEvent.OTP_SEND_FAILED,
                {
                    "provider_name": config.provider,
                    "challenge_id": issued.challenge.id,
                    "error_type": type(exc).__name__,
                },
            )
            raise
        finally:
            # Ensure transient OTP is not retained on the orchestrator instance.
            otp_code = None  # noqa: F841
            request = None  # noqa: F841
