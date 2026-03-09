# Phase 11A: URL persistence and user journey navigation tests
# Tests only — no changes to application logic.
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from masterdata.models import City, Pooja
from profiles.models import PanditProfile

User = get_user_model()


class URLPersistenceTests(TestCase):
    """Verify search and navigation URLs preserve parameters and endpoints respond safely."""

    def setUp(self):
        self.client = Client()

    def test_search_query_persistence(self):
        """Step 3: Query and pagination parameters remain intact in search URL."""
        response = self.client.get(
            reverse("search_api:search_pandits"),
            {"q": "puja", "page": 2},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("pagination", data)
        self.assertEqual(data["pagination"]["page"], 2)

    def test_search_filters_persistence(self):
        """Step 4: Filters (city_id, pooja_id, enable_call) survive in URL."""
        # Create minimal master data so API validation accepts city_id/pooja_id (Phase 11A.2)
        city = City.objects.create(name="Test City Filters")
        pooja = Pooja.objects.create(name="Ganesh Puja")
        user = User.objects.create_user(email="pandit-filters@test.com", password="testpass123", role="pandit")
        # PanditProfile is created by signal for role=pandit; use it and add filters
        profile = user.pandit_profile
        profile.display_name = "Test Pandit Filters"
        profile.is_profile_approved = True
        profile.save()
        profile.cities_served.add(city)
        profile.poojas_performed.add(pooja)

        url = reverse("search_api:search_pandits")
        response = self.client.get(
            url,
            {
                "q": "puja",
                "city_id": city.id,
                "pooja_id": pooja.id,
                "enable_call": "true",
            },
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertIn("results", response_data)

    def test_pagination_url_persistence(self):
        """Step 5: Page parameter is preserved."""
        response = self.client.get(
            reverse("search_api:search_pandits"),
            {"q": "puja", "page": 3},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["pagination"]["page"], 3)

    def test_back_navigation_flow(self):
        """Step 6: Search results then profile page — both endpoints work independently."""
        search = self.client.get(
            reverse("search_api:search_pandits"),
            {"q": "puja"},
        )
        self.assertEqual(search.status_code, 200)
        profile = self.client.get(
            reverse("profiles:profile_public", kwargs={"identifier": "test-slug"}),
        )
        self.assertIn(profile.status_code, (200, 404))

    def test_forward_navigation(self):
        """Step 7: Search → profile flow; both requests complete."""
        self.client.get(
            reverse("search_api:search_pandits"),
            {"q": "puja"},
        )
        profile = self.client.get(
            reverse("profiles:profile_public", kwargs={"identifier": "test-slug"}),
        )
        self.assertIn(profile.status_code, (200, 404))

    def test_empty_query_url(self):
        """Step 8: Empty q= does not break API."""
        response = self.client.get(
            reverse("search_api:search_pandits"),
            {"q": ""},
        )
        self.assertEqual(response.status_code, 200)

    def test_invalid_query_parameters(self):
        """Step 9: Invalid/special params do not break API."""
        response = self.client.get(
            reverse("search_api:search_pandits"),
            {"q": "<script>", "page": 9999},
        )
        self.assertEqual(response.status_code, 200)

    def test_autocomplete_url(self):
        """Step 10: Autocomplete endpoint accepts q and returns 200."""
        response = self.client.get(
            reverse("search_api:search_suggestions"),
            {"q": "pu"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("suggestions", data)

    def test_trending_endpoint(self):
        """Step 11: Trending endpoint returns 200."""
        response = self.client.get(reverse("search_api:search_trending"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("trending", data)

    def test_related_searches_endpoint(self):
        """Step 12: Related searches endpoint accepts q and returns 200."""
        response = self.client.get(
            reverse("search_api:search_related"),
            {"q": "puja"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("related", data)
