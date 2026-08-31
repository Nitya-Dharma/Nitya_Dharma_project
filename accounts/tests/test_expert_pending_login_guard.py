"""Regression: pending ExpertProfile must block login regardless of user.role."""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from core.models import ExpertProfile

User = get_user_model()


class ExpertPendingLoginGuardTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.login_url = reverse("accounts:login")
        self.pending_url = reverse("expert_pending")
        self.password = "pass12345"

    def test_pending_expert_blocks_pandit_role_login(self):
        """Case A: role=pandit must not bypass pending-Expert guard."""
        email = "pandit-pending-expert@example.com"
        user = User.objects.create_user(
            email=email,
            password=self.password,
            role="pandit",
            status="active",
            is_active=True,
            email_verified=True,
        )
        ExpertProfile.objects.create(
            name="Pending Expert Pandit",
            expert_type="ASTROLOGER",
            email=email,
            phone="9876500881",
            experience_years=3,
            description="Pending expert linked to pandit-role user",
            is_active=False,
        )

        response = self.client.post(
            self.login_url,
            {"email": email, "password": self.password},
        )

        self.assertRedirects(response, self.pending_url)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_normal_user_login_without_pending_expert(self):
        """Case B: users without pending ExpertProfile still log in normally."""
        email = "normal-user-no-expert@example.com"
        User.objects.create_user(
            email=email,
            password=self.password,
            role="user",
            status="active",
            is_active=True,
        )

        response = self.client.post(
            self.login_url,
            {"email": email, "password": self.password},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)
        self.assertEqual(
            int(self.client.session["_auth_user_id"]),
            User.objects.get(email=email).pk,
        )
