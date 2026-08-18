"""Core OTP engine services: generation, hashing, validation, and orchestration."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Mapping

from django.conf import settings

from otp_verification.config import OTPConfiguration, get_configuration
from otp_verification.domain.challenge import (
    ChallengeIssueResult,
    ChallengeRecord,
    ChallengeView,
    to_challenge_view,
)
from otp_verification.domain.lifecycle import ChallengeLifecycle
from otp_verification.enums import AuditEvent, ChallengeStatus
from otp_verification.exceptions import (
    ChallengeExpiredException,
    ChallengeLockedException,
    ConfigurationException,
    InvalidOTPException,
    ReplayAttackException,
    SecurityException,
    ValidationException,
)
from otp_verification.interfaces import (
    BaseAttemptTracker,
    BaseAuditLogger,
    BaseChallengeManager,
    BaseChallengeRepository,
    BaseHasher,
    BaseOTPGenerator,
    BaseOTPValidator,
    BaseReplayProtector,
    BaseTokenManager,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OTPGenerator(BaseOTPGenerator):
    """Secure numeric OTP generator driven by configuration."""

    def __init__(self, *, configuration: OTPConfiguration | None = None) -> None:
        self.configuration = configuration

    def generate(self, *, length: int) -> str:
        """Return a numeric OTP with leading zeros preserved."""

        if length < 1:
            raise ConfigurationException("OTP length must be >= 1.")
        upper = 10**length
        value = secrets.randbelow(upper)
        return str(value).zfill(length)


class OTPHasher(BaseHasher):
    """HMAC-SHA256 OTP hasher using Django SECRET_KEY by default.

    Stored format: ``<salt>$<hex_digest>``. Plaintext OTP is never retained.
    """

    def __init__(self, *, secret_source=None) -> None:
        self.secret_source = secret_source

    def _secret_bytes(self) -> bytes:
        secret = self.secret_source
        if secret is None:
            secret = getattr(settings, "SECRET_KEY", None)
        if not secret:
            raise ConfigurationException("OTP hasher requires a secret source.")
        if isinstance(secret, bytes):
            return secret
        return str(secret).encode("utf-8")

    def hash_value(self, raw_value: str) -> str:
        """Hash an OTP immediately after generation."""

        if not raw_value:
            raise SecurityException("Cannot hash an empty OTP value.")
        salt = secrets.token_hex(16)
        digest = hmac.new(
            self._secret_bytes(),
            f"{salt}:{raw_value}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"{salt}${digest}"

    def verify_value(self, raw_value: str, hashed_value: str) -> bool:
        """Verify OTP against a stored hash using constant-time comparison."""

        try:
            salt, digest = hashed_value.split("$", 1)
        except (AttributeError, ValueError) as exc:
            raise SecurityException("Malformed OTP hash.") from exc
        expected = hmac.new(
            self._secret_bytes(),
            f"{salt}:{raw_value}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, digest)


class OTPValidator(BaseOTPValidator):
    """Compares submitted OTPs against stored hashes only."""

    def __init__(
        self,
        *,
        hasher: BaseHasher | None = None,
        repository: BaseChallengeRepository | None = None,
        attempt_tracker: BaseAttemptTracker | None = None,
    ) -> None:
        self.hasher = hasher
        self.repository = repository
        self.attempt_tracker = attempt_tracker

    def validate(self, *, submitted_otp: str, context: Mapping[str, object]) -> bool:
        """Return whether a submitted OTP matches the challenge hash."""

        if self.hasher is None:
            raise ConfigurationException("OTPValidator requires a hasher.")
        otp_hash = context.get("otp_hash")
        if not isinstance(otp_hash, str) or not otp_hash:
            raise ValidationException("OTP validation context requires otp_hash.")
        if not isinstance(submitted_otp, str) or not submitted_otp.strip():
            raise InvalidOTPException("OTP code is required.")
        return self.hasher.verify_value(submitted_otp.strip(), otp_hash)


class TokenManager(BaseTokenManager):
    """Verified-registration token service remains deferred to later phases."""

    def __init__(self, *, replay_protector=None, serializer=None) -> None:
        self.replay_protector = replay_protector
        self.serializer = serializer

    def issue(self, *, context: Mapping[str, object]) -> str:
        raise NotImplementedError("Token issuance is implemented in a later OTP phase.")

    def consume(self, token: str) -> Mapping[str, object]:
        raise NotImplementedError("Token consumption is implemented in a later OTP phase.")


class ChallengeManager(BaseChallengeManager):
    """Orchestrates OTP challenge creation, expiry, and verification."""

    def __init__(
        self,
        *,
        repository: BaseChallengeRepository | None = None,
        audit_logger: BaseAuditLogger | None = None,
        policies=None,
        generator: BaseOTPGenerator | None = None,
        hasher: BaseHasher | None = None,
        validator: BaseOTPValidator | None = None,
        attempt_tracker: BaseAttemptTracker | None = None,
        replay_protector: BaseReplayProtector | None = None,
        configuration: OTPConfiguration | None = None,
    ) -> None:
        self.repository = repository
        self.audit_logger = audit_logger
        self.policies = policies or ()
        self.generator = generator
        self.hasher = hasher
        self.validator = validator
        self.attempt_tracker = attempt_tracker
        self.replay_protector = replay_protector
        self.configuration = configuration

    def _config(self) -> OTPConfiguration:
        return self.configuration or get_configuration()

    def _require_dependencies(self) -> None:
        missing = [
            name
            for name, value in (
                ("repository", self.repository),
                ("generator", self.generator),
                ("hasher", self.hasher),
                ("validator", self.validator),
                ("attempt_tracker", self.attempt_tracker),
                ("replay_protector", self.replay_protector),
                ("audit_logger", self.audit_logger),
            )
            if value is None
        ]
        if missing:
            raise ConfigurationException(
                "ChallengeManager is missing dependencies: " + ", ".join(missing)
            )

    def _audit(self, event: str, payload: Mapping[str, object]) -> None:
        assert self.audit_logger is not None
        # Never include plaintext OTP or hash material in audit payloads.
        safe_payload = {
            key: value
            for key, value in payload.items()
            if key not in {"otp_code", "otp", "otp_hash", "hash"}
        }
        self.audit_logger.record(event=event, payload=safe_payload)

    def _persist(self, record: ChallengeRecord) -> ChallengeRecord:
        assert self.repository is not None
        return self.repository.update(record.id, payload={"record": record})

    def _transition(self, record: ChallengeRecord, next_status: str) -> ChallengeRecord:
        ChallengeLifecycle.assert_transition(record.status, next_status)
        updated = record.copy_with(status=next_status, updated_at=_utcnow())
        return self._persist(updated)

    def evaluate_expiry(self, record: ChallengeRecord) -> ChallengeRecord:
        """Expire an active challenge when its TTL has elapsed."""

        if record.status in {
            ChallengeStatus.EXPIRED,
            ChallengeStatus.VERIFIED,
            ChallengeStatus.LOCKED,
            ChallengeStatus.CONSUMED,
            ChallengeStatus.CANCELLED,
            ChallengeStatus.ARCHIVED,
        }:
            return record

        expires_at = record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at > _utcnow():
            return record

        expired = self._transition(record, ChallengeStatus.EXPIRED)
        self._audit(
            AuditEvent.CHALLENGE_EXPIRED,
            {"challenge_id": expired.id, "flow_type": expired.flow_type},
        )
        return expired

    def create_challenge(
        self, *, flow_type: str, context: Mapping[str, object]
    ) -> ChallengeIssueResult:
        """Create an active challenge with hashed OTP and calculated expiry.

        Returns a secret-free challenge view plus a transient ``otp_code`` for
        future provider handoff. The repository stores only the hash.
        """

        self._require_dependencies()
        assert self.repository is not None
        assert self.generator is not None
        assert self.hasher is not None

        if not flow_type:
            raise ValidationException("flow_type is required.")

        config = self._config()
        now = _utcnow()
        otp_code = self.generator.generate(length=config.otp_length)
        otp_hash = self.hasher.hash_value(otp_code)

        record = ChallengeRecord(
            id=str(uuid.uuid4()),
            flow_type=flow_type,
            status=ChallengeStatus.INITIATED,
            otp_hash=otp_hash,
            expires_at=now + timedelta(seconds=config.otp_expiry_seconds),
            max_attempts=config.max_attempts,
            attempt_count=0,
            context=dict(context or {}),
            created_at=now,
            updated_at=now,
        )
        created = self.repository.create(payload={"record": record})
        active = self._transition(created, ChallengeStatus.VERIFY_PENDING)
        self._audit(
            AuditEvent.CHALLENGE_CREATED,
            {
                "challenge_id": active.id,
                "flow_type": active.flow_type,
                "expires_at": active.expires_at.isoformat(),
            },
        )
        # otp_code is returned transiently and must never be logged.
        return ChallengeIssueResult(challenge=to_challenge_view(active), otp_code=otp_code)

    def get_challenge(self, challenge_id: str) -> ChallengeView:
        """Return a secret-free challenge view after applying expiry evaluation."""

        self._require_dependencies()
        assert self.repository is not None
        record = self.evaluate_expiry(self.repository.get_by_id(challenge_id))
        return to_challenge_view(record)

    def verify_challenge(self, *, challenge_id: str, submitted_otp: str) -> ChallengeView:
        """Verify a submitted OTP against an active challenge."""

        self._require_dependencies()
        assert self.repository is not None
        assert self.validator is not None
        assert self.attempt_tracker is not None
        assert self.replay_protector is not None

        record = self.evaluate_expiry(self.repository.get_by_id(challenge_id))

        if record.status == ChallengeStatus.EXPIRED:
            raise ChallengeExpiredException("OTP challenge has expired.")
        if record.status == ChallengeStatus.LOCKED:
            raise ChallengeLockedException("OTP challenge is locked.")
        if ChallengeLifecycle.is_replay_blocked(record.status):
            self.replay_protector.assert_not_replayed(token=record.id)
            raise ReplayAttackException("OTP challenge is no longer reusable.")
        if not ChallengeLifecycle.is_active(record.status):
            raise ValidationException(
                f"Challenge '{challenge_id}' is not active for verification."
            )

        # Challenge-level replay protection for already-verified identifiers.
        self.replay_protector.assert_not_replayed(token=record.id)

        matched = self.validator.validate(
            submitted_otp=submitted_otp,
            context={"otp_hash": record.otp_hash, "challenge_id": record.id},
        )

        if matched:
            self.attempt_tracker.record_attempt(challenge_id=record.id, successful=True)
            verified = self._transition(record, ChallengeStatus.VERIFIED)
            verified = verified.copy_with(verified_at=_utcnow(), updated_at=_utcnow())
            verified = self._persist(verified)
            if hasattr(self.replay_protector, "mark_consumed"):
                self.replay_protector.mark_consumed(token=verified.id)
            self._audit(
                AuditEvent.OTP_VERIFIED,
                {"challenge_id": verified.id, "flow_type": verified.flow_type},
            )
            return to_challenge_view(verified)

        self.attempt_tracker.record_attempt(challenge_id=record.id, successful=False)
        refreshed = self.repository.get_by_id(record.id)
        self._audit(
            AuditEvent.OTP_VERIFY_FAILED,
            {
                "challenge_id": refreshed.id,
                "flow_type": refreshed.flow_type,
                "attempt_count": refreshed.attempt_count,
            },
        )

        if refreshed.attempt_count >= refreshed.max_attempts:
            locked = self._transition(refreshed, ChallengeStatus.LOCKED)
            self._audit(
                AuditEvent.CHALLENGE_LOCKED,
                {
                    "challenge_id": locked.id,
                    "flow_type": locked.flow_type,
                    "attempt_count": locked.attempt_count,
                },
            )
            raise ChallengeLockedException("Maximum verification attempts exceeded.")

        raise InvalidOTPException("Invalid OTP code.")
