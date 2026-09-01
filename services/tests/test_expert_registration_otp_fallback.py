"""Expert registration OTP fallback and later phone verification tests."""

from __future__ import annotations

import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from core.models import ExpertProfile, ExpertService
from dashboards.views import expert_dashboard_view
from otp_verification import constants
from otp_verification.config import OTPConfiguration
from otp_verification.enums import SimulationMode
from otp_verification.registration.factory import build_registration_otp_service
from otp_verification.registration.session import (
    get_pending_registration,
    minimize_registration_payload,
    store_pending_registration,
    store_phone_challenge,
)
from otp_verification.registration.views import verify_registration_otp
from otp_verification.services.factory import (
    build_otp_engine,
    build_otp_provider_runtime,
    reset_otp_process_storage,
)
from otp_verification.storage.memory import InMemoryChallengeRepository
from services.views_expert_ui import (
    expert_register_page,
    expert_register_skip_phone_otp,
)

User = get_user_model()


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


def _prepare_request(factory, *, method="post", path="/", data=None, user=None):
    if method == "post":
        request = factory.post(path, data=data or {})
    else:
        request = factory.get(path)
    request.session = SessionStore()
    request._messages = FallbackStorage(request)
    if user is not None:
        request.user = user
    return request


def _expert_raw_payload(*, email="otp-fallback@example.com", phone="9876543211"):
    return {
        "name": "OTP Fallback Expert",
        "email": email,
        "password": "StrongPass123!",
        "phone": phone,
        "experience_years": 4,
        "description": "OTP fallback test expert",
        "expert_type": "ASTROLOGER",
        "service_slugs": ["astrology"],
        "social_links": ["https://example.com/expert"],
    }


@override_settings(
    SECRET_KEY="test-secret-expert-otp-fallback",
    OTP_ENABLED=True,
    OTP_PROVIDER=constants.PROVIDER_MOCK_SMS,
)
class ExpertRegistrationOTPFallbackTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.astrology, _ = ExpertService.objects.get_or_create(
            slug="astrology",
            defaults={"name": "Astrology", "display_order": 1},
        )

    def setUp(self):
        reset_otp_process_storage()
        self.factory = RequestFactory()
        config = _otp_config()
        engine = build_otp_engine(
            configuration=config,
            repository=InMemoryChallengeRepository(),
        )
        self.runtime = build_otp_provider_runtime(configuration=config, engine=engine)
        self.service = build_registration_otp_service(runtime=self.runtime)

    def _registration_post_data(self, *, email="otp-fallback@example.com", phone="9876543211"):
        return {
            "name": "OTP Fallback Expert",
            "email": email,
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
            "phone": phone,
            "experience_years": "4",
            "description": "OTP fallback test expert",
            "social_links[]": ["https://example.com/expert"],
            "services": [str(self.astrology.id)],
        }

    def _issue_expert_challenge(self, *, phone="9876543212"):
        return self.runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_EXPERT_REGISTRATION,
            context={},
        )

    def _store_expert_pending(
        self, request, *, email="verified-otp@example.com", phone="9876543212"
    ):
        issued = self._issue_expert_challenge(phone=phone)
        payload = minimize_registration_payload(
            flow_type=constants.FLOW_EXPERT_REGISTRATION,
            payload=_expert_raw_payload(email=email, phone=phone),
        )
        store_pending_registration(
            request,
            flow_type=constants.FLOW_EXPERT_REGISTRATION,
            challenge_id=issued.challenge.id,
            destination=phone,
            payload=payload,
            resume_path="/services/expert/register/",
        )
        return issued

    def test_otp_verified_registration_completes_with_phone_verified(self):
        session_holder = _prepare_request(self.factory)
        issued = self._store_expert_pending(
            session_holder,
            email="verified-otp@example.com",
            phone="9876543212",
        )
        request = _prepare_request(
            self.factory,
            path=reverse("otp_verification:verify_registration_otp"),
            data={
                "challenge_id": issued.challenge.id,
                "otp": issued.otp_code,
            },
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
        expert = ExpertProfile.objects.get(email="verified-otp@example.com")
        self.assertFalse(expert.is_active)
        user = User.objects.get(email="verified-otp@example.com")
        self.assertTrue(user.is_phone_verified)
        self.assertEqual(user.phone_number, "9876543212")

    def test_skip_phone_otp_completes_registration_without_verification(self):
        request = _prepare_request(
            self.factory,
            path=reverse("expert_register_skip_phone_otp"),
        )
        self._store_expert_pending(
            request, email="skip-otp@example.com", phone="9876543213"
        )
        response = expert_register_skip_phone_otp(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("expert_pending"))
        expert = ExpertProfile.objects.get(email="skip-otp@example.com")
        self.assertFalse(expert.is_active)
        user = User.objects.get(email="skip-otp@example.com")
        self.assertFalse(user.is_phone_verified)
        self.assertIsNone(get_pending_registration(request, enforce_ttl=False))

    def test_registration_form_skip_flag_bypasses_otp_gate(self):
        request = _prepare_request(
            self.factory,
            path=f"{reverse('expert_register')}?type=astrology",
            data={
                **self._registration_post_data(
                    email="form-skip@example.com", phone="9876543214"
                ),
                "skip_phone_verification": "1",
            },
        )
        with patch(
            "otp_verification.registration.gate.begin_otp_or_continue",
            side_effect=AssertionError("OTP gate must not run when skipping"),
        ):
            response = expert_register_page(request)
        self.assertEqual(response.status_code, 200)
        expert = ExpertProfile.objects.get(email="form-skip@example.com")
        self.assertFalse(expert.is_active)
        user = User.objects.get(email="form-skip@example.com")
        self.assertFalse(user.is_phone_verified)

    def test_invalid_otp_does_not_mark_phone_verified_and_skip_still_works(self):
        request = _prepare_request(
            self.factory,
            path=reverse("otp_verification:verify_registration_otp"),
            data={"challenge_id": "pending", "otp": "000000"},
        )
        issued = self._store_expert_pending(
            request, email="invalid-otp@example.com", phone="9876543215"
        )
        verify_request = _prepare_request(
            self.factory,
            path=reverse("otp_verification:verify_registration_otp"),
            data={"challenge_id": issued.challenge.id, "otp": "000000"},
        )
        verify_request.session = request.session
        verify_request.META["HTTP_ACCEPT"] = "application/json"
        with patch(
            "otp_verification.registration.views.build_registration_otp_service",
            return_value=self.service,
        ):
            response = verify_registration_otp(verify_request)
        body = json.loads(response.content.decode("utf-8"))
        self.assertEqual(body["status"], "error")
        self.assertFalse(
            ExpertProfile.objects.filter(email="invalid-otp@example.com").exists()
        )

        skip_request = _prepare_request(
            self.factory,
            path=reverse("expert_register_skip_phone_otp"),
        )
        self._store_expert_pending(
            skip_request,
            email="invalid-otp@example.com",
            phone="9876543215",
        )
        response = expert_register_skip_phone_otp(skip_request)
        self.assertEqual(response.status_code, 302)
        expert = ExpertProfile.objects.get(email="invalid-otp@example.com")
        self.assertFalse(expert.is_active)
        user = User.objects.get(email="invalid-otp@example.com")
        self.assertFalse(user.is_phone_verified)

    def test_later_profile_phone_verification_marks_user_verified(self):
        user = User.objects.create_user(
            email="profile-verify@example.com",
            username="profile-verify@example.com",
            password="Password123!",
            phone_number="9876543216",
            is_phone_verified=False,
        )
        expert = ExpertProfile.objects.create(
            name="Profile Verify Expert",
            email=user.email,
            phone="9876543216",
            experience_years=3,
            description="Needs phone verification",
            expert_type="ASTROLOGER",
            is_active=True,
        )
        expert.services.set([self.astrology])

        issued = self._issue_expert_challenge(phone="9876543216")
        request = _prepare_request(
            self.factory,
            path=reverse("otp_verification:verify_registration_otp"),
            data={"challenge_id": issued.challenge.id, "otp": issued.otp_code},
            user=user,
        )
        store_phone_challenge(
            request,
            challenge_id=issued.challenge.id,
            flow_type=constants.FLOW_EXPERT_REGISTRATION,
            destination="9876543216",
            resend_count=0,
        )
        request.META["HTTP_ACCEPT"] = "application/json"
        with patch(
            "otp_verification.registration.views.build_registration_otp_service",
            return_value=self.service,
        ):
            response = verify_registration_otp(request)
        body = json.loads(response.content.decode("utf-8"))
        self.assertEqual(body["status"], "success")
        self.assertTrue(body["result"]["phone_verified"])

        user.refresh_from_db()
        expert.refresh_from_db()
        self.assertTrue(user.is_phone_verified)
        self.assertTrue(expert.is_active)

        dashboard_request = _prepare_request(
            self.factory,
            path=f"{reverse('module5_dashboards:expert_dashboard')}?tab=profile",
            user=user,
        )
        with patch(
            "whatsapp_verification.integration.widget_helpers.widget_context_for_subject",
            return_value={},
        ):
            response = expert_dashboard_view(dashboard_request)
        self.assertContains(response, "Verified")

    def test_changing_profile_phone_resets_verification(self):
        user = User.objects.create_user(
            email="phone-change-reset@example.com",
            username="phone-change-reset@example.com",
            password="Password123!",
            phone_number="9876543210",
            is_phone_verified=True,
        )
        expert = ExpertProfile.objects.create(
            name="Phone Change Expert",
            email=user.email,
            phone="9876543210",
            experience_years=3,
            description="Verified phone will change",
            expert_type="ASTROLOGER",
            is_active=True,
        )
        expert.services.set([self.astrology])

        request = _prepare_request(
            self.factory,
            path=f"{reverse('module5_dashboards:expert_dashboard')}?tab=profile",
            data={
                "name": expert.name,
                "phone": "9876543211",
                "experience_years": str(expert.experience_years),
                "description": expert.description,
                "services": [str(self.astrology.id)],
            },
            user=user,
        )
        response = expert_dashboard_view(request)
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        expert.refresh_from_db()
        self.assertFalse(user.is_phone_verified)
        self.assertEqual(user.phone_number, "9876543211")
        self.assertEqual(expert.phone, "9876543211")

    def test_saving_same_phone_does_not_reset_verification(self):
        user = User.objects.create_user(
            email="same-phone@example.com",
            username="same-phone@example.com",
            password="Password123!",
            phone_number="9876543212",
            is_phone_verified=True,
        )
        expert = ExpertProfile.objects.create(
            name="Same Phone Expert",
            email=user.email,
            phone="9876543212",
            experience_years=3,
            description="Same phone save",
            expert_type="ASTROLOGER",
            is_active=True,
        )
        expert.services.set([self.astrology])

        request = _prepare_request(
            self.factory,
            path=f"{reverse('module5_dashboards:expert_dashboard')}?tab=profile",
            data={
                "name": expert.name,
                "phone": expert.phone,
                "experience_years": str(expert.experience_years),
                "description": expert.description,
                "services": [str(self.astrology.id)],
            },
            user=user,
        )
        response = expert_dashboard_view(request)
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.is_phone_verified)
        self.assertEqual(user.phone_number, "9876543212")
