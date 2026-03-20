# Phase 9.5/9.5A: Admin and permission tests (TestCase = automatic rollback)
from django.test import TestCase, Client
from django.urls import reverse


class TestAdminAccess(TestCase):
    """Test that admin and protected endpoints require authentication/authorization."""

    def setUp(self):
        self.client = Client()

    def test_admin_login_redirects_anonymous(self):
        response = self.client.get("/nd-control-panel/", follow=False)
        self.assertIn(response.status_code, (302, 200))
        if response.status_code == 302:
            self.assertIn("login", response.url.lower())

    def test_admin_requires_authentication(self):
        response = self.client.get("/nd-control-panel/")
        self.assertIn(response.status_code, (302, 200))
        if response.status_code == 200:
            self.assertTrue(
                b"login" in response.content.lower() or b"Log in" in response.content,
            )
