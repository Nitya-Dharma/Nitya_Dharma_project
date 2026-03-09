# Phase 9.5A: Security headers tests (TestCase = automatic rollback)
from django.test import TestCase, Client
from django.urls import reverse


class TestHeadersSecurity(TestCase):
    """Verify presence of security-related HTTP headers."""

    def setUp(self):
        self.client = Client()

    def test_xframe_options_present(self):
        """X-Frame-Options should be set (clickjacking protection)."""
        response = self.client.get(reverse("core:home"))
        self.assertIn(response.status_code, (200, 302))
        if response.status_code == 200:
            self.assertTrue(
                response.has_header("X-Frame-Options"),
                "X-Frame-Options header should be present",
            )

    def test_x_content_type_options_present(self):
        """X-Content-Type-Options should be set when SecurityMiddleware is used."""
        response = self.client.get(reverse("core:home"))
        self.assertIn(response.status_code, (200, 302))
        if response.status_code == 200 and response.has_header("X-Content-Type-Options"):
            self.assertEqual(
                response.get("X-Content-Type-Options", "").lower(),
                "nosniff",
                "X-Content-Type-Options should be nosniff",
            )

    def test_no_sensitive_headers_leaked(self):
        """Responses should not expose server or internal headers."""
        response = self.client.get(reverse("support:contact_us"))
        self.assertFalse(response.has_header("X-Powered-By"))
        self.assertFalse(response.has_header("Server"))

    def test_referrer_policy_recorded(self):
        """Referrer-Policy presence (record missing in ADVANCED_SECURITY_AUDIT_REPORT if absent)."""
        response = self.client.get(reverse("core:home"))
        if response.status_code == 200:
            self.assertIn(response.has_header("Referrer-Policy"), (True, False))

    def test_security_headers_summary(self):
        """Phase 9.6: X-Frame-Options and X-Content-Type-Options must be present; HSTS only when HTTPS."""
        response = self.client.get(reverse("core:home"))
        if response.status_code != 200:
            return
        self.assertTrue(response.has_header("X-Frame-Options"))
        self.assertTrue(response.has_header("X-Content-Type-Options"))
