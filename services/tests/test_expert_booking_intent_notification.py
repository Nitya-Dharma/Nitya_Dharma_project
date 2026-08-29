"""Expert owner Notification after successful booking-intent create."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from core.models import ExpertProfile
from notifications.constants import NOTIFICATION_TYPE_BOOKING_INTENT
from notifications.models import Notification
from services.models import ExpertBookingIntent

User = get_user_model()


class ExpertBookingIntentNotificationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.requester = User.objects.create_user(
            email="expert-notif-requester@example.com",
            password="pass12345",
        )
        self.owner = User.objects.create_user(
            email="expert-notif-owner@example.com",
            password="pass12345",
        )
        self.expert = ExpertProfile.objects.create(
            name="Notification Target Expert",
            expert_type="ASTROLOGER",
            email=self.owner.email,
            phone="9876500011",
            experience_years=5,
            description="Active expert for notification tests",
            is_active=True,
            is_verified=False,
        )
        self.intent_url = reverse(
            "expert_booking_intent",
            args=[self.expert.pk],
        )
        self.valid_payload = {
            "name": "Notification Seeker",
            "phone": "9000111222",
            "message": "Need astrology consultation.",
        }

    def _owner_booking_notifications(self):
        return Notification.objects.filter(
            recipient=self.owner,
            notification_type=NOTIFICATION_TYPE_BOOKING_INTENT,
            source_module="services",
        )

    def test_successful_intent_creates_owner_notification(self):
        self.client.force_login(self.requester)

        response = self.client.post(self.intent_url, self.valid_payload)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ExpertBookingIntent.objects.filter(
                expert=self.expert,
                user=self.requester,
            ).exists()
        )
        notifications = self._owner_booking_notifications()
        self.assertEqual(notifications.count(), 1)
        notification = notifications.get()
        self.assertEqual(notification.recipient_id, self.owner.id)
        self.assertFalse(notification.is_read)
        self.assertEqual(
            notification.payload.get("url"),
            "/dashboard/expert/?tab=requests",
        )
        # Customer must not receive the owner alert.
        self.assertFalse(
            Notification.objects.filter(recipient=self.requester).exists()
        )

    def test_notification_failure_does_not_destroy_successful_intent(self):
        self.client.force_login(self.requester)
        with patch(
            "notifications.services.NotificationService.create_notification",
            side_effect=RuntimeError("forced notification failure"),
        ):
            response = self.client.post(self.intent_url, self.valid_payload)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ExpertBookingIntent.objects.filter(
                expert=self.expert,
                user=self.requester,
            ).exists()
        )
        self.assertEqual(self._owner_booking_notifications().count(), 0)

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
            ExpertBookingIntent.objects.filter(
                expert=self.expert,
                user=self.requester,
            ).count(),
            1,
        )
        self.assertEqual(self._owner_booking_notifications().count(), 1)

    def test_inactive_expert_creates_no_notification(self):
        inactive = ExpertProfile.objects.create(
            name="Inactive Expert",
            expert_type="ASTROLOGER",
            email="inactive-expert-owner@example.com",
            phone="9876500099",
            is_active=False,
        )
        inactive_owner = User.objects.create_user(
            email="inactive-expert-owner@example.com",
            password="pass12345",
        )
        url = reverse("expert_booking_intent", args=[inactive.pk])
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
        self.assertFalse(
            ExpertBookingIntent.objects.filter(expert=inactive).exists()
        )
        self.assertEqual(
            Notification.objects.filter(
                recipient=inactive_owner,
                notification_type=NOTIFICATION_TYPE_BOOKING_INTENT,
                source_module="services",
            ).count(),
            0,
        )
