"""Regression: ExpertInquiry public create + owner scoping (core.ExpertInquiry)."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from core.models import ExpertInquiry, ExpertProfile
from notifications.constants import NOTIFICATION_TYPE_BOOKING_INTENT
from notifications.models import Notification

User = get_user_model()


class ExpertInquiryRegressionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.owner_a = User.objects.create_user(
            email="expert-inquiry-owner-a@example.com",
            password="pass12345",
        )
        self.owner_b = User.objects.create_user(
            email="expert-inquiry-owner-b@example.com",
            password="pass12345",
        )
        self.expert_a = ExpertProfile.objects.create(
            name="Inquiry Expert A",
            expert_type="ASTROLOGER",
            email=self.owner_a.email,
            phone="9876500301",
            experience_years=5,
            description="Active expert A for inquiry tests",
            is_active=True,
        )
        self.expert_b = ExpertProfile.objects.create(
            name="Inquiry Expert B",
            expert_type="NUMEROLOGIST",
            email=self.owner_b.email,
            phone="9876500302",
            experience_years=4,
            description="Active expert B for inquiry tests",
            is_active=True,
        )
        self.detail_a = reverse("expert_profile", args=[self.expert_a.pk])
        self.detail_b = reverse("expert_profile", args=[self.expert_b.pk])
        self.valid_payload = {
            "name": "Inquiry Seeker",
            "phone": "9111222333",
            "message": "UNIQUE_EXPERT_INQUIRY_MESSAGE_A",
        }

    def test_active_expert_public_inquiry_creates_row(self):
        response = self.client.post(self.detail_a, self.valid_payload)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["contact_success"])
        inquiries = ExpertInquiry.objects.filter(expert=self.expert_a)
        self.assertEqual(inquiries.count(), 1)
        inquiry = inquiries.get()
        self.assertEqual(inquiry.expert_id, self.expert_a.id)
        self.assertEqual(inquiry.name, "Inquiry Seeker")
        self.assertEqual(inquiry.phone, "9111222333")
        self.assertEqual(inquiry.message, "UNIQUE_EXPERT_INQUIRY_MESSAGE_A")
        self.assertFalse(
            ExpertInquiry.objects.filter(expert=self.expert_b).exists()
        )

    def test_owner_requests_tab_scopes_inquiries_to_expert(self):
        ExpertInquiry.objects.create(
            expert=self.expert_a,
            name="Seeker A",
            phone="9222333444",
            message="UNIQUE_INQUIRY_OWNER_SCOPE_A",
        )
        ExpertInquiry.objects.create(
            expert=self.expert_b,
            name="Seeker B",
            phone="9333444555",
            message="UNIQUE_INQUIRY_OWNER_SCOPE_B",
        )

        self.client.force_login(self.owner_a)
        response = self.client.get("/dashboard/expert/?tab=requests")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "UNIQUE_INQUIRY_OWNER_SCOPE_A")
        self.assertNotContains(response, "UNIQUE_INQUIRY_OWNER_SCOPE_B")
        scoped = list(response.context["inquiries"])
        self.assertEqual(len(scoped), 1)
        self.assertEqual(scoped[0].expert_id, self.expert_a.id)
        self.assertEqual(scoped[0].message, "UNIQUE_INQUIRY_OWNER_SCOPE_A")

    def test_inactive_expert_public_detail_creates_no_inquiry(self):
        inactive = ExpertProfile.objects.create(
            name="Inactive Inquiry Expert",
            expert_type="PALMIST",
            email="inactive-inquiry-owner@example.com",
            phone="9876500399",
            is_active=False,
        )
        url = reverse("expert_profile", args=[inactive.pk])

        get_response = self.client.get(url)
        self.assertEqual(get_response.status_code, 404)

        post_response = self.client.post(
            url,
            {
                "name": "Hidden Seeker",
                "phone": "9444555666",
                "message": "UNIQUE_INACTIVE_EXPERT_INQUIRY_SECRET",
            },
        )
        self.assertEqual(post_response.status_code, 404)
        self.assertFalse(
            ExpertInquiry.objects.filter(expert=inactive).exists()
        )
        body = post_response.content.decode("utf-8", errors="ignore")
        self.assertNotIn("UNIQUE_INACTIVE_EXPERT_INQUIRY_SECRET", body)

    def _owner_inquiry_notifications(self):
        return Notification.objects.filter(
            recipient=self.owner_a,
            notification_type=NOTIFICATION_TYPE_BOOKING_INTENT,
            source_module="services",
        )

    def test_successful_inquiry_creates_owner_notification(self):
        response = self.client.post(self.detail_a, self.valid_payload)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["contact_success"])
        self.assertEqual(ExpertInquiry.objects.filter(expert=self.expert_a).count(), 1)
        notifications = self._owner_inquiry_notifications()
        self.assertEqual(notifications.count(), 1)
        notification = notifications.get()
        self.assertEqual(notification.recipient_id, self.owner_a.id)
        self.assertFalse(notification.is_read)
        self.assertEqual(notification.payload.get("title"), "New inquiry")
        self.assertEqual(
            notification.payload.get("url"),
            "/dashboard/expert/?tab=requests",
        )
        self.assertFalse(
            Notification.objects.filter(recipient=self.owner_b).exists()
        )

    def test_invalid_inquiry_does_not_notify(self):
        response = self.client.post(
            self.detail_a,
            {
                "name": "",
                "phone": "9111222333",
                "message": "Should not notify.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["contact_success"])
        self.assertFalse(ExpertInquiry.objects.filter(expert=self.expert_a).exists())
        self.assertEqual(self._owner_inquiry_notifications().count(), 0)

    def test_notification_failure_does_not_break_inquiry(self):
        with patch(
            "notifications.services.NotificationService.create_notification",
            side_effect=RuntimeError("forced notification failure"),
        ):
            response = self.client.post(self.detail_a, self.valid_payload)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["contact_success"])
        self.assertEqual(ExpertInquiry.objects.filter(expert=self.expert_a).count(), 1)
        self.assertEqual(self._owner_inquiry_notifications().count(), 0)
