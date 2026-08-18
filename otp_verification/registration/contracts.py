"""Registration-safe DTOs for the Registration OTP Service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping


@dataclass(frozen=True)
class RegistrationOTPIssueRequest:
    """Inbound request from a registration module (no provider knowledge)."""

    flow_type: str
    destination: str
    context: Mapping[str, object] | None = None


@dataclass(frozen=True)
class RegistrationOTPIssueResult:
    """Registration-safe issue response (never contains OTP or provider payloads)."""

    challenge_id: str
    flow_type: str
    status: str
    expires_at: datetime
    attempt_count: int
    max_attempts: int


@dataclass(frozen=True)
class RegistrationOTPVerifyRequest:
    """Inbound verification request from a registration module."""

    challenge_id: str
    submitted_otp: str


@dataclass(frozen=True)
class RegistrationOTPVerifyResult:
    """Registration-safe verification response."""

    challenge_id: str
    flow_type: str
    status: str
    verified_at: datetime | None
    expires_at: datetime


@dataclass(frozen=True)
class RegistrationOTPStatusResult:
    """Registration-safe challenge status snapshot."""

    challenge_id: str
    flow_type: str
    status: str
    expires_at: datetime
    attempt_count: int
    max_attempts: int
    verified_at: datetime | None = None


@dataclass(frozen=True)
class RegistrationOTPResendResult:
    """Registration-safe resend response (no OTP / provider payloads)."""

    challenge_id: str
    flow_type: str
    status: str
    expires_at: datetime
    resend_count: int
    remaining_attempts: int
    cooldown_seconds: int
