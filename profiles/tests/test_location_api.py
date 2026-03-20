"""
STEP-2: Tests for Pandit location update API.

POST /api/pandit/update-location/
- Authenticated Pandit → 200, location updated.
- Anonymous → 401.
- Non-Pandit user → 403.
- Invalid coordinates → 400.
- Missing latitude/longitude → 400.
- Numeric string coordinates → accepted, 200.
- Duplicate location → 200 "Location unchanged".
- Rate limit (second update within 5s) → 429.
"""
import json

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from profiles.models import PanditProfile

User = get_user_model()

URL_NAME = "profiles_api:update_pandit_location"


class PanditLocationUpdateAPITest(TestCase):
    """Test POST /api/pandit/update-location/."""

    def setUp(self):
        self.client = Client()
        self.url = reverse(URL_NAME)

    def test_authenticated_pandit_success(self):
        """Authenticated Pandit can update location and gets 200."""
        user = User.objects.create_user(
            email="pandit-loc-api@test.com",
            password="testpass123",
            role="pandit",
            status="active",
        )
        self.client.force_login(user)

        response = self.client.post(
            self.url,
            data=json.dumps({"latitude": 17.3850, "longitude": 78.4867}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["message"], "Location updated successfully")
        self.assertAlmostEqual(data["data"]["latitude"], 17.3850)
        self.assertAlmostEqual(data["data"]["longitude"], 78.4867)

        user.pandit_profile.refresh_from_db()
        self.assertAlmostEqual(float(user.pandit_profile.latitude), 17.3850)
        self.assertAlmostEqual(float(user.pandit_profile.longitude), 78.4867)
        self.assertEqual(user.pandit_profile.location_source, "gps")
        self.assertFalse(user.pandit_profile.is_location_verified)

    def test_anonymous_user_401(self):
        """Anonymous user receives 401."""
        response = self.client.post(
            self.url,
            data=json.dumps({"latitude": 17.3850, "longitude": 78.4867}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data["status"], "error")

    def test_non_pandit_user_403(self):
        """User with role other than pandit receives 403."""
        user = User.objects.create_user(
            email="enduser@test.com",
            password="testpass123",
            role="user",
            status="active",
        )
        self.client.force_login(user)

        response = self.client.post(
            self.url,
            data=json.dumps({"latitude": 17.3850, "longitude": 78.4867}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertEqual(data["status"], "error")

    def test_missing_coordinates_400(self):
        """Missing latitude or longitude in JSON returns 400."""
        user = User.objects.create_user(
            email="pandit-missing@test.com",
            password="testpass123",
            role="pandit",
            status="active",
        )
        self.client.force_login(user)
        response = self.client.post(
            self.url,
            data=json.dumps({"latitude": 17.3850}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing", response.json()["message"])

        response2 = self.client.post(
            self.url,
            data=json.dumps({"longitude": 78.4867}),
            content_type="application/json",
        )
        self.assertEqual(response2.status_code, 400)

    def test_invalid_coordinates_400(self):
        """Invalid coordinates return 400."""
        user = User.objects.create_user(
            email="pandit-invalid@test.com",
            password="testpass123",
            role="pandit",
            status="active",
        )
        self.client.force_login(user)

        response = self.client.post(
            self.url,
            data=json.dumps({"latitude": 999, "longitude": 78.4867}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertIn("Invalid", data["message"])

    def test_malformed_json_400(self):
        """Malformed JSON body returns 400 with 'Invalid JSON' message."""
        user = User.objects.create_user(
            email="pandit-malformed@test.com",
            password="testpass123",
            role="pandit",
            status="active",
        )
        self.client.force_login(user)
        response = self.client.post(
            self.url,
            data="not valid json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertIn("JSON", data["message"])

    def test_wrong_content_type_400(self):
        """Wrong Content-Type returns 400."""
        user = User.objects.create_user(
            email="pandit-ct@test.com",
            password="testpass123",
            role="pandit",
            status="active",
        )
        self.client.force_login(user)
        response = self.client.post(
            self.url,
            data="latitude=17&longitude=78",
            content_type="application/x-www-form-urlencoded",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Content-Type", response.json()["message"])

    def test_missing_pandit_profile_404(self):
        """Pandit user without PanditProfile receives 404."""
        from django.db import connection

        user = User.objects.create_user(
            email="pandit-noprofile@test.com",
            password="testpass123",
            role="pandit",
            status="active",
        )
        # Signal creates profile; remove row via SQL to simulate missing profile
        # (PanditProfile is NO_DELETE so we bypass ORM for this test only)
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM profiles_panditprofile WHERE user_id = %s",
                [user.id],
            )
        self.client.force_login(user)
        response = self.client.post(
            self.url,
            data=json.dumps({"latitude": 17.3850, "longitude": 78.4867}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertIn("profile", data["message"].lower())

    def test_numeric_string_coordinates_accepted(self):
        """Numeric strings in JSON are accepted and return 200."""
        user = User.objects.create_user(
            email="pandit-strings@test.com",
            password="testpass123",
            role="pandit",
            status="active",
        )
        self.client.force_login(user)

        response = self.client.post(
            self.url,
            data=json.dumps({"latitude": "17.3850", "longitude": "78.4867"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertAlmostEqual(data["data"]["latitude"], 17.385)
        self.assertAlmostEqual(data["data"]["longitude"], 78.4867)

    def test_rate_limit_second_update_429(self):
        """Second update within 5 seconds returns 429 (rate limited)."""
        user = User.objects.create_user(
            email="pandit-rate@test.com",
            password="testpass123",
            role="pandit",
            status="active",
        )
        PanditProfile.objects.get_or_create(user=user)
        self.client.force_login(user)

        first = self.client.post(
            self.url,
            data=json.dumps({"latitude": 17.3850, "longitude": 78.4867}),
            content_type="application/json",
        )
        self.assertEqual(first.status_code, 200)

        second = self.client.post(
            self.url,
            data=json.dumps({"latitude": 17.4000, "longitude": 78.5000}),
            content_type="application/json",
        )
        self.assertEqual(second.status_code, 429)
        data = second.json()
        self.assertEqual(data["status"], "error")
        self.assertIn("frequently", data["message"])

    def test_duplicate_location_returns_unchanged(self):
        """Sending the same coordinates again returns 200 with 'Location unchanged'."""
        user = User.objects.create_user(
            email="pandit-dup@test.com",
            password="testpass123",
            role="pandit",
            status="active",
        )
        PanditProfile.objects.get_or_create(user=user)
        self.client.force_login(user)

        payload = json.dumps({"latitude": 17.3850, "longitude": 78.4867})

        first = self.client.post(
            self.url,
            data=payload,
            content_type="application/json",
        )
        self.assertEqual(first.status_code, 200)

        second = self.client.post(
            self.url,
            data=payload,
            content_type="application/json",
        )
        data = second.json()
        self.assertEqual(second.status_code, 200)
        self.assertEqual(data["message"], "Location unchanged")
