"""Security service implementations for the internal OTP engine."""

from __future__ import annotations

from threading import RLock
from typing import Mapping

from otp_verification.exceptions import ReplayAttackException, SecurityException
from otp_verification.interfaces.security import BaseReplayProtector


class ReplayProtection(BaseReplayProtector):
    """Prevents reuse of verified or otherwise consumed challenge identifiers."""

    def __init__(self) -> None:
        self._consumed_tokens: set[str] = set()
        self._lock = RLock()

    def assert_not_replayed(self, *, token: str) -> None:
        """Raise when a challenge/token identifier has already been consumed."""

        if not token:
            raise SecurityException("Replay protection requires a token.")
        with self._lock:
            if token in self._consumed_tokens:
                raise ReplayAttackException("OTP challenge replay blocked.")

    def mark_consumed(self, *, token: str) -> None:
        """Mark a challenge/token as consumed after successful verification."""

        if not token:
            raise SecurityException("Cannot mark an empty token as consumed.")
        with self._lock:
            self._consumed_tokens.add(token)

    def clear(self) -> None:
        """Clear consumed tokens (intended for tests)."""

        with self._lock:
            self._consumed_tokens.clear()


class ContextBinder:
    """Request-to-flow binding remains deferred."""

    def bind(self, *, context: Mapping[str, object]) -> Mapping[str, object]:
        raise NotImplementedError("Context binding is implemented in a later OTP phase.")


class SignatureService:
    """Token signing remains deferred."""

    def sign(self, payload: Mapping[str, object]) -> str:
        raise NotImplementedError("Signature generation is implemented in a later OTP phase.")

    def verify(self, token: str) -> Mapping[str, object]:
        raise NotImplementedError("Signature verification is implemented in a later OTP phase.")


class RequestFingerprinting:
    """Request fingerprinting remains deferred."""

    def build(self, *, request_meta: Mapping[str, object]) -> str:
        raise NotImplementedError(
            "Request fingerprinting is implemented in a later OTP phase."
        )


class SecurityPolicyValidator:
    """Additional security policy validation remains deferred."""

    def validate(self, *, context: Mapping[str, object]) -> None:
        raise NotImplementedError("Security policy validation is implemented later.")
