"""Mock OTP provider implementing BaseOTPProvider with no network I/O."""

from __future__ import annotations

from typing import Mapping

from otp_verification import constants
from otp_verification.config import OTPConfiguration, get_configuration
from otp_verification.enums import AuditEvent, ProviderLifecycleStatus, ProviderResultStatus
from otp_verification.exceptions import (
    ConfigurationException,
    ProviderDisabledException,
    ProviderFailureException,
    ProviderTimeoutException,
    ProviderUnavailableException,
    ValidationException,
)
from otp_verification.interfaces import BaseAuditLogger
from otp_verification.interfaces.providers import BaseOTPProvider, ProviderRequest, ProviderResponse
from otp_verification.providers.lifecycle import ProviderLifecycle
from otp_verification.providers.metrics import ProviderMetrics
from otp_verification.providers.results import ProviderResult, validate_provider_result
from otp_verification.providers.simulation import MockSimulationEngine
from otp_verification.services.support import AuditLogger, NullLoggingBackend


class MockOTPProvider(BaseOTPProvider):
    """Configuration-driven mock SMS provider.

    Satisfies ``BaseOTPProvider.send`` and never performs network communication.
    """

    provider_name = constants.PROVIDER_MOCK_SMS

    def __init__(
        self,
        *,
        configuration: OTPConfiguration | None = None,
        audit_logger: BaseAuditLogger | None = None,
        metrics: ProviderMetrics | None = None,
        simulation_engine: MockSimulationEngine | None = None,
    ) -> None:
        self.configuration = configuration or get_configuration()
        self.audit_logger = audit_logger or AuditLogger(backend=NullLoggingBackend())
        self.metrics = metrics or ProviderMetrics()
        self.simulation_engine = simulation_engine or MockSimulationEngine(
            configuration=self.configuration
        )
        self.lifecycle = ProviderLifecycle(initial=ProviderLifecycleStatus.INITIALIZED)
        self._audit(
            AuditEvent.PROVIDER_INITIALIZED,
            {"provider_name": self.provider_name},
        )
        if self.configuration.provider_enabled:
            self.lifecycle.transition_to(ProviderLifecycleStatus.READY)
        else:
            self.lifecycle.transition_to(ProviderLifecycleStatus.DISABLED)
            self._audit(
                AuditEvent.PROVIDER_DISABLED,
                {"provider_name": self.provider_name},
            )

    def _audit(self, event: str, payload: Mapping[str, object]) -> None:
        if not self.configuration.provider_audit_enabled:
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

    def _validate_request(self, request: ProviderRequest) -> None:
        if not isinstance(request, ProviderRequest):
            raise ValidationException("Provider request must be a ProviderRequest.")
        if not request.destination:
            raise ValidationException("Provider request requires destination.")
        if not request.channel:
            raise ValidationException("Provider request requires channel.")
        # Intentionally do not inspect/log request.message (may contain OTP).

    def _raise_for_status(self, status: str, message: str) -> None:
        if status == ProviderResultStatus.TIMEOUT:
            raise ProviderTimeoutException(message)
        if status == ProviderResultStatus.UNAVAILABLE:
            raise ProviderUnavailableException(message)
        if status in {ProviderResultStatus.FAILURE, ProviderResultStatus.ERROR}:
            raise ProviderFailureException(message)

    def send(self, request: ProviderRequest) -> ProviderResponse:
        """Simulate outbound OTP delivery without network activity."""

        if not self.configuration.provider_enabled:
            self.lifecycle.status = ProviderLifecycleStatus.DISABLED
            self._audit(
                AuditEvent.PROVIDER_DISABLED,
                {"provider_name": self.provider_name},
            )
            raise ProviderDisabledException("Mock OTP provider is disabled.")

        if self.lifecycle.status == ProviderLifecycleStatus.DISABLED:
            raise ProviderDisabledException("Mock OTP provider is disabled.")

        if self.lifecycle.status != ProviderLifecycleStatus.READY:
            # Allow reuse after terminal outcomes by returning to READY first.
            if self.lifecycle.status in {
                ProviderLifecycleStatus.SUCCESS,
                ProviderLifecycleStatus.FAILED,
                ProviderLifecycleStatus.TIMEOUT,
            }:
                self.lifecycle.transition_to(ProviderLifecycleStatus.READY)
            elif self.lifecycle.status == ProviderLifecycleStatus.INITIALIZED:
                self.lifecycle.transition_to(ProviderLifecycleStatus.READY)
            else:
                raise ValidationException(
                    f"Mock provider cannot send from lifecycle state '{self.lifecycle.status}'."
                )

        self._validate_request(request)
        self.lifecycle.transition_to(ProviderLifecycleStatus.SENDING)
        self._audit(
            AuditEvent.PROVIDER_SEND_STARTED,
            {
                "provider_name": self.provider_name,
                "destination_present": bool(request.destination),
                "channel": request.channel,
                "challenge_id": (request.metadata or {}).get("challenge_id"),
            },
        )
        self._audit(
            AuditEvent.PROVIDER_EXECUTION_STARTED,
            {"provider_name": self.provider_name},
        )

        outcome = self.simulation_engine.execute()
        result = validate_provider_result(
            ProviderResult(
                status=outcome.status,
                provider_name=self.provider_name,
                provider_message=outcome.provider_message,
                provider_reference=outcome.provider_reference,
                timestamp=outcome.timestamp,
            )
        )

        if self.configuration.provider_metrics_enabled:
            self.metrics.record(
                success=result.status == ProviderResultStatus.SUCCESS,
                failure=result.status
                in {ProviderResultStatus.FAILURE, ProviderResultStatus.ERROR},
                timeout=result.status == ProviderResultStatus.TIMEOUT,
                unavailable=result.status == ProviderResultStatus.UNAVAILABLE,
                duration_ms=outcome.duration_ms,
                available=result.status
                not in {ProviderResultStatus.UNAVAILABLE, ProviderResultStatus.DISABLED},
            )

        if result.status == ProviderResultStatus.SUCCESS:
            self.lifecycle.transition_to(ProviderLifecycleStatus.SUCCESS)
            self._audit(
                AuditEvent.PROVIDER_SEND_SUCCESS,
                {
                    "provider_name": result.provider_name,
                    "provider_reference": result.provider_reference,
                    "status": result.status,
                },
            )
            self._audit(
                AuditEvent.PROVIDER_COMPLETED,
                {
                    "provider_name": result.provider_name,
                    "provider_reference": result.provider_reference,
                    "status": result.status,
                },
            )
            self.lifecycle.transition_to(ProviderLifecycleStatus.READY)
            return ProviderResponse(
                accepted=True,
                provider_name=result.provider_name,
                provider_reference=result.provider_reference,
                metadata={
                    "status": result.status,
                    "provider_message": result.provider_message,
                    "timestamp": result.timestamp,
                },
            )

        if result.status == ProviderResultStatus.TIMEOUT:
            self.lifecycle.transition_to(ProviderLifecycleStatus.TIMEOUT)
            self._audit(
                AuditEvent.PROVIDER_TIMEOUT,
                {
                    "provider_name": result.provider_name,
                    "provider_reference": result.provider_reference,
                    "status": result.status,
                },
            )
        elif result.status == ProviderResultStatus.UNAVAILABLE:
            self.lifecycle.transition_to(ProviderLifecycleStatus.FAILED)
            self._audit(
                AuditEvent.PROVIDER_UNAVAILABLE,
                {
                    "provider_name": result.provider_name,
                    "provider_reference": result.provider_reference,
                    "status": result.status,
                },
            )
        else:
            self.lifecycle.transition_to(ProviderLifecycleStatus.FAILED)
            self._audit(
                AuditEvent.PROVIDER_SEND_FAILURE,
                {
                    "provider_name": result.provider_name,
                    "provider_reference": result.provider_reference,
                    "status": result.status,
                },
            )

        self.lifecycle.transition_to(ProviderLifecycleStatus.READY)
        self._raise_for_status(result.status, result.provider_message)
        raise ConfigurationException("Unreachable mock provider failure path.")
