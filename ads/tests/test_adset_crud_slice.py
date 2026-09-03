"""Isolated AdSet CRUD tests (legacy ads.AdSet only; no delivery/pricing)."""

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from ads.models import Advertisement, Campaign, AdSet
from ads.forms import AdSetForm


User = get_user_model()


@override_settings(ENABLE_CAMPAIGNS=True)
class AdSetCRUDTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            email="adset-admin@example.com",
            password="test-pass-12345",
        )
        self.normal = User.objects.create_user(
            email="adset-user@example.com",
            password="test-pass-12345",
        )
        self.campaign = Campaign.objects.create(
            name="Parent Campaign",
            status=Campaign.STATUS_PAUSED,
        )

    def test_campaign_exists_without_adset(self):
        self.assertEqual(self.campaign.ad_sets.count(), 0)
        self.assertTrue(Campaign.objects.filter(pk=self.campaign.pk).exists())

    def test_adset_created_under_campaign(self):
        adset = AdSet.objects.create(name="Set A", campaign=self.campaign)
        self.assertEqual(adset.campaign_id, self.campaign.pk)
        self.assertEqual(self.campaign.ad_sets.count(), 1)

    def test_adset_requires_campaign(self):
        with self.assertRaises(IntegrityError):
            AdSet.objects.create(name="Orphan Set", campaign=None)

    def test_advertisement_without_adset_ok(self):
        ad = Advertisement.objects.create(
            name="Orphan Ad",
            placement="top",
            slots=["top"],
            ad_type=Advertisement.AD_TYPE_SCRIPT,
            script_code="<div>x</div>",
            is_active=True,
        )
        self.assertIsNone(ad.ad_set_id)
        self.assertIsNone(ad.campaign_id)

    def test_advertisement_optional_adset_link(self):
        adset = AdSet.objects.create(name="Linked Set", campaign=self.campaign)
        ad = Advertisement.objects.create(
            name="Linked Ad",
            placement="sidebar",
            slots=["sidebar"],
            ad_type=Advertisement.AD_TYPE_SCRIPT,
            script_code="<div>y</div>",
            is_active=True,
            ad_set=adset,
            campaign=self.campaign,
        )
        self.assertEqual(ad.ad_set_id, adset.pk)

    def test_superuser_list_create_edit(self):
        self.client.force_login(self.superuser)
        list_resp = self.client.get(reverse("ads:adset_list"))
        self.assertEqual(list_resp.status_code, 200)

        create_resp = self.client.post(
            reverse("ads:adset_create"),
            {
                "name": "Slice AdSet",
                "campaign": self.campaign.pk,
                "is_active": "on",
                "pricing_model": AdSet.PRICING_IMPRESSION,
                "placements": "[]",
                "target_urls": "[]",
                "target_roles": "[]",
                "target_locations": "[]",
            },
        )
        self.assertEqual(create_resp.status_code, 302)
        adset = AdSet.objects.get(name="Slice AdSet")
        self.assertEqual(adset.campaign_id, self.campaign.pk)

        edit_resp = self.client.post(
            reverse("ads:adset_edit", args=[adset.pk]),
            {
                "name": "Slice AdSet Edited",
                "campaign": self.campaign.pk,
                "is_active": "on",
                "pricing_model": AdSet.PRICING_IMPRESSION,
                "placements": "[]",
                "target_urls": "[]",
                "target_roles": "[]",
                "target_locations": "[]",
            },
        )
        self.assertEqual(edit_resp.status_code, 302)
        adset.refresh_from_db()
        self.assertEqual(adset.name, "Slice AdSet Edited")

    def test_non_superuser_rejected(self):
        self.client.force_login(self.normal)
        resp = self.client.get(reverse("ads:adset_list"))
        self.assertEqual(resp.status_code, 404)

    def test_toggle_active(self):
        adset = AdSet.objects.create(name="Toggle Me", campaign=self.campaign, is_active=True)
        self.client.force_login(self.superuser)
        resp = self.client.post(reverse("ads:adset_toggle", args=[adset.pk]))
        self.assertEqual(resp.status_code, 302)
        adset.refresh_from_db()
        self.assertFalse(adset.is_active)

    def test_campaign_crud_still_works(self):
        self.client.force_login(self.superuser)
        resp = self.client.post(
            reverse("ads:campaign_create"),
            {
                "name": "Still Works",
                "status": Campaign.STATUS_PAUSED,
                "priority": 1,
                "spent_amount": "0",
                "target_roles": ["user"],
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Campaign.objects.filter(name="Still Works").exists())

    def test_form_requires_campaign(self):
        form = AdSetForm(
            data={
                "name": "No Campaign",
                "is_active": True,
                "pricing_model": AdSet.PRICING_IMPRESSION,
                "placements": "[]",
                "target_urls": "[]",
                "target_roles": "[]",
                "target_locations": "[]",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("campaign", form.errors)


@override_settings(ENABLE_CAMPAIGNS=False)
class AdSetFlagOffTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            email="adset-flag-off@example.com",
            password="test-pass-12345",
        )

    def test_flag_off_redirects_list(self):
        self.client.force_login(self.superuser)
        resp = self.client.get(reverse("ads:adset_list"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("ads:advertisement_list"), resp["Location"])
