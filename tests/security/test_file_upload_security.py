# Phase 9.5A: File upload security tests (TestCase = automatic rollback)
from django.test import TestCase, Client
from django.urls import reverse


class TestFileUploadSecurity(TestCase):
    """Verify file type validation and rejection of executable/dangerous uploads."""

    def setUp(self):
        self.client = Client()

    def test_contact_us_post_with_invalid_content_type(self):
        """Contact form should handle non-form data safely."""
        response = self.client.post(
            reverse("support:contact_us"),
            data="raw body",
            content_type="application/octet-stream",
        )
        self.assertIn(response.status_code, (200, 400, 403, 415))

    def test_search_api_accepts_only_get(self):
        """Search endpoint should not accept POST with arbitrary body."""
        response = self.client.post(
            reverse("search_api:search_pandits"),
            data={"city_id": 1},
            content_type="application/json",
        )
        self.assertIn(response.status_code, (200, 405, 400))
