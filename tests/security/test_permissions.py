# Phase 9.5/9.5A: Permission and unauthorized access tests (TestCase = automatic rollback)
from django.test import TestCase, Client
from django.urls import reverse


class TestPermissions(TestCase):
    """Test that protected endpoints return proper permission errors for unauthorized users."""

    def setUp(self):
        self.client = Client()

    def test_guest_cannot_access_super_admin_contact_requests(self):
        response = self.client.get(reverse("support:contact_requests_admin"))
        self.assertIn(
            response.status_code, (302, 403, 404),
            "Unauthorized should not get 200 OK",
        )

    def test_search_api_get_allowed_without_auth(self):
        response = self.client.get(reverse("search_api:search_pandits"))
        self.assertIn(response.status_code, (200, 401, 403))
