"""Tests for shared Pandit referral registration validation."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from referrals.models import ReferralLink
from referrals.registration_validation import (
    validate_referral_for_pandit_get,
    validate_referral_for_pandit_post,
    validate_referral_link_by_id,
    validate_referral_link_state,
)

User = get_user_model()


class ReferralRegistrationValidationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin-pandit@example.com",
            password="testpass123",
            role="admin",
            status="active",
            is_active=True,
        )
        self.referral_link = ReferralLink.objects.create(
            created_by=self.admin,
            token="tok-valid-123",
            referral_code="tok-valid-123",
            code="REFAPVALID1",
            max_uses=5,
            used_count=0,
            is_active=True,
            status=ReferralLink.STATUS_ACTIVE,
            expires_at=timezone.now() + timedelta(days=7),
        )

    def test_valid_get_and_post(self):
        get_result = validate_referral_for_pandit_get("tok-valid-123")
        self.assertTrue(get_result.is_valid)
        post_result = validate_referral_for_pandit_post("tok-valid-123", "tok-valid-123")
        self.assertTrue(post_result.is_valid)

    def test_invalid_token_blocked(self):
        result = validate_referral_for_pandit_post("missing-token", "tok-valid-123")
        self.assertFalse(result.is_valid)

    def test_expired_referral_blocked(self):
        self.referral_link.expires_at = timezone.now() - timedelta(minutes=1)
        self.referral_link.save(update_fields=["expires_at"])
        result = validate_referral_link_state(self.referral_link)
        self.assertFalse(result.is_valid)
        self.assertIn("expired", (result.error_message or "").lower())

    def test_revoked_referral_blocked(self):
        self.referral_link.status = ReferralLink.STATUS_REVOKED
        self.referral_link.save(update_fields=["status"])
        result = validate_referral_link_state(self.referral_link)
        self.assertFalse(result.is_valid)

    def test_inactive_referral_blocked(self):
        self.referral_link.is_active = False
        self.referral_link.save(update_fields=["is_active"])
        result = validate_referral_link_state(self.referral_link)
        self.assertFalse(result.is_valid)

    def test_exhausted_referral_blocked(self):
        self.referral_link.used_count = self.referral_link.max_uses
        self.referral_link.save(update_fields=["used_count"])
        result = validate_referral_link_state(self.referral_link)
        self.assertFalse(result.is_valid)

    def test_validate_by_id_for_completion(self):
        result = validate_referral_link_by_id(self.referral_link.id, "tok-valid-123")
        self.assertTrue(result.is_valid)

    def test_code_field_match_supported(self):
        post_result = validate_referral_for_pandit_post("REFAPVALID1", "REFAPVALID1")
        self.assertTrue(post_result.is_valid)
