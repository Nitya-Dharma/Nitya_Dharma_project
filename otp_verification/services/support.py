"""Support services for audit hooks and deferred registration context."""

from __future__ import annotations

import logging
from typing import Mapping

from otp_verification.interfaces import BaseAuditLogger
from otp_verification.logging.contracts import AuditEventPayload, LoggingBackend

logger = logging.getLogger("otp_verification.audit")


class NullLoggingBackend(LoggingBackend):
    """No-op audit backend used when no external sink is configured."""

    def emit(self, payload: AuditEventPayload) -> None:
        return None


class StructuredLoggingBackend(LoggingBackend):
    """Writes secret-free audit events to the standard logging framework."""

    def emit(self, payload: AuditEventPayload) -> None:
        # Intentionally omits any OTP plaintext/hash fields.
        logger.info("otp_audit event=%s metadata=%s", payload.event, dict(payload.metadata))


class AuditLogger(BaseAuditLogger):
    """Internal audit hook service for OTP engine events."""

    def __init__(self, *, backend: LoggingBackend | None = None) -> None:
        self.backend = backend or NullLoggingBackend()

    def record(self, *, event: str, payload: Mapping[str, object]) -> None:
        """Record an OTP audit event through the configured backend."""

        safe_payload = {
            key: value
            for key, value in payload.items()
            if key not in {"otp_code", "otp", "otp_hash", "hash", "plaintext_otp"}
        }
        self.backend.emit(AuditEventPayload(event=event, metadata=safe_payload))


class RegistrationContextBuilder:
    """Build secret-free registration context for OTP challenges."""

    def __init__(self, *, adapters=None) -> None:
        self.adapters = adapters or {}

    def build(self, *, flow_type: str, payload: Mapping[str, object]) -> Mapping[str, object]:
        from otp_verification import constants
        from otp_verification.validators import validate_enabled_flow

        validated_flow = validate_enabled_flow(flow_type)
        safe: dict[str, object] = {
            constants.CONTEXT_FLOW_TYPE: validated_flow,
            constants.CONTEXT_REGISTRATION_CONTEXT: True,
        }
        for key, value in (payload or {}).items():
            if key in {"otp", "otp_code", "otp_hash", "plaintext_otp", "password", "message"}:
                continue
            safe[key] = value
        adapter = self.adapters.get(validated_flow)
        if adapter is not None:
            extra = adapter.build_context(payload=payload)
            for key, value in dict(extra).items():
                if key in {"otp", "otp_code", "otp_hash", "plaintext_otp", "password", "message"}:
                    continue
                safe[key] = value
        return safe
