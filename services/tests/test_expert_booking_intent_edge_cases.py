"""Regression: Expert booking-intent edge cases (services.ExpertBookingIntent)."""

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from core.models import ExpertProfile
from services.models import ExpertBookingIntent

User = get_user_model()


class ExpertBookingIntentEdgeCaseTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.requester = User.objects.create_user(
            email="expert-edge-requester@example.com",
            password="pass12345",
        )
        self.owner = User.objects.create_user(
            email="expert-edge-owner@example.com",
            password="pass12345",
        )
        self.expert = ExpertProfile.objects.create(
            name="Edge Case Expert",
            expert_type="ASTROLOGER",
            email=self.owner.email,
            phone="9876500100",
            experience_years=5,
            description="Active expert for booking edge-case tests",
            is_active=True,
            is_verified=False,
        )
        self.intent_url = reverse(
            "expert_booking_intent",
            args=[self.expert.pk],
        )
        self.booking_redirect = (
            reverse("expert_profile", args=[self.expert.pk]) + "#booking"
        )
        self.valid_payload = {
            "name": "Edge Seeker",
            "phone": "9111222333",
            "message": "Need astrology consultation.",
        }

    def test_successful_booking_intent_creates_canonical_row(self):
        self.client.force_login(self.requester)

        response = self.client.post(self.intent_url, self.valid_payload)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.booking_redirect)
        intents = ExpertBookingIntent.objects.filter(
            expert=self.expert,
            user=self.requester,
        )
        self.assertEqual(intents.count(), 1)
        intent = intents.get()
        self.assertEqual(intent.name, "Edge Seeker")
        self.assertEqual(intent.phone, "9111222333")
        self.assertEqual(intent.message, "Need astrology consultation.")
        self.assertFalse(intent.is_viewed)

    def test_inactive_expert_rejected(self):
        inactive = ExpertProfile.objects.create(
            name="Inactive Edge Expert",
            expert_type="ASTROLOGER",
            email="inactive-edge-owner@example.com",
            phone="9876500199",
            is_active=False,
        )
        url = reverse("expert_booking_intent", args=[inactive.pk])
        self.client.force_login(self.requester)

        response = self.client.post(url, self.valid_payload)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("core:home"))
        self.assertFalse(
            ExpertBookingIntent.objects.filter(expert=inactive).exists()
        )

    def test_duplicate_pending_unread_intent_rejected(self):
        self.client.force_login(self.requester)
        first = self.client.post(self.intent_url, self.valid_payload)
        self.assertEqual(first.status_code, 302)
        self.assertEqual(
            ExpertBookingIntent.objects.filter(
                expert=self.expert,
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
        self.assertEqual(second["Location"], self.booking_redirect)
        self.assertEqual(
            ExpertBookingIntent.objects.filter(
                expert=self.expert,
                user=self.requester,
            ).count(),
            1,
        )
        self.assertEqual(
            ExpertBookingIntent.objects.filter(
                expert=self.expert,
                user=self.requester,
                is_viewed=False,
            ).count(),
            1,
        )

    def test_phone_cooldown_enforced(self):
        other_requester = User.objects.create_user(
            email="expert-edge-other@example.com",
            password="pass12345",
        )
        self.client.force_login(self.requester)
        first = self.client.post(self.intent_url, self.valid_payload)
        self.assertEqual(first.status_code, 302)
        self.assertEqual(
            ExpertBookingIntent.objects.filter(
                expert=self.expert,
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
        self.assertEqual(blocked["Location"], self.booking_redirect)
        self.assertEqual(
            ExpertBookingIntent.objects.filter(
                expert=self.expert,
                phone="9111222333",
            ).count(),
            1,
        )
        self.assertFalse(
            ExpertBookingIntent.objects.filter(
                expert=self.expert,
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
        self.assertEqual(limited["Location"], self.booking_redirect)
        self.assertEqual(
            ExpertBookingIntent.objects.filter(
                expert=self.expert,
                user=self.requester,
            ).count(),
            1,
        )


class ExpertBookingIntentMarkViewedOwnershipTests(TestCase):
    """Owner can mark viewed; non-owners cannot mutate another expert's intent."""

    REQUESTS_UPDATED = "/dashboard/expert/?tab=requests&updated=1"

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.requester = User.objects.create_user(
            email="expert-mark-requester@example.com",
            password="pass12345",
        )
        self.owner = User.objects.create_user(
            email="expert-mark-owner@example.com",
            password="pass12345",
        )
        self.expert = ExpertProfile.objects.create(
            name="Mark Viewed Expert",
            expert_type="NUMEROLOGIST",
            email=self.owner.email,
            phone="9876500200",
            experience_years=4,
            description="Active expert for mark-viewed ownership",
            is_active=True,
            is_verified=False,
        )
        self.intent = ExpertBookingIntent.objects.create(
            expert=self.expert,
            user=self.requester,
            name="Mark Seeker",
            phone="9123456789",
            message="Please contact me.",
            is_viewed=False,
        )
        self.mark_url = reverse(
            "mark_expert_intent_viewed",
            args=[self.intent.pk],
        )

    def test_owner_can_mark_own_intent_viewed(self):
        self.assertFalse(self.intent.is_viewed)
        self.client.force_login(self.owner)

        response = self.client.post(self.mark_url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.REQUESTS_UPDATED)
        self.intent.refresh_from_db()
        self.assertTrue(self.intent.is_viewed)

    def test_non_owner_cannot_mark_intent_viewed(self):
        stranger = User.objects.create_user(
            email="expert-mark-stranger@example.com",
            password="pass12345",
        )
        other_owner = User.objects.create_user(
            email="expert-mark-other-owner@example.com",
            password="pass12345",
        )
        ExpertProfile.objects.create(
            name="Other Mark Expert",
            expert_type="PALMIST",
            email=other_owner.email,
            phone="9876500201",
            is_active=True,
        )

        self.client.force_login(stranger)
        stranger_response = self.client.post(self.mark_url)
        self.assertEqual(stranger_response.status_code, 302)
        self.assertEqual(stranger_response["Location"], "/dashboard/user/")
        self.intent.refresh_from_db()
        self.assertFalse(self.intent.is_viewed)

        self.client.force_login(other_owner)
        other_response = self.client.post(self.mark_url)
        self.assertEqual(other_response.status_code, 404)
        self.intent.refresh_from_db()
        self.assertFalse(self.intent.is_viewed)
