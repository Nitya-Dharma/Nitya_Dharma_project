# Phase 9.6: Privilege escalation tests
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class TestPrivilegeEscalation(TestCase):
    def setUp(self):
        self.client = Client()
        self.normal_user = User.objects.create_user(
            email="normal@example.com", password="pass123",
            role="end_user", status="active",
        )

    def test_normal_user_admin_redirect_or_forbidden(self):
        self.client.force_login(self.normal_user)
        response = self.client.get("/admin/", follow=False)
        self.assertIn(response.status_code, (302, 403))
        if response.status_code == 302:
            self.assertIn("login", response.url.lower())

    def test_normal_user_super_admin_contact_requests_denied(self):
        self.client.force_login(self.normal_user)
        response = self.client.get(reverse("support:contact_requests_admin"))
        self.assertIn(response.status_code, (302, 403, 404))
