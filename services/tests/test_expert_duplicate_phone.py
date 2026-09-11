"""Focused Expert duplicate-phone enforcement runtime tests."""

from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from accounts.phone_utils import normalize_phone_number
from core.models import ExpertProfile, ExpertService
from dashboards.views import expert_dashboard_view
from otp_verification import constants
from otp_verification.config import OTPConfiguration
from otp_verification.enums import SimulationMode
from otp_verification.registration.factory import build_registration_otp_service
from otp_verification.registration.session import (
    minimize_registration_payload,
    store_pending_registration,
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
TAKEN_PHONE = "9876543299"
TAKEN_PHONE_E164 = "919876543299"


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


@override_settings(
    SECRET_KEY="test-secret-expert-dup-phone",
    OTP_ENABLED=True,
    OTP_PROVIDER=constants.PROVIDER_MOCK_SMS,
)
class ExpertDuplicatePhoneTests(TestCase):
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
        self.owner = User.objects.create_user(
            email="phone-owner@example.com",
            username="phone-owner@example.com",
            password="Password123!",
            phone_number=TAKEN_PHONE,
        )
        self.assertEqual(
            normalize_phone_number(self.owner.phone_number),
            normalize_phone_number(TAKEN_PHONE),
        )

    def _registration_post_data(self, *, email, phone):
        return {
            "name": "Dup Phone Expert",
            "email": email,
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
            "phone": phone,
            "experience_years": "4",
            "description": "Duplicate phone test",
            "social_links[]": ["https://example.com/expert"],
            "services": [str(self.astrology.id)],
        }

    def _store_expert_pending(self, request, *, email, phone):
        issued = self.runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_EXPERT_REGISTRATION,
            context={},
        )
        payload = minimize_registration_payload(
            flow_type=constants.FLOW_EXPERT_REGISTRATION,
            payload={
                "name": "Dup Skip Expert",
                "email": email,
                "password": "StrongPass123!",
                "phone": phone,
                "experience_years": 4,
                "description": "Skip dup phone",
                "expert_type": "ASTROLOGER",
                "service_slugs": ["astrology"],
                "social_links": ["https://example.com/expert"],
            },
        )
        # ensure password hash present for completion
        payload["password_hash"] = make_password("StrongPass123!")
        store_pending_registration(
            request,
            flow_type=constants.FLOW_EXPERT_REGISTRATION,
            challenge_id=issued.challenge.id,
            destination=phone,
            payload=payload,
            resume_path="/services/expert/register/",
        )
        return issued

    @patch("otp_verification.registration.gate.begin_otp_or_continue")
    def test_registration_rejects_duplicate_phone_without_creating_expert(
        self, mock_gate
    ):
        users_before = User.objects.count()
        experts_before = ExpertProfile.objects.count()
        request = _prepare_request(
            self.factory,
            path=f"{reverse('expert_register')}?type=astrology",
            data=self._registration_post_data(
                email="dup-register@example.com",
                phone=TAKEN_PHONE,
            ),
        )
        response = expert_register_page(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Phone number already registered")
        self.assertFalse(
            User.objects.filter(email="dup-register@example.com").exists()
        )
        self.assertFalse(
            ExpertProfile.objects.filter(email="dup-register@example.com").exists()
        )
        self.assertEqual(User.objects.count(), users_before)
        self.assertEqual(ExpertProfile.objects.count(), experts_before)
        mock_gate.assert_not_called()

    def test_skip_otp_rejects_duplicate_phone_without_creating_expert(self):
        users_before = User.objects.count()
        experts_before = ExpertProfile.objects.count()
        request = _prepare_request(
            self.factory,
            path=reverse("expert_register_skip_phone_otp"),
        )
        self._store_expert_pending(
            request,
            email="dup-skip@example.com",
            phone=TAKEN_PHONE,
        )
        response = expert_register_skip_phone_otp(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("expert_register"))
        self.assertFalse(User.objects.filter(email="dup-skip@example.com").exists())
        self.assertFalse(
            ExpertProfile.objects.filter(email="dup-skip@example.com").exists()
        )
        self.assertEqual(User.objects.count(), users_before)
        self.assertEqual(ExpertProfile.objects.count(), experts_before)
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.phone_number, TAKEN_PHONE)

    def test_profile_edit_rejects_another_users_phone(self):
        user = User.objects.create_user(
            email="expert-edit-a@example.com",
            username="expert-edit-a@example.com",
            password="Password123!",
            phone_number="9876543201",
            is_phone_verified=True,
        )
        expert = ExpertProfile.objects.create(
            name="Edit A",
            email=user.email,
            phone="9876543201",
            experience_years=3,
            description="Own phone",
            expert_type="ASTROLOGER",
            is_active=True,
        )
        expert.services.set([self.astrology])

        before_phone = user.phone_number
        before_expert_phone = expert.phone
        before_verified = user.is_phone_verified
        before_owner_phone = self.owner.phone_number

        request = _prepare_request(
            self.factory,
            path=f"{reverse('module5_dashboards:expert_dashboard')}?tab=profile",
            data={
                "name": expert.name,
                "phone": TAKEN_PHONE,
                "experience_years": str(expert.experience_years),
                "description": expert.description,
                "services": [str(self.astrology.id)],
            },
            user=user,
        )
        response = expert_dashboard_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Phone number already registered")
        user.refresh_from_db()
        expert.refresh_from_db()
        self.owner.refresh_from_db()
        self.assertEqual(user.phone_number, before_phone)
        self.assertEqual(expert.phone, before_expert_phone)
        self.assertEqual(user.is_phone_verified, before_verified)
        self.assertTrue(user.is_phone_verified)
        self.assertEqual(self.owner.phone_number, before_owner_phone)

    def test_profile_edit_allows_unique_phone_and_resets_verification(self):
        user = User.objects.create_user(
            email="expert-unique-edit@example.com",
            username="expert-unique-edit@example.com",
            password="Password123!",
            phone_number="9876543202",
            is_phone_verified=True,
        )
        expert = ExpertProfile.objects.create(
            name="Unique Edit",
            email=user.email,
            phone="9876543202",
            experience_years=3,
            description="Will change phone",
            expert_type="ASTROLOGER",
            is_active=True,
        )
        expert.services.set([self.astrology])

        request = _prepare_request(
            self.factory,
            path=f"{reverse('module5_dashboards:expert_dashboard')}?tab=profile",
            data={
                "name": expert.name,
                "phone": "9876543203",
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
        self.assertEqual(user.phone_number, "9876543203")
        self.assertEqual(expert.phone, "9876543203")
        self.assertFalse(user.is_phone_verified)

        issued = self.runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_EXPERT_REGISTRATION,
            context={},
        )
        from otp_verification.registration.session import store_phone_challenge

        otp_request = _prepare_request(
            self.factory,
            path=reverse("otp_verification:verify_registration_otp"),
            data={"challenge_id": issued.challenge.id, "otp": issued.otp_code},
            user=user,
        )
        store_phone_challenge(
            otp_request,
            challenge_id=issued.challenge.id,
            flow_type=constants.FLOW_EXPERT_REGISTRATION,
            destination="9876543203",
            resend_count=0,
        )
        otp_request.META["HTTP_ACCEPT"] = "application/json"
        with patch(
            "otp_verification.registration.views.build_registration_otp_service",
            return_value=self.service,
        ):
            otp_response = verify_registration_otp(otp_request)
        body = __import__("json").loads(otp_response.content.decode("utf-8"))
        self.assertEqual(body["status"], "success")
        user.refresh_from_db()
        self.assertTrue(user.is_phone_verified)

    def test_normalize_equivalence_blocks_91_prefixed_duplicate(self):
        """Helper treats 10-digit and 91XXXXXXXXXX as the same canonical phone."""
        self.assertEqual(
            normalize_phone_number(TAKEN_PHONE),
            normalize_phone_number(TAKEN_PHONE_E164),
        )
        users_before = User.objects.count()
        request = _prepare_request(
            self.factory,
            path=f"{reverse('expert_register')}?type=astrology",
            data=self._registration_post_data(
                email="dup-91@example.com",
                phone=TAKEN_PHONE_E164,
            ),
        )
        with patch(
            "otp_verification.registration.gate.begin_otp_or_continue",
            side_effect=AssertionError("OTP must not start for duplicate phone"),
        ):
            response = expert_register_page(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Phone number already registered")
        self.assertEqual(User.objects.count(), users_before)
        self.assertFalse(User.objects.filter(email="dup-91@example.com").exists())
