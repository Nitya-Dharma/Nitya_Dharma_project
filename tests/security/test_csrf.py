# Phase 9.5/9.5A: CSRF protection tests (TestCase = automatic rollback)
from django.test import TestCase, Client
from django.urls import reverse


class TestCsrfProtection(TestCase):
    """Verify that state-changing POSTs without CSRF token are rejected."""

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def test_booking_intent_create_post_without_csrf_forbidden(self):
        response = self.client.post(
            reverse("booking_intent_api:create_intent"),
            data={"pandit_id": 1, "message": "test"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403, "POST without CSRF should be 403 Forbidden")

    def test_contact_form_post_without_csrf_forbidden(self):
        response = self.client.post(
            reverse("support:contact_us"),
            data={"email": "a@b.com", "subject": "Test", "message": "Test"},
        )
        self.assertEqual(response.status_code, 403, "Contact form POST without CSRF should be 403")
