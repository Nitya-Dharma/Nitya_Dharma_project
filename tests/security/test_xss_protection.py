# Phase 9.5/9.5A: XSS protection tests (TestCase = automatic rollback)
from django.test import TestCase, Client
from django.urls import reverse


class TestXssProtection(TestCase):
    def setUp(self):
        self.client = Client()

    def test_search_xss_payload_in_params(self):
        xss = "<script>alert(1)</script>"
        response = self.client.get(
            reverse("search_api:search_pandits"),
            {"city_id": xss, "page": 1},
        )
        self.assertIn(response.status_code, (200, 400))
        content = response.content.decode("utf-8", errors="replace")
        self.assertNotIn("ProgrammingError", content)
        self.assertNotIn("OperationalError", content)

    def test_contact_us_page_returns_200(self):
        response = self.client.get(reverse("support:contact_us"))
        self.assertEqual(response.status_code, 200)
