"""Unit tests for the internal OTP engine (Phase 2 Task 2)."""

from __future__ import annotations

from datetime import timedelta

from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from otp_verification.config import OTPConfiguration
from otp_verification.domain.lifecycle import ChallengeLifecycle
from otp_verification.enums import ChallengeStatus
from otp_verification.exceptions import (
    ChallengeExpiredException,
    ChallengeLockedException,
    InvalidOTPException,
    ReplayAttackException,
    ValidationException,
)
from otp_verification.security.contracts import ReplayProtection
from otp_verification.services.factory import build_otp_engine, reset_otp_process_storage
from otp_verification.services.support import AuditLogger, NullLoggingBackend
from otp_verification.storage.memory import InMemoryChallengeRepository


def _config(**overrides) -> OTPConfiguration:
    base = dict(
        enabled=True,
        mode="mock",
        provider="mock_sms",
        enabled_flows=("user_registration",),
        otp_expiry_seconds=600,
        resend_cooldown_seconds=30,
        otp_length=6,
        max_attempts=3,
        max_resends=3,
    )
    base.update(overrides)
    return OTPConfiguration(**base)


@override_settings(SECRET_KEY="test-secret-key-for-otp-engine")
class OTPEngineTests(SimpleTestCase):
    def setUp(self):
        reset_otp_process_storage()
        self.engine = build_otp_engine(
            configuration=_config(),
            repository=InMemoryChallengeRepository(),
            replay_protector=ReplayProtection(),
            audit_logger=AuditLogger(backend=NullLoggingBackend()),
        )
        self.manager = self.engine.challenge_manager

    def test_generate_numeric_otp_from_configuration_length(self):
        code = self.engine.generator.generate(length=6)
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())

    def test_hash_never_equals_plaintext_and_verifies_securely(self):
        code = "123456"
        hashed = self.engine.hasher.hash_value(code)
        self.assertNotEqual(hashed, code)
        self.assertIn("$", hashed)
        self.assertTrue(self.engine.hasher.verify_value(code, hashed))
        self.assertFalse(self.engine.hasher.verify_value("000000", hashed))

    def test_create_challenge_stores_hash_not_plaintext(self):
        result = self.manager.create_challenge(
            flow_type="user_registration",
            context={"canonical_phone": "+919999999999"},
        )
        self.assertEqual(result.challenge.status, ChallengeStatus.VERIFY_PENDING)
        self.assertEqual(len(result.otp_code), 6)
        stored = self.engine.repository.get_by_id(result.challenge.id)
        self.assertNotEqual(stored.otp_hash, result.otp_code)
        self.assertNotIn(result.otp_code, stored.otp_hash)
        self.assertFalse(hasattr(result.challenge, "otp_hash"))

    def test_verify_success_transitions_to_verified(self):
        issued = self.manager.create_challenge(
            flow_type="user_registration",
            context={},
        )
        verified = self.manager.verify_challenge(
            challenge_id=issued.challenge.id,
            submitted_otp=issued.otp_code,
        )
        self.assertEqual(verified.status, ChallengeStatus.VERIFIED)

    def test_invalid_otp_increments_attempts(self):
        issued = self.manager.create_challenge(flow_type="user_registration", context={})
        with self.assertRaises(InvalidOTPException):
            self.manager.verify_challenge(
                challenge_id=issued.challenge.id,
                submitted_otp="000000",
            )
        stored = self.engine.repository.get_by_id(issued.challenge.id)
        self.assertEqual(stored.attempt_count, 1)
        self.assertEqual(stored.status, ChallengeStatus.VERIFY_PENDING)

    def test_max_attempts_locks_challenge(self):
        issued = self.manager.create_challenge(flow_type="user_registration", context={})
        for _ in range(2):
            with self.assertRaises(InvalidOTPException):
                self.manager.verify_challenge(
                    challenge_id=issued.challenge.id,
                    submitted_otp="000000",
                )
        with self.assertRaises(ChallengeLockedException):
            self.manager.verify_challenge(
                challenge_id=issued.challenge.id,
                submitted_otp="000000",
            )
        stored = self.engine.repository.get_by_id(issued.challenge.id)
        self.assertEqual(stored.status, ChallengeStatus.LOCKED)
        self.assertEqual(stored.attempt_count, 3)

    def test_replay_after_verified_is_blocked(self):
        issued = self.manager.create_challenge(flow_type="user_registration", context={})
        self.manager.verify_challenge(
            challenge_id=issued.challenge.id,
            submitted_otp=issued.otp_code,
        )
        with self.assertRaises(ReplayAttackException):
            self.manager.verify_challenge(
                challenge_id=issued.challenge.id,
                submitted_otp=issued.otp_code,
            )

    def test_expired_challenge_cannot_verify(self):
        issued = self.manager.create_challenge(flow_type="user_registration", context={})
        stored = self.engine.repository.get_by_id(issued.challenge.id)
        expired = stored.copy_with(expires_at=timezone.now() - timedelta(seconds=1))
        self.engine.repository.update(stored.id, payload={"record": expired})
        with self.assertRaises(ChallengeExpiredException):
            self.manager.verify_challenge(
                challenge_id=issued.challenge.id,
                submitted_otp=issued.otp_code,
            )
        refreshed = self.engine.repository.get_by_id(issued.challenge.id)
        self.assertEqual(refreshed.status, ChallengeStatus.EXPIRED)

    def test_invalid_lifecycle_transition_rejected(self):
        with self.assertRaises(ValidationException):
            ChallengeLifecycle.assert_transition(
                ChallengeStatus.EXPIRED,
                ChallengeStatus.VERIFIED,
            )
