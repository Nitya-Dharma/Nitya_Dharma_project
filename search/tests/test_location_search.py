"""
STEP-3: Tests for location-based search.

GET /api/search/pandits/?lat=...&lon=...&radius_km=...
- Valid lat/lon returns nearby Pandits, sorted by distance.
- Invalid coordinates return 400.
- Pandits outside radius excluded; null coordinates excluded.
"""
from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from masterdata.models import City
from profiles.models import PanditProfile
from search.location_search_service import find_nearby_pandits

User = get_user_model()


class LocationSearchServiceTest(TestCase):
    """Test find_nearby_pandits service."""

    def setUp(self):
        self.city = City.objects.create(name="Hyderabad", state="Telangana", is_active=True)
        self.user1 = User.objects.create_user(
            email="pandit-near@test.com",
            password="testpass123",
            role="pandit",
            status="active",
        )
        self.profile1 = self.user1.pandit_profile
        self.profile1.latitude = Decimal("17.3850")
        self.profile1.longitude = Decimal("78.4867")
        self.profile1.is_profile_approved = True
        self.profile1.save()
        self.profile1.cities_served.add(self.city)

        self.user2 = User.objects.create_user(
            email="pandit-far@test.com",
            password="testpass123",
            role="pandit",
            status="active",
        )
        self.profile2 = self.user2.pandit_profile
        # Bangalore ~500 km away
        self.profile2.latitude = Decimal("12.9716")
        self.profile2.longitude = Decimal("77.5946")
        self.profile2.is_profile_approved = True
        self.profile2.save()
        self.profile2.cities_served.add(self.city)

    def test_valid_location_returns_nearby_pandits(self):
        """Valid lat/lon returns list with distance_km, sorted by distance."""
        results = find_nearby_pandits(17.3850, 78.4867, radius_km=20)
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        near = [r for r in results if r["pandit_id"] == self.user1.id]
        self.assertEqual(len(near), 1)
        self.assertAlmostEqual(near[0]["distance_km"], 0.0, places=2)
        self.assertEqual(near[0]["name"], self.profile1.get_display_name() or self.user1.get_full_name())
        self.assertEqual(near[0]["city"], "Hyderabad")
        # Results sorted by distance
        for i in range(len(results) - 1):
            self.assertLessEqual(results[i]["distance_km"], results[i + 1]["distance_km"])

    def test_invalid_coordinates_raises(self):
        """Invalid coordinates raise ValueError."""
        with self.assertRaises(ValueError):
            find_nearby_pandits(999, 78.0, radius_km=20)
        with self.assertRaises(ValueError):
            find_nearby_pandits(17.0, None, radius_km=20)

    def test_negative_radius_raises_error(self):
        """Negative radius raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            find_nearby_pandits(17.3850, 78.4867, radius_km=-10)
        self.assertIn("Radius", str(ctx.exception))

    def test_pandits_outside_radius_excluded(self):
        """Pandits beyond radius_km are not in results."""
        results = find_nearby_pandits(17.3850, 78.4867, radius_km=10)
        ids = [r["pandit_id"] for r in results]
        self.assertIn(self.user1.id, ids)
        self.assertNotIn(self.user2.id, ids)

    def test_results_sorted_by_distance(self):
        """Results are ordered by distance ascending."""
        results = find_nearby_pandits(17.3850, 78.4867, radius_km=600)
        self.assertGreaterEqual(len(results), 2)
        for i in range(len(results) - 1):
            self.assertLessEqual(results[i]["distance_km"], results[i + 1]["distance_km"])

    def test_results_have_deterministic_order(self):
        """Results are sorted by distance then pandit_id for stable ordering."""
        results = find_nearby_pandits(17.3850, 78.4867, radius_km=600)
        if len(results) > 1:
            distances = [r["distance_km"] for r in results]
            self.assertEqual(distances, sorted(distances))
        self.assertEqual(
            results,
            sorted(results, key=lambda x: (x["distance_km"], x["pandit_id"])),
            "Results must be ordered by distance_km then pandit_id for deterministic order.",
        )

    def test_null_coordinates_excluded(self):
        """Pandits with null lat/lon are not returned."""
        user3 = User.objects.create_user(
            email="pandit-null-loc@test.com",
            password="testpass123",
            role="pandit",
            status="active",
        )
        user3.pandit_profile.is_profile_approved = True
        user3.pandit_profile.latitude = None
        user3.pandit_profile.longitude = None
        user3.pandit_profile.save()
        results = find_nearby_pandits(17.3850, 78.4867, radius_km=1000)
        ids = [r["pandit_id"] for r in results]
        self.assertNotIn(user3.id, ids)

    def test_profiles_with_null_coordinates_are_skipped(self):
        """Defensive check: profiles with null coordinates are skipped and do not crash."""
        user = User.objects.create_user(
            email="pandit-null-only@test.com",
            password="testpass123",
            role="pandit",
            status="active",
        )
        profile = user.pandit_profile
        profile.latitude = None
        profile.longitude = None
        profile.is_profile_approved = True
        profile.save()
        # Only this profile has null coords; DB filter or defensive check excludes it
        results = find_nearby_pandits(17.3850, 78.4867, radius_km=1000)
        self.assertNotIn(user.id, [r["pandit_id"] for r in results])
        # No crash; function returns safely
        self.assertIsInstance(results, list)


class LocationSearchAPITest(TestCase):
    """Test GET /api/search/pandits/?lat=...&lon=..."""

    def setUp(self):
        self.client = Client()
        self.url = reverse("search_api:search_pandits")

    def test_valid_lat_lon_returns_200_and_results(self):
        """Request with lat and lon returns 200 and results list."""
        response = self.client.get(self.url, {"lat": "17.3850", "lon": "78.4867"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("results", data)
        self.assertIsInstance(data["results"], list)

    def test_invalid_coordinates_return_400(self):
        """Invalid lat/lon returns 400 with error message."""
        response = self.client.get(self.url, {"lat": "999", "lon": "78.4867"})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertIn("location", data["message"].lower())

    def test_search_without_lat_lon_unchanged(self):
        """Request without lat/lon uses normal search (different response shape)."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Normal search returns results + pagination, not status/results
        self.assertIn("results", data)
        self.assertIn("pagination", data)
        self.assertNotIn("status", data)  # location search returns status
