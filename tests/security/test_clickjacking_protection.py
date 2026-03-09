# Phase 9.6: Clickjacking protection tests
from django.test import TestCase, Client
from django.urls import reverse


class TestClickjackingProtection(TestCase):
    def setUp(self):
        self.client = Client()

    def test_homepage_xframe_options_present(self):
        response = self.client.get(reverse("core:home"))
        self.assertTrue(response.has_header("X-Frame-Options"))
        value = response.get("X-Frame-Options", "").upper()
        self.assertIn(value, ("DENY", "SAMEORIGIN"))

    def test_login_page_xframe_options_present(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertTrue(response.has_header("X-Frame-Options"))
        value = response.get("X-Frame-Options", "").upper()
        self.assertIn(value, ("DENY", "SAMEORIGIN"))
