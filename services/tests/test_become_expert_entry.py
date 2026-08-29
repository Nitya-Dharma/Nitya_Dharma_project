"""Become-Expert is a thin entry to canonical Expert registration (no create)."""

from django.test import Client, TestCase
from django.urls import reverse

from core.models import ExpertProfile


class BecomeExpertEntryTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.become_url = reverse("become_expert")
        self.register_url = reverse("expert_register")

    def test_become_expert_landing_is_reachable(self):
        response = self.client.get(self.become_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Become an Expert")
        self.assertContains(response, "Register as Expert")

    def test_become_expert_cta_points_to_canonical_register(self):
        response = self.client.get(self.become_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.register_url)
        self.assertEqual(
            response.context["expert_register_url"],
            self.register_url,
        )

    def test_become_expert_post_does_not_create_expert_profile(self):
        before = ExpertProfile.objects.count()
        response = self.client.post(
            self.become_url,
            {
                "name": "Should Not Create",
                "expert_type": "ASTROLOGER",
                "experience_years": "5",
                "description": "Unsafe WIP payload must not create.",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.register_url)
        self.assertEqual(ExpertProfile.objects.count(), before)
        self.assertFalse(
            ExpertProfile.objects.filter(name="Should Not Create").exists()
        )

    def test_expert_type_entry_does_not_create_expert_profile(self):
        before = ExpertProfile.objects.count()
        response = self.client.get(
            reverse("expert_type_page", args=["astrologer"])
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(self.register_url, response["Location"])
        self.assertIn("type=astrologer", response["Location"])
        self.assertEqual(ExpertProfile.objects.count(), before)

    def test_invalid_expert_type_does_not_create_expert_profile(self):
        before = ExpertProfile.objects.count()
        response = self.client.get(
            reverse("expert_type_page", args=["not-a-real-type"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ExpertProfile.objects.count(), before)

    def test_canonical_expert_register_remains_reachable(self):
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
