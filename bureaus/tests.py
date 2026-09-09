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
from bureaus.models import BureauBookingIntent, BureauProfile, BureauReview
from bureaus.utils import (
    get_bureau_for_user,
    get_homepage_bureaus,
    get_owned_email_verified_bureau,
    get_visible_bureaus,
    is_profile_complete_for_listing,
)
from notifications.constants import NOTIFICATION_TYPE_BOOKING_INTENT
from notifications.models import Notification
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

    def test_visible_bureau_detail_restores_direct_whatsapp_cta(self):
        """Public detail renders 200 with the pre-47aa575 direct wa.me CTA."""
        with_whatsapp = _make_bureau(
            email="visible-wa@example.com",
            bureau_name="Visible WhatsApp Bureau",
            is_active=True,
            is_approved=True,
            is_email_verified=True,
        )
        stored_whatsapp = "9123456792"
        with_whatsapp.whatsapp_number = stored_whatsapp
        with_whatsapp.save(update_fields=["whatsapp_number"])

        without_whatsapp = _make_bureau(
            email="visible-no-wa@example.com",
            bureau_name="Visible No WhatsApp Bureau",
            is_active=True,
            is_approved=True,
            is_email_verified=True,
        )

        with_response = self.client.get(
            reverse("bureaus:bureau_detail", kwargs={"public_id": with_whatsapp.public_id})
        )
        self.assertEqual(with_response.status_code, 200)
        with_body = with_response.content.decode("utf-8", errors="ignore")
        expected_href = f'href="https://wa.me/{stored_whatsapp}"'
        self.assertIn(expected_href, with_body)
        self.assertRegex(
            with_body,
            rf'{expected_href} target="_blank" rel="noopener noreferrer"[^>]*>\s*WhatsApp\s*<',
        )
        self.assertNotIn("whatsapp_cta_link.html", with_body)
        self.assertNotIn("track_whatsapp", with_body)

        without_response = self.client.get(
            reverse(
                "bureaus:bureau_detail",
                kwargs={"public_id": without_whatsapp.public_id},
            )
        )
        self.assertEqual(without_response.status_code, 200)
        without_body = without_response.content.decode("utf-8", errors="ignore")
        self.assertNotIn("https://wa.me/", without_body)

        city_response = self.client.get(
            reverse("bureaus:bureau_city", kwargs={"city": "hyderabad"})
        )
        self.assertEqual(city_response.status_code, 200)

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


class BureauReviewSubmissionTests(TestCase):
    """Regression tests for bureau_review_submit_view (test-only slice)."""

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.reviewer = _make_user(email="review-submitter@example.com")
        self.bureau = _make_bureau(
            email="review-target-bureau@example.com",
            bureau_name="Review Target Bureau",
            is_active=True,
            is_approved=True,
            is_email_verified=True,
        )
        self.review_url = reverse(
            "bureaus:bureau_review",
            kwargs={"public_id": self.bureau.public_id},
        )

    def test_anonymous_submission_rejected(self):
        response = self.client.post(
            self.review_url,
            {"rating": "5", "review_text": "Should not be saved."},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])
        self.assertIn(f"/bureaus/{self.bureau.public_id}/", response["Location"])
        self.assertFalse(BureauReview.objects.filter(bureau=self.bureau).exists())

    def test_valid_review_for_visible_bureau_creates_and_upserts(self):
        self.client.force_login(self.reviewer)
        response = self.client.post(
            self.review_url,
            {"rating": "4", "review_text": "Good experience."},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], f"/bureaus/{self.bureau.public_id}/")
        review = BureauReview.objects.get(bureau=self.bureau, user=self.reviewer)
        self.assertEqual(review.rating, 4)
        self.assertEqual(review.review_text, "Good experience.")

        response = self.client.post(
            self.review_url,
            {"rating": "5", "review_text": "Updated review."},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            BureauReview.objects.filter(bureau=self.bureau, user=self.reviewer).count(),
            1,
        )
        review.refresh_from_db()
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.review_text, "Updated review.")

    def test_hidden_bureau_rejects_review(self):
        hidden = _make_bureau(
            email="hidden-review-bureau@example.com",
            is_active=False,
            is_approved=False,
            is_email_verified=False,
        )
        url = reverse("bureaus:bureau_review", kwargs={"public_id": hidden.public_id})
        self.client.force_login(self.reviewer)
        response = self.client.post(
            url,
            {"rating": "5", "review_text": "Should not be saved."},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/bureaus/")
        self.assertFalse(BureauReview.objects.filter(bureau=hidden).exists())

    def test_invalid_rating_rejected(self):
        self.client.force_login(self.reviewer)
        response = self.client.post(
            self.review_url,
            {"rating": "99", "review_text": "Invalid rating."},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], f"/bureaus/{self.bureau.public_id}/")
        self.assertFalse(BureauReview.objects.filter(bureau=self.bureau).exists())

    def test_rate_limit_enforced(self):
        self.client.force_login(self.reviewer)
        for i in range(3):
            response = self.client.post(
                self.review_url,
                {"rating": str(i + 1), "review_text": f"Review attempt {i + 1}."},
            )
            self.assertEqual(response.status_code, 302, msg=f"attempt {i + 1}")
            self.assertEqual(response["Location"], f"/bureaus/{self.bureau.public_id}/")

        limited = self.client.post(
            self.review_url,
            {"rating": "5", "review_text": "Should be rate limited."},
        )
        self.assertEqual(limited.status_code, 302)
        self.assertEqual(limited["Location"], f"/bureaus/{self.bureau.public_id}/")
        self.assertEqual(
            BureauReview.objects.filter(bureau=self.bureau, user=self.reviewer).count(),
            1,
        )

    def test_submission_does_not_mutate_lifecycle_flags(self):
        self.client.force_login(self.reviewer)
        before = {
            "is_email_verified": self.bureau.is_email_verified,
            "is_approved": self.bureau.is_approved,
            "is_active": self.bureau.is_active,
        }
        response = self.client.post(
            self.review_url,
            {"rating": "5", "review_text": "Lifecycle check."},
        )
        self.assertEqual(response.status_code, 302)
        self.bureau.refresh_from_db()
        self.assertEqual(self.bureau.is_email_verified, before["is_email_verified"])
        self.assertEqual(self.bureau.is_approved, before["is_approved"])
        self.assertEqual(self.bureau.is_active, before["is_active"])


class BureauBookingIntentSubmissionTests(TestCase):
    """Regression tests for bureau_booking_intent_view (test-only slice)."""

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.requester = _make_user(email="booking-intent-requester@example.com")
        self.bureau = _make_bureau(
            email="booking-intent-target@example.com",
            bureau_name="Booking Intent Target Bureau",
            is_active=True,
            is_approved=True,
            is_email_verified=True,
        )
        self.intent_url = reverse(
            "bureaus:bureau_intent",
            kwargs={"public_id": self.bureau.public_id},
        )
        self.valid_payload = {
            "name": "Booking Seeker",
            "phone": "9988776655",
            "message": "Looking for matrimony assistance.",
        }

    def test_anonymous_submission_rejected(self):
        response = self.client.post(self.intent_url, self.valid_payload)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])
        self.assertFalse(
            BureauBookingIntent.objects.filter(bureau=self.bureau).exists()
        )

    def test_visible_bureau_submission_creates_intent(self):
        self.client.force_login(self.requester)
        response = self.client.post(self.intent_url, self.valid_payload)
        self.assertEqual(response.status_code, 302)
        self.assertIn(f"/bureaus/{self.bureau.public_id}/", response["Location"])
        intent = BureauBookingIntent.objects.get(
            bureau=self.bureau,
            user=self.requester,
        )
        self.assertEqual(intent.name, "Booking Seeker")
        self.assertEqual(intent.phone, "9988776655")
        self.assertEqual(intent.message, "Looking for matrimony assistance.")

    def test_hidden_bureau_rejects_submission(self):
        hidden = _make_bureau(
            email="booking-intent-hidden@example.com",
            is_active=False,
            is_approved=False,
            is_email_verified=False,
        )
        url = reverse(
            "bureaus:bureau_intent",
            kwargs={"public_id": hidden.public_id},
        )
        self.client.force_login(self.requester)
        response = self.client.post(
            url,
            {
                "name": "Hidden Seeker",
                "phone": "8877665544",
                "message": "Should not be created.",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/bureaus/")
        self.assertFalse(
            BureauBookingIntent.objects.filter(bureau=hidden).exists()
        )

    def test_submission_does_not_mutate_lifecycle_flags(self):
        self.client.force_login(self.requester)
        before = {
            "is_email_verified": self.bureau.is_email_verified,
            "is_approved": self.bureau.is_approved,
            "is_active": self.bureau.is_active,
        }
        response = self.client.post(self.intent_url, self.valid_payload)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            BureauBookingIntent.objects.filter(
                bureau=self.bureau,
                user=self.requester,
            ).exists()
        )
        self.bureau.refresh_from_db()
        self.assertEqual(self.bureau.is_email_verified, before["is_email_verified"])
        self.assertEqual(self.bureau.is_approved, before["is_approved"])
        self.assertEqual(self.bureau.is_active, before["is_active"])


@override_settings(EMAIL_BACKEND=LOCMEM_EMAIL)
class BureauOwnerProfileEditAuthTests(TestCase):
    """Owner profile-edit auth: ownership + email verified; not approval/activation."""

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.edit_url = reverse("bureaus:bureau_profile_edit")

    def _post_profile(self, **overrides):
        payload = {
            "description": "Updated bureau description for owner edit.",
            "phone_number": "9876543210",
            "whatsapp_number": "",
            "address": "99 Owner Edit Road",
            "city": "Hyderabad",
            "caste_data": '{"OC": ["brahmin"]}',
        }
        payload.update(overrides)
        return self.client.post(self.edit_url, payload)

    def test_verified_owner_unapproved_inactive_can_open_edit(self):
        bureau = _make_bureau(
            email="owner-edit-ok@example.com",
            is_active=False,
            is_approved=False,
            is_email_verified=True,
        )
        self.client.force_login(bureau.user)
        response = self.client.get(self.edit_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("bureau_profile", response.context)
        self.assertEqual(response.context["bureau_profile"].id, bureau.id)
        self.assertContains(response, 'name="phone_number"')
        self.assertContains(response, 'name="whatsapp_number"')
        self.assertContains(response, bureau.phone_number)
        self.assertNotContains(response, "whatsapp_verification/_widget.html")
        self.assertNotContains(response, "wa_subject_type")

    def test_verified_owner_incomplete_can_open_edit(self):
        bureau = _make_bureau(
            email="owner-edit-incomplete@example.com",
            description="",
            caste_data={},
            is_active=False,
            is_approved=False,
            is_email_verified=True,
        )
        self.client.force_login(bureau.user)
        response = self.client.get(self.edit_url)
        self.assertEqual(response.status_code, 200)

    def test_unverified_owner_denied(self):
        bureau = _make_bureau(
            email="owner-edit-unverified@example.com",
            is_active=False,
            is_approved=False,
            is_email_verified=False,
        )
        self.client.force_login(bureau.user)
        response = self.client.get(self.edit_url)
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("/bureaus/profile/edit/", response["Location"])

    def test_non_owner_and_anonymous_denied(self):
        _make_bureau(
            email="owner-edit-target@example.com",
            is_active=False,
            is_approved=False,
            is_email_verified=True,
        )
        anon = self.client.get(self.edit_url)
        self.assertEqual(anon.status_code, 302)
        self.assertIn("/accounts/login/", anon["Location"])

        other = _make_user(email="owner-edit-other@example.com")
        self.client.force_login(other)
        denied = self.client.get(self.edit_url)
        self.assertEqual(denied.status_code, 302)
        self.assertNotIn("/bureaus/profile/edit/", denied["Location"])

    def test_owner_edit_preserves_lifecycle_flags_and_ownership(self):
        bureau = _make_bureau(
            email="owner-edit-flags@example.com",
            description="",
            caste_data={},
            is_active=False,
            is_approved=False,
            is_email_verified=True,
        )
        owner_id = bureau.user_id
        self.client.force_login(bureau.user)

        response = self._post_profile(
            whatsapp_number="9123456799",
            is_approved="true",
            is_active="true",
            is_email_verified="false",
            user=str(owner_id + 999),
            role="admin",
            status="pending",
        )
        self.assertIn(response.status_code, (302, 200))

        bureau.refresh_from_db()
        self.assertFalse(bureau.is_approved)
        self.assertFalse(bureau.is_active)
        self.assertTrue(bureau.is_email_verified)
        self.assertEqual(bureau.user_id, owner_id)
        self.assertEqual(bureau.description, "Updated bureau description for owner edit.")
        self.assertEqual(bureau.address, "99 Owner Edit Road")
        self.assertEqual(bureau.city, "Hyderabad")
        self.assertEqual(bureau.caste_data, {"OC": ["brahmin"]})
        self.assertEqual(bureau.whatsapp_number, "9123456799")
        self.assertNotIn(bureau.id, get_visible_bureaus().values_list("id", flat=True))

    def test_owner_edit_invalid_phone_returns_validation_response(self):
        bureau = _make_bureau(
            email="owner-edit-invalid@example.com",
            is_active=False,
            is_approved=False,
            is_email_verified=True,
        )
        self.client.force_login(bureau.user)
        response = self._post_profile(phone_number="abc")
        self.assertEqual(response.status_code, 400)
        self.assertNotEqual(response.status_code, 500)
        bureau.refresh_from_db()
        self.assertEqual(bureau.phone_number, "9876543210")

    def test_get_bureau_for_user_unchanged_for_pre_approval_owner(self):
        bureau = _make_bureau(
            email="owner-edit-helper@example.com",
            is_active=False,
            is_approved=False,
            is_email_verified=True,
        )
        self.assertIsNone(get_bureau_for_user(bureau.user))
        owned = get_owned_email_verified_bureau(bureau.user)
        self.assertIsNotNone(owned)
        self.assertEqual(owned.id, bureau.id)

        eligible = _make_bureau(
            email="owner-edit-eligible@example.com",
            is_active=True,
            is_approved=True,
            is_email_verified=True,
        )
        self.assertEqual(get_bureau_for_user(eligible.user).id, eligible.id)


@override_settings(EMAIL_BACKEND=LOCMEM_EMAIL)
class BureauOwnerProfileEditRedirectTests(TestCase):
    """Profile-edit success redirect alignment (Phase 7 post-Slice C)."""

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.edit_url = reverse("bureaus:bureau_profile_edit")
        self.dashboard_url = "/dashboard/bureau/"
        self.status_url = reverse("bureaus:bureau_owner_status")

    def _post_profile(self, **overrides):
        payload = {
            "description": "Updated bureau description for owner edit.",
            "phone_number": "9876543210",
            "whatsapp_number": "",
            "address": "99 Owner Edit Road",
            "city": "Hyderabad",
            "caste_data": '{"OC": ["brahmin"]}',
        }
        payload.update(overrides)
        return self.client.post(self.edit_url, payload)

    def test_eligible_owner_success_redirects_to_dashboard(self):
        bureau = _make_bureau(
            email="edit-redirect-eligible@example.com",
            is_active=True,
            is_approved=True,
            is_email_verified=True,
        )
        self.client.force_login(bureau.user)
        response = self._post_profile()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.dashboard_url)

    def test_non_eligible_owner_success_redirects_to_status(self):
        bureau = _make_bureau(
            email="edit-redirect-pending@example.com",
            description="",
            caste_data={},
            is_active=False,
            is_approved=False,
            is_email_verified=True,
        )
        self.client.force_login(bureau.user)
        response = self._post_profile()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.status_url)

    def test_successful_edit_does_not_mutate_lifecycle_for_pending_owner(self):
        bureau = _make_bureau(
            email="edit-redirect-immutable@example.com",
            description="",
            caste_data={},
            is_active=False,
            is_approved=False,
            is_email_verified=True,
        )
        before = {
            "is_email_verified": bureau.is_email_verified,
            "is_approved": bureau.is_approved,
            "is_active": bureau.is_active,
            "user_id": bureau.user_id,
        }
        self.client.force_login(bureau.user)
        response = self._post_profile()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.status_url)
        bureau.refresh_from_db()
        self.assertEqual(bureau.is_email_verified, before["is_email_verified"])
        self.assertEqual(bureau.is_approved, before["is_approved"])
        self.assertEqual(bureau.is_active, before["is_active"])
        self.assertEqual(bureau.user_id, before["user_id"])

    def test_unverified_owner_still_denied(self):
        bureau = _make_bureau(
            email="edit-redirect-unverified@example.com",
            is_active=False,
            is_approved=False,
            is_email_verified=False,
        )
        self.client.force_login(bureau.user)
        response = self._post_profile()
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("/bureaus/profile/edit/", response["Location"])
        self.assertNotEqual(response["Location"], self.status_url)


@override_settings(EMAIL_BACKEND=LOCMEM_EMAIL)
class BureauSuperAdminApproveTests(TestCase):
    """approve_bureau is Super Admin only; sets is_approved only."""

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.bureau = _make_bureau(
            email="approve-target@example.com",
            description="Complete enough for listing checks.",
            is_active=False,
            is_approved=False,
            is_email_verified=True,
        )
        self.approve_url = reverse(
            "module5_dashboards:approve_bureau",
            kwargs={"public_id": self.bureau.public_id},
        )

    def _make_superuser(self, *, email: str) -> User:
        return User.objects.create_superuser(
            email=email,
            password="BureauTestPass123!",
            username=f"su_{email.split('@')[0][:16]}",
        )

    def test_superuser_post_approves_only_is_approved(self):
        superuser = self._make_superuser(email="su-approve@example.com")
        self.client.force_login(superuser)

        before_active = self.bureau.is_active
        before_email = self.bureau.is_email_verified
        response = self.client.post(self.approve_url)

        self.assertEqual(response.status_code, 302)
        self.bureau.refresh_from_db()
        self.assertTrue(self.bureau.is_approved)
        self.assertEqual(self.bureau.is_active, before_active)
        self.assertEqual(self.bureau.is_email_verified, before_email)
        self.assertFalse(self.bureau.is_active)
        self.assertNotIn(
            self.bureau.id,
            get_visible_bureaus().values_list("id", flat=True),
        )

    def test_get_approve_rejected(self):
        superuser = self._make_superuser(email="su-approve-get@example.com")
        self.client.force_login(superuser)
        response = self.client.get(self.approve_url)
        self.assertEqual(response.status_code, 405)
        self.bureau.refresh_from_db()
        self.assertFalse(self.bureau.is_approved)

    def test_anonymous_normal_owner_admin_pandit_staff_denied(self):
        anon = self.client.post(self.approve_url)
        self.assertEqual(anon.status_code, 302)
        self.assertIn("/accounts/login/", anon["Location"])
        self.bureau.refresh_from_db()
        self.assertFalse(self.bureau.is_approved)

        normal = _make_user(email="approve-normal@example.com")
        self.client.force_login(normal)
        self.assertEqual(self.client.post(self.approve_url).status_code, 404)
        self.bureau.refresh_from_db()
        self.assertFalse(self.bureau.is_approved)

        self.client.force_login(self.bureau.user)
        self.assertEqual(self.client.post(self.approve_url).status_code, 404)
        self.bureau.refresh_from_db()
        self.assertFalse(self.bureau.is_approved)

        admin_pandit = _make_user(email="approve-admin-pandit@example.com")
        admin_pandit.role = "admin"
        admin_pandit.is_staff = True
        admin_pandit.is_superuser = False
        admin_pandit.save(update_fields=["role", "is_staff", "is_superuser"])
        self.client.force_login(admin_pandit)
        self.assertEqual(self.client.post(self.approve_url).status_code, 404)
        self.bureau.refresh_from_db()
        self.assertFalse(self.bureau.is_approved)

        staff = _make_user(email="approve-staff@example.com")
        staff.is_staff = True
        staff.is_superuser = False
        staff.save(update_fields=["is_staff", "is_superuser"])
        self.client.force_login(staff)
        self.assertEqual(self.client.post(self.approve_url).status_code, 404)
        self.bureau.refresh_from_db()
        self.assertFalse(self.bureau.is_approved)

    def test_approved_unverified_or_incomplete_still_hidden(self):
        unverified = _make_bureau(
            email="approve-unverified@example.com",
            is_active=True,
            is_approved=False,
            is_email_verified=False,
        )
        incomplete = _make_bureau(
            email="approve-incomplete@example.com",
            description="",
            caste_data={},
            is_active=True,
            is_approved=False,
            is_email_verified=True,
        )
        superuser = self._make_superuser(email="su-approve-vis@example.com")
        self.client.force_login(superuser)

        for bureau in (unverified, incomplete, self.bureau):
            url = reverse(
                "module5_dashboards:approve_bureau",
                kwargs={"public_id": bureau.public_id},
            )
            self.client.post(url)
            bureau.refresh_from_db()
            self.assertTrue(bureau.is_approved)
            self.assertNotIn(
                bureau.id,
                get_visible_bureaus().values_list("id", flat=True),
            )


@override_settings(EMAIL_BACKEND=LOCMEM_EMAIL)
class BureauSuperAdminActivateTests(TestCase):
    """activate_bureau is Super Admin only; sets is_active only after approval."""

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.bureau = _make_bureau(
            email="activate-target@example.com",
            description="Complete enough for listing checks.",
            is_active=False,
            is_approved=True,
            is_email_verified=False,
        )
        self.activate_url = reverse(
            "module5_dashboards:activate_bureau",
            kwargs={"public_id": self.bureau.public_id},
        )

    def _make_superuser(self, *, email: str) -> User:
        return User.objects.create_superuser(
            email=email,
            password="BureauTestPass123!",
            username=f"su_{email.split('@')[0][:16]}",
        )

    def test_superuser_post_activates_only_is_active(self):
        superuser = self._make_superuser(email="su-activate@example.com")
        self.client.force_login(superuser)

        before_approved = self.bureau.is_approved
        before_email = self.bureau.is_email_verified
        before_user_id = self.bureau.user_id
        response = self.client.post(self.activate_url)

        self.assertEqual(response.status_code, 302)
        self.bureau.refresh_from_db()
        self.assertTrue(self.bureau.is_active)
        self.assertEqual(self.bureau.is_approved, before_approved)
        self.assertTrue(self.bureau.is_approved)
        self.assertEqual(self.bureau.is_email_verified, before_email)
        self.assertFalse(self.bureau.is_email_verified)
        self.assertEqual(self.bureau.user_id, before_user_id)
        # Email still unverified → not publicly visible.
        self.assertNotIn(
            self.bureau.id,
            get_visible_bureaus().values_list("id", flat=True),
        )

    def test_get_activate_rejected(self):
        superuser = self._make_superuser(email="su-activate-get@example.com")
        self.client.force_login(superuser)
        response = self.client.get(self.activate_url)
        self.assertEqual(response.status_code, 405)
        self.bureau.refresh_from_db()
        self.assertFalse(self.bureau.is_active)

    def test_anonymous_normal_owner_admin_pandit_staff_denied(self):
        anon = self.client.post(self.activate_url)
        self.assertEqual(anon.status_code, 302)
        self.assertIn("/accounts/login/", anon["Location"])
        self.bureau.refresh_from_db()
        self.assertFalse(self.bureau.is_active)

        normal = _make_user(email="activate-normal@example.com")
        self.client.force_login(normal)
        self.assertEqual(self.client.post(self.activate_url).status_code, 404)
        self.bureau.refresh_from_db()
        self.assertFalse(self.bureau.is_active)

        self.client.force_login(self.bureau.user)
        self.assertEqual(self.client.post(self.activate_url).status_code, 404)
        self.bureau.refresh_from_db()
        self.assertFalse(self.bureau.is_active)

        admin_pandit = _make_user(email="activate-admin-pandit@example.com")
        admin_pandit.role = "admin"
        admin_pandit.is_staff = True
        admin_pandit.is_superuser = False
        admin_pandit.save(update_fields=["role", "is_staff", "is_superuser"])
        self.client.force_login(admin_pandit)
        self.assertEqual(self.client.post(self.activate_url).status_code, 404)
        self.bureau.refresh_from_db()
        self.assertFalse(self.bureau.is_active)

        staff = _make_user(email="activate-staff@example.com")
        staff.is_staff = True
        staff.is_superuser = False
        staff.save(update_fields=["is_staff", "is_superuser"])
        self.client.force_login(staff)
        self.assertEqual(self.client.post(self.activate_url).status_code, 404)
        self.bureau.refresh_from_db()
        self.assertFalse(self.bureau.is_active)

    def test_unapproved_bureau_cannot_be_activated(self):
        unapproved = _make_bureau(
            email="activate-unapproved@example.com",
            is_active=False,
            is_approved=False,
            is_email_verified=True,
        )
        url = reverse(
            "module5_dashboards:activate_bureau",
            kwargs={"public_id": unapproved.public_id},
        )
        superuser = self._make_superuser(email="su-activate-unapproved@example.com")
        self.client.force_login(superuser)

        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)
        unapproved.refresh_from_db()
        self.assertFalse(unapproved.is_active)
        self.assertFalse(unapproved.is_approved)
        self.assertTrue(unapproved.is_email_verified)
@override_settings(EMAIL_BACKEND=LOCMEM_EMAIL)
class BureauSuperAdminReviewTests(TestCase):
    """review_bureau is Super Admin GET-only; never mutates lifecycle flags."""

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.bureau = _make_bureau(
            email="review-target@example.com",
            description="Reviewable bureau description.",
            is_active=False,
            is_approved=False,
            is_email_verified=False,
        )
        self.review_url = reverse(
            "module5_dashboards:review_bureau",
            kwargs={"public_id": self.bureau.public_id},
        )

    def _make_superuser(self, *, email: str) -> User:
        return User.objects.create_superuser(
            email=email,
            password="BureauTestPass123!",
            username=f"su_{email.split('@')[0][:16]}",
        )

    def test_superuser_get_review_ok_and_no_flag_changes(self):
        superuser = self._make_superuser(email="su-review@example.com")
        self.client.force_login(superuser)

        before_approved = self.bureau.is_approved
        before_active = self.bureau.is_active
        before_email = self.bureau.is_email_verified

        response = self.client.get(self.review_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.bureau.bureau_name)
        self.assertContains(response, str(self.bureau.public_id))
        self.assertContains(response, self.bureau.user.email)

        self.bureau.refresh_from_db()
        self.assertEqual(self.bureau.is_approved, before_approved)
        self.assertEqual(self.bureau.is_active, before_active)
        self.assertEqual(self.bureau.is_email_verified, before_email)
        self.assertFalse(self.bureau.is_approved)
        self.assertFalse(self.bureau.is_active)
        self.assertFalse(self.bureau.is_email_verified)

    def test_review_inactive_unverified_unapproved_ok(self):
        superuser = self._make_superuser(email="su-review-states@example.com")
        self.client.force_login(superuser)
        response = self.client.get(self.review_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(
            self.bureau.id,
            get_visible_bureaus().values_list("id", flat=True),
        )

    def test_anonymous_normal_owner_admin_pandit_staff_denied(self):
        anon = self.client.get(self.review_url)
        self.assertEqual(anon.status_code, 302)
        self.assertIn("/accounts/login/", anon["Location"])

        normal = _make_user(email="review-normal@example.com")
        self.client.force_login(normal)
        self.assertEqual(self.client.get(self.review_url).status_code, 404)

        self.client.force_login(self.bureau.user)
        self.assertEqual(self.client.get(self.review_url).status_code, 404)

        admin_pandit = _make_user(email="review-admin-pandit@example.com")
        admin_pandit.role = "admin"
        admin_pandit.is_staff = True
        admin_pandit.is_superuser = False
        admin_pandit.save(update_fields=["role", "is_staff", "is_superuser"])
        self.client.force_login(admin_pandit)
        self.assertEqual(self.client.get(self.review_url).status_code, 404)

        staff = _make_user(email="review-staff@example.com")
        staff.is_staff = True
        staff.is_superuser = False
        staff.save(update_fields=["is_staff", "is_superuser"])
        self.client.force_login(staff)
        self.assertEqual(self.client.get(self.review_url).status_code, 404)

    def test_post_rejected_and_no_writes(self):
        superuser = self._make_superuser(email="su-review-post@example.com")
        self.client.force_login(superuser)
        before_approved = self.bureau.is_approved
        before_active = self.bureau.is_active
        before_email = self.bureau.is_email_verified

        response = self.client.post(self.review_url)
        self.assertEqual(response.status_code, 405)

        self.bureau.refresh_from_db()
        self.assertEqual(self.bureau.is_approved, before_approved)
        self.assertEqual(self.bureau.is_active, before_active)
        self.assertEqual(self.bureau.is_email_verified, before_email)

    def test_missing_public_id_404(self):
        superuser = self._make_superuser(email="su-review-missing@example.com")
        self.client.force_login(superuser)
        missing = reverse(
            "module5_dashboards:review_bureau",
            kwargs={"public_id": "00000000-0000-4000-8000-000000000001"},
        )
        self.assertEqual(self.client.get(missing).status_code, 404)

    def test_visibility_helper_unchanged_after_review(self):
        visible_ids_before = set(get_visible_bureaus().values_list("id", flat=True))
        superuser = self._make_superuser(email="su-review-vis@example.com")
        self.client.force_login(superuser)
        self.client.get(self.review_url)
        visible_ids_after = set(get_visible_bureaus().values_list("id", flat=True))
        self.assertEqual(visible_ids_before, visible_ids_after)
        self.assertNotIn(self.bureau.id, visible_ids_after)

    def test_pending_review_shows_approve_not_activate(self):
        superuser = self._make_superuser(email="su-review-approve-btn@example.com")
        self.client.force_login(superuser)
        approve_url = reverse(
            "module5_dashboards:approve_bureau",
            kwargs={"public_id": self.bureau.public_id},
        )
        activate_url = reverse(
            "module5_dashboards:activate_bureau",
            kwargs={"public_id": self.bureau.public_id},
        )
        response = self.client.get(self.review_url)
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn('action="%s"' % approve_url, body)
        self.assertIn("csrfmiddlewaretoken", body)
        self.assertRegex(body, r'<button[^>]*type="submit"[^>]*>\s*Approve\s*</button>')
        self.assertNotIn('action="%s"' % activate_url, body)
        self.assertNotRegex(body, r'<button[^>]*type="submit"[^>]*>\s*Activate\s*</button>')

    def test_approved_inactive_review_shows_activate_not_approve(self):
        approved = _make_bureau(
            email="review-approved-inactive@example.com",
            is_active=False,
            is_approved=True,
            is_email_verified=False,
        )
        url = reverse(
            "module5_dashboards:review_bureau",
            kwargs={"public_id": approved.public_id},
        )
        approve_url = reverse(
            "module5_dashboards:approve_bureau",
            kwargs={"public_id": approved.public_id},
        )
        activate_url = reverse(
            "module5_dashboards:activate_bureau",
            kwargs={"public_id": approved.public_id},
        )
        superuser = self._make_superuser(email="su-review-activate-btn@example.com")
        self.client.force_login(superuser)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn('action="%s"' % activate_url, body)
        self.assertIn("csrfmiddlewaretoken", body)
        self.assertRegex(body, r'<button[^>]*type="submit"[^>]*>\s*Activate\s*</button>')
        self.assertNotIn('action="%s"' % approve_url, body)
        self.assertNotRegex(body, r'<button[^>]*type="submit"[^>]*>\s*Approve\s*</button>')

    def test_approved_active_review_shows_no_lifecycle_actions(self):
        live = _make_bureau(
            email="review-approved-active@example.com",
            is_active=True,
            is_approved=True,
            is_email_verified=True,
        )
        url = reverse(
            "module5_dashboards:review_bureau",
            kwargs={"public_id": live.public_id},
        )
        approve_url = reverse(
            "module5_dashboards:approve_bureau",
            kwargs={"public_id": live.public_id},
        )
        activate_url = reverse(
            "module5_dashboards:activate_bureau",
            kwargs={"public_id": live.public_id},
        )
        superuser = self._make_superuser(email="su-review-no-btn@example.com")
        self.client.force_login(superuser)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("No lifecycle action available.", body)
        self.assertNotIn('action="%s"' % approve_url, body)
        self.assertNotIn('action="%s"' % activate_url, body)
        self.assertNotRegex(body, r'<button[^>]*type="submit"[^>]*>\s*Approve\s*</button>')
        self.assertNotRegex(body, r'<button[^>]*type="submit"[^>]*>\s*Activate\s*</button>')


@override_settings(EMAIL_BACKEND=LOCMEM_EMAIL)
class BureauResendVerificationTests(TestCase):
    """Bureau owner authenticated email verification resend."""

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.resend_url = reverse("bureaus:bureau_resend_verification")
        self.register_url = reverse("bureaus:bureau_register")

    def test_anonymous_post_rejected(self):
        response = self.client.post(self.resend_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_non_bureau_user_cannot_resend(self):
        user = _make_user(email="plain-resend@example.com")
        self.client.force_login(user)
        response = self.client.post(self.resend_url)
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("/bureaus/resend-verification/", response["Location"])

    def test_unverified_bureau_owner_can_resend(self):
        bureau = _make_bureau(email="bureau-resend-ok@example.com")
        self.client.force_login(bureau.user)
        with patch(
            "bureaus.services_verification.create_email_verification"
        ) as create_email_verification:
            response = self.client.post(self.resend_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.register_url)
        create_email_verification.assert_called_once_with(bureau.user)

    def test_verified_bureau_owner_cannot_resend(self):
        bureau = _make_bureau(
            email="bureau-resend-verified@example.com",
            is_email_verified=True,
        )
        bureau.user.email_verified = True
        bureau.user.email_verified_at = timezone.now()
        bureau.user.save(update_fields=["email_verified", "email_verified_at"])
        self.client.force_login(bureau.user)
        with patch(
            "bureaus.services_verification.create_email_verification"
        ) as create_email_verification:
            response = self.client.post(self.resend_url)
        self.assertEqual(response.status_code, 302)
        create_email_verification.assert_not_called()

    def test_unapproved_bureau_owner_can_resend(self):
        bureau = _make_bureau(
            email="bureau-resend-unapproved@example.com",
            is_approved=False,
            is_active=False,
        )
        self.assertFalse(bureau.is_approved)
        self.assertFalse(bureau.is_active)
        self.client.force_login(bureau.user)
        with patch(
            "bureaus.services_verification.create_email_verification"
        ) as create_email_verification:
            response = self.client.post(self.resend_url)
        self.assertEqual(response.status_code, 302)
        create_email_verification.assert_called_once_with(bureau.user)
        bureau.refresh_from_db()
        self.assertFalse(bureau.is_approved)
        self.assertFalse(bureau.is_active)

    def test_inactive_bureau_owner_can_resend(self):
        bureau = _make_bureau(
            email="bureau-resend-inactive@example.com",
            is_active=False,
        )
        self.client.force_login(bureau.user)
        with patch(
            "bureaus.services_verification.create_email_verification"
        ) as create_email_verification:
            response = self.client.post(self.resend_url)
        self.assertEqual(response.status_code, 302)
        create_email_verification.assert_called_once_with(bureau.user)
        bureau.refresh_from_db()
        self.assertFalse(bureau.is_active)

    def test_endpoint_is_self_only_no_target_params(self):
        owner = _make_bureau(email="bureau-resend-owner@example.com")
        other = _make_bureau(email="bureau-resend-other@example.com")
        self.client.force_login(owner.user)
        with patch(
            "bureaus.services_verification.create_email_verification"
        ) as create_email_verification:
            response = self.client.post(
                self.resend_url,
                data={"email": other.user.email, "user_id": other.user.id},
            )
        self.assertEqual(response.status_code, 302)
        create_email_verification.assert_called_once_with(owner.user)

    def test_cooldown_enforced(self):
        bureau = _make_bureau(email="bureau-resend-cooldown@example.com")
        self.client.force_login(bureau.user)
        with patch(
            "bureaus.services_verification.create_email_verification"
        ) as create_email_verification:
            first = self.client.post(self.resend_url)
            second = self.client.post(self.resend_url)
        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 302)
        self.assertEqual(create_email_verification.call_count, 1)

    def test_daily_limit_enforced(self):
        bureau = _make_bureau(email="bureau-resend-limit@example.com")
        user = bureau.user
        user.last_verification_email_sent_at = timezone.now()
        user.save(update_fields=["last_verification_email_sent_at"])
        for _ in range(5):
            EmailVerificationToken.objects.create(user=user)
        self.client.force_login(user)
        with patch(
            "bureaus.services_verification.create_email_verification"
        ) as create_email_verification:
            response = self.client.post(self.resend_url)
        self.assertEqual(response.status_code, 302)
        create_email_verification.assert_not_called()

    def test_resend_invalidates_old_active_token_via_shared_helper(self):
        bureau = _make_bureau(email="bureau-resend-token@example.com")
        user = bureau.user
        old_token = EmailVerificationToken.objects.create(user=user)
        self.assertFalse(old_token.is_used)
        self.client.force_login(user)
        response = self.client.post(self.resend_url)
        self.assertEqual(response.status_code, 302)
        old_token.refresh_from_db()
        self.assertTrue(old_token.is_used)
        new_token = (
            EmailVerificationToken.objects.filter(user=user, is_used=False)
            .order_by("-created_at")
            .first()
        )
        self.assertIsNotNone(new_token)
        self.assertNotEqual(old_token.token, new_token.token)

    def test_lifecycle_fields_unchanged_after_resend(self):
        bureau = _make_bureau(
            email="bureau-resend-flags@example.com",
            is_active=False,
            is_approved=False,
            is_email_verified=False,
        )
        original_user_id = bureau.user_id
        self.client.force_login(bureau.user)
        with patch(
            "bureaus.services_verification.create_email_verification"
        ) as create_email_verification:
            response = self.client.post(self.resend_url)
        self.assertEqual(response.status_code, 302)
        create_email_verification.assert_called_once_with(bureau.user)
        bureau.refresh_from_db()
        self.assertFalse(bureau.is_active)
        self.assertFalse(bureau.is_approved)
        self.assertFalse(bureau.is_email_verified)
        self.assertEqual(bureau.user_id, original_user_id)

    def test_success_redirect_and_message(self):
        bureau = _make_bureau(email="bureau-resend-success@example.com")
        self.client.force_login(bureau.user)
        with patch(
            "bureaus.services_verification.create_email_verification"
        ) as create_email_verification:
            response = self.client.post(self.resend_url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request["PATH_INFO"], self.register_url)
        create_email_verification.assert_called_once_with(bureau.user)
        body = response.content.decode("utf-8", errors="ignore")
        self.assertIn("Verification email has been sent", body)


@override_settings(EMAIL_BACKEND=LOCMEM_EMAIL)
class BureauOwnerStatusTests(TestCase):
    """Bureau owner read-only onboarding status page (Phase 7 Slice A)."""

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.status_url = reverse("bureaus:bureau_owner_status")
        self.dashboard_url = "/dashboard/bureau/"
        self.resend_url = reverse("bureaus:bureau_resend_verification")
        self.profile_edit_url = reverse("bureaus:bureau_profile_edit")

    def test_anonymous_get_redirects_to_login(self):
        response = self.client.get(self.status_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])
        self.assertIn("/bureaus/status/", response["Location"])

    def test_non_bureau_user_redirects_home(self):
        user = _make_user(email="status-plain-user@example.com")
        self.client.force_login(user)
        response = self.client.get(self.status_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("core:home"))
        self.assertFalse(BureauProfile.objects.filter(user=user).exists())

    def test_unverified_bureau_owner_sees_pending_email(self):
        bureau = _make_bureau(email="status-unverified@example.com")
        before = {
            "is_email_verified": bureau.is_email_verified,
            "is_approved": bureau.is_approved,
            "is_active": bureau.is_active,
            "user_id": bureau.user_id,
        }
        self.client.force_login(bureau.user)
        response = self.client.get(self.status_url)
        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8", errors="ignore")
        self.assertIn("Email Verification", body)
        self.assertIn("Pending", body)
        self.assertIn(self.resend_url, body)
        bureau.refresh_from_db()
        self.assertEqual(bureau.is_email_verified, before["is_email_verified"])
        self.assertEqual(bureau.is_approved, before["is_approved"])
        self.assertEqual(bureau.is_active, before["is_active"])
        self.assertEqual(bureau.user_id, before["user_id"])

    def test_verified_unapproved_owner_sees_approval_pending(self):
        bureau = _make_bureau(
            email="status-verified-unapproved@example.com",
            is_email_verified=True,
            description="",
        )
        bureau.user.email_verified = True
        bureau.user.email_verified_at = timezone.now()
        bureau.user.save(update_fields=["email_verified", "email_verified_at"])
        self.client.force_login(bureau.user)
        response = self.client.get(self.status_url)
        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8", errors="ignore")
        self.assertIn("Admin Approval", body)
        self.assertIn("Pending", body)
        self.assertIn(self.profile_edit_url, body)

    def test_approved_inactive_owner_sees_activation_pending(self):
        bureau = _make_bureau(
            email="status-approved-inactive@example.com",
            is_approved=True,
            is_email_verified=True,
        )
        self.client.force_login(bureau.user)
        response = self.client.get(self.status_url)
        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8", errors="ignore")
        self.assertIn("Account Activation", body)
        self.assertIn("Pending", body)

    def test_fully_ready_owner_redirects_to_dashboard(self):
        bureau = _make_bureau(
            email="status-ready@example.com",
            is_active=True,
            is_approved=True,
            is_email_verified=True,
        )
        self.client.force_login(bureau.user)
        response = self.client.get(self.status_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.dashboard_url)

    def test_eligible_incomplete_profile_shows_profile_edit_link(self):
        bureau = _make_bureau(
            email="status-incomplete-profile@example.com",
            is_active=True,
            is_approved=True,
            is_email_verified=True,
            description="",
        )
        self.client.force_login(bureau.user)
        response = self.client.get(self.status_url)
        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8", errors="ignore")
        self.assertIn("Profile Completeness", body)
        self.assertIn("Incomplete", body)
        self.assertIn(self.profile_edit_url, body)

    def test_post_returns_method_not_allowed(self):
        bureau = _make_bureau(email="status-post@example.com")
        self.client.force_login(bureau.user)
        response = self.client.post(self.status_url)
        self.assertEqual(response.status_code, 405)

    def test_get_does_not_mutate_lifecycle_fields(self):
        bureau = _make_bureau(
            email="status-immutable@example.com",
            is_approved=True,
            is_active=False,
            is_email_verified=False,
        )
        original_user_id = bureau.user_id
        self.client.force_login(bureau.user)
        response = self.client.get(self.status_url)
        self.assertEqual(response.status_code, 200)
        bureau.refresh_from_db()
        self.assertFalse(bureau.is_email_verified)
        self.assertTrue(bureau.is_approved)
        self.assertFalse(bureau.is_active)
        self.assertEqual(bureau.user_id, original_user_id)

    def test_phase6_resend_tests_still_present(self):
        """Guard: Phase 6 resend test class remains importable and runnable."""
        self.assertTrue(hasattr(BureauResendVerificationTests, "test_anonymous_post_rejected"))


class BureauOwnerDashboardRoutingTests(TestCase):
    """Phase 7 Slice B: pending Bureau owners route to status from user dashboard."""

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.dashboard_user_url = reverse("module5_dashboards:dashboard_user")
        self.status_url = reverse("bureaus:bureau_owner_status")
        self.bureau_dashboard_url = "/dashboard/bureau/"

    def _login_phone_verified(self, user):
        user.is_phone_verified = True
        user.save(update_fields=["is_phone_verified"])
        self.client.force_login(user)

    def test_normal_user_dashboard_unchanged(self):
        user = _make_user(email="sliceb-plain-user@example.com")
        self._login_phone_verified(user)
        response = self.client.get(self.dashboard_user_url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(BureauProfile.objects.filter(user=user).exists())

    def test_pending_bureau_owner_redirects_to_status(self):
        bureau = _make_bureau(email="sliceb-pending@example.com")
        self._login_phone_verified(bureau.user)
        response = self.client.get(self.dashboard_user_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.status_url)

    def test_fully_eligible_bureau_owner_redirects_to_bureau_dashboard(self):
        bureau = _make_bureau(
            email="sliceb-eligible@example.com",
            is_active=True,
            is_approved=True,
            is_email_verified=True,
        )
        self._login_phone_verified(bureau.user)
        response = self.client.get(self.dashboard_user_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.bureau_dashboard_url)

    def test_pending_bureau_owner_does_not_mutate_lifecycle(self):
        bureau = _make_bureau(
            email="sliceb-immutable@example.com",
            is_approved=True,
            is_active=False,
            is_email_verified=False,
        )
        before = {
            "is_email_verified": bureau.is_email_verified,
            "is_approved": bureau.is_approved,
            "is_active": bureau.is_active,
            "user_id": bureau.user_id,
        }
        self._login_phone_verified(bureau.user)
        response = self.client.get(self.dashboard_user_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.status_url)
        bureau.refresh_from_db()
        self.assertEqual(bureau.is_email_verified, before["is_email_verified"])
        self.assertEqual(bureau.is_approved, before["is_approved"])
        self.assertEqual(bureau.is_active, before["is_active"])
        self.assertEqual(bureau.user_id, before["user_id"])


class BureauOwnerLoginRoutingTests(TestCase):
    """Phase 7 Slice C: Bureau-aware post-login routing (pending → status, eligible → dashboard)."""

    PASSWORD = "BureauTestPass123!"

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.login_url = reverse("accounts:login")
        self.status_url = reverse("bureaus:bureau_owner_status")
        self.bureau_dashboard_url = "/dashboard/bureau/"
        self.home_url = reverse("core:home")
        self.user_dashboard_url = reverse("module5_dashboards:dashboard_user")
        self.pandit_dashboard_url = reverse("module5_dashboards:dashboard_pandit")
        self.super_admin_dashboard_url = reverse(
            "module5_dashboards:dashboard_super_admin"
        )

    def _post_login(self, email: str, password: str | None = None):
        return self.client.post(
            self.login_url,
            {
                "email": email,
                "password": password or self.PASSWORD,
            },
        )

    def test_pending_bureau_owner_login_redirects_to_status(self):
        bureau = _make_bureau(email="slicec-pending-login@example.com")
        response = self._post_login(bureau.user.email)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.status_url)

    def test_fully_eligible_bureau_owner_login_redirects_to_bureau_dashboard(self):
        bureau = _make_bureau(
            email="slicec-eligible-login@example.com",
            is_active=True,
            is_approved=True,
            is_email_verified=True,
        )
        response = self._post_login(bureau.user.email)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.bureau_dashboard_url)

    def test_normal_user_login_preserves_non_bureau_destination(self):
        user = _make_user(email="slicec-plain-login@example.com")
        response = self._post_login(user.email)
        self.assertEqual(response.status_code, 302)
        location = response["Location"]
        self.assertNotEqual(location, self.status_url)
        self.assertNotEqual(location, self.bureau_dashboard_url)
        # Committed HEAD fallthrough is core:home. Working-tree may still contain
        # unrelated end-user → dashboard_user WIP; Slice C must not Bureau-route them.
        self.assertIn(
            location,
            {self.home_url, self.user_dashboard_url, "/"},
        )

    def test_pandit_login_unchanged(self):
        pandit = User.objects.create_user(
            email="slicec-pandit-login@example.com",
            password=self.PASSWORD,
            username="u_slicec_pandit",
            role="pandit",
            status="active",
            is_active=True,
            email_verified=True,
        )
        response = self._post_login(pandit.email)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.pandit_dashboard_url)

    def test_expert_login_unchanged(self):
        from core.models import ExpertProfile

        expert_user = _make_user(email="slicec-expert-login@example.com")
        ExpertProfile.objects.create(
            name="Slice C Expert",
            expert_type="ASTROLOGER",
            email=expert_user.email,
            is_active=True,
        )
        response = self._post_login(expert_user.email)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/dashboard/expert/")

    def test_superuser_login_unchanged(self):
        admin = User.objects.create_superuser(
            email="slicec-super-login@example.com",
            password=self.PASSWORD,
            username="u_slicec_super",
        )
        response = self._post_login(admin.email)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.super_admin_dashboard_url)

    def test_pending_bureau_login_does_not_mutate_lifecycle(self):
        bureau = _make_bureau(
            email="slicec-immutable-login@example.com",
            is_approved=True,
            is_active=False,
            is_email_verified=False,
        )
        before = {
            "is_email_verified": bureau.is_email_verified,
            "is_approved": bureau.is_approved,
            "is_active": bureau.is_active,
            "user_id": bureau.user_id,
        }
        response = self._post_login(bureau.user.email)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.status_url)
        bureau.refresh_from_db()
        self.assertEqual(bureau.is_email_verified, before["is_email_verified"])
        self.assertEqual(bureau.is_approved, before["is_approved"])
        self.assertEqual(bureau.is_active, before["is_active"])
        self.assertEqual(bureau.user_id, before["user_id"])


@override_settings(EMAIL_BACKEND=LOCMEM_EMAIL)
class BureauOwnerMarkIntentViewedTests(TestCase):
    """Regression: owner mark_intent_viewed + requests-tab ownership (test-only)."""

    REQUESTS_UPDATED = "/dashboard/bureau/?tab=requests&updated=1"

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.requester = _make_user(email="mark-viewed-requester@example.com")
        self.bureau = _make_bureau(
            email="mark-viewed-owner@example.com",
            bureau_name="Mark Viewed Owner Bureau",
            is_active=True,
            is_approved=True,
            is_email_verified=True,
        )
        self.intent = BureauBookingIntent.objects.create(
            bureau=self.bureau,
            user=self.requester,
            name="Seeking Match",
            phone="9123456789",
            message="Please contact me about membership.",
            is_viewed=False,
        )
        self.mark_url = reverse(
            "bureaus:mark_intent_viewed",
            kwargs={"intent_id": self.intent.id},
        )

    def _lifecycle_snapshot(self, bureau):
        return {
            "is_email_verified": bureau.is_email_verified,
            "is_approved": bureau.is_approved,
            "is_active": bureau.is_active,
        }

    def _intent_snapshot(self, intent):
        return {
            "name": intent.name,
            "phone": intent.phone,
            "message": intent.message,
            "status": intent.status,
            "user_id": intent.user_id,
            "bureau_id": intent.bureau_id,
        }

    def test_owner_can_mark_own_intent_viewed(self):
        before_lifecycle = self._lifecycle_snapshot(self.bureau)
        before_intent = self._intent_snapshot(self.intent)
        self.assertFalse(self.intent.is_viewed)

        self.client.force_login(self.bureau.user)
        response = self.client.post(self.mark_url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.REQUESTS_UPDATED)

        self.intent.refresh_from_db()
        self.assertTrue(self.intent.is_viewed)
        self.assertEqual(self._intent_snapshot(self.intent), before_intent)

        self.bureau.refresh_from_db()
        self.assertEqual(self._lifecycle_snapshot(self.bureau), before_lifecycle)

    def test_already_viewed_intent_remains_viewed(self):
        self.intent.is_viewed = True
        self.intent.save(update_fields=["is_viewed"])
        before_count = BureauBookingIntent.objects.filter(bureau=self.bureau).count()
        before_lifecycle = self._lifecycle_snapshot(self.bureau)
        before_intent = self._intent_snapshot(self.intent)

        self.client.force_login(self.bureau.user)
        response = self.client.post(self.mark_url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.REQUESTS_UPDATED)

        self.intent.refresh_from_db()
        self.assertTrue(self.intent.is_viewed)
        self.assertEqual(self._intent_snapshot(self.intent), before_intent)
        self.assertEqual(
            BureauBookingIntent.objects.filter(bureau=self.bureau).count(),
            before_count,
        )

        self.bureau.refresh_from_db()
        self.assertEqual(self._lifecycle_snapshot(self.bureau), before_lifecycle)

    def test_cross_owner_mark_viewed_returns_404(self):
        other_bureau = _make_bureau(
            email="mark-viewed-other-owner@example.com",
            bureau_name="Other Owner Bureau",
            is_active=True,
            is_approved=True,
            is_email_verified=True,
        )
        other_url = reverse(
            "bureaus:mark_intent_viewed",
            kwargs={"intent_id": self.intent.id},
        )
        before_lifecycle = self._lifecycle_snapshot(self.bureau)

        self.client.force_login(other_bureau.user)
        response = self.client.post(other_url)

        self.assertEqual(response.status_code, 404)
        self.intent.refresh_from_db()
        self.assertFalse(self.intent.is_viewed)

        self.bureau.refresh_from_db()
        self.assertEqual(self._lifecycle_snapshot(self.bureau), before_lifecycle)

    def test_anonymous_mark_viewed_redirects_to_login(self):
        response = self.client.post(self.mark_url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])
        self.assertIn("next=", response["Location"])
        self.assertIn(self.mark_url, response["Location"])

        self.intent.refresh_from_db()
        self.assertFalse(self.intent.is_viewed)

    def test_get_mark_viewed_rejected(self):
        self.client.force_login(self.bureau.user)
        response = self.client.get(self.mark_url)

        self.assertEqual(response.status_code, 405)
        self.intent.refresh_from_db()
        self.assertFalse(self.intent.is_viewed)

    def test_requests_tab_scopes_intents_to_owner_bureau(self):
        other_bureau = _make_bureau(
            email="requests-tab-other@example.com",
            bureau_name="Requests Tab Other Bureau",
            is_active=True,
            is_approved=True,
            is_email_verified=True,
        )
        other_intent = BureauBookingIntent.objects.create(
            bureau=other_bureau,
            user=self.requester,
            name="Other Bureau Seeker",
            phone="9000000001",
            message="Should not appear for owner A.",
            is_viewed=False,
        )

        self.client.force_login(self.bureau.user)
        response = self.client.get("/dashboard/bureau/?tab=requests")

        self.assertEqual(response.status_code, 200)
        scoped = response.context["bureau_profile"].booking_intents.all()
        scoped_ids = set(scoped.values_list("id", flat=True))
        self.assertIn(self.intent.id, scoped_ids)
        self.assertNotIn(other_intent.id, scoped_ids)
        self.assertEqual(response.context["bureau_profile"].id, self.bureau.id)


class BureauBookingIntentEdgeCaseTests(TestCase):
    """Regression: duplicate pending, phone cooldown, IP rate limit, validation, GET."""

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.requester = _make_user(email="intent-edge-requester@example.com")
        self.bureau = _make_bureau(
            email="intent-edge-target@example.com",
            bureau_name="Intent Edge Target Bureau",
            is_active=True,
            is_approved=True,
            is_email_verified=True,
        )
        self.intent_url = reverse(
            "bureaus:bureau_intent",
            kwargs={"public_id": self.bureau.public_id},
        )
        self.detail_booking = (
            reverse(
                "bureaus:bureau_detail",
                kwargs={"public_id": self.bureau.public_id},
            )
            + "#booking"
        )
        self.valid_payload = {
            "name": "Edge Seeker",
            "phone": "9111222333",
            "message": "Need matrimony assistance soon.",
        }

    def test_duplicate_pending_intent_rejected(self):
        self.client.force_login(self.requester)
        first = self.client.post(self.intent_url, self.valid_payload)
        self.assertEqual(first.status_code, 302)
        self.assertEqual(
            BureauBookingIntent.objects.filter(
                bureau=self.bureau,
                user=self.requester,
                is_viewed=False,
            ).count(),
            1,
        )

        second = self.client.post(
            self.intent_url,
            {
                "name": "Edge Seeker Again",
                "phone": "9111222334",
                "message": "Second attempt while pending.",
            },
        )
        self.assertEqual(second.status_code, 302)
        self.assertEqual(second["Location"], self.detail_booking)
        self.assertEqual(
            BureauBookingIntent.objects.filter(
                bureau=self.bureau,
                user=self.requester,
            ).count(),
            1,
        )
        self.assertEqual(
            BureauBookingIntent.objects.filter(
                bureau=self.bureau,
                user=self.requester,
                is_viewed=False,
            ).count(),
            1,
        )

    def test_phone_cooldown_enforced(self):
        other_requester = _make_user(email="intent-edge-other@example.com")
        self.client.force_login(self.requester)
        first = self.client.post(self.intent_url, self.valid_payload)
        self.assertEqual(first.status_code, 302)
        self.assertEqual(
            BureauBookingIntent.objects.filter(
                bureau=self.bureau,
                phone="9111222333",
            ).count(),
            1,
        )

        self.client.force_login(other_requester)
        blocked = self.client.post(
            self.intent_url,
            {
                "name": "Other Seeker Same Phone",
                "phone": "9111222333",
                "message": "Same phone within cooldown window.",
            },
        )
        self.assertEqual(blocked.status_code, 302)
        self.assertEqual(blocked["Location"], f"/bureaus/{self.bureau.public_id}/")
        self.assertEqual(
            BureauBookingIntent.objects.filter(
                bureau=self.bureau,
                phone="9111222333",
            ).count(),
            1,
        )
        self.assertFalse(
            BureauBookingIntent.objects.filter(
                bureau=self.bureau,
                user=other_requester,
            ).exists()
        )

    def test_ip_rate_limit_enforced(self):
        self.client.force_login(self.requester)
        for i in range(5):
            response = self.client.post(
                self.intent_url,
                {
                    "name": f"Rate Seeker {i}",
                    "phone": f"922233344{i}",
                    "message": f"Rate limit probe {i}.",
                },
            )
            self.assertEqual(response.status_code, 302, msg=f"attempt {i + 1}")

        limited = self.client.post(
            self.intent_url,
            {
                "name": "Rate Seeker Limited",
                "phone": "9333444555",
                "message": "Should be IP rate limited.",
            },
        )
        self.assertEqual(limited.status_code, 302)
        self.assertEqual(limited["Location"], f"/bureaus/{self.bureau.public_id}/")
        self.assertEqual(
            BureauBookingIntent.objects.filter(
                bureau=self.bureau,
                user=self.requester,
            ).count(),
            1,
        )

    def test_invalid_payload_rejected(self):
        self.client.force_login(self.requester)
        response = self.client.post(
            self.intent_url,
            {
                "name": "Invalid Seeker",
                "phone": "9444555666",
                "message": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.detail_booking)
        self.assertFalse(
            BureauBookingIntent.objects.filter(
                bureau=self.bureau,
                user=self.requester,
            ).exists()
        )

    def test_get_request_rejected(self):
        self.client.force_login(self.requester)
        response = self.client.get(self.intent_url)
        self.assertEqual(response.status_code, 405)
        self.assertFalse(
            BureauBookingIntent.objects.filter(bureau=self.bureau).exists()
        )


class BureauPublicReviewDisplayTests(TestCase):
    """Regression: public detail + owner reviews-tab display of BureauReview data."""

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.reviewer_a = _make_user(email="review-display-a@example.com")
        self.reviewer_b = _make_user(email="review-display-b@example.com")
        self.bureau = _make_bureau(
            email="review-display-owner@example.com",
            bureau_name="Review Display Owner Bureau",
            is_active=True,
            is_approved=True,
            is_email_verified=True,
        )
        self.detail_url = reverse(
            "bureaus:bureau_detail",
            kwargs={"public_id": self.bureau.public_id},
        )

    def test_public_detail_displays_review_content(self):
        BureauReview.objects.create(
            bureau=self.bureau,
            user=self.reviewer_a,
            rating=4,
            review_text="UNIQUE_DISPLAY_ALPHA_REVIEW_TEXT",
        )
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "UNIQUE_DISPLAY_ALPHA_REVIEW_TEXT")
        self.assertContains(response, "4/5")
        self.assertEqual(response.context["bureau"]["review_count"], 1)
        self.assertEqual(response.context["bureau"]["avg_rating"], 4.0)
        self.assertEqual(len(response.context["bureau"]["reviews"]), 1)
        self.assertEqual(
            response.context["bureau"]["reviews"][0]["review_text"],
            "UNIQUE_DISPLAY_ALPHA_REVIEW_TEXT",
        )
        self.assertEqual(response.context["bureau"]["reviews"][0]["rating"], 4)

    def test_public_detail_displays_multiple_reviews(self):
        BureauReview.objects.create(
            bureau=self.bureau,
            user=self.reviewer_a,
            rating=5,
            review_text="UNIQUE_DISPLAY_MULTI_FIRST",
        )
        BureauReview.objects.create(
            bureau=self.bureau,
            user=self.reviewer_b,
            rating=3,
            review_text="UNIQUE_DISPLAY_MULTI_SECOND",
        )
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "UNIQUE_DISPLAY_MULTI_FIRST")
        self.assertContains(response, "UNIQUE_DISPLAY_MULTI_SECOND")
        self.assertContains(response, "5/5")
        self.assertContains(response, "3/5")
        self.assertEqual(response.context["bureau"]["review_count"], 2)
        self.assertEqual(response.context["bureau"]["avg_rating"], 4.0)
        rendered_texts = {
            item["review_text"] for item in response.context["bureau"]["reviews"]
        }
        self.assertEqual(
            rendered_texts,
            {"UNIQUE_DISPLAY_MULTI_FIRST", "UNIQUE_DISPLAY_MULTI_SECOND"},
        )

    def test_hidden_bureau_detail_does_not_expose_reviews(self):
        hidden = _make_bureau(
            email="review-display-hidden@example.com",
            bureau_name="Review Display Hidden Bureau",
            is_active=False,
            is_approved=False,
            is_email_verified=False,
        )
        BureauReview.objects.create(
            bureau=hidden,
            user=self.reviewer_a,
            rating=5,
            review_text="UNIQUE_HIDDEN_BUREAU_REVIEW_SECRET",
        )
        response = self.client.get(
            reverse(
                "bureaus:bureau_detail",
                kwargs={"public_id": hidden.public_id},
            )
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].endswith("/bureaus/"))
        body = response.content.decode("utf-8", errors="ignore")
        self.assertNotIn("UNIQUE_HIDDEN_BUREAU_REVIEW_SECRET", body)

    def test_owner_reviews_tab_displays_own_bureau_reviews(self):
        other_bureau = _make_bureau(
            email="review-display-other@example.com",
            bureau_name="Review Display Other Bureau",
            is_active=True,
            is_approved=True,
            is_email_verified=True,
        )
        BureauReview.objects.create(
            bureau=self.bureau,
            user=self.reviewer_a,
            rating=5,
            review_text="UNIQUE_OWNER_TAB_OWN_REVIEW",
        )
        BureauReview.objects.create(
            bureau=other_bureau,
            user=self.reviewer_b,
            rating=2,
            review_text="UNIQUE_OWNER_TAB_OTHER_REVIEW",
        )

        self.client.force_login(self.bureau.user)
        response = self.client.get("/dashboard/bureau/?tab=reviews")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "UNIQUE_OWNER_TAB_OWN_REVIEW")
        self.assertNotContains(response, "UNIQUE_OWNER_TAB_OTHER_REVIEW")
        self.assertEqual(response.context["bureau_profile"].id, self.bureau.id)
        self.assertEqual(response.context["review_count"], 1)
        self.assertEqual(response.context["avg_rating"], 5.0)
        scoped_ids = set(
            response.context["bureau_profile"].reviews.values_list("id", flat=True)
        )
        own_review = BureauReview.objects.get(
            bureau=self.bureau,
            review_text="UNIQUE_OWNER_TAB_OWN_REVIEW",
        )
        other_review = BureauReview.objects.get(
            bureau=other_bureau,
            review_text="UNIQUE_OWNER_TAB_OTHER_REVIEW",
        )
        self.assertIn(own_review.id, scoped_ids)
        self.assertNotIn(other_review.id, scoped_ids)


@override_settings(EMAIL_BACKEND=LOCMEM_EMAIL)
class BureauBookingIntentNotificationTests(TestCase):
    """Shared Notification created after successful Bureau booking intent only."""

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.requester = _make_user(email="bureau-notif-requester@example.com")
        self.bureau = _make_bureau(
            email="bureau-notif-owner@example.com",
            bureau_name="Notification Target Bureau",
            is_active=True,
            is_approved=True,
            is_email_verified=True,
        )
        self.intent_url = reverse(
            "bureaus:bureau_intent",
            kwargs={"public_id": self.bureau.public_id},
        )
        self.valid_payload = {
            "name": "Notification Seeker",
            "phone": "9000111222",
            "message": "Need marriage bureau assistance.",
        }

    def _owner_booking_notifications(self):
        return Notification.objects.filter(
            recipient=self.bureau.user,
            notification_type=NOTIFICATION_TYPE_BOOKING_INTENT,
            source_module="bureaus",
        )

    def test_successful_intent_creates_owner_notification(self):
        self.client.force_login(self.requester)
        before_flags = {
            "is_email_verified": self.bureau.is_email_verified,
            "is_approved": self.bureau.is_approved,
            "is_active": self.bureau.is_active,
        }

        response = self.client.post(self.intent_url, self.valid_payload)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            BureauBookingIntent.objects.filter(
                bureau=self.bureau,
                user=self.requester,
            ).exists()
        )
        notifications = self._owner_booking_notifications()
        self.assertEqual(notifications.count(), 1)
        notification = notifications.get()
        self.assertEqual(notification.recipient_id, self.bureau.user_id)
        self.assertFalse(notification.is_read)
        self.assertEqual(notification.payload.get("url"), "/dashboard/bureau/?tab=requests")
        self.bureau.refresh_from_db()
        self.assertEqual(self.bureau.is_email_verified, before_flags["is_email_verified"])
        self.assertEqual(self.bureau.is_approved, before_flags["is_approved"])
        self.assertEqual(self.bureau.is_active, before_flags["is_active"])

    def test_anonymous_request_creates_no_notification(self):
        response = self.client.post(self.intent_url, self.valid_payload)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])
        self.assertFalse(
            BureauBookingIntent.objects.filter(bureau=self.bureau).exists()
        )
        self.assertEqual(self._owner_booking_notifications().count(), 0)

    def test_hidden_bureau_creates_no_notification(self):
        hidden = _make_bureau(
            email="bureau-notif-hidden@example.com",
            is_active=False,
            is_approved=False,
            is_email_verified=False,
        )
        url = reverse(
            "bureaus:bureau_intent",
            kwargs={"public_id": hidden.public_id},
        )
        self.client.force_login(self.requester)
        response = self.client.post(
            url,
            {
                "name": "Hidden Seeker",
                "phone": "9000333444",
                "message": "Should not notify.",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/bureaus/")
        self.assertFalse(BureauBookingIntent.objects.filter(bureau=hidden).exists())
        self.assertEqual(
            Notification.objects.filter(
                recipient=hidden.user,
                notification_type=NOTIFICATION_TYPE_BOOKING_INTENT,
                source_module="bureaus",
            ).count(),
            0,
        )

    def test_rejected_duplicate_creates_no_extra_notification(self):
        self.client.force_login(self.requester)
        first = self.client.post(self.intent_url, self.valid_payload)
        self.assertEqual(first.status_code, 302)
        self.assertEqual(self._owner_booking_notifications().count(), 1)

        second = self.client.post(
            self.intent_url,
            {
                "name": "Notification Seeker Again",
                "phone": "9000111223",
                "message": "Duplicate while pending.",
            },
        )
        self.assertEqual(second.status_code, 302)
        self.assertEqual(
            BureauBookingIntent.objects.filter(
                bureau=self.bureau,
                user=self.requester,
            ).count(),
            1,
        )
        self.assertEqual(self._owner_booking_notifications().count(), 1)

    def test_notification_failure_does_not_destroy_successful_intent(self):
        self.client.force_login(self.requester)
        before_flags = {
            "is_email_verified": self.bureau.is_email_verified,
            "is_approved": self.bureau.is_approved,
            "is_active": self.bureau.is_active,
        }
        with patch(
            "notifications.services.NotificationService.create_notification",
            side_effect=RuntimeError("forced notification failure"),
        ):
            response = self.client.post(self.intent_url, self.valid_payload)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            BureauBookingIntent.objects.filter(
                bureau=self.bureau,
                user=self.requester,
            ).exists()
        )
        self.assertEqual(self._owner_booking_notifications().count(), 0)
        self.bureau.refresh_from_db()
        self.assertEqual(self.bureau.is_email_verified, before_flags["is_email_verified"])
        self.assertEqual(self.bureau.is_approved, before_flags["is_approved"])
        self.assertEqual(self.bureau.is_active, before_flags["is_active"])
