"""Unit tests for durable Django challenge repository (Phase 2 Task 8)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta

from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from otp_verification.config import OTPConfiguration
from otp_verification.enums import ChallengeStatus
from otp_verification.exceptions import (
    ChallengeNotFoundException,
    ReplayAttackException,
    ValidationException,
)
from otp_verification.security.contracts import ReplayProtection
from otp_verification.services.factory import (
    build_otp_engine,
    reset_otp_process_storage,
    resolve_challenge_repository,
    resolve_replay_protector,
)
from otp_verification.services.support import AuditLogger, NullLoggingBackend
from otp_verification.storage.django_db import DjangoChallengeRepository
from otp_verification.storage.memory import InMemoryChallengeRepository
from otp_verification.storage.replay_db import DatabaseReplayProtection


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


@override_settings(
    SECRET_KEY="test-secret-key-for-otp-durable",
    OTP_CHALLENGE_STORAGE="database",
)
class DjangoChallengeRepositoryTests(TestCase):
    def setUp(self):
        reset_otp_process_storage()
        self.repo = DjangoChallengeRepository()
        self.replay = DatabaseReplayProtection()
        self.engine = build_otp_engine(
            configuration=_config(),
            repository=self.repo,
            replay_protector=self.replay,
            audit_logger=AuditLogger(backend=NullLoggingBackend()),
        )
        self.manager = self.engine.challenge_manager

    def tearDown(self):
        reset_otp_process_storage()

    def test_create_get_update_persist(self):
        issued = self.manager.create_challenge(
            flow_type="user_registration",
            context={"canonical_phone": "919999999999"},
        )
        loaded = DjangoChallengeRepository().get_by_id(issued.challenge.id)
        self.assertEqual(loaded.status, ChallengeStatus.VERIFY_PENDING)
        self.assertEqual(loaded.context.get("canonical_phone"), "919999999999")
        self.assertNotEqual(loaded.otp_hash, issued.otp_code)

        verified = self.manager.verify_challenge(
            challenge_id=issued.challenge.id,
            submitted_otp=issued.otp_code,
        )
        self.assertEqual(verified.status, ChallengeStatus.VERIFIED)
        again = DjangoChallengeRepository().get_by_id(issued.challenge.id)
        self.assertEqual(again.status, ChallengeStatus.VERIFIED)
        self.assertIsNotNone(again.verified_at)

    def test_delete_not_found_and_duplicate_create(self):
        with self.assertRaises(ChallengeNotFoundException):
            self.repo.get_by_id("missing-challenge-id")

        issued = self.manager.create_challenge(flow_type="user_registration", context={})
        record = self.repo.get_by_id(issued.challenge.id)
        with self.assertRaises(ValidationException):
            self.repo.create(payload={"record": record})

    def test_expiration_persisted(self):
        issued = self.manager.create_challenge(flow_type="user_registration", context={})
        record = self.repo.get_by_id(issued.challenge.id)
        past = record.copy_with(expires_at=timezone.now() - timedelta(seconds=5))
        self.repo.update(record.id, payload={"record": past})
        view = self.manager.get_challenge(issued.challenge.id)
        self.assertEqual(view.status, ChallengeStatus.EXPIRED)
        self.assertEqual(
            DjangoChallengeRepository().get_by_id(issued.challenge.id).status,
            ChallengeStatus.EXPIRED,
        )

    def test_worker_restart_simulation_shared_db(self):
        """New engine instances (simulating other workers) see the same challenge."""

        issued = self.manager.create_challenge(flow_type="user_registration", context={})
        other = build_otp_engine(
            configuration=_config(),
            repository=DjangoChallengeRepository(),
            replay_protector=DatabaseReplayProtection(),
            audit_logger=AuditLogger(backend=NullLoggingBackend()),
        )
        verified = other.challenge_manager.verify_challenge(
            challenge_id=issued.challenge.id,
            submitted_otp=issued.otp_code,
        )
        self.assertEqual(verified.status, ChallengeStatus.VERIFIED)

        restarted = build_otp_engine(
            configuration=_config(),
            repository=DjangoChallengeRepository(),
            replay_protector=DatabaseReplayProtection(),
            audit_logger=AuditLogger(backend=NullLoggingBackend()),
        )
        with self.assertRaises(ReplayAttackException):
            restarted.challenge_manager.verify_challenge(
                challenge_id=issued.challenge.id,
                submitted_otp=issued.otp_code,
            )

    def test_replay_persists_across_protector_instances(self):
        issued = self.manager.create_challenge(flow_type="user_registration", context={})
        self.manager.verify_challenge(
            challenge_id=issued.challenge.id,
            submitted_otp=issued.otp_code,
        )
        other_replay = DatabaseReplayProtection()
        with self.assertRaises(ReplayAttackException):
            other_replay.assert_not_replayed(token=issued.challenge.id)

    def test_resend_style_new_challenge_persists(self):
        first = self.manager.create_challenge(flow_type="user_registration", context={})
        second = self.manager.create_challenge(flow_type="user_registration", context={})
        self.assertNotEqual(first.challenge.id, second.challenge.id)
        self.assertEqual(
            DjangoChallengeRepository().get_by_id(second.challenge.id).status,
            ChallengeStatus.VERIFY_PENDING,
        )

    def test_factory_resolves_database_backend(self):
        repo = resolve_challenge_repository()
        replay = resolve_replay_protector()
        self.assertIsInstance(repo, DjangoChallengeRepository)
        self.assertIsInstance(replay, DatabaseReplayProtection)


@override_settings(
    SECRET_KEY="test-secret-key-for-otp-durable-concurrency",
    OTP_CHALLENGE_STORAGE="database",
)
class DjangoChallengeConcurrencyTests(TransactionTestCase):
    """TransactionTestCase so threaded workers can see committed challenge rows."""

    def setUp(self):
        reset_otp_process_storage()

    def tearDown(self):
        reset_otp_process_storage()

    def test_concurrent_verify_only_one_succeeds(self):
        engine = build_otp_engine(
            configuration=_config(),
            repository=DjangoChallengeRepository(),
            replay_protector=DatabaseReplayProtection(),
            audit_logger=AuditLogger(backend=NullLoggingBackend()),
        )
        issued = engine.challenge_manager.create_challenge(
            flow_type="user_registration",
            context={},
        )
        otp = issued.otp_code
        challenge_id = issued.challenge.id

        def _verify():
            from django.db import connection

            try:
                worker = build_otp_engine(
                    configuration=_config(),
                    repository=DjangoChallengeRepository(),
                    replay_protector=DatabaseReplayProtection(),
                    audit_logger=AuditLogger(backend=NullLoggingBackend()),
                )
                return worker.challenge_manager.verify_challenge(
                    challenge_id=challenge_id,
                    submitted_otp=otp,
                )
            finally:
                connection.close()

        successes = 0
        failures = 0
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(_verify), pool.submit(_verify)]
            for fut in as_completed(futures):
                try:
                    result = fut.result()
                    if result.status == ChallengeStatus.VERIFIED:
                        successes += 1
                except Exception:
                    failures += 1

        self.assertEqual(successes, 1)
        self.assertEqual(failures, 1)
        self.assertEqual(
            DjangoChallengeRepository().get_by_id(challenge_id).status,
            ChallengeStatus.VERIFIED,
        )


@override_settings(
    SECRET_KEY="test-secret-key-for-otp-memory-flag",
    OTP_CHALLENGE_STORAGE="memory",
)
class MemoryStorageFlagTests(TestCase):
    def setUp(self):
        reset_otp_process_storage()

    def tearDown(self):
        reset_otp_process_storage()

    def test_factory_resolves_memory_backend(self):
        self.assertIsInstance(resolve_challenge_repository(), InMemoryChallengeRepository)
        self.assertIsInstance(resolve_replay_protector(), ReplayProtection)

    def test_memory_backend_still_verifies(self):
        engine = build_otp_engine(
            configuration=_config(),
            audit_logger=AuditLogger(backend=NullLoggingBackend()),
        )
        issued = engine.challenge_manager.create_challenge(
            flow_type="user_registration",
            context={},
        )
        verified = engine.challenge_manager.verify_challenge(
            challenge_id=issued.challenge.id,
            submitted_otp=issued.otp_code,
        )
        self.assertEqual(verified.status, ChallengeStatus.VERIFIED)
