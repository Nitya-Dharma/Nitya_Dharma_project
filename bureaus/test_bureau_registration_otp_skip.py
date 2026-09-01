"""Bureau registration OTP skip / non-blocking tests."""

from __future__ import annotations

import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.core.cache import cache
from django.http import HttpResponse
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

from bureaus.models import BureauProfile
from bureaus.views import bureau_register_skip_phone_otp
from otp_verification import constants
from otp_verification.config import OTPConfiguration
from otp_verification.enums import SimulationMode
from otp_verification.registration.factory import build_registration_otp_service
from otp_verification.registration.session import (
    get_pending_registration,
    store_pending_registration,
)
from otp_verification.registration.views import verify_registration_otp
from otp_verification.services.factory import (
    build_otp_engine,
    build_otp_provider_runtime,
    reset_otp_process_storage,
)
from otp_verification.storage.memory import InMemoryChallengeRepository

User = get_user_model()
LOCMEM_EMAIL = "django.core.mail.backends.locmem.EmailBackend"


def _otp_config(**overrides):
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
        registration_pending_ttl_seconds=900,
        registration_completed_ttl_seconds=1800,
    )
    base.update(overrides)
    return OTPConfiguration(**base)


def _prepare_request(factory, *, method="post", path="/", data=None):
    if method == "post":
        request = factory.post(path, data=data or {})
    else:
        request = factory.get(path)
    request.session = SessionStore()
    request._messages = FallbackStorage(request)
    return request


def _bureau_payload(*, email="bureau-skip@example.com", phone="9123456701"):
    return {
        "bureau_name": "Skip Test Bureau",
        "email": email,
        "password": "BureauTestPass123!",
        "confirm_password": "BureauTestPass123!",
        "phone_number": phone,
        "address": "1 Skip Road",
        "city": "Hyderabad",
        "whatsapp_number": "",
    }


def _bureau_raw_payload(*, email="bureau-skip@example.com", phone="9123456701"):
    return {
        "bureau_name": "Skip Test Bureau",
        "email": email,
        "password": "BureauTestPass123!",
        "phone_number": phone,
        "address": "1 Skip Road",
        "city": "Hyderabad",
        "whatsapp_number": "",
    }


def _store_bureau_pending(request, *, email="bureau-skip@example.com", phone="9123456701"):
    store_pending_registration(
        request,
        flow_type=constants.FLOW_BUREAU_REGISTRATION,
        challenge_id="pending-challenge",
        destination=phone,
        payload=_bureau_raw_payload(email=email, phone=phone),
        resume_path="/bureaus/register/",
    )
    return _bureau_raw_payload(email=email, phone=phone)


@override_settings(EMAIL_BACKEND=LOCMEM_EMAIL)
class BureauRegistrationOTPSkipTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.factory = RequestFactory()
        reset_otp_process_storage()
        config = _otp_config()
        engine = build_otp_engine(
            configuration=config,
            repository=InMemoryChallengeRepository(),
        )
        self.runtime = build_otp_provider_runtime(configuration=config, engine=engine)
        self.service = build_registration_otp_service(runtime=self.runtime)

    def _issue_bureau_challenge(self, *, phone="9123456701"):
        return self.runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_BUREAU_REGISTRATION,
            context={"resume_path": "/bureaus/register/"},
        )

    def _store_bureau_pending_with_challenge(
        self, request, *, email="bureau-skip@example.com", phone="9123456701"
    ):
        issued = self._issue_bureau_challenge(phone=phone)
        store_pending_registration(
            request,
            flow_type=constants.FLOW_BUREAU_REGISTRATION,
            challenge_id=issued.challenge.id,
            destination=phone,
            payload=_bureau_raw_payload(email=email, phone=phone),
            resume_path="/bureaus/register/",
        )
        return issued

    def test_skip_endpoint_completes_registration_without_verification(self):
        request = _prepare_request(
            self.factory,
            path=reverse("bureaus:bureau_register_skip_phone_otp"),
        )
        _store_bureau_pending(request, email="skip-endpoint@example.com")
        response = bureau_register_skip_phone_otp(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("bureaus:bureau_register"))
        user = User.objects.get(email="skip-endpoint@example.com")
        profile = BureauProfile.objects.get(user=user)
        self.assertFalse(user.is_phone_verified)
        self.assertFalse(profile.is_active)
        self.assertFalse(profile.is_approved)
        self.assertFalse(profile.is_email_verified)
        self.assertIsNone(get_pending_registration(request, enforce_ttl=False))

    def test_form_skip_bypasses_otp_gate_and_creates_once(self):
        register_url = reverse("bureaus:bureau_register")
        payload = {
            **_bureau_payload(email="form-skip@example.com", phone="9123456702"),
            "skip_phone_verification": "1",
        }
        with (
            patch(
                "otp_verification.registration.factory.is_registration_otp_required",
                return_value=True,
            ),
            patch(
                "otp_verification.registration.gate.begin_otp_or_continue",
                side_effect=AssertionError("OTP gate must not run when skipping"),
            ),
            patch(
                "otp_verification.registration.session.consume_phone_verified_session",
                return_value=None,
            ),
        ):
            response = self.client.post(register_url, payload)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(User.objects.filter(email__iexact=payload["email"]).count(), 1)
        self.assertEqual(BureauProfile.objects.filter(user__email=payload["email"]).count(), 1)
        user = User.objects.get(email__iexact=payload["email"])
        self.assertFalse(user.is_phone_verified)

    def test_otp_required_without_skip_still_calls_gate(self):
        register_url = reverse("bureaus:bureau_register")
        payload = _bureau_payload(email="gate-required@example.com", phone="9123456703")
        otp_response_content = b"otp-challenge"

        with (
            patch(
                "otp_verification.registration.factory.is_registration_otp_required",
                return_value=True,
            ),
            patch(
                "otp_verification.registration.gate.begin_otp_or_continue",
                return_value=HttpResponse(otp_response_content, status=202),
            ) as begin_otp,
        ):
            response = self.client.post(register_url, payload)

        self.assertEqual(response.status_code, 202)
        begin_otp.assert_called_once()
        self.assertFalse(User.objects.filter(email__iexact=payload["email"]).exists())

    def test_invalid_otp_does_not_create_user_and_skip_still_works(self):
        session_holder = _prepare_request(self.factory)
        issued = self._store_bureau_pending_with_challenge(
            session_holder,
            email="invalid-then-skip@example.com",
            phone="9123456704",
        )
        verify_request = _prepare_request(
            self.factory,
            path=reverse("otp_verification:verify_registration_otp"),
            data={"challenge_id": issued.challenge.id, "otp": "000000"},
        )
        verify_request.session = session_holder.session
        verify_request.META["HTTP_ACCEPT"] = "application/json"
        with patch(
            "otp_verification.registration.views.build_registration_otp_service",
            return_value=self.service,
        ):
            response = verify_registration_otp(verify_request)
        body = json.loads(response.content.decode("utf-8"))
        self.assertEqual(body["status"], "error")
        self.assertFalse(
            User.objects.filter(email="invalid-then-skip@example.com").exists()
        )

        skip_request = _prepare_request(
            self.factory,
            path=reverse("bureaus:bureau_register_skip_phone_otp"),
        )
        self._store_bureau_pending_with_challenge(
            skip_request,
            email="invalid-then-skip@example.com",
            phone="9123456704",
        )
        response = bureau_register_skip_phone_otp(skip_request)
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email="invalid-then-skip@example.com")
        self.assertFalse(user.is_phone_verified)

    def test_successful_otp_completion_still_creates_bureau(self):
        session_holder = _prepare_request(self.factory)
        issued = self._store_bureau_pending_with_challenge(
            session_holder,
            email="verified-otp@example.com",
            phone="9123456705",
        )
        request = _prepare_request(
            self.factory,
            path=reverse("otp_verification:verify_registration_otp"),
            data={"challenge_id": issued.challenge.id, "otp": issued.otp_code},
        )
        request.session = session_holder.session
        request.META["HTTP_ACCEPT"] = "application/json"
        with patch(
            "otp_verification.registration.views.build_registration_otp_service",
            return_value=self.service,
        ):
            response = verify_registration_otp(request)
        body = json.loads(response.content.decode("utf-8"))
        self.assertEqual(body["status"], "success")
        user = User.objects.get(email="verified-otp@example.com")
        profile = BureauProfile.objects.get(user=user)
        self.assertTrue(user.is_phone_verified)
        self.assertFalse(profile.is_active)
        self.assertFalse(profile.is_approved)

    def test_otp_verify_page_context_includes_bureau_skip_action(self):
        from otp_verification.registration.views import (
            _expert_skip_phone_verification_context,
        )

        ctx = _expert_skip_phone_verification_context(
            {"flow_type": constants.FLOW_BUREAU_REGISTRATION}
        )
        self.assertTrue(ctx["allow_skip_phone_verification"])
        self.assertEqual(
            ctx["skip_phone_verification_url"],
            reverse("bureaus:bureau_register_skip_phone_otp"),
        )
