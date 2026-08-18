from unittest.mock import patch

from django.test import TestCase

from core.models import ExpertProfile
from services.expert_contact import (
    get_expert_contact_info,
    get_expert_whatsapp_url,
)


class ExpertContactHelperTests(TestCase):
    def test_valid_phone_builds_wa_me_url(self):
        expert = ExpertProfile.objects.create(
            name="Expert",
            expert_type="ASTROLOGER",
            phone="9876543210",
            is_active=True,
        )

        info = get_expert_contact_info(expert)

        self.assertEqual(info["whatsapp_url"], "https://wa.me/919876543210")
        self.assertTrue(info["has_whatsapp"])
        self.assertIn("wa.me", info["whatsapp_url"])

    def test_no_phone_returns_no_whatsapp_cta(self):
        expert = ExpertProfile.objects.create(
            name="No Phone",
            expert_type="ASTROLOGER",
            phone=None,
            is_active=True,
        )

        info = get_expert_contact_info(expert)

        self.assertIsNone(info["whatsapp_url"])
        self.assertFalse(info["has_whatsapp"])

    def test_invalid_phone_returns_no_whatsapp_cta(self):
        expert = ExpertProfile.objects.create(
            name="Invalid Phone",
            expert_type="ASTROLOGER",
            phone="abc",
            is_active=True,
        )

        info = get_expert_contact_info(expert)

        self.assertIsNone(info["whatsapp_url"])
        self.assertFalse(info["has_whatsapp"])

    def test_helper_does_not_access_whatsapp_verification_records(self):
        expert = ExpertProfile.objects.create(
            name="Safe Expert",
            expert_type="ASTROLOGER",
            phone="9876543210",
            is_active=True,
        )

        with patch(
            "whatsapp_verification.models.WhatsAppVerification.objects.filter",
            side_effect=AssertionError("WhatsAppVerification should not be queried"),
        ):
            url = get_expert_whatsapp_url(expert)

        self.assertEqual(url, "https://wa.me/919876543210")

    def test_helper_does_not_call_external_whatsapp_provider(self):
        expert = ExpertProfile.objects.create(
            name="No API Expert",
            expert_type="ASTROLOGER",
            phone="9876543210",
            is_active=True,
        )

        with patch(
            "whatsapp_verification.providers.registry.get_whatsapp_provider",
            side_effect=AssertionError("External WhatsApp provider should not be used"),
        ):
            info = get_expert_contact_info(expert)

        self.assertEqual(info["whatsapp_url"], "https://wa.me/919876543210")
        self.assertTrue(info["has_whatsapp"])
