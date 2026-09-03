"""Isolated Campaign CRUD tests (legacy ads.Campaign only)."""

from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from ads.models import Advertisement, Campaign
from ads.forms import CampaignForm


User = get_user_model()


@override_settings(ENABLE_CAMPAIGNS=True)
class CampaignCRUDTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            email="campaign-admin@example.com",
            password="test-pass-12345",
        )
        self.normal = User.objects.create_user(
            email="campaign-user@example.com",
            password="test-pass-12345",
        )

    def test_superuser_can_create_campaign(self):
        self.client.force_login(self.superuser)
        resp = self.client.post(
            reverse("ads:campaign_create"),
            {
                "name": "Slice Campaign",
                "status": Campaign.STATUS_PAUSED,
                "priority": 1,
                "spent_amount": "0",
                "target_roles": ["user"],
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Campaign.objects.filter(name="Slice Campaign").exists())

    def test_non_superuser_rejected(self):
        self.client.force_login(self.normal)
        resp = self.client.get(reverse("ads:campaign_list"))
        self.assertEqual(resp.status_code, 404)

    def test_advertisement_without_campaign_ok(self):
        ad = Advertisement.objects.create(
            name="Orphan Ad",
            placement="top",
            slots=["top"],
            ad_type=Advertisement.AD_TYPE_SCRIPT,
            script_code="<div>x</div>",
            is_active=True,
        )
        self.assertIsNone(ad.campaign_id)

    def test_form_rejects_inverted_dates(self):
        form = CampaignForm(
            data={
                "name": "Bad Dates",
                "status": Campaign.STATUS_PAUSED,
                "priority": 1,
                "start_date": "2026-05-02T10:00",
                "end_date": "2026-05-01T10:00",
                "spent_amount": "0",
            }
        )
        self.assertFalse(form.is_valid())

    def test_toggle_active_paused(self):
        campaign = Campaign.objects.create(name="Toggle Me", status=Campaign.STATUS_PAUSED)
        self.client.force_login(self.superuser)
        resp = self.client.post(reverse("ads:campaign_toggle", args=[campaign.pk]))
        self.assertEqual(resp.status_code, 302)
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, Campaign.STATUS_ACTIVE)


@override_settings(ENABLE_CAMPAIGNS=False)
class CampaignFlagOffTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            email="campaign-flag-off@example.com",
            password="test-pass-12345",
        )

    def test_flag_off_redirects_list(self):
        self.client.force_login(self.superuser)
        resp = self.client.get(reverse("ads:campaign_list"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("ads:advertisement_list"), resp["Location"])
