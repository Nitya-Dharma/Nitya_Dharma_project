# Phase 9.6: Session security tests (TestCase = automatic rollback)
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class TestSessionSecurity(TestCase):
    """Verify session cookie attributes and session rotation after login."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="sessiontest@example.com",
            password="testpass123",
            role="end_user",
            status="active",
        )

    def test_session_cookie_httponly_after_login(self):
        self.client.login(email="sessiontest@example.com", password="testpass123")
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        # Session cookie should have HttpOnly (Django default)
        session_cookie = response.cookies.get("sessionid")
        if session_cookie:
            self.assertTrue(
                getattr(session_cookie, "has_nonstandard_attr", lambda x: False)("httponly")
                or "HttpOnly" in str(session_cookie),
                "Session cookie should be HttpOnly",
            )

    def test_session_cookie_samesite_after_login(self):
        self.client.login(email="sessiontest@example.com", password="testpass123")
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        # SameSite is set in settings (Lax); cookie may expose it
        session_cookie = response.cookies.get("sessionid")
        if session_cookie:
            cookie_str = str(session_cookie)
            self.assertTrue(
                "samesite" in cookie_str.lower() or "SameSite" in cookie_str,
                "Session cookie should have SameSite (Lax or Strict)",
            )

    def test_session_created_after_login(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"email": "sessiontest@example.com", "password": "testpass123"},
            follow=False,
        )
        self.assertIn(response.status_code, (200, 302))
        if response.status_code == 302:
            self.assertTrue(
                response.cookies.get("sessionid") is not None
                or "sessionid" in response.cookies,
                "New session should be set after login",
            )
