"""Pandit Edit Profile post-registration phone verification tests."""

from __future__ import annotations

import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.core.cache import cache
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

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
from profiles.models import PanditProfile

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


def _make_pandit(
    *,
    email="pandit-profile-verify@example.com",
    phone="9123456801",
    is_phone_verified=False,
    email_verified=True,
    is_active=True,
    status="active",
):
    user = User.objects.create_user(
        email=email,
        password="PanditTestPass123!",
        first_name="Profile",
        last_name="Pandit",
        role="pandit",
        status=status,
        is_active=is_active,
        email_verified=email_verified,
        is_phone_verified=is_phone_verified,
    )
    profile, _created = PanditProfile.objects.get_or_create(user=user)
    profile.call_mobile_number = phone
    profile.enable_call = True
    profile.allow_call = True
    profile.save(
        update_fields=[
            "call_mobile_number",
            "enable_call",
            "allow_call",
            "updated_at",
        ]
    )
    return user, profile


@override_settings(EMAIL_BACKEND=LOCMEM_EMAIL, OTP_ENABLED=True)
class PanditProfilePhoneVerificationTests(TestCase):
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

    def test_unverified_pandit_shows_verify_mobile_ui(self):
        user, _profile = _make_pandit(is_phone_verified=False)
        self.client.force_login(user)
        response = self.client.get(reverse("profiles:profile_edit"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Not verified")
        self.assertContains(response, "pandit_profile_mv-root")

    def test_verified_pandit_hides_verify_mobile_ui(self):
        user, profile = _make_pandit(is_phone_verified=True)
        user.phone_number = profile.call_mobile_number
        user.save(update_fields=["phone_number"])
        self.client.force_login(user)
        response = self.client.get(reverse("profiles:profile_edit"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Verified")
        self.assertNotContains(response, "pandit_profile_mv-root")

    def test_profile_get_syncs_user_phone_from_pandit_profile(self):
        user, profile = _make_pandit(
            email="sync-phone@example.com",
            phone="9123456802",
            is_phone_verified=False,
        )
        self.assertFalse(user.phone_number)
        self.client.force_login(user)
        self.client.get(reverse("profiles:profile_edit"))
        user.refresh_from_db()
        self.assertEqual(user.phone_number, profile.call_mobile_number)

    def test_successful_profile_otp_marks_user_verified_only(self):
        user, profile = _make_pandit(
            email="profile-otp-ok@example.com",
            phone="9123456803",
            is_phone_verified=False,
            is_active=False,
            status="pending",
            email_verified=False,
        )
        user.phone_number = profile.call_mobile_number
        user.save(update_fields=["phone_number"])
        issued = self.runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_PANDIT_REGISTRATION,
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
            flow_type=constants.FLOW_PANDIT_REGISTRATION,
            destination=profile.call_mobile_number,
            resend_count=0,
        )
        request.META["HTTP_ACCEPT"] = "application/json"
        before_active = user.is_active
        before_status = user.status
        before_email = user.email_verified
        before_profile_approved = profile.is_profile_approved
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
        self.assertEqual(user.is_active, before_active)
        self.assertEqual(user.status, before_status)
        self.assertEqual(user.email_verified, before_email)
        self.assertEqual(profile.is_profile_approved, before_profile_approved)
        self.assertFalse(user.is_active)
        self.assertFalse(profile.is_profile_approved)

    def test_wrong_profile_otp_leaves_user_unverified(self):
        user, profile = _make_pandit(
            email="profile-otp-bad@example.com",
            phone="9123456804",
            is_phone_verified=False,
            is_active=False,
            status="pending",
        )
        user.phone_number = profile.call_mobile_number
        user.save(update_fields=["phone_number"])
        issued = self.runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_PANDIT_REGISTRATION,
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
            flow_type=constants.FLOW_PANDIT_REGISTRATION,
            destination=profile.call_mobile_number,
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
        self.assertFalse(user.is_active)
        self.assertFalse(profile.is_profile_approved)

    def test_changing_profile_phone_resets_verification(self):
        user, profile = _make_pandit(
            email="phone-change-reset@example.com",
            phone="9123456810",
            is_phone_verified=True,
        )
        user.phone_number = profile.call_mobile_number
        user.save(update_fields=["phone_number"])
        self.client.force_login(user)
        response = self.client.post(
            reverse("profiles:profile_edit"),
            {
                "call_mobile_number": "9123456811",
                "use_same_number_for_call_and_whatsapp": "1",
                "about_description": "Updated bio",
            },
        )
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        profile.refresh_from_db()
        self.assertFalse(user.is_phone_verified)
        self.assertEqual(user.phone_number, "9123456811")
        self.assertEqual(profile.call_mobile_number, "9123456811")

    def test_saving_same_phone_does_not_reset_verification(self):
        user, profile = _make_pandit(
            email="same-phone@example.com",
            phone="9123456812",
            is_phone_verified=True,
        )
        user.phone_number = profile.call_mobile_number
        user.save(update_fields=["phone_number", "is_phone_verified"])
        self.client.force_login(user)
        response = self.client.post(
            reverse("profiles:profile_edit"),
            {
                "call_mobile_number": profile.call_mobile_number,
                "use_same_number_for_call_and_whatsapp": "1",
                "about_description": "Same phone save",
            },
        )
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.is_phone_verified)

    def test_unauthenticated_user_cannot_verify_pandit_phone(self):
        user, profile = _make_pandit(
            email="anon-verify@example.com",
            phone="9123456813",
            is_phone_verified=False,
        )
        user.phone_number = profile.call_mobile_number
        user.save(update_fields=["phone_number"])
        issued = self.runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_PANDIT_REGISTRATION,
            context={},
        )
        request = _prepare_request(
            self.factory,
            path=reverse("otp_verification:verify_registration_otp"),
            data={"challenge_id": issued.challenge.id, "otp": issued.otp_code},
        )
        store_phone_challenge(
            request,
            challenge_id=issued.challenge.id,
            flow_type=constants.FLOW_PANDIT_REGISTRATION,
            destination=profile.call_mobile_number,
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
        user.refresh_from_db()
        self.assertFalse(user.is_phone_verified)

    def test_pandit_verification_cannot_affect_another_user(self):
        owner, owner_profile = _make_pandit(
            email="owner-verify@example.com",
            phone="9123456814",
            is_phone_verified=False,
        )
        other, other_profile = _make_pandit(
            email="other-verify@example.com",
            phone="9123456815",
            is_phone_verified=False,
        )
        owner.phone_number = owner_profile.call_mobile_number
        owner.save(update_fields=["phone_number"])
        other.phone_number = other_profile.call_mobile_number
        other.save(update_fields=["phone_number"])
        issued = self.runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_PANDIT_REGISTRATION,
            context={},
        )
        request = _prepare_request(
            self.factory,
            path=reverse("otp_verification:verify_registration_otp"),
            data={"challenge_id": issued.challenge.id, "otp": issued.otp_code},
            user=other,
        )
        store_phone_challenge(
            request,
            challenge_id=issued.challenge.id,
            flow_type=constants.FLOW_PANDIT_REGISTRATION,
            destination=owner_profile.call_mobile_number,
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
        owner.refresh_from_db()
        other.refresh_from_db()
        self.assertFalse(owner.is_phone_verified)
        self.assertFalse(other.is_phone_verified)

    def test_blank_phone_does_not_show_verify_mobile_ui(self):
        user, profile = _make_pandit(
            email="blank-phone@example.com",
            phone="9123456816",
            is_phone_verified=False,
        )
        profile.call_mobile_number = None
        profile.primary_mobile_number = None
        profile.phone_number = None
        profile.save(
            update_fields=[
                "call_mobile_number",
                "primary_mobile_number",
                "phone_number",
                "updated_at",
            ]
        )
        self.client.force_login(user)
        response = self.client.get(reverse("profiles:profile_edit"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "pandit_profile_mv-root")

    def test_profile_edit_rejects_another_users_phone(self):
        user_a, profile_a = _make_pandit(
            email="dup-edit-a@example.com",
            phone="9123456820",
            is_phone_verified=True,
        )
        user_a.phone_number = profile_a.call_mobile_number
        user_a.save(update_fields=["phone_number", "is_phone_verified"])

        user_b, _profile_b = _make_pandit(
            email="dup-edit-b@example.com",
            phone="9123456821",
            is_phone_verified=True,
        )
        user_b.phone_number = "9123456821"
        user_b.save(update_fields=["phone_number"])

        before_a_phone = user_a.phone_number
        before_a_call = profile_a.call_mobile_number
        before_a_verified = user_a.is_phone_verified
        before_b_phone = user_b.phone_number
        before_b_verified = user_b.is_phone_verified

        self.client.force_login(user_a)
        response = self.client.post(
            reverse("profiles:profile_edit"),
            {
                "call_mobile_number": "9123456821",
                "use_same_number_for_call_and_whatsapp": "1",
                "about_description": "Should not save duplicate phone",
            },
        )
        self.assertEqual(response.status_code, 302)
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(
            any("Phone number already registered" in m for m in messages),
            messages,
        )

        user_a.refresh_from_db()
        profile_a.refresh_from_db()
        user_b.refresh_from_db()
        self.assertEqual(user_a.phone_number, before_a_phone)
        self.assertEqual(profile_a.call_mobile_number, before_a_call)
        self.assertEqual(user_a.is_phone_verified, before_a_verified)
        self.assertTrue(user_a.is_phone_verified)
        self.assertEqual(user_b.phone_number, before_b_phone)
        self.assertEqual(user_b.is_phone_verified, before_b_verified)

    def test_profile_edit_allows_unique_phone_and_resets_verification(self):
        user, profile = _make_pandit(
            email="unique-edit@example.com",
            phone="9123456830",
            is_phone_verified=True,
        )
        user.phone_number = profile.call_mobile_number
        user.save(update_fields=["phone_number", "is_phone_verified"])

        self.client.force_login(user)
        response = self.client.post(
            reverse("profiles:profile_edit"),
            {
                "call_mobile_number": "9123456831",
                "use_same_number_for_call_and_whatsapp": "1",
                "about_description": "Legitimate unique phone change",
            },
        )
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        profile.refresh_from_db()
        self.assertEqual(user.phone_number, "9123456831")
        self.assertEqual(profile.call_mobile_number, "9123456831")
        self.assertFalse(user.is_phone_verified)

        issued = self.runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_PANDIT_REGISTRATION,
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
            flow_type=constants.FLOW_PANDIT_REGISTRATION,
            destination="9123456831",
            resend_count=0,
        )
        request.META["HTTP_ACCEPT"] = "application/json"
        with patch(
            "otp_verification.registration.views.build_registration_otp_service",
            return_value=self.service,
        ):
            otp_response = verify_registration_otp(request)
        body = json.loads(otp_response.content.decode("utf-8"))
        self.assertEqual(body["status"], "success")
        user.refresh_from_db()
        self.assertTrue(user.is_phone_verified)
