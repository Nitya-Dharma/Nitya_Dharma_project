"""Pandit registration OTP skip / non-blocking tests."""

from __future__ import annotations

import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.core.cache import cache
from django.http import HttpResponse
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import EmailVerificationToken
from accounts.views import pandit_register_skip_phone_otp
from otp_verification import constants
from otp_verification.config import OTPConfiguration
from otp_verification.enums import SimulationMode
from otp_verification.registration.factory import build_registration_otp_service
from otp_verification.registration.session import (
    get_pending_registration,
    store_pending_registration,
    store_phone_verified,
)
from otp_verification.registration.views import verify_registration_otp
from otp_verification.services.factory import (
    build_otp_engine,
    build_otp_provider_runtime,
    reset_otp_process_storage,
)
from otp_verification.storage.memory import InMemoryChallengeRepository
from profiles.models import PanditProfile
from referrals.models import ReferralLink, ReferralUsage

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


def _pandit_form_payload(*, email="pandit-skip@example.com", phone="9876543210"):
    return {
        "referral_code": "pandit-tok-001",
        "first_name": "Skip",
        "last_name": "Pandit",
        "email": email,
        "password": "securepass123",
        "phone_number": phone,
    }


def _pandit_raw_payload(
    *,
    email="pandit-skip@example.com",
    phone="9876543210",
    referral_link,
):
    return {
        "email": email,
        "password_hash": make_password("securepass123"),
        "first_name": "Skip",
        "last_name": "Pandit",
        "phone_number": phone,
        "referral_link_id": referral_link.id,
        "referral_code": referral_link.referral_code,
    }


@override_settings(EMAIL_BACKEND=LOCMEM_EMAIL)
class PanditRegistrationOTPSkipTests(TestCase):
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

        self.admin = User.objects.create_user(
            email="admin-pandit-skip@example.com",
            password="testpass123",
            role="admin",
            status="active",
            is_active=True,
        )
        self.referral_link = ReferralLink.objects.create(
            created_by=self.admin,
            token="pandit-tok-001",
            referral_code="pandit-tok-001",
            code="REFAPSKIP1",
            max_uses=5,
            used_count=0,
            is_active=True,
            status=ReferralLink.STATUS_ACTIVE,
            expires_at=timezone.now() + timedelta(days=7),
        )
        self.register_url = reverse(
            "accounts:pandit_register",
            kwargs={"referral_token": self.referral_link.token},
        )
        self.resume_path = self.register_url

    def _issue_pandit_challenge(self, *, phone="9876543210"):
        return self.runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_PANDIT_REGISTRATION,
            context={"resume_path": self.resume_path},
        )

    def _store_pandit_pending(
        self,
        request,
        *,
        email="pandit-skip@example.com",
        phone="9876543210",
        challenge_id="pending-challenge",
    ):
        store_pending_registration(
            request,
            flow_type=constants.FLOW_PANDIT_REGISTRATION,
            challenge_id=challenge_id,
            destination=phone,
            payload=_pandit_raw_payload(
                email=email,
                phone=phone,
                referral_link=self.referral_link,
            ),
            resume_path=self.resume_path,
        )

    def _store_pandit_pending_with_challenge(
        self,
        request,
        *,
        email="pandit-skip@example.com",
        phone="9876543210",
    ):
        issued = self._issue_pandit_challenge(phone=phone)
        self._store_pandit_pending(
            request,
            email=email,
            phone=phone,
            challenge_id=issued.challenge.id,
        )
        return issued

    def test_skip_endpoint_completes_registration_without_verification(self):
        request = _prepare_request(
            self.factory,
            path=reverse("accounts:pandit_register_skip_phone_otp"),
        )
        self._store_pandit_pending(request, email="skip-endpoint@example.com")
        response = pandit_register_skip_phone_otp(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.resume_path)
        user = User.objects.get(email="skip-endpoint@example.com")
        profile = PanditProfile.objects.get(user=user)
        self.assertFalse(user.is_phone_verified)
        self.assertEqual(user.status, "pending")
        self.assertFalse(user.is_active)
        self.assertFalse(profile.is_profile_approved)
        self.assertTrue(ReferralUsage.objects.filter(referred_pandit=user).exists())
        self.assertTrue(
            EmailVerificationToken.objects.filter(user=user).exists()
        )
        self.assertIsNone(get_pending_registration(request, enforce_ttl=False))

    def test_form_skip_bypasses_otp_gate_and_creates_once(self):
        payload = {
            **_pandit_form_payload(email="form-skip@example.com", phone="9876543211"),
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
            response = self.client.post(self.register_url, payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(email="form-skip@example.com").count(), 1)
        user = User.objects.get(email="form-skip@example.com")
        profile = PanditProfile.objects.get(user=user)
        self.assertFalse(user.is_phone_verified)
        self.assertEqual(user.status, "pending")
        self.assertFalse(user.is_active)
        self.assertFalse(profile.is_profile_approved)
        self.assertEqual(user.phone_number, "9876543211")
        self.assertTrue(ReferralUsage.objects.filter(referred_pandit=user).exists())
        self.assertTrue(EmailVerificationToken.objects.filter(user=user).exists())

    def test_otp_required_without_skip_still_calls_gate(self):
        payload = _pandit_form_payload(email="gate-required@example.com", phone="9876543212")
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
            response = self.client.post(self.register_url, payload)

        self.assertEqual(response.status_code, 202)
        begin_otp.assert_called_once()
        self.assertFalse(User.objects.filter(email="gate-required@example.com").exists())

    def test_invalid_otp_does_not_create_user_and_skip_still_works(self):
        session_holder = _prepare_request(self.factory)
        issued = self._store_pandit_pending_with_challenge(
            session_holder,
            email="invalid-then-skip@example.com",
            phone="9876543213",
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
            path=reverse("accounts:pandit_register_skip_phone_otp"),
        )
        self._store_pandit_pending_with_challenge(
            skip_request,
            email="invalid-then-skip@example.com",
            phone="9876543213",
        )
        response = pandit_register_skip_phone_otp(skip_request)
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email="invalid-then-skip@example.com")
        self.assertFalse(user.is_phone_verified)

    def test_successful_otp_completion_sets_phone_verified_without_activation(self):
        session_holder = _prepare_request(self.factory)
        issued = self._store_pandit_pending_with_challenge(
            session_holder,
            email="verified-otp@example.com",
            phone="9876543214",
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
        profile = PanditProfile.objects.get(user=user)
        self.assertTrue(user.is_phone_verified)
        self.assertEqual(user.status, "pending")
        self.assertFalse(user.is_active)
        self.assertFalse(profile.is_profile_approved)
        self.assertTrue(ReferralUsage.objects.filter(referred_pandit=user).exists())
        self.assertTrue(EmailVerificationToken.objects.filter(user=user).exists())

    def test_otp_verify_page_context_includes_pandit_skip_action(self):
        from otp_verification.registration.views import (
            _expert_skip_phone_verification_context,
        )

        ctx = _expert_skip_phone_verification_context(
            {"flow_type": constants.FLOW_PANDIT_REGISTRATION}
        )
        self.assertTrue(ctx["allow_skip_phone_verification"])
        self.assertEqual(
            ctx["skip_phone_verification_url"],
            reverse("accounts:pandit_register_skip_phone_otp"),
        )

    def test_skip_endpoint_rejects_missing_referral_in_pending_payload(self):
        request = _prepare_request(
            self.factory,
            path=reverse("accounts:pandit_register_skip_phone_otp"),
        )
        store_pending_registration(
            request,
            flow_type=constants.FLOW_PANDIT_REGISTRATION,
            challenge_id="bad-challenge",
            destination="9876543215",
            payload={
                "email": "bad-referral-skip@example.com",
                "password_hash": make_password("securepass123"),
                "first_name": "Bad",
                "last_name": "Referral",
                "phone_number": "9876543215",
            },
            resume_path=self.resume_path,
        )
        response = pandit_register_skip_phone_otp(request)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            User.objects.filter(email="bad-referral-skip@example.com").exists()
        )

    def _seed_client_widget_proof(self, *, phone):
        """Verify a Pandit challenge on the test runtime and store session proof."""

        issued = self._issue_pandit_challenge(phone=phone)
        self.service.verify_challenge(
            challenge_id=issued.challenge.id,
            submitted_otp=issued.otp_code,
        )
        holder = _prepare_request(self.factory)
        session = self.client.session
        holder.session = session
        store_phone_verified(
            holder,
            challenge_id=issued.challenge.id,
            destination=phone,
            flow_type=constants.FLOW_PANDIT_REGISTRATION,
        )
        session.save()
        return issued

    def test_widget_verified_session_marks_phone_verified_without_activation(self):
        phone = "9876543216"
        email = "widget-verified@example.com"
        self._seed_client_widget_proof(phone=phone)
        payload = _pandit_form_payload(email=email, phone=phone)
        with (
            patch(
                "otp_verification.registration.factory.is_registration_otp_required",
                return_value=True,
            ),
            patch(
                "otp_verification.registration.gate.build_registration_otp_service",
                return_value=self.service,
            ),
        ):
            response = self.client.post(self.register_url, payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(email=email).count(), 1)
        user = User.objects.get(email=email)
        profile = PanditProfile.objects.get(user=user)
        self.assertTrue(user.is_phone_verified)
        self.assertEqual(user.status, "pending")
        self.assertFalse(user.is_active)
        self.assertFalse(profile.is_profile_approved)
        self.assertEqual(
            ReferralUsage.objects.filter(referred_pandit=user).count(),
            1,
        )

    def test_skip_registration_stays_unverified_when_widget_proof_is_present(self):
        # skip_phone_verification bypasses begin_otp_or_continue. A prior widget
        # proof can still be in the session; that submission must stay unverified.
        phone = "9876543217"
        email = "widget-skip-stale@example.com"
        self._seed_client_widget_proof(phone=phone)
        payload = {
            **_pandit_form_payload(email=email, phone=phone),
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
                "otp_verification.registration.gate.build_registration_otp_service",
                return_value=self.service,
            ),
        ):
            response = self.client.post(self.register_url, payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(email=email).count(), 1)
        user = User.objects.get(email=email)
        self.assertFalse(user.is_phone_verified)
        self.assertEqual(user.status, "pending")
        self.assertFalse(user.is_active)
        self.assertFalse(PanditProfile.objects.get(user=user).is_profile_approved)
