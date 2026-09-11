"""Focused Bureau duplicate-phone enforcement runtime tests."""

from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.core.cache import cache
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

from accounts.phone_utils import normalize_phone_number
from bureaus.models import BureauProfile
from bureaus.views import bureau_profile_edit_view, bureau_register_skip_phone_otp
from otp_verification import constants
from otp_verification.registration.completions import CompletionError, _complete_bureau
from otp_verification.registration.session import store_pending_registration

User = get_user_model()
LOCMEM_EMAIL = "django.core.mail.backends.locmem.EmailBackend"
TAKEN_PHONE = "9876543299"
TAKEN_PHONE_E164 = "919876543299"
UNIQUE_PHONE = "9876543208"


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


def _bureau_register_payload(*, email, phone):
    return {
        "bureau_name": "Dup Phone Bureau",
        "email": email,
        "password": "BureauTestPass123!",
        "confirm_password": "BureauTestPass123!",
        "phone_number": phone,
        "address": "1 Dup Road",
        "city": "Hyderabad",
        "whatsapp_number": "",
    }


def _bureau_completion_payload(*, email, phone):
    return {
        "bureau_name": "Dup Complete Bureau",
        "email": email,
        "password_hash": make_password("BureauTestPass123!"),
        "phone_number": phone,
        "address": "1 Complete Road",
        "city": "Hyderabad",
        "whatsapp_number": "",
    }


def _make_email_verified_bureau(
    *,
    email,
    phone,
    is_phone_verified=True,
):
    user = User.objects.create_user(
        email=email,
        username=f"u_{email.split('@')[0][:20]}",
        password="BureauTestPass123!",
        role="user",
        status="active",
        is_active=True,
        phone_number=phone,
        is_phone_verified=is_phone_verified,
    )
    profile = BureauProfile.objects.create(
        user=user,
        bureau_name="Edit Dup Bureau",
        phone_number=phone,
        address="1 Edit Road",
        city="Hyderabad",
        whatsapp_number="",
        description="Bureau description for edit profile access.",
        caste_data={"OC": ["Brahmin"]},
        is_active=False,
        is_approved=False,
        is_email_verified=True,
    )
    return user, profile


@override_settings(EMAIL_BACKEND=LOCMEM_EMAIL)
class BureauDuplicatePhoneTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.factory = RequestFactory()
        self.owner = User.objects.create_user(
            email="bureau-phone-owner@example.com",
            username="bureau-phone-owner",
            password="Password123!",
            phone_number=TAKEN_PHONE,
        )
        self.assertEqual(
            normalize_phone_number(self.owner.phone_number),
            normalize_phone_number(TAKEN_PHONE),
        )

    def test_registration_rejects_duplicate_phone_without_creating_bureau(self):
        users_before = User.objects.count()
        bureaus_before = BureauProfile.objects.count()
        payload = _bureau_register_payload(
            email="dup-register@example.com",
            phone=TAKEN_PHONE,
        )
        with (
            patch(
                "otp_verification.registration.factory.is_registration_otp_required",
                return_value=True,
            ),
            patch(
                "otp_verification.registration.gate.begin_otp_or_continue",
                side_effect=AssertionError("OTP must not start for duplicate phone"),
            ),
        ):
            response = self.client.post(reverse("bureaus:bureau_register"), payload)
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response, "Phone number already registered", status_code=400
        )
        self.assertFalse(User.objects.filter(email="dup-register@example.com").exists())
        self.assertEqual(User.objects.count(), users_before)
        self.assertEqual(BureauProfile.objects.count(), bureaus_before)

    def test_skip_otp_rejects_duplicate_phone_without_creating_bureau(self):
        users_before = User.objects.count()
        bureaus_before = BureauProfile.objects.count()
        request = _prepare_request(
            self.factory,
            path=reverse("bureaus:bureau_register_skip_phone_otp"),
        )
        store_pending_registration(
            request,
            flow_type=constants.FLOW_BUREAU_REGISTRATION,
            challenge_id="dup-pending-challenge",
            destination=TAKEN_PHONE,
            payload={
                "bureau_name": "Skip Dup Bureau",
                "email": "dup-skip@example.com",
                "password": "BureauTestPass123!",
                "phone_number": TAKEN_PHONE,
                "address": "1 Skip Road",
                "city": "Hyderabad",
                "whatsapp_number": "",
            },
            resume_path="/bureaus/register/",
        )
        response = bureau_register_skip_phone_otp(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("bureaus:bureau_register"))
        self.assertFalse(User.objects.filter(email="dup-skip@example.com").exists())
        self.assertEqual(User.objects.count(), users_before)
        self.assertEqual(BureauProfile.objects.count(), bureaus_before)

    def test_complete_bureau_rejects_duplicate_phone(self):
        users_before = User.objects.count()
        bureaus_before = BureauProfile.objects.count()
        with self.assertRaises(CompletionError) as ctx:
            _complete_bureau(
                _bureau_completion_payload(
                    email="dup-complete@example.com",
                    phone=TAKEN_PHONE,
                )
            )
        self.assertEqual(str(ctx.exception), "Phone number already registered")
        self.assertFalse(User.objects.filter(email="dup-complete@example.com").exists())
        self.assertEqual(User.objects.count(), users_before)
        self.assertEqual(BureauProfile.objects.count(), bureaus_before)

    def test_profile_edit_rejects_another_users_phone(self):
        user, profile = _make_email_verified_bureau(
            email="bureau-edit-a@example.com",
            phone="9876543201",
            is_phone_verified=True,
        )
        before_phone = user.phone_number
        before_profile_phone = profile.phone_number
        before_verified = user.is_phone_verified
        before_owner_phone = self.owner.phone_number

        request = _prepare_request(
            self.factory,
            path=reverse("bureaus:bureau_profile_edit"),
            data={
                "description": profile.description,
                "phone_number": TAKEN_PHONE,
                "whatsapp_number": "",
                "address": profile.address,
                "city": profile.city,
                "caste_data": '{"OC": ["Brahmin"]}',
            },
            user=user,
        )
        response = bureau_profile_edit_view(request)
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response, "Phone number already registered", status_code=400
        )
        user.refresh_from_db()
        profile.refresh_from_db()
        self.owner.refresh_from_db()
        self.assertEqual(user.phone_number, before_phone)
        self.assertEqual(profile.phone_number, before_profile_phone)
        self.assertEqual(user.is_phone_verified, before_verified)
        self.assertTrue(user.is_phone_verified)
        self.assertEqual(self.owner.phone_number, before_owner_phone)

    def test_profile_edit_allows_unique_phone_and_resets_verification(self):
        user, profile = _make_email_verified_bureau(
            email="bureau-unique-edit@example.com",
            phone="9876543202",
            is_phone_verified=True,
        )
        request = _prepare_request(
            self.factory,
            path=reverse("bureaus:bureau_profile_edit"),
            data={
                "description": profile.description,
                "phone_number": UNIQUE_PHONE,
                "whatsapp_number": "",
                "address": profile.address,
                "city": profile.city,
                "caste_data": '{"OC": ["Brahmin"]}',
            },
            user=user,
        )
        response = bureau_profile_edit_view(request)
        self.assertIn(response.status_code, (200, 302))
        user.refresh_from_db()
        profile.refresh_from_db()
        self.assertEqual(user.phone_number, UNIQUE_PHONE)
        self.assertEqual(profile.phone_number, UNIQUE_PHONE)
        self.assertFalse(user.is_phone_verified)

    def test_normalize_equivalence_blocks_91_prefixed_duplicate(self):
        self.assertEqual(
            normalize_phone_number(TAKEN_PHONE),
            normalize_phone_number(TAKEN_PHONE_E164),
        )
        users_before = User.objects.count()
        payload = _bureau_register_payload(
            email="dup-91@example.com",
            phone=TAKEN_PHONE_E164,
        )
        with (
            patch(
                "otp_verification.registration.factory.is_registration_otp_required",
                return_value=True,
            ),
            patch(
                "otp_verification.registration.gate.begin_otp_or_continue",
                side_effect=AssertionError("OTP must not start for duplicate phone"),
            ),
        ):
            response = self.client.post(reverse("bureaus:bureau_register"), payload)
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response, "Phone number already registered", status_code=400
        )
        self.assertEqual(User.objects.count(), users_before)
        self.assertFalse(User.objects.filter(email="dup-91@example.com").exists())
