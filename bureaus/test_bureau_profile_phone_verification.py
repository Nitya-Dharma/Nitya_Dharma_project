"""Bureau Edit Profile post-registration phone verification tests."""

from __future__ import annotations

import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.core.cache import cache
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

from bureaus.models import BureauProfile
from otp_verification import constants
from otp_verification.config import OTPConfiguration
from otp_verification.enums import SimulationMode
from otp_verification.registration.factory import build_registration_otp_service
from otp_verification.registration.session import store_phone_challenge
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


def _make_bureau_owner(
    *,
    email="bureau-profile-verify@example.com",
    phone="9123456801",
    is_phone_verified=False,
    is_email_verified=True,
):
    user = User.objects.create_user(
        email=email,
        username=f"u_{email.split('@')[0][:20]}",
        password="BureauTestPass123!",
        role="user",
        status="active",
        is_active=True,
        is_phone_verified=is_phone_verified,
    )
    profile = BureauProfile.objects.create(
        user=user,
        bureau_name="Profile Verify Bureau",
        phone_number=phone,
        address="1 Profile Road",
        city="Hyderabad",
        whatsapp_number="",
        description="Bureau description for edit profile access.",
        caste_data={"OC": ["Brahmin"]},
        is_active=False,
        is_approved=False,
        is_email_verified=is_email_verified,
    )
    return user, profile


@override_settings(EMAIL_BACKEND=LOCMEM_EMAIL, OTP_ENABLED=True)
class BureauProfilePhoneVerificationTests(TestCase):
    def setUp(self):
        cache.clear()
        reset_otp_process_storage()
        self.client = Client()
        self.factory = RequestFactory()
        config = _otp_config()
        engine = build_otp_engine(
            configuration=config,
            repository=InMemoryChallengeRepository(),
        )
        self.runtime = build_otp_provider_runtime(configuration=config, engine=engine)
        self.service = build_registration_otp_service(runtime=self.runtime)

    def test_unverified_profile_shows_verify_mobile_ui(self):
        user, _profile = _make_bureau_owner(is_phone_verified=False)
        self.client.force_login(user)
        response = self.client.get(reverse("bureaus:bureau_profile_edit"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Not verified")
        self.assertContains(response, "bureau_profile_mv-root")

    def test_verified_profile_hides_verify_mobile_ui(self):
        user, _profile = _make_bureau_owner(is_phone_verified=True)
        user.phone_number = "9123456801"
        user.save(update_fields=["phone_number"])
        self.client.force_login(user)
        response = self.client.get(reverse("bureaus:bureau_profile_edit"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Verified")
        self.assertNotContains(response, "bureau_profile_mv-root")

    def test_profile_get_syncs_user_phone_from_bureau_profile(self):
        user, profile = _make_bureau_owner(
            email="sync-phone@example.com",
            phone="9123456802",
            is_phone_verified=False,
        )
        self.assertFalse(user.phone_number)
        self.client.force_login(user)
        self.client.get(reverse("bureaus:bureau_profile_edit"))
        user.refresh_from_db()
        self.assertEqual(user.phone_number, profile.phone_number)

    def test_successful_profile_otp_marks_user_verified_only(self):
        user, profile = _make_bureau_owner(
            email="profile-otp-ok@example.com",
            phone="9123456803",
            is_phone_verified=False,
        )
        user.phone_number = profile.phone_number
        user.save(update_fields=["phone_number"])
        issued = self.runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_BUREAU_REGISTRATION,
            context={},
        )
        request = _prepare_request(
            self.factory,
            path=reverse("otp_verification:verify_registration_otp"),
            data={"challenge_id": issued.challenge.id, "otp": issued.otp_code},
            user=user,
        )
        store_phone_challenge(
            request,
            challenge_id=issued.challenge.id,
            flow_type=constants.FLOW_BUREAU_REGISTRATION,
            destination=profile.phone_number,
            resend_count=0,
        )
        request.META["HTTP_ACCEPT"] = "application/json"
        before_active = profile.is_active
        before_approved = profile.is_approved
        before_email = profile.is_email_verified
        with patch(
            "otp_verification.registration.views.build_registration_otp_service",
            return_value=self.service,
        ):
            response = verify_registration_otp(request)
        body = json.loads(response.content.decode("utf-8"))
        self.assertEqual(body["status"], "success")
        self.assertTrue(body["result"]["phone_verified"])
        user.refresh_from_db()
        profile.refresh_from_db()
        self.assertTrue(user.is_phone_verified)
        self.assertEqual(profile.is_active, before_active)
        self.assertEqual(profile.is_approved, before_approved)
        self.assertEqual(profile.is_email_verified, before_email)
        self.assertFalse(profile.is_active)
        self.assertFalse(profile.is_approved)

    def test_wrong_profile_otp_leaves_user_unverified(self):
        user, profile = _make_bureau_owner(
            email="profile-otp-bad@example.com",
            phone="9123456804",
            is_phone_verified=False,
        )
        user.phone_number = profile.phone_number
        user.save(update_fields=["phone_number"])
        issued = self.runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_BUREAU_REGISTRATION,
            context={},
        )
        request = _prepare_request(
            self.factory,
            path=reverse("otp_verification:verify_registration_otp"),
            data={"challenge_id": issued.challenge.id, "otp": "000000"},
            user=user,
        )
        store_phone_challenge(
            request,
            challenge_id=issued.challenge.id,
            flow_type=constants.FLOW_BUREAU_REGISTRATION,
            destination=profile.phone_number,
            resend_count=0,
        )
        request.META["HTTP_ACCEPT"] = "application/json"
        with patch(
            "otp_verification.registration.views.build_registration_otp_service",
            return_value=self.service,
        ):
            response = verify_registration_otp(request)
        body = json.loads(response.content.decode("utf-8"))
        self.assertEqual(body["status"], "error")
        user.refresh_from_db()
        profile.refresh_from_db()
        self.assertFalse(user.is_phone_verified)
        self.assertFalse(profile.is_active)
        self.assertFalse(profile.is_approved)
        self.assertTrue(profile.is_email_verified)

    def test_profile_otp_does_not_create_duplicate_records(self):
        user, profile = _make_bureau_owner(
            email="profile-no-dup@example.com",
            phone="9123456805",
            is_phone_verified=False,
        )
        user.phone_number = profile.phone_number
        user.save(update_fields=["phone_number"])
        issued = self.runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_BUREAU_REGISTRATION,
            context={},
        )
        request = _prepare_request(
            self.factory,
            path=reverse("otp_verification:verify_registration_otp"),
            data={"challenge_id": issued.challenge.id, "otp": issued.otp_code},
            user=user,
        )
        store_phone_challenge(
            request,
            challenge_id=issued.challenge.id,
            flow_type=constants.FLOW_BUREAU_REGISTRATION,
            destination=profile.phone_number,
            resend_count=0,
        )
        request.META["HTTP_ACCEPT"] = "application/json"
        with patch(
            "otp_verification.registration.views.build_registration_otp_service",
            return_value=self.service,
        ):
            verify_registration_otp(request)
        self.assertEqual(User.objects.filter(email=user.email).count(), 1)
        self.assertEqual(BureauProfile.objects.filter(user=user).count(), 1)

    def test_changing_profile_phone_resets_verification(self):
        user, profile = _make_bureau_owner(
            email="phone-change-reset@example.com",
            phone="9123456810",
            is_phone_verified=True,
        )
        user.phone_number = profile.phone_number
        user.save(update_fields=["phone_number"])
        self.client.force_login(user)
        response = self.client.post(
            reverse("bureaus:bureau_profile_edit"),
            {
                "description": profile.description,
                "phone_number": "9123456811",
                "whatsapp_number": "",
                "address": profile.address,
                "city": profile.city,
                "caste_data": '{"OC": ["Brahmin"]}',
            },
        )
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        profile.refresh_from_db()
        self.assertFalse(user.is_phone_verified)
        self.assertEqual(user.phone_number, "9123456811")
        self.assertEqual(profile.phone_number, "9123456811")
