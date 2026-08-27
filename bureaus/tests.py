"""Minimal Bureau smoke / regression tests.

Isolated to Django's test database (test_nityadharma_db).
OTP and WhatsApp integrations are mocked; email uses locmem.
Does not exercise Pandit, Temple, Ads, or production implementations.
"""

from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.http import HttpResponse
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from bureaus.models import BureauBookingIntent, BureauProfile

User = get_user_model()

LOCMEM_EMAIL = "django.core.mail.backends.locmem.EmailBackend"


def _make_user(*, email: str, password: str = "BureauTestPass123!") -> User:
    return User.objects.create_user(
        email=email,
        password=password,
        username=f"u_{email.split('@')[0][:20]}",
        role="user",
        status="active",
        is_active=True,
    )


def _make_bureau(
    *,
    email: str,
    bureau_name: str = "Test Marriage Bureau",
    city: str = "Hyderabad",
    is_active: bool = False,
    is_approved: bool = False,
    is_email_verified: bool = False,
) -> BureauProfile:
    user = _make_user(email=email)
    return BureauProfile.objects.create(
        user=user,
        bureau_name=bureau_name,
        phone_number="9876543210",
        whatsapp_number="",
        address="12 Test Street",
        city=city,
        description="Full bureau description for listing completeness.",
        caste_data={"OC": ["brahmin"]},
        is_active=is_active,
        is_approved=is_approved,
        is_email_verified=is_email_verified,
    )


@override_settings(EMAIL_BACKEND=LOCMEM_EMAIL)
class BureauSmokeTests(TestCase):
    """Eight pre-release Bureau smoke checks."""

    def setUp(self):
        cache.clear()
        self.client = Client()

    def test_registration_requires_otp_gate_when_enabled(self):
        """When OTP is required, registration pauses and creates no User/Bureau."""
        otp_response = HttpResponse("otp-challenge", status=202)
        register_url = reverse("bureaus:bureau_register")
        payload = {
            "bureau_name": "OTP Gate Bureau",
            "email": "otp-gate-bureau@example.com",
            "password": "BureauTestPass123!",
            "confirm_password": "BureauTestPass123!",
            "phone_number": "9123456780",
            "address": "1 Gate Road",
            "city": "Hyderabad",
            "whatsapp_number": "",
        }

        with (
            patch(
                "otp_verification.registration.factory.is_registration_otp_required",
                return_value=True,
            ),
            patch(
                "otp_verification.registration.gate.begin_otp_or_continue",
                return_value=otp_response,
            ) as begin_otp,
        ):
            response = self.client.post(register_url, payload)

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.content, b"otp-challenge")
        begin_otp.assert_called_once()
        self.assertFalse(User.objects.filter(email__iexact=payload["email"]).exists())
        self.assertFalse(
            BureauProfile.objects.filter(bureau_name=payload["bureau_name"]).exists()
        )

    def test_valid_registration_creates_inactive_bureau(self):
        """Valid registration creates User + inactive/unapproved BureauProfile."""
        register_url = reverse("bureaus:bureau_register")
        payload = {
            "bureau_name": "Fresh Bureau",
            "email": "fresh-bureau@example.com",
            "password": "BureauTestPass123!",
            "confirm_password": "BureauTestPass123!",
            "phone_number": "9123456781",
            "address": "2 Fresh Road",
            "city": "Chennai",
            "whatsapp_number": "",
        }

        with (
            patch(
                "otp_verification.registration.factory.is_registration_otp_required",
                return_value=False,
            ),
            patch(
                "otp_verification.registration.session.consume_phone_verified_session",
                return_value=None,
            ),
        ):
            response = self.client.post(register_url, payload)

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email__iexact=payload["email"])
        profile = BureauProfile.objects.get(user=user)
        self.assertEqual(profile.bureau_name, "Fresh Bureau")
        self.assertFalse(profile.is_active)
        self.assertFalse(profile.is_approved)
        self.assertFalse(profile.is_email_verified)

    def test_registration_rejects_missing_required_fields(self):
        """Incomplete required registration input returns HTTP 400 and creates nothing."""
        register_url = reverse("bureaus:bureau_register")
        payload = {
            "bureau_name": "",
            "email": "",
            "password": "",
            "confirm_password": "",
            "phone_number": "",
            "address": "",
            "city": "",
            "whatsapp_number": "",
        }

        with patch(
            "otp_verification.registration.factory.is_registration_otp_required",
            return_value=False,
        ):
            response = self.client.post(register_url, payload)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(BureauProfile.objects.count(), 0)

    def test_registration_rejects_empty_email(self):
        """Empty email is rejected by current required-field validation."""
        register_url = reverse("bureaus:bureau_register")
        payload = {
            "bureau_name": "No Email Bureau",
            "email": "   ",
            "password": "BureauTestPass123!",
            "confirm_password": "BureauTestPass123!",
            "phone_number": "9123456782",
            "address": "3 Empty Email Road",
            "city": "Hyderabad",
            "whatsapp_number": "",
        }

        with patch(
            "otp_verification.registration.factory.is_registration_otp_required",
            return_value=False,
        ):
            response = self.client.post(register_url, payload)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            BureauProfile.objects.filter(bureau_name=payload["bureau_name"]).exists()
        )

    def test_registration_rejects_weak_password(self):
        """Django validate_password rejects a weak password with HTTP 400."""
        register_url = reverse("bureaus:bureau_register")
        payload = {
            "bureau_name": "Weak Password Bureau",
            "email": "weak-password-bureau@example.com",
            "password": "123",
            "confirm_password": "123",
            "phone_number": "9123456783",
            "address": "4 Weak Pass Road",
            "city": "Hyderabad",
            "whatsapp_number": "",
        }

        with patch(
            "otp_verification.registration.factory.is_registration_otp_required",
            return_value=False,
        ):
            response = self.client.post(register_url, payload)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(email__iexact=payload["email"]).exists())
        self.assertFalse(
            BureauProfile.objects.filter(bureau_name=payload["bureau_name"]).exists()
        )

    def test_registration_rejects_duplicate_email(self):
        """An existing email cannot register another Bureau account."""
        _make_user(email="taken-bureau@example.com")
        register_url = reverse("bureaus:bureau_register")
        payload = {
            "bureau_name": "Duplicate Email Bureau",
            "email": "taken-bureau@example.com",
            "password": "BureauTestPass123!",
            "confirm_password": "BureauTestPass123!",
            "phone_number": "9123456784",
            "address": "5 Duplicate Road",
            "city": "Hyderabad",
            "whatsapp_number": "",
        }

        with patch(
            "otp_verification.registration.factory.is_registration_otp_required",
            return_value=False,
        ):
            response = self.client.post(register_url, payload)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.filter(email__iexact=payload["email"]).count(), 1)
        self.assertFalse(
            BureauProfile.objects.filter(bureau_name=payload["bureau_name"]).exists()
        )

    def test_registration_rejects_case_insensitive_duplicate_email(self):
        """email__iexact uniqueness rejects a differently cased existing email."""
        _make_user(email="Example@Email.com")
        register_url = reverse("bureaus:bureau_register")
        payload = {
            "bureau_name": "Case Dup Bureau",
            "email": "example@email.com",
            "password": "BureauTestPass123!",
            "confirm_password": "BureauTestPass123!",
            "phone_number": "9123456785",
            "address": "6 Case Dup Road",
            "city": "Hyderabad",
            "whatsapp_number": "",
        }

        with patch(
            "otp_verification.registration.factory.is_registration_otp_required",
            return_value=False,
        ):
            response = self.client.post(register_url, payload)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.filter(email__iexact="example@email.com").count(), 1)
        self.assertFalse(
            BureauProfile.objects.filter(bureau_name=payload["bureau_name"]).exists()
        )

    def test_registration_rate_limit_returns_429(self):
        """Fourth valid attempt from the same IP is rate-limited (limit=3 / 600s)."""
        register_url = reverse("bureaus:bureau_register")

        def _payload(n: int) -> dict:
            return {
                "bureau_name": f"Rate Limit Bureau {n}",
                "email": f"rate-limit-bureau-{n}@example.com",
                "password": "BureauTestPass123!",
                "confirm_password": "BureauTestPass123!",
                "phone_number": f"91234567{80 + n:02d}",
                "address": f"{n} Rate Limit Road",
                "city": "Hyderabad",
                "whatsapp_number": "",
            }

        with (
            patch(
                "otp_verification.registration.factory.is_registration_otp_required",
                return_value=False,
            ),
            patch(
                "otp_verification.registration.session.consume_phone_verified_session",
                return_value=None,
            ),
        ):
            for n in range(1, 4):
                response = self.client.post(register_url, _payload(n))
                self.assertEqual(response.status_code, 201, msg=f"attempt {n}")
            limited = self.client.post(register_url, _payload(4))

        self.assertEqual(limited.status_code, 429)
        self.assertFalse(
            User.objects.filter(email__iexact="rate-limit-bureau-4@example.com").exists()
        )
        self.assertFalse(
            BureauProfile.objects.filter(bureau_name="Rate Limit Bureau 4").exists()
        )

    def test_registration_sets_role_user_and_inactive_flags(self):
        """Successful registration uses role=user (never bureau) and safe initial flags."""
        register_url = reverse("bureaus:bureau_register")
        payload = {
            "bureau_name": "Role Flags Bureau",
            "email": "role-flags-bureau@example.com",
            "password": "BureauTestPass123!",
            "confirm_password": "BureauTestPass123!",
            "phone_number": "9123456790",
            "address": "7 Role Flags Road",
            "city": "Hyderabad",
            "whatsapp_number": "",
        }

        with (
            patch(
                "otp_verification.registration.factory.is_registration_otp_required",
                return_value=False,
            ),
            patch(
                "otp_verification.registration.session.consume_phone_verified_session",
                return_value=None,
            ),
        ):
            response = self.client.post(register_url, payload)

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email__iexact=payload["email"])
        profile = BureauProfile.objects.get(user=user)
        self.assertEqual(user.role, "user")
        self.assertNotEqual(user.role, "bureau")
        self.assertFalse(profile.is_active)
        self.assertFalse(profile.is_approved)
        self.assertFalse(profile.is_email_verified)
        self.assertEqual(profile.user_id, user.id)

    def test_registration_stores_optional_whatsapp_number(self):
        """Optional whatsapp_number is stored on BureauProfile as profile data only."""
        register_url = reverse("bureaus:bureau_register")
        payload = {
            "bureau_name": "WhatsApp Field Bureau",
            "email": "wa-field-bureau@example.com",
            "password": "BureauTestPass123!",
            "confirm_password": "BureauTestPass123!",
            "phone_number": "9123456791",
            "address": "8 WhatsApp Field Road",
            "city": "Hyderabad",
            "whatsapp_number": "9123456792",
        }

        with (
            patch(
                "otp_verification.registration.factory.is_registration_otp_required",
                return_value=False,
            ),
            patch(
                "otp_verification.registration.session.consume_phone_verified_session",
                return_value=None,
            ),
        ):
            response = self.client.post(register_url, payload)

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email__iexact=payload["email"])
        profile = BureauProfile.objects.get(user=user)
        self.assertEqual(profile.whatsapp_number, "9123456792")
        self.assertFalse(profile.is_active)
        self.assertFalse(profile.is_approved)
        self.assertFalse(profile.is_email_verified)

    def test_unauthorized_dashboard_access_rejected(self):
        """Anonymous and non-bureau users cannot open the Bureau dashboard."""
        dashboard_url = reverse("bureaus_dashboard:bureau_dashboard")

        anon = self.client.get(dashboard_url)
        self.assertEqual(anon.status_code, 302)
        self.assertIn("/accounts/login/", anon["Location"])

        plain = _make_user(email="plain-user@example.com")
        self.client.force_login(plain)
        denied = self.client.get(dashboard_url)
        self.assertEqual(denied.status_code, 302)
        self.assertNotIn("/dashboard/bureau/", denied["Location"])

    def test_visibility_gating_hides_unapproved_bureau(self):
        """Only active+approved+email_verified bureaus appear on the public list."""
        visible = _make_bureau(
            email="visible-bureau@example.com",
            bureau_name="Visible Bureau",
            is_active=True,
            is_approved=True,
            is_email_verified=True,
        )
        hidden = _make_bureau(
            email="hidden-bureau@example.com",
            bureau_name="Hidden Bureau",
            is_active=False,
            is_approved=False,
            is_email_verified=False,
        )

        list_response = self.client.get(reverse("bureaus:bureau_list"))
        self.assertEqual(list_response.status_code, 200)
        body = list_response.content.decode("utf-8", errors="ignore")
        self.assertIn("Visible Bureau", body)
        self.assertNotIn("Hidden Bureau", body)

        hidden_detail = self.client.get(
            reverse("bureaus:bureau_detail", kwargs={"public_id": hidden.public_id})
        )
        self.assertEqual(hidden_detail.status_code, 302)
        self.assertTrue(hidden_detail["Location"].endswith("/bureaus/"))

        visible_detail = self.client.get(
            reverse("bureaus:bureau_detail", kwargs={"public_id": visible.public_id})
        )
        self.assertEqual(visible_detail.status_code, 200)

    def test_public_profile_visible_bureau_ok(self):
        """A fully visible bureau public profile returns HTTP 200."""
        bureau = _make_bureau(
            email="public-ok-bureau@example.com",
            bureau_name="Public OK Bureau",
            is_active=True,
            is_approved=True,
            is_email_verified=True,
        )
        response = self.client.get(
            reverse("bureaus:bureau_detail", kwargs={"public_id": bureau.public_id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Public OK Bureau")

    def test_booking_intent_created_by_logged_in_user(self):
        """Logged-in user can create a BureauBookingIntent on a visible bureau."""
        bureau = _make_bureau(
            email="intent-owner@example.com",
            bureau_name="Intent Owner Bureau",
            is_active=True,
            is_approved=True,
            is_email_verified=True,
        )
        requester = _make_user(email="intent-requester@example.com")
        self.client.force_login(requester)

        url = reverse(
            "bureaus:bureau_intent", kwargs={"public_id": bureau.public_id}
        )
        response = self.client.post(
            url,
            {
                "name": "Seeker Name",
                "phone": "9988776655",
                "message": "Looking for matrimony assistance.",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            BureauBookingIntent.objects.filter(
                bureau=bureau,
                user=requester,
                name="Seeker Name",
                phone="9988776655",
            ).exists()
        )

    def test_booking_intent_rejected_when_anonymous(self):
        """Anonymous booking-intent POST is rejected (login required)."""
        bureau = _make_bureau(
            email="anon-intent-bureau@example.com",
            bureau_name="Anon Intent Bureau",
            is_active=True,
            is_approved=True,
            is_email_verified=True,
        )
        url = reverse(
            "bureaus:bureau_intent", kwargs={"public_id": bureau.public_id}
        )
        response = self.client.post(
            url,
            {
                "name": "Anonymous Seeker",
                "phone": "8877665544",
                "message": "Should not be created.",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])
        self.assertFalse(
            BureauBookingIntent.objects.filter(bureau=bureau).exists()
        )

    def test_profile_edit_unauthorized_rejected(self):
        """Anonymous and non-bureau users cannot open profile edit."""
        edit_url = reverse("bureaus:bureau_profile_edit")

        anon = self.client.get(edit_url)
        self.assertEqual(anon.status_code, 302)
        self.assertIn("/accounts/login/", anon["Location"])

        plain = _make_user(email="edit-denied@example.com")
        self.client.force_login(plain)
        denied = self.client.get(edit_url)
        self.assertEqual(denied.status_code, 302)
        self.assertNotIn("/bureaus/profile/edit/", denied["Location"])
