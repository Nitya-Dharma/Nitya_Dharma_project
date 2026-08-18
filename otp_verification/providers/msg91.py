"""MSG91 SMS Flow API v5 provider — delivery only, no OTP ownership."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Mapping

from otp_verification import constants
from otp_verification.config import OTPConfiguration, get_configuration, validate_msg91_configuration
from otp_verification.enums import AuditEvent, ProviderLifecycleStatus, ProviderResultStatus
from otp_verification.exceptions import (
    ConfigurationException,
    InvalidPhoneException,
    InvalidProviderResponseException,
    ProviderAuthenticationException,
    ProviderDisabledException,
    ProviderFailureException,
    ProviderTimeoutException,
    ProviderUnavailableException,
    RateLimitException,
    ValidationException,
)
from otp_verification.interfaces import BaseAuditLogger
from otp_verification.interfaces.providers import BaseOTPProvider, ProviderRequest, ProviderResponse
from otp_verification.providers.lifecycle import ProviderLifecycle
from otp_verification.providers.metrics import ProviderMetrics
from otp_verification.providers.results import ProviderResult, validate_provider_result
from otp_verification.services.support import AuditLogger, NullLoggingBackend
from otp_verification.transport.exceptions import (
    TransportAuthenticationError,
    TransportConnectionError,
    TransportError,
    TransportRateLimitError,
    TransportTimeoutError,
    TransportUnavailableError,
)
from otp_verification.transport.http import HttpTransportResult, RequestsHttpTransport


class Msg91SmsProvider(BaseOTPProvider):
    """Production SMS delivery provider using MSG91 Flow API v5."""

    provider_name = constants.PROVIDER_MSG91

    def __init__(
        self,
        *,
        configuration: OTPConfiguration | None = None,
        audit_logger: BaseAuditLogger | None = None,
        metrics: ProviderMetrics | None = None,
        transport: RequestsHttpTransport | None = None,
    ) -> None:
        self.configuration = configuration or get_configuration()
        self.audit_logger = audit_logger or AuditLogger(backend=NullLoggingBackend())
        self.metrics = metrics or ProviderMetrics()
        self.transport = transport or RequestsHttpTransport()
        self.lifecycle = ProviderLifecycle(initial=ProviderLifecycleStatus.INITIALIZED)

        try:
            validate_msg91_configuration(self.configuration)
        except ConfigurationException:
            self._audit(
                AuditEvent.PROVIDER_CONFIG_FAILURE,
                {"provider_name": self.provider_name},
            )
            raise

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
                "auth_key",
                "authkey",
                "authorization",
                "credentials",
                "headers",
                "request_body",
                "response_body",
                "payload",
                "flow_id",
                "sender_id",
                "template_variable",
                "template_variables",
            }
        }
        self.audit_logger.record(event=event, payload=safe_payload)

    def normalize_destination(self, destination: str) -> str:
        """Normalize destination into MSG91 international digits (no '+')."""

        if not destination or not str(destination).strip():
            raise InvalidPhoneException("Destination phone number is required.")

        raw = str(destination).strip()
        raw = raw.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if raw.startswith("+"):
            raw = raw[1:]
        if not raw.isdigit():
            raise InvalidPhoneException("Destination phone number must contain digits only.")

        country = re.sub(r"\D", "", self.configuration.msg91_country_code or "")
        if not country:
            raise ConfigurationException("MSG91_COUNTRY_CODE is invalid.")

        if raw.startswith(country):
            normalized = raw
        elif len(raw) == 10 and country == "91":
            normalized = f"{country}{raw}"
        else:
            # Accept already-international numbers that don't match default country.
            if len(raw) < 10 or len(raw) > 15:
                raise InvalidPhoneException("Destination phone number length is invalid.")
            normalized = raw

        if len(normalized) < 10 or len(normalized) > 15:
            raise InvalidPhoneException("Normalized destination phone number is invalid.")
        return normalized

    def build_headers(self) -> dict[str, str]:
        return {
            "authkey": self.configuration.msg91_auth_key,
            "content-type": "application/json",
        }

    def build_payload(self, *, request: ProviderRequest, mobile: str) -> dict[str, Any]:
        """Map ProviderRequest into MSG91 Flow API payload (OTP never logged)."""

        if not request.message:
            raise ValidationException("ProviderRequest.message (OTP) is required.")
        var_name = self.configuration.msg91_template_variable
        recipient: dict[str, Any] = {
            "mobiles": mobile,
            var_name: request.message,
        }
        return {
            "flow_id": self.configuration.msg91_flow_id,
            "sender": self.configuration.msg91_sender_id,
            "recipients": [recipient],
        }

    def parse_response(self, transport_result: HttpTransportResult) -> ProviderResult:
        """Convert transport result into a secret-free ProviderResult."""

        payload = transport_result.payload or {}
        msg91_type = str(payload.get("type") or "").strip().lower()
        reference = str(payload.get("message") or "").strip()
        now = datetime.now(timezone.utc)

        if msg91_type == "success":
            if not reference:
                raise InvalidProviderResponseException(
                    "MSG91 success response missing provider reference."
                )
            return validate_provider_result(
                ProviderResult(
                    status=ProviderResultStatus.SUCCESS,
                    provider_name=self.provider_name,
                    provider_message="MSG91 accepted SMS delivery request.",
                    provider_reference=reference,
                    timestamp=now,
                )
            )

        if msg91_type == "error":
            # Do not include raw MSG91 message text if it may echo secrets.
            return validate_provider_result(
                ProviderResult(
                    status=ProviderResultStatus.FAILURE,
                    provider_name=self.provider_name,
                    provider_message="MSG91 rejected SMS delivery request.",
                    provider_reference=reference or f"msg91-error-{transport_result.status_code}",
                    timestamp=now,
                )
            )

        raise InvalidProviderResponseException("Unexpected MSG91 response payload.")

    def _translate_transport_error(self, exc: Exception) -> None:
        if isinstance(exc, TransportTimeoutError):
            self._audit(
                AuditEvent.PROVIDER_TIMEOUT,
                {"provider_name": self.provider_name},
            )
            raise ProviderTimeoutException("MSG91 request timed out.") from exc
        if isinstance(exc, TransportAuthenticationError):
            self._audit(
                AuditEvent.PROVIDER_AUTH_FAILURE,
                {"provider_name": self.provider_name},
            )
            raise ProviderAuthenticationException(
                "MSG91 authentication failed."
            ) from exc
        if isinstance(exc, TransportRateLimitError):
            raise RateLimitException("MSG91 rate limit exceeded.") from exc
        if isinstance(exc, TransportUnavailableError):
            self._audit(
                AuditEvent.PROVIDER_UNAVAILABLE,
                {"provider_name": self.provider_name},
            )
            raise ProviderUnavailableException("MSG91 provider unavailable.") from exc
        if isinstance(exc, TransportConnectionError):
            self._audit(
                AuditEvent.PROVIDER_UNAVAILABLE,
                {"provider_name": self.provider_name},
            )
            raise ProviderUnavailableException(
                "MSG91 connection failure."
            ) from exc
        if isinstance(exc, TransportError):
            self._audit(
                AuditEvent.PROVIDER_SEND_FAILURE,
                {
                    "provider_name": self.provider_name,
                    "status_code": getattr(exc, "status_code", None),
                },
            )
            raise ProviderFailureException("MSG91 provider request failed.") from exc
        raise ProviderFailureException("Unexpected MSG91 provider failure.") from exc

    def send(self, request: ProviderRequest) -> ProviderResponse:
        """Deliver an engine-generated OTP via MSG91 SMS Flow API."""

        if not self.configuration.provider_enabled:
            self.lifecycle.status = ProviderLifecycleStatus.DISABLED
            self._audit(
                AuditEvent.PROVIDER_DISABLED,
                {"provider_name": self.provider_name},
            )
            raise ProviderDisabledException("MSG91 provider is disabled.")

        if self.lifecycle.status != ProviderLifecycleStatus.READY:
            if self.lifecycle.status in {
                ProviderLifecycleStatus.SUCCESS,
                ProviderLifecycleStatus.FAILED,
                ProviderLifecycleStatus.TIMEOUT,
            }:
                self.lifecycle.transition_to(ProviderLifecycleStatus.READY)
            elif self.lifecycle.status == ProviderLifecycleStatus.INITIALIZED:
                self.lifecycle.transition_to(ProviderLifecycleStatus.READY)
            elif self.lifecycle.status == ProviderLifecycleStatus.DISABLED:
                raise ProviderDisabledException("MSG91 provider is disabled.")
            else:
                raise ValidationException(
                    f"MSG91 provider cannot send from lifecycle state '{self.lifecycle.status}'."
                )

        if not isinstance(request, ProviderRequest):
            raise ValidationException("Provider request must be a ProviderRequest.")
        if not request.destination:
            raise ValidationException("Provider request requires destination.")
        if not request.channel:
            raise ValidationException("Provider request requires channel.")

        mobile = self.normalize_destination(request.destination)
        headers = self.build_headers()
        payload = self.build_payload(request=request, mobile=mobile)

        self.lifecycle.transition_to(ProviderLifecycleStatus.SENDING)
        self._audit(
            AuditEvent.PROVIDER_SEND_STARTED,
            {
                "provider_name": self.provider_name,
                "destination_present": True,
                "channel": request.channel,
                "challenge_id": (request.metadata or {}).get("challenge_id"),
            },
        )
        self._audit(
            AuditEvent.TRANSPORT_STARTED,
            {"provider_name": self.provider_name},
        )

        try:
            transport_result = self.transport.post_json(
                url=self.configuration.msg91_base_url,
                headers=headers,
                payload=payload,
                timeout_seconds=float(self.configuration.msg91_timeout_seconds),
            )
        except Exception as exc:  # noqa: BLE001 - translated immediately below
            if self.lifecycle.status == ProviderLifecycleStatus.SENDING:
                if isinstance(exc, TransportTimeoutError):
                    self.lifecycle.transition_to(ProviderLifecycleStatus.TIMEOUT)
                else:
                    self.lifecycle.transition_to(ProviderLifecycleStatus.FAILED)
                self.lifecycle.transition_to(ProviderLifecycleStatus.READY)
            self._translate_transport_error(exc)
            raise  # pragma: no cover

        self._audit(
            AuditEvent.TRANSPORT_COMPLETED,
            {
                "provider_name": self.provider_name,
                "status_code": transport_result.status_code,
            },
        )

        try:
            result = self.parse_response(transport_result)
        except InvalidProviderResponseException:
            self.lifecycle.transition_to(ProviderLifecycleStatus.FAILED)
            self.lifecycle.transition_to(ProviderLifecycleStatus.READY)
            self._audit(
                AuditEvent.PROVIDER_SEND_FAILURE,
                {"provider_name": self.provider_name},
            )
            raise

        if self.configuration.provider_metrics_enabled:
            self.metrics.record(
                success=result.status == ProviderResultStatus.SUCCESS,
                failure=result.status != ProviderResultStatus.SUCCESS,
                duration_ms=0.0,
                available=True,
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
        raise ProviderFailureException(result.provider_message)
