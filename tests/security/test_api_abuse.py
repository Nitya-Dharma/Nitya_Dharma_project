# Phase 9.6: API abuse simulation (max 20 requests per endpoint; no DoS)
from django.test import TestCase, Client
from django.urls import reverse


class TestApiAbuse(TestCase):
    """Simulate up to 20 repeated requests per endpoint; server must not crash."""

    def setUp(self):
        self.client = Client()
        self.max_requests = 20

    def test_repeated_login_requests_no_crash(self):
        for i in range(self.max_requests):
            response = self.client.post(
                reverse("accounts:login"),
                {"email": "abuse@example.com", "password": "wrong"},
                follow=False,
            )
            self.assertIn(response.status_code, (200, 302), f"Request {i+1}")

    def test_repeated_search_requests_no_crash(self):
        for i in range(self.max_requests):
            response = self.client.get(
                reverse("search_api:search_pandits"),
                {"page": 1},
                follow=False,
            )
            self.assertIn(response.status_code, (200, 400, 401, 403), f"Request {i+1}")

    def test_repeated_booking_api_requests_no_crash(self):
        for i in range(self.max_requests):
            response = self.client.get(
                reverse("booking_intent_api:list_my_intents"),
                follow=False,
            )
            self.assertIn(response.status_code, (200, 302, 401, 403), f"Request {i+1}")

    def test_repeated_contact_form_get_no_crash(self):
        for i in range(self.max_requests):
            response = self.client.get(reverse("support:contact_us"), follow=False)
            self.assertEqual(response.status_code, 200, f"Request {i+1}")
