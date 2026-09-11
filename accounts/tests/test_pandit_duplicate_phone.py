"""Focused Pandit duplicate-phone enforcement runtime tests."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.core.cache import cache
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.phone_utils import normalize_phone_number
from accounts.views import pandit_register_skip_phone_otp
from otp_verification import constants
from otp_verification.config import OTPConfiguration
from otp_verification.enums import SimulationMode
from otp_verification.registration.factory import build_registration_otp_service
from otp_verification.registration.session import store_pending_registration
from otp_verification.services.factory import (
    build_otp_engine,
    build_otp_provider_runtime,
    reset_otp_process_storage,
)
from otp_verification.storage.memory import InMemoryChallengeRepository
from profiles.models import PanditProfile
from referrals.models import ReferralLink

User = get_user_model()
LOCMEM_EMAIL = "django.core.mail.backends.locmem.EmailBackend"
TAKEN_PHONE = "9876543210"


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


@override_settings(EMAIL_BACKEND=LOCMEM_EMAIL)
class PanditDuplicatePhoneTests(TestCase):
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
            email="admin-dup-phone@example.com",
            password="testpass123",
            role="admin",
            status="active",
            is_active=True,
        )
        self.referral_link = ReferralLink.objects.create(
            created_by=self.admin,
            token="pandit-dup-tok-001",
            referral_code="pandit-dup-tok-001",
            code="REFAPDUP1",
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

        self.existing = User.objects.create_user(
            email="existing-phone-owner@example.com",
            password="testpass123",
            role="user",
            status="active",
            is_active=True,
            phone_number=TAKEN_PHONE,
        )
        self.assertEqual(
            normalize_phone_number(self.existing.phone_number),
            normalize_phone_number(TAKEN_PHONE),
        )

    @override_settings(OTP_ENABLED=True, OTP_ENABLED_FLOWS=constants.FLOW_CHOICES)
    @patch("otp_verification.registration.gate.build_registration_otp_service")
    def test_registration_rejects_duplicate_phone_without_creating_user(
        self, mock_build_service
    ):
        mock_service = mock_build_service.return_value
        users_before = User.objects.count()
        profiles_before = PanditProfile.objects.count()

        response = self.client.post(
            self.register_url,
            {
                "referral_code": self.referral_link.referral_code,
                "first_name": "Dup",
                "last_name": "Register",
                "email": "dup-register@example.com",
                "password": "securepass123",
                "phone_number": TAKEN_PHONE,
            },
        )

        self.assertEqual(response.status_code, 200)
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(
            any("Phone number already registered" in m for m in messages),
            messages,
        )
        self.assertFalse(User.objects.filter(email="dup-register@example.com").exists())
        self.assertEqual(User.objects.count(), users_before)
        self.assertEqual(PanditProfile.objects.count(), profiles_before)
        mock_service.start_verification.assert_not_called()
        mock_build_service.assert_not_called()

        self.existing.refresh_from_db()
        self.assertEqual(self.existing.phone_number, TAKEN_PHONE)

    def test_skip_otp_rejects_duplicate_phone_without_creating_user(self):
        users_before = User.objects.count()
        profiles_before = PanditProfile.objects.count()
        existing_email = self.existing.email
        existing_phone = self.existing.phone_number

        request = _prepare_request(
            self.factory,
            path=reverse("accounts:pandit_register_skip_phone_otp"),
        )
        store_pending_registration(
            request,
            flow_type=constants.FLOW_PANDIT_REGISTRATION,
            challenge_id="dup-skip-challenge",
            destination=TAKEN_PHONE,
            payload={
                "email": "dup-skip@example.com",
                "password_hash": make_password("securepass123"),
                "first_name": "Dup",
                "last_name": "Skip",
                "phone_number": TAKEN_PHONE,
                "referral_link_id": self.referral_link.id,
                "referral_code": self.referral_link.referral_code,
            },
            resume_path=self.resume_path,
        )

        response = pandit_register_skip_phone_otp(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.resume_path)

        messages = [str(m) for m in get_messages(request)]
        self.assertTrue(
            any("Phone number already registered" in m for m in messages),
            messages,
        )
        self.assertFalse(User.objects.filter(email="dup-skip@example.com").exists())
        self.assertEqual(User.objects.count(), users_before)
        self.assertEqual(PanditProfile.objects.count(), profiles_before)

        self.existing.refresh_from_db()
        self.assertEqual(self.existing.email, existing_email)
        self.assertEqual(self.existing.phone_number, existing_phone)
