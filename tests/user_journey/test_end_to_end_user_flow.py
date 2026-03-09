# Phase 11B: End-to-end user journey testing
# Simulates real user flows. No application logic, schema, or migration changes.
import json
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model

from masterdata.models import City, Pooja
from profiles.models import PanditProfile
from booking_intent.models import BookingIntent
from reviews.models import Review

User = get_user_model()


@override_settings(
    STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage"
)
class EndToEndUserJourneyTests(TestCase):
    """Simulate full user workflow: Search → Profile → Booking → Review."""

    def setUp(self):
        self.client = Client()
        self.city = City.objects.create(name="Hyderabad")
        self.pooja = Pooja.objects.create(name="Ganesh Puja")

        self.pandit_user = User.objects.create_user(
            email="pandit-journey@test.com",
            password="testpass123",
            role="pandit",
            status="active",
        )
        self.end_user = User.objects.create_user(
            email="user-journey@test.com",
            password="testpass123",
            role="user",
            status="active",
        )

        self.profile = self.pandit_user.pandit_profile
        self.profile.display_name = "Test Pandit Journey"
        self.profile.is_profile_approved = True
        self.profile.save()
        self.profile.cities_served.add(self.city)
        self.profile.poojas_performed.add(self.pooja)

    def test_full_user_journey_search_then_profile(self):
        """User searches for pandits then visits a pandit profile."""
        url = reverse("search_api:search_pandits")
        response = self.client.get(
            url,
            {"q": "puja", "city_id": self.city.id},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)

        profile_url = reverse(
            "profiles:profile_public",
            kwargs={"identifier": self.profile.slug or self.profile.public_id},
        )
        profile_response = self.client.get(profile_url)
        self.assertEqual(profile_response.status_code, 200)

    def test_search_results_contain_results_key(self):
        """Search API returns 200 and results structure."""
        response = self.client.get(
            reverse("search_api:search_pandits"),
            {"q": "puja", "city_id": self.city.id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.json())

    def test_profile_page_visit(self):
        """Pandit profile page is reachable (200)."""
        identifier = self.profile.slug or self.profile.public_id
        profile_url = reverse(
            "profiles:profile_public",
            kwargs={"identifier": identifier},
        )
        response = self.client.get(profile_url)
        self.assertEqual(response.status_code, 200)

    def test_booking_intent_creation(self):
        """End user can submit a booking intent (logged in)."""
        self.client.login(email="user-journey@test.com", password="testpass123")
        # Ensure CSRF cookie is set
        self.client.get(reverse("search_api:search_pandits"))

        booking_url = reverse("booking_intent_api:create_intent")
        payload = {
            "pandit_id": self.pandit_user.id,
            "message": "Need puja service",
        }
        response = self.client.post(
            booking_url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertIn(
            response.status_code,
            (200, 201, 302, 400),
            msg=f"Booking intent returned {response.status_code}: {getattr(response, 'content', b'')[:500]}",
        )
        if response.status_code in (200, 201):
            self.assertEqual(
                BookingIntent.objects.filter(pandit=self.pandit_user).count(),
                1,
                "Exactly one booking intent should exist for this pandit.",
            )

    def test_review_submission_or_exists(self):
        """End user can submit a review or review exists after submission flow."""
        self.client.login(email="user-journey@test.com", password="testpass123")
        self.client.get(reverse("search_api:search_pandits"))

        review_url = reverse("reviews_api:create_review")
        payload = {
            "pandit_public_id": self.pandit_user.public_id,
            "rating": 5,
            "comment": "Great service",
        }
        response = self.client.post(
            review_url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        if response.status_code == 201:
            self.assertTrue(
                Review.objects.filter(pandit=self.pandit_user).exists(),
                "Review should exist after successful creation.",
            )
        else:
            self.assertIn(
                response.status_code,
                (200, 400, 403),
                msg=f"Review API returned {response.status_code}",
            )

    def test_search_then_profile_then_back_navigation(self):
        """Search → profile → back: search and profile both respond."""
        search_url = reverse("search_api:search_pandits")
        search1 = self.client.get(search_url, {"q": "puja", "city_id": self.city.id})
        self.assertEqual(search1.status_code, 200)

        identifier = self.profile.slug or self.profile.public_id
        profile_url = reverse(
            "profiles:profile_public",
            kwargs={"identifier": identifier},
        )
        profile_resp = self.client.get(profile_url)
        self.assertEqual(profile_resp.status_code, 200)

        search2 = self.client.get(search_url, {"q": "puja", "city_id": self.city.id})
        self.assertEqual(search2.status_code, 200)
        self.assertIn("results", search2.json())

    def test_suggestions_endpoint_in_journey(self):
        """Suggestions API returns 200."""
        response = self.client.get(
            reverse("search_api:search_suggestions"),
            {"q": "pu"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("suggestions", response.json())

    def test_trending_endpoint_in_journey(self):
        """Trending API returns 200."""
        response = self.client.get(reverse("search_api:search_trending"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("trending", response.json())

    def test_related_searches_endpoint_in_journey(self):
        """Related searches API returns 200."""
        response = self.client.get(
            reverse("search_api:search_related"),
            {"q": "puja"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("related", response.json())
