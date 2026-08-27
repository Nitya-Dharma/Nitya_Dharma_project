"""Minimal Bureau smoke / regression tests.

Isolated to Django's test database (test_nityadharma_db).
OTP and WhatsApp integrations are mocked; email uses locmem.
Does not exercise Pandit, Temple, Ads, or production implementations.
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.http import HttpResponse
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.email_verification import verify_email
from accounts.models import EmailVerificationToken
from bureaus.models import BureauBookingIntent, BureauProfile
from bureaus.utils import (
    get_bureau_for_user,
    get_homepage_bureaus,
    get_visible_bureaus,
    is_profile_complete_for_listing,
)
from otp_verification import constants as otp_constants
from otp_verification.registration.completions import _complete_bureau

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
    phone_number: str = "9876543210",
    address: str = "12 Test Street",
    description: str = "Full bureau description for listing completeness.",
    caste_data: dict | None = None,
    is_active: bool = False,
    is_approved: bool = False,
    is_email_verified: bool = False,
) -> BureauProfile:
    user = _make_user(email=email)
    if caste_data is None:
        caste_data = {"OC": ["brahmin"]}
    return BureauProfile.objects.create(
        user=user,
        bureau_name=bureau_name,
        phone_number=phone_number,
        whatsapp_number="",
        address=address,
        city=city,
        description=description,
        caste_data=caste_data,
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
            patch(
                "accounts.email_verification.create_email_verification"
            ) as create_email_verification,
        ):
            response = self.client.post(register_url, payload)

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.content, b"otp-challenge")
        begin_otp.assert_called_once()
        create_email_verification.assert_not_called()
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

    def test_direct_registration_initiates_email_verification(self):
        """Successful direct Bureau create calls existing create_email_verification once."""
        register_url = reverse("bureaus:bureau_register")
        payload = {
            "bureau_name": "Email Init Bureau",
            "email": "email-init-bureau@example.com",
            "password": "BureauTestPass123!",
            "confirm_password": "BureauTestPass123!",
            "phone_number": "9123456793",
            "address": "9 Email Init Road",
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
            patch(
                "accounts.email_verification.create_email_verification"
            ) as create_email_verification,
        ):
            response = self.client.post(register_url, payload)

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email__iexact=payload["email"])
        profile = BureauProfile.objects.get(user=user)
        create_email_verification.assert_called_once_with(user)
        self.assertEqual(user.role, "user")
        self.assertFalse(profile.is_active)
        self.assertFalse(profile.is_approved)
        self.assertFalse(profile.is_email_verified)

    def test_otp_bureau_completion_initiates_email_verification(self):
        """Successful _complete_bureau calls existing create_email_verification once."""
        payload = {
            "email": "otp-complete-bureau@example.com",
            "password_hash": make_password("BureauTestPass123!"),
            "bureau_name": "OTP Complete Bureau",
            "phone_number": "9123456794",
            "address": "10 OTP Complete Road",
            "city": "Hyderabad",
            "whatsapp_number": "",
        }

        with patch(
            "accounts.email_verification.create_email_verification"
        ) as create_email_verification:
            result = _complete_bureau(payload)

        user = User.objects.get(email__iexact=payload["email"])
        profile = BureauProfile.objects.get(user=user)
        self.assertEqual(result["flow_type"], otp_constants.FLOW_BUREAU_REGISTRATION)
        self.assertEqual(result["user_id"], user.id)
        create_email_verification.assert_called_once_with(user)
        self.assertEqual(user.role, "user")
        self.assertFalse(profile.is_active)
        self.assertFalse(profile.is_approved)
        self.assertFalse(profile.is_email_verified)

    def test_bureau_email_verification_syncs_profile_flag(self):
        """Valid verify_email sets User + BureauProfile email verified flags only."""
        profile = _make_bureau(email="bureau-verify-sync@example.com")
        user = profile.user
        self.assertFalse(user.email_verified)
        self.assertFalse(profile.is_email_verified)
        token = EmailVerificationToken.objects.create(user=user)

        verify_email(token.token)

        user.refresh_from_db()
        profile.refresh_from_db()
        self.assertTrue(user.email_verified)
        self.assertIsNotNone(user.email_verified_at)
        self.assertTrue(profile.is_email_verified)
        self.assertFalse(profile.is_active)
        self.assertFalse(profile.is_approved)
        self.assertEqual(user.role, "user")

    def test_normal_user_email_verification_creates_no_bureau_profile(self):
        """Valid verify_email for a non-bureau user does not create BureauProfile."""
        user = _make_user(email="plain-verify@example.com")
        self.assertFalse(user.email_verified)
        self.assertFalse(BureauProfile.objects.filter(user=user).exists())
        token = EmailVerificationToken.objects.create(user=user)

        verify_email(token.token)

        user.refresh_from_db()
        self.assertTrue(user.email_verified)
        self.assertIsNotNone(user.email_verified_at)
        self.assertFalse(BureauProfile.objects.filter(user=user).exists())

    def test_invalid_expired_used_token_does_not_sync_bureau_flag(self):
        """Invalid, expired, and used tokens leave BureauProfile.is_email_verified False."""
        profile = _make_bureau(email="bureau-bad-token@example.com")
        user = profile.user

        with self.assertRaises(ValidationError):
            verify_email("not-a-real-verification-token")
        profile.refresh_from_db()
        self.assertFalse(profile.is_email_verified)
        self.assertFalse(user.email_verified)

        expired = EmailVerificationToken.objects.create(user=user)
        EmailVerificationToken.objects.filter(pk=expired.pk).update(
            expires_at=timezone.now() - timedelta(hours=1)
        )
        expired.refresh_from_db()
        with self.assertRaises(ValidationError):
            verify_email(expired.token)
        profile.refresh_from_db()
        user.refresh_from_db()
        self.assertFalse(profile.is_email_verified)
        self.assertFalse(user.email_verified)

        used = EmailVerificationToken.objects.create(user=user)
        EmailVerificationToken.objects.filter(pk=used.pk).update(
            is_used=True,
            used_at=timezone.now(),
        )
        used.refresh_from_db()
        with self.assertRaises(ValidationError):
            verify_email(used.token)
        profile.refresh_from_db()
        user.refresh_from_db()
        self.assertFalse(profile.is_email_verified)
        self.assertFalse(user.email_verified)

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

    def test_get_visible_bureaus_requires_listing_completeness(self):
        """Public visibility queryset requires flags plus listing completeness."""
        complete = _make_bureau(
            email="visible-complete@example.com",
            bureau_name="Complete Visible Bureau",
            is_active=True,
            is_approved=True,
            is_email_verified=True,
        )
        missing_description = _make_bureau(
            email="missing-description@example.com",
            bureau_name="Missing Description Bureau",
            description="",
            is_active=True,
            is_approved=True,
            is_email_verified=True,
        )
        missing_phone = _make_bureau(
            email="missing-phone@example.com",
            bureau_name="Missing Phone Bureau",
            phone_number="",
            is_active=True,
            is_approved=True,
            is_email_verified=True,
        )
        missing_address = _make_bureau(
            email="missing-address@example.com",
            bureau_name="Missing Address Bureau",
            address="",
            is_active=True,
            is_approved=True,
            is_email_verified=True,
        )
        missing_city = _make_bureau(
            email="missing-city@example.com",
            bureau_name="Missing City Bureau",
            city="",
            is_active=True,
            is_approved=True,
            is_email_verified=True,
        )
        empty_caste = _make_bureau(
            email="empty-caste@example.com",
            bureau_name="Empty Caste Bureau",
            caste_data={},
            is_active=True,
            is_approved=True,
            is_email_verified=True,
        )
        inactive = _make_bureau(
            email="inactive-complete@example.com",
            bureau_name="Inactive Complete Bureau",
            is_active=False,
            is_approved=True,
            is_email_verified=True,
        )
        unapproved = _make_bureau(
            email="unapproved-complete@example.com",
            bureau_name="Unapproved Complete Bureau",
            is_active=True,
            is_approved=False,
            is_email_verified=True,
        )
        unverified = _make_bureau(
            email="unverified-complete@example.com",
            bureau_name="Unverified Complete Bureau",
            is_active=True,
            is_approved=True,
            is_email_verified=False,
        )

        qs = get_visible_bureaus()
        self.assertIsInstance(qs, QuerySet)
        visible_ids = set(qs.values_list("id", flat=True))
        self.assertIn(complete.id, visible_ids)
        self.assertNotIn(missing_description.id, visible_ids)
        self.assertNotIn(missing_phone.id, visible_ids)
        self.assertNotIn(missing_address.id, visible_ids)
        self.assertNotIn(missing_city.id, visible_ids)
        self.assertNotIn(empty_caste.id, visible_ids)
        self.assertNotIn(inactive.id, visible_ids)
        self.assertNotIn(unapproved.id, visible_ids)
        self.assertNotIn(unverified.id, visible_ids)

        self.assertTrue(is_profile_complete_for_listing(complete))
        self.assertFalse(is_profile_complete_for_listing(missing_description))
        self.assertFalse(is_profile_complete_for_listing(empty_caste))

        list_response = self.client.get(reverse("bureaus:bureau_list"))
        self.assertEqual(list_response.status_code, 200)
        body = list_response.content.decode("utf-8", errors="ignore")
        self.assertIn("Complete Visible Bureau", body)
        self.assertNotIn("Missing Description Bureau", body)
        self.assertNotIn("Empty Caste Bureau", body)

        incomplete_detail = self.client.get(
            reverse(
                "bureaus:bureau_detail",
                kwargs={"public_id": missing_description.public_id},
            )
        )
        self.assertEqual(incomplete_detail.status_code, 302)
        self.assertTrue(incomplete_detail["Location"].endswith("/bureaus/"))

        homepage = get_homepage_bureaus()
        homepage_ids = {b.id for b in homepage}
        self.assertIn(complete.id, homepage_ids)
        self.assertNotIn(missing_description.id, homepage_ids)
        self.assertNotIn(empty_caste.id, homepage_ids)

    def test_incomplete_public_profile_does_not_block_owner_lookup(self):
        """Owner access helper stays flag-based; completeness is public-only."""
        incomplete = _make_bureau(
            email="owner-incomplete@example.com",
            bureau_name="Owner Incomplete Bureau",
            description="",
            caste_data={},
            is_active=True,
            is_approved=True,
            is_email_verified=True,
        )
        self.assertNotIn(incomplete.id, get_visible_bureaus().values_list("id", flat=True))
        self.assertEqual(get_bureau_for_user(incomplete.user).id, incomplete.id)

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
