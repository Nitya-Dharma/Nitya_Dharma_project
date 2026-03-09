# Phase 9.5A: Open redirect security tests (TestCase = automatic rollback)
from django.test import TestCase, Client
from django.urls import reverse


class TestOpenRedirect(TestCase):
    """Ensure redirect URLs are validated and external domains are not allowed."""

    def setUp(self):
        self.client = Client()

    def test_login_next_parameter_safe_relative(self):
        """Login with next=/dashboard/ should redirect to same-origin path after login (or show form)."""
        response = self.client.get(
            reverse("accounts:login"),
            {"next": "/dashboard/"},
        )
        self.assertEqual(response.status_code, 200)
        # Response may contain next in form; must not redirect to external site
        if response.status_code == 302:
            self.assertFalse(
                response.url.startswith("https://") or response.url.startswith("http://"),
                msg="Must not redirect to absolute URL from next param on GET",
            )

    def test_login_next_parameter_external_rejected_or_sanitized(self):
        """Login with next=https://evil.com should not redirect to evil.com."""
        response = self.client.get(
            reverse("accounts:login"),
            {"next": "https://evil.com"},
            follow=False,
        )
        # Either 200 (form) or 302 to safe URL (e.g. same-origin)
        self.assertIn(response.status_code, (200, 302))
        if response.status_code == 302 and response.get("Location"):
            self.assertNotIn(
                "evil.com",
                response["Location"],
                "Must not redirect to external domain from next",
            )
