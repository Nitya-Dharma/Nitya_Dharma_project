"""Expert registration/approval emails must use SITE_URL + reverse(), not hardcoded localhost."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

from core.models import ExpertProfile, ExpertService
from services.views_expert_ui import expert_register_page

User = get_user_model()

TEST_SITE_URL = "https://experts.example.com"


@override_settings(SITE_URL=TEST_SITE_URL, OTP_ENABLED=False)
class ExpertEmailUrlTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.astrology, _ = ExpertService.objects.get_or_create(
            slug="astrology",
            defaults={"name": "Astrology", "display_order": 1},
        )

    def setUp(self):
        self.factory = RequestFactory()
        self.client = Client()

    def _registration_request(self, *, email="expert-email-url@example.com"):
        request = self.factory.post(
            "/services/expert/register/?type=astrology",
            data={
                "name": "Email URL Expert",
                "email": email,
                "password": "StrongPass123!",
                "confirm_password": "StrongPass123!",
                "phone": "9876543299",
                "experience_years": "5",
                "description": "Email URL test expert",
                "social_links[]": ["https://example.com/profile"],
                "services": [str(self.astrology.id)],
            },
        )
        request.session = SessionStore()
        return request

    @patch("services.views_expert_ui.send_mail")
    def test_registration_email_uses_site_url_password_reset_path(self, mock_send_mail):
        request = self._registration_request()

        expert_register_page(request)

        password_reset_calls = [
            call
            for call in mock_send_mail.call_args_list
            if call.kwargs.get("subject") == "Set Your Password"
            or (call.args and call.args[0] == "Set Your Password")
        ]
        self.assertEqual(len(password_reset_calls), 1)
        message = (
            password_reset_calls[0].kwargs.get("message")
            or password_reset_calls[0].args[1]
        )
        self.assertNotIn("127.0.0.1", message)
        self.assertNotIn("localhost", message)
        self.assertIn(f"{TEST_SITE_URL}/accounts/password-reset/", message)

    @patch("dashboards.views.send_mail")
    def test_approval_email_uses_site_url_login_and_dashboard_paths(self, mock_send_mail):
        admin = User.objects.create_superuser(
            email="expert-email-admin@example.com",
            password="AdminPass123!",
        )
        expert = ExpertProfile.objects.create(
            name="Pending Email Expert",
            expert_type="ASTROLOGER",
            email="expert-email-approve@example.com",
            phone="9876543298",
            experience_years=3,
            description="Pending approval email test",
            is_active=False,
        )
        expert.services.add(self.astrology)

        self.client.force_login(admin)
        response = self.client.post(
            reverse("module5_dashboards:super_admin_experts"),
            {"expert_id": expert.id, "action": "approve"},
        )

        self.assertEqual(response.status_code, 302)
        approval_calls = [
            call
            for call in mock_send_mail.call_args_list
            if call.kwargs.get("subject") == "Your Expert Profile is Approved"
            or (call.args and call.args[0] == "Your Expert Profile is Approved")
        ]
        self.assertEqual(len(approval_calls), 1)
        message = (
            approval_calls[0].kwargs.get("message")
            or approval_calls[0].args[1]
        )
        self.assertNotIn("127.0.0.1", message)
        self.assertNotIn("localhost", message)
        self.assertIn(f"{TEST_SITE_URL}/accounts/login/", message)
        self.assertIn(f"{TEST_SITE_URL}/dashboard/expert/", message)
