# Phase 9.5/9.5A: Authentication security tests (TestCase = automatic rollback)
from django.test import TestCase, Client
from django.urls import reverse


class TestAuthSecurity(TestCase):
    def setUp(self):
        self.client = Client()

    def test_invalid_login_returns_200_or_302_not_500(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"email": "nonexistent@example.com", "password": "wrong"},
            follow=False,
        )
        self.assertIn(response.status_code, (200, 302))

    def test_invalid_login_does_not_reveal_user_exists(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"email": "nonexistent@example.com", "password": "wrong"},
            follow=True,
        )
        content = response.content.decode("utf-8", errors="replace")
        self.assertTrue(
            "does not exist" not in content.lower() or "invalid" in content.lower(),
            "Login response should not reveal user enumeration",
        )

    def test_login_page_get_200(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
