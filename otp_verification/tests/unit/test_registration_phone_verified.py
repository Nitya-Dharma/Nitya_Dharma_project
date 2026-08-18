"""Unit tests for otp.registration.phone_verified (Phase 3 Task 2 Part C)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.test import RequestFactory, SimpleTestCase, override_settings

from otp_verification import constants
from otp_verification.config import OTPConfiguration
from otp_verification.enums import SimulationMode
from otp_verification.registration.factory import build_registration_otp_service
from otp_verification.registration.responses import (
    ERROR_EXPIRED_CHALLENGE,
    ERROR_LOCKED_CHALLENGE,
    ERROR_OTP_FAILED,
    ERROR_OWNERSHIP,
)
from otp_verification.registration.session import (
    PHONE_CHALLENGE_SESSION_KEY,
    PHONE_VERIFIED_SESSION_KEY,
    clear_phone_verified,
    get_phone_challenge,
    get_phone_verified,
    store_phone_challenge,
    store_phone_verified,
)
from otp_verification.registration.views import verify_registration_otp
from otp_verification.security.contracts import ReplayProtection
from otp_verification.services.factory import (
    build_otp_engine,
    build_otp_provider_runtime,
    reset_otp_process_storage,
)
from otp_verification.services.support import AuditLogger, NullLoggingBackend
from otp_verification.storage.memory import InMemoryChallengeRepository


def _config(**overrides) -> OTPConfiguration:
    base = dict(
        enabled=True,
        mode="mock",
        provider=constants.PROVIDER_MOCK_SMS,
        enabled_flows=constants.FLOW_CHOICES,
        otp_expiry_seconds=600,
        resend_cooldown_seconds=60,
        otp_length=6,
        max_attempts=3,
        max_resends=3,
        provider_enabled=True,
        mock_simulation_mode=SimulationMode.SUCCESS.value,
        mock_execution_delay_ms=0,
        mock_allow_random=False,
        provider_audit_enabled=True,
        provider_metrics_enabled=True,
        registration_pending_ttl_seconds=900,
        registration_completed_ttl_seconds=1800,
    )
    base.update(overrides)
    return OTPConfiguration(**base)


def _json(response):
    return json.loads(response.content.decode("utf-8"))


@override_settings(
    SECRET_KEY="test-secret-key-for-phone-verified",
    OTP_CHALLENGE_STORAGE="memory",
    OTP_ENABLED=True,
    OTP_PROVIDER=constants.PROVIDER_MOCK_SMS,
    OTP_REGISTRATION_PENDING_TTL_SECONDS=900,
)
class PhoneVerifiedSessionTests(SimpleTestCase):
    def setUp(self):
        reset_otp_process_storage()
        self.factory = RequestFactory()
        self.config = _config()
        self.engine = build_otp_engine(
            configuration=self.config,
            repository=InMemoryChallengeRepository(),
            replay_protector=ReplayProtection(),
            audit_logger=AuditLogger(backend=NullLoggingBackend()),
        )
        self.runtime = build_otp_provider_runtime(
            configuration=self.config,
            engine=self.engine,
        )
        self.service = build_registration_otp_service(
            runtime=self.runtime,
            configuration=self.config,
        )

    def tearDown(self):
        reset_otp_process_storage()

    def _issue(self):
        return self.runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_USER_REGISTRATION,
            context={},
        )

    def _prepare_verify(self, *, challenge_id: str, otp: str):
        request = self.factory.post(
            "/otp/registration/verify/",
            data={"challenge_id": challenge_id, "otp": otp},
        )
        request.session = SessionStore()
        request.META["HTTP_ACCEPT"] = "application/json"
        return request

    def _seed_phone_challenge(self, request, *, challenge_id: str, destination="9876543210"):
        store_phone_challenge(
            request,
            challenge_id=challenge_id,
            flow_type=constants.FLOW_USER_REGISTRATION,
            destination=destination,
        )

    def test_successful_verification_creates_phone_verified(self):
        issued = self._issue()
        request = self._prepare_verify(challenge_id=issued.challenge.id, otp=issued.otp_code)
        self._seed_phone_challenge(request, challenge_id=issued.challenge.id)
        with patch(
            "otp_verification.registration.views.build_registration_otp_service",
            return_value=self.service,
        ):
            response = verify_registration_otp(request)
        self.assertEqual(response.status_code, 200)
        body = _json(response)
        self.assertEqual(body["status"], "success")
        self.assertTrue((body.get("result") or {}).get("phone_verified"))
        verified = get_phone_verified(request)
        self.assertIsNotNone(verified)
        self.assertEqual(verified["challenge_id"], issued.challenge.id)
        self.assertEqual(verified["destination"], "9876543210")
        self.assertEqual(verified["flow_type"], constants.FLOW_USER_REGISTRATION)
        self.assertIn("verified_at", verified)
        self.assertIn("expires_at", verified)
        self.assertNotIn("password", verified)
        self.assertNotIn("email", verified)
        self.assertNotIn("payload", verified)
        self.assertNotIn("otp", verified)
        self.assertNotIn("otp_hash", verified)
        # phone_challenge retained with separate role
        self.assertIsNotNone(get_phone_challenge(request))

    def test_session_contents_only_allowed_fields(self):
        request = self.factory.get("/")
        request.session = SessionStore()
        store_phone_verified(
            request,
            challenge_id="c-1",
            destination="9876543210",
            flow_type=constants.FLOW_USER_REGISTRATION,
        )
        data = request.session[PHONE_VERIFIED_SESSION_KEY]
        self.assertEqual(
            set(data.keys()),
            {"challenge_id", "destination", "flow_type", "verified_at", "expires_at"},
        )

    def test_wrong_otp_does_not_create_phone_verified(self):
        issued = self._issue()
        request = self._prepare_verify(challenge_id=issued.challenge.id, otp="000000")
        self._seed_phone_challenge(request, challenge_id=issued.challenge.id)
        with patch(
            "otp_verification.registration.views.build_registration_otp_service",
            return_value=self.service,
        ):
            response = verify_registration_otp(request)
        body = _json(response)
        self.assertEqual(body["status"], "error")
        self.assertIn(body["error"], {ERROR_OTP_FAILED, "otp_verification_failed"})
        self.assertIsNone(get_phone_verified(request, enforce_ttl=False))
        self.assertIsNotNone(get_phone_challenge(request))

    def test_expired_otp_does_not_create_phone_verified(self):
        issued = self._issue()
        record = self.runtime.engine.challenge_manager.repository.get_by_id(
            issued.challenge.id
        )
        expired_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        updated = record.copy_with(expires_at=expired_at, updated_at=expired_at)
        self.runtime.engine.challenge_manager.repository.update(
            issued.challenge.id, payload={"record": updated}
        )
        request = self._prepare_verify(challenge_id=issued.challenge.id, otp=issued.otp_code)
        self._seed_phone_challenge(request, challenge_id=issued.challenge.id)
        with patch(
            "otp_verification.registration.views.build_registration_otp_service",
            return_value=self.service,
        ):
            response = verify_registration_otp(request)
        body = _json(response)
        self.assertEqual(body["error"], ERROR_EXPIRED_CHALLENGE)
        self.assertIsNone(get_phone_verified(request, enforce_ttl=False))

    def test_locked_otp_does_not_create_phone_verified(self):
        issued = self._issue()
        for _ in range(3):
            try:
                self.service.verify_challenge(
                    challenge_id=issued.challenge.id,
                    submitted_otp="000000",
                )
            except Exception:
                pass
        request = self._prepare_verify(challenge_id=issued.challenge.id, otp="000000")
        self._seed_phone_challenge(request, challenge_id=issued.challenge.id)
        with patch(
            "otp_verification.registration.views.build_registration_otp_service",
            return_value=self.service,
        ):
            response = verify_registration_otp(request)
        body = _json(response)
        self.assertEqual(body["error"], ERROR_LOCKED_CHALLENGE)
        self.assertIsNone(get_phone_verified(request, enforce_ttl=False))

    def test_ownership_failure_does_not_create_phone_verified(self):
        issued = self._issue()
        request = self._prepare_verify(challenge_id="forged", otp=issued.otp_code)
        self._seed_phone_challenge(request, challenge_id=issued.challenge.id)
        with patch(
            "otp_verification.registration.views.build_registration_otp_service",
            return_value=self.service,
        ):
            response = verify_registration_otp(request)
        body = _json(response)
        self.assertEqual(body["error"], ERROR_OWNERSHIP)
        self.assertIsNone(get_phone_verified(request, enforce_ttl=False))

    def test_expiry_clears_phone_verified(self):
        request = self.factory.get("/")
        request.session = SessionStore()
        store_phone_verified(
            request,
            challenge_id="c-exp",
            destination="9876543210",
            flow_type=constants.FLOW_USER_REGISTRATION,
        )
        data = request.session[PHONE_VERIFIED_SESSION_KEY]
        data["expires_at"] = (
            datetime.now(timezone.utc) - timedelta(seconds=1)
        ).isoformat()
        request.session[PHONE_VERIFIED_SESSION_KEY] = data
        self.assertIsNone(get_phone_verified(request, enforce_ttl=True))
        self.assertNotIn(PHONE_VERIFIED_SESSION_KEY, request.session)

    def test_cleanup_helper_clears_phone_verified(self):
        request = self.factory.get("/")
        request.session = SessionStore()
        store_phone_verified(
            request,
            challenge_id="c-clear",
            destination="9876543210",
            flow_type=constants.FLOW_USER_REGISTRATION,
        )
        clear_phone_verified(request)
        self.assertIsNone(get_phone_verified(request, enforce_ttl=False))

    def test_new_phone_challenge_clears_prior_phone_verified(self):
        request = self.factory.get("/")
        request.session = SessionStore()
        store_phone_verified(
            request,
            challenge_id="old",
            destination="9876543210",
            flow_type=constants.FLOW_USER_REGISTRATION,
        )
        store_phone_challenge(
            request,
            challenge_id="new",
            flow_type=constants.FLOW_USER_REGISTRATION,
            destination="9876543210",
        )
        self.assertIsNone(get_phone_verified(request, enforce_ttl=False))
        self.assertIn(PHONE_CHALLENGE_SESSION_KEY, request.session)
