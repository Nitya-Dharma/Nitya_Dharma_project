# Phase 11C: Load & concurrency testing
# Simulates concurrent traffic. No application logic, schema, or API changes.
from concurrent.futures import ThreadPoolExecutor

from django.test import TransactionTestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model

from masterdata.models import City, Pooja
from profiles.models import PanditProfile

User = get_user_model()

# Safe concurrency limits (do not exceed to avoid stressing dev machines)
SEARCH_CONCURRENT_REQUESTS = 50
SEARCH_MAX_WORKERS = 10
PROFILE_CONCURRENT_REQUESTS = 30
PROFILE_MAX_WORKERS = 10
BOOKING_CONCURRENT_REQUESTS = 20
BOOKING_MAX_WORKERS = 5


@override_settings(
    STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage"
)
class ConcurrentAPIUsageTests(TransactionTestCase):
    """
    Simulate multiple simultaneous users hitting search, profile, and booking APIs.
    Uses TransactionTestCase so committed data is visible to worker threads.
    """

    def setUp(self):
        self.city = City.objects.create(name="Hyderabad Load")
        self.pooja = Pooja.objects.create(name="Ganesh Puja Load")

        self.pandit_user = User.objects.create_user(
            email="pandit-load@test.com",
            password="testpass123",
            role="pandit",
            status="active",
        )
        self.profile = self.pandit_user.pandit_profile
        self.profile.display_name = "Test Pandit Load"
        self.profile.is_profile_approved = True
        self.profile.save()
        self.profile.cities_served.add(self.city)
        self.profile.poojas_performed.add(self.pooja)

        # Multiple end users for booking concurrency
        self.end_users = []
        for i in range(BOOKING_CONCURRENT_REQUESTS):
            user = User.objects.create_user(
                email=f"user-load-{i}@test.com",
                password="testpass123",
                role="user",
                status="active",
            )
            self.end_users.append(user)

        self.profile_identifier = self.profile.slug or self.profile.public_id

    def test_concurrent_search_requests(self):
        """50 concurrent search requests; no 500s, most responses 200."""
        city_id = self.city.id
        url = reverse("search_api:search_pandits")

        def perform_search(_):
            client = Client()
            response = client.get(url, {"q": "puja", "city_id": city_id})
            return response.status_code

        with ThreadPoolExecutor(max_workers=SEARCH_MAX_WORKERS) as executor:
            results = list(executor.map(perform_search, range(SEARCH_CONCURRENT_REQUESTS)))

        self.assertNotIn(500, results, "No request should return 500")
        success = sum(1 for c in results if c == 200)
        self.assertGreaterEqual(
            success,
            SEARCH_CONCURRENT_REQUESTS * 9 // 10,
            f"At least 90% of requests should be 200; got {success}/{SEARCH_CONCURRENT_REQUESTS}",
        )

    def test_concurrent_profile_views(self):
        """30 concurrent profile page visits; all must be 200."""
        identifier = self.profile_identifier
        url = reverse(
            "profiles:profile_public",
            kwargs={"identifier": identifier},
        )

        def view_profile(_):
            client = Client()
            response = client.get(url)
            return response.status_code

        with ThreadPoolExecutor(max_workers=PROFILE_MAX_WORKERS) as executor:
            results = list(executor.map(view_profile, range(PROFILE_CONCURRENT_REQUESTS)))

        self.assertNotIn(500, results, "No profile request should return 500")
        self.assertEqual(
            results.count(200),
            PROFILE_CONCURRENT_REQUESTS,
            f"All profile requests should be 200; got {results}",
        )

    def test_concurrent_booking_requests(self):
        """20 concurrent booking intent submissions; no 500s. 200/201/302/400 accepted."""
        import json

        pandit_id = self.pandit_user.id
        booking_url = reverse("booking_intent_api:create_intent")
        payload = {"pandit_id": pandit_id, "message": "Concurrent load test"}

        def submit_booking(user_index):
            client = Client()
            user = self.end_users[user_index]
            client.login(email=user.email, password="testpass123")
            client.get(reverse("search_api:search_pandits"))
            response = client.post(
                booking_url,
                data=json.dumps(payload),
                content_type="application/json",
            )
            return response.status_code

        with ThreadPoolExecutor(max_workers=BOOKING_MAX_WORKERS) as executor:
            results = list(
                executor.map(submit_booking, range(BOOKING_CONCURRENT_REQUESTS))
            )

        self.assertNotIn(
            500,
            results,
            "No booking request should return 500",
        )
        allowed = {200, 201, 302, 400, 429}
        for code in results:
            self.assertIn(
                code,
                allowed,
                f"Booking response must be in {allowed}; got {code}",
            )

    def test_repeated_search_queries_no_stampede(self):
        """Repeated identical search queries do not produce server errors (cache stampede risk)."""
        url = reverse("search_api:search_pandits")
        city_id = self.city.id
        queries = ["puja", "puja hyderabad"]

        for q in queries:
            client = Client()
            for _ in range(15):
                response = client.get(url, {"q": q, "city_id": city_id})
                self.assertIn(
                    response.status_code,
                    (200, 400),
                    f"Repeated query '{q}' must not return 500",
                )
