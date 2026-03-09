# Phase 9.6: Mass assignment vulnerability tests
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class TestMassAssignment(TestCase):
    def setUp(self):
        self.client = Client()

    def test_register_post_with_extra_privilege_fields_ignored(self):
        response = self.client.post(
            reverse("accounts:register"),
            data={
                "email": "massassign@example.com",
                "password1": "ValidPass123!",
                "password2": "ValidPass123!",
                "first_name": "Test",
                "last_name": "User",
                "is_superuser": "true",
                "is_staff": "true",
                "role": "super_admin",
            },
            follow=False,
        )
        self.assertIn(response.status_code, (200, 302, 400))
        if response.status_code == 302:
            user = User.objects.filter(email="massassign@example.com").first()
            if user:
                self.assertFalse(getattr(user, "is_superuser", False))
                self.assertFalse(getattr(user, "is_staff", False))

    def test_login_post_extra_fields_do_not_elevate(self):
        user = User.objects.create_user(
            email="loginmass@example.com", password="pass123",
            role="end_user", status="active",
        )
        self.client.post(
            reverse("accounts:login"),
            data={
                "email": "loginmass@example.com",
                "password": "pass123",
                "is_superuser": "true",
                "role": "super_admin",
            },
            follow=False,
        )
        user.refresh_from_db()
        self.assertFalse(getattr(user, "is_superuser", False))
        self.assertEqual(user.role, "end_user")
