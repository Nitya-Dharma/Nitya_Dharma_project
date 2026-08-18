"""Hardening tests for registration OTP session, verify security, and flags."""

from __future__ import annotations

from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.test import RequestFactory, SimpleTestCase, override_settings

from otp_verification import constants
from otp_verification.config import OTPConfiguration
from otp_verification.enums import SimulationMode
from otp_verification.registration.exceptions import RegistrationOTPInvalid
from otp_verification.registration.factory import (
    build_registration_otp_service,
    is_registration_otp_required,
)
from otp_verification.registration.session import (
    clear_pending_registration,
    get_completed_registration,
    get_pending_registration,
    is_registration_otp_verified,
    mark_registration_completed,
    mark_registration_otp_verified,
    minimize_registration_payload,
    store_pending_registration,
)
from otp_verification.registration.views import verify_registration_otp
from otp_verification.security.contracts import ReplayProtection
from otp_verification.services.factory import (
    build_otp_engine,
    build_otp_provider_runtime,
    reset_otp_process_storage,
)
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
        max_attempts=5,
        max_resends=3,
        provider_enabled=True,
        mock_simulation_mode=SimulationMode.SUCCESS.value,
        mock_execution_delay_ms=0,
        mock_allow_random=False,
        provider_audit_enabled=True,
        provider_metrics_enabled=True,
    )
    base.update(overrides)
    return OTPConfiguration(**base)


def _prepare_request(factory: RequestFactory, method="get", path="/otp/registration/verify/", data=None):
    if method == "post":
        request = factory.post(path, data=data or {})
    else:
        request = factory.get(path)
    # Signed-cookie session avoids DB access in SimpleTestCase.
    request.session = SessionStore()
    request._messages = FallbackStorage(request)
    return request


@override_settings(SECRET_KEY="test-secret-key-for-registration-hardening")
class RegistrationOTPHardeningTests(SimpleTestCase):
    def setUp(self):
        reset_otp_process_storage()
        self.factory = RequestFactory()

    def test_minimize_payload_strips_disallowed_and_caps_size(self):
        payload = minimize_registration_payload(
            flow_type=constants.FLOW_EXPERT_REGISTRATION,
            payload={
                "name": "Expert",
                "email": "e@example.com",
                "password": "Secret123!",
                "phone": "9876543210",
                "description": "x" * 2000,
                "service_slugs": [
                    "PALMISTRY",
                    "astrology",
                    "numerology",
                    "ignored-fourth",
                ],
                "social_links": ["https://a.com"] * 10,
                "uploaded_file": "blob",
            },
        )
        self.assertNotIn("password", payload)
        self.assertIn("password_hash", payload)
        self.assertNotIn("uploaded_file", payload)
        self.assertEqual(len(payload["description"]), 500)
        self.assertEqual(len(payload["social_links"]), 5)
        self.assertEqual(
            payload["service_slugs"],
            ["palmistry", "astrology", "numerology"],
        )

    def test_bureau_payload_excludes_extra_keys(self):
        payload = minimize_registration_payload(
            flow_type=constants.FLOW_BUREAU_REGISTRATION,
            payload={
                "bureau_name": "Test Bureau",
                "email": "b@example.com",
                "password": "Secret123!",
                "phone_number": "9876543210",
                "address": "Addr",
                "city": "City",
                "whatsapp_number": "9876543210",
                "certificate": "bigfile",
                "biography": "long text",
            },
        )
        self.assertNotIn("certificate", payload)
        self.assertNotIn("biography", payload)
        self.assertIn("password_hash", payload)

    @override_settings(OTP_ENABLED=False)
    def test_feature_flag_off_skips_otp_requirement(self):
        self.assertFalse(is_registration_otp_required(constants.FLOW_BUREAU_REGISTRATION))

    def test_challenge_mismatch_clears_pending(self):
        request = _prepare_request(
            self.factory,
            method="post",
            data={"challenge_id": "forged", "otp": "123456"},
        )
        store_pending_registration(
            request,
            flow_type=constants.FLOW_USER_REGISTRATION,
            challenge_id="real-challenge",
            destination="9876543210",
            payload={"email": "u@example.com", "password": "Secret123!"},
            resume_path="/accounts/register/",
        )
        response = verify_registration_otp(request)
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(get_pending_registration(request))

    def test_wrong_otp_keeps_pending_via_service(self):
        config = _config()
        engine = build_otp_engine(
            configuration=config,
            repository=InMemoryChallengeRepository(),
            replay_protector=ReplayProtection(),
        )
        runtime = build_otp_provider_runtime(configuration=config, engine=engine)
        issued = runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_USER_REGISTRATION,
            context={},
        )
        request = _prepare_request(self.factory)
        store_pending_registration(
            request,
            flow_type=constants.FLOW_USER_REGISTRATION,
            challenge_id=issued.challenge.id,
            destination="9876543210",
            payload={"email": "u2@example.com", "password": "Secret123!"},
            resume_path="/accounts/register/",
        )
        service = build_registration_otp_service(runtime=runtime)
        with self.assertRaises(RegistrationOTPInvalid):
            service.verify_challenge(challenge_id=issued.challenge.id, submitted_otp="000000")
        self.assertIsNotNone(get_pending_registration(request))

    def test_idempotent_completed_marker(self):
        request = _prepare_request(
            self.factory,
            method="post",
            data={"challenge_id": "done-1", "otp": "ignored"},
        )
        mark_registration_completed(
            request,
            challenge_id="done-1",
            flow_type=constants.FLOW_USER_REGISTRATION,
            result={
                "flow_type": constants.FLOW_USER_REGISTRATION,
                "user_id": 1,
                "email": "a@b.c",
            },
        )
        clear_pending_registration(request)
        response = verify_registration_otp(request)
        self.assertIn(response.status_code, {200, 302})
        completed = get_completed_registration(request)
        self.assertEqual(completed["challenge_id"], "done-1")

    def test_verified_marker_matches_challenge(self):
        request = _prepare_request(self.factory)
        mark_registration_otp_verified(
            request,
            challenge_id="c1",
            flow_type=constants.FLOW_BUREAU_REGISTRATION,
        )
        self.assertTrue(
            is_registration_otp_verified(
                request,
                flow_type=constants.FLOW_BUREAU_REGISTRATION,
                challenge_id="c1",
            )
        )
        self.assertFalse(
            is_registration_otp_verified(
                request,
                flow_type=constants.FLOW_BUREAU_REGISTRATION,
                challenge_id="other",
            )
        )

    def test_store_pending_does_not_keep_plaintext_password(self):
        request = _prepare_request(self.factory)
        store_pending_registration(
            request,
            flow_type=constants.FLOW_USER_REGISTRATION,
            challenge_id="c-store",
            destination="9876543210",
            payload={"email": "x@example.com", "password": "PlainSecret!"},
            resume_path="/accounts/register/",
        )
        pending = get_pending_registration(request)
        self.assertNotIn("password", pending["payload"])
        self.assertIn("password_hash", pending["payload"])
        self.assertNotEqual(pending["payload"]["password_hash"], "PlainSecret!")
