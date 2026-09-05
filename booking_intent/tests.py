"""Regression: WEB booking-intent create must fail closed on can_create_intent."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse

from booking_intent.models import BookingIntent
from profiles.models import PanditProfile


User = get_user_model()


class WebBookingCreatePermissionFailClosedTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.pandit = User.objects.create_user(
            email="target-pandit@example.com",
            password="PanditTestPass123!",
            role="pandit",
            status="active",
            is_active=True,
            email_verified=True,
        )
        profile, _ = PanditProfile.objects.get_or_create(user=self.pandit)
        profile.is_profile_approved = True
        profile.display_name = "Target Pandit"
        profile.save()
        self.url = reverse(
            "booking_intent_ui:create",
            kwargs={"pandit_public_id": profile.public_id},
        )
        self.valid_post = {
            "user_mobile_number": "9123456789",
            "message": "Need Satyanarayana puja",
        }

    def _create_user(self, *, email, role):
        return User.objects.create_user(
            email=email,
            password="UserTestPass123!",
            role=role,
            status="active",
            is_active=True,
            email_verified=True,
        )

    def _message_texts(self, response):
        return [str(m) for m in get_messages(response.wsgi_request)]

    def test_normal_user_can_create_booking_intent(self):
        user = self._create_user(email="end-user@example.com", role="user")
        self.client.login(email="end-user@example.com", password="UserTestPass123!")
        before = BookingIntent.objects.count()

        response = self.client.post(self.url, data=self.valid_post)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(BookingIntent.objects.count(), before + 1)
        intent = BookingIntent.objects.latest("id")
        self.assertEqual(intent.requester_id, user.id)
        self.assertEqual(intent.pandit_id, self.pandit.id)
        self.assertEqual(intent.user_mobile_number, "9123456789")

    def test_pandit_denied_does_not_create_or_call_service(self):
        self._create_user(email="other-pandit@example.com", role="pandit")
        self.client.login(email="other-pandit@example.com", password="UserTestPass123!")
        before = BookingIntent.objects.count()

        with patch(
            "booking_intent.services.BookingIntentService.create_intent"
        ) as mocked_create:
            response = self.client.post(self.url, data=self.valid_post)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(BookingIntent.objects.count(), before)
        mocked_create.assert_not_called()
        self.assertTrue(
            any("permission" in m.lower() for m in self._message_texts(response)),
            self._message_texts(response),
        )

    def test_admin_denied_does_not_create_or_call_service(self):
        self._create_user(email="admin@example.com", role="admin")
        self.client.login(email="admin@example.com", password="UserTestPass123!")
        before = BookingIntent.objects.count()

        with patch(
            "booking_intent.services.BookingIntentService.create_intent"
        ) as mocked_create:
            response = self.client.post(self.url, data=self.valid_post)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(BookingIntent.objects.count(), before)
        mocked_create.assert_not_called()

    def test_user_missing_mobile_still_validates_without_creating(self):
        self._create_user(email="noval-user@example.com", role="user")
        self.client.login(email="noval-user@example.com", password="UserTestPass123!")
        before = BookingIntent.objects.count()

        response = self.client.post(
            self.url,
            data={"message": "No mobile provided", "user_mobile_number": ""},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(BookingIntent.objects.count(), before)
        texts = self._message_texts(response)
        self.assertTrue(
            any("mobile" in m.lower() or "validation" in m.lower() for m in texts),
            texts,
        )
