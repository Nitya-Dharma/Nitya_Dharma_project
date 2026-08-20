"""Focused Pandit registration + OTP integration tests."""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from otp_verification import constants as otp_constants
from otp_verification.registration.completions import (
    CompletionError,
    complete_pending_registration,
)
from profiles.models import PanditProfile
from referrals.models import ReferralLink, ReferralUsage

User = get_user_model()


class PanditRegistrationOTPIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            email="admin-pandit@example.com",
            password="testpass123",
            role="admin",
            status="active",
            is_active=True,
        )
        self.referral_link = ReferralLink.objects.create(
            created_by=self.admin,
            token="pandit-tok-001",
            referral_code="pandit-tok-001",
            code="REFAPPAND1",
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

    @override_settings(OTP_ENABLED=False)
    def test_direct_registration_still_works_when_otp_disabled(self):
        response = self.client.post(
            self.register_url,
            {
                "referral_code": self.referral_link.referral_code,
                "first_name": "Direct",
                "last_name": "Pandit",
                "email": "direct-pandit@example.com",
                "password": "securepass123",
            },
        )
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(email="direct-pandit@example.com")
        self.assertEqual(user.role, "pandit")
        self.assertEqual(user.status, "pending")
        self.assertFalse(user.is_active)
        self.assertFalse(user.email_verified)
        self.assertTrue(PanditProfile.objects.filter(user=user).exists())
        self.assertTrue(ReferralUsage.objects.filter(referred_pandit=user).exists())

    @override_settings(OTP_ENABLED=True, OTP_ENABLED_FLOWS=otp_constants.FLOW_CHOICES)
    @patch("otp_verification.registration.gate.build_registration_otp_service")
    def test_otp_required_pauses_registration(self, mock_build_service):
        mock_service = mock_build_service.return_value
        mock_service.start_verification.return_value = type(
            "Issued",
            (),
            {"challenge_id": "chal-pandit-1", "expires_at": timezone.now() + timedelta(minutes=10)},
        )()

        response = self.client.post(
            self.register_url,
            {
                "referral_code": self.referral_link.referral_code,
                "first_name": "Otp",
                "last_name": "Pandit",
                "email": "otp-pandit@example.com",
                "password": "securepass123",
                "phone_number": "9876543210",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="otp-pandit@example.com").exists())
        mock_service.start_verification.assert_called_once()

    @override_settings(OTP_ENABLED=False)
    def test_invalid_referral_blocks_direct_registration(self):
        expired = ReferralLink.objects.create(
            created_by=self.admin,
            token="expired-tok",
            referral_code="expired-tok",
            code="REFAPEXP1",
            max_uses=1,
            used_count=0,
            is_active=True,
            status=ReferralLink.STATUS_ACTIVE,
            expires_at=timezone.now() - timedelta(minutes=5),
        )
        url = reverse("accounts:pandit_register", kwargs={"referral_token": expired.token})
        response = self.client.post(
            url,
            {
                "referral_code": expired.referral_code,
                "first_name": "Bad",
                "last_name": "Referral",
                "email": "bad-referral@example.com",
                "password": "securepass123",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="bad-referral@example.com").exists())

    def test_complete_pandit_requires_valid_referral(self):
        with self.assertRaises(CompletionError):
            complete_pending_registration(
                pending={
                    "flow_type": otp_constants.FLOW_PANDIT_REGISTRATION,
                    "payload": {
                        "email": "otp-complete@example.com",
                        "password_hash": "!",
                        "first_name": "Otp",
                        "last_name": "Complete",
                        "phone_number": "9876543210",
                    },
                }
            )

    def test_complete_pandit_does_not_auto_approve_account(self):
        result = complete_pending_registration(
            pending={
                "flow_type": otp_constants.FLOW_PANDIT_REGISTRATION,
                "payload": {
                    "email": "otp-complete@example.com",
                    "password_hash": make_password("securepass123"),
                    "first_name": "Otp",
                    "last_name": "Complete",
                    "phone_number": "9876543210",
                    "referral_link_id": self.referral_link.id,
                    "referral_code": self.referral_link.referral_code,
                },
            }
        )
        user = User.objects.get(email="otp-complete@example.com")
        self.assertEqual(result["email"], user.email)
        self.assertEqual(user.status, "pending")
        self.assertFalse(user.is_active)
        self.assertFalse(user.email_verified)
        profile = PanditProfile.objects.get(user=user)
        self.assertFalse(profile.is_profile_approved)
