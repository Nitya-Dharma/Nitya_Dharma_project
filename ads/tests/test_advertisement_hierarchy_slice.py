"""Advertisement ↔ Campaign ↔ AdSet management linkage tests (CRUD UX only)."""

from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from ads.models import Advertisement, Campaign, AdSet
from ads.forms import AdvertisementForm


User = get_user_model()


@override_settings(ENABLE_CAMPAIGNS=True)
class AdvertisementHierarchyTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            email="adv-hier-admin@example.com",
            password="test-pass-12345",
        )
        self.normal = User.objects.create_user(
            email="adv-hier-user@example.com",
            password="test-pass-12345",
        )
        self.campaign = Campaign.objects.create(
            name="Hier Campaign",
            status=Campaign.STATUS_PAUSED,
        )
        self.other_campaign = Campaign.objects.create(
            name="Other Campaign",
            status=Campaign.STATUS_PAUSED,
        )
        self.adset = AdSet.objects.create(name="Hier AdSet", campaign=self.campaign)

    def _script_ad(self, **kwargs):
        defaults = {
            "name": "Script Ad",
            "placement": "top",
            "slots": ["top"],
            "ad_type": Advertisement.AD_TYPE_SCRIPT,
            "script_code": "<div>x</div>",
            "is_active": True,
        }
        defaults.update(kwargs)
        return Advertisement.objects.create(**defaults)

    def test_advertisement_without_campaign_or_adset(self):
        ad = self._script_ad(name="Orphan")
        self.assertIsNone(ad.campaign_id)
        self.assertIsNone(ad.ad_set_id)

    def test_advertisement_with_campaign_only(self):
        ad = self._script_ad(name="Camp Only", campaign=self.campaign)
        self.assertEqual(ad.campaign_id, self.campaign.pk)
        self.assertIsNone(ad.ad_set_id)

    def test_advertisement_with_campaign_and_adset(self):
        ad = self._script_ad(
            name="Linked",
            campaign=self.campaign,
            ad_set=self.adset,
        )
        self.assertEqual(ad.campaign_id, self.campaign.pk)
        self.assertEqual(ad.ad_set_id, self.adset.pk)

    def test_form_rejects_mismatched_campaign_adset(self):
        form = AdvertisementForm(
            data={
                "name": "Bad Link",
                "ad_type": Advertisement.AD_TYPE_SCRIPT,
                "script_code": "<div>x</div>",
                "slots": ["top"],
                "is_active": True,
                "campaign": self.other_campaign.pk,
                "ad_set": self.adset.pk,
            }
        )
        self.assertFalse(form.is_valid())

    def test_form_autofills_campaign_from_adset(self):
        form = AdvertisementForm(
            data={
                "name": "Auto Camp",
                "ad_type": Advertisement.AD_TYPE_SCRIPT,
                "script_code": "<div>x</div>",
                "slots": ["top"],
                "is_active": True,
                "ad_set": self.adset.pk,
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        ad = form.save()
        self.assertEqual(ad.ad_set_id, self.adset.pk)
        self.assertEqual(ad.campaign_id, self.campaign.pk)

    def test_list_filters_by_campaign_and_adset(self):
        matched = self._script_ad(
            name="Matched",
            campaign=self.campaign,
            ad_set=self.adset,
        )
        self._script_ad(name="Other", campaign=self.other_campaign)
        self.client.force_login(self.superuser)

        camp_resp = self.client.get(
            reverse("ads:advertisement_list"),
            {"campaign_id": self.campaign.pk},
        )
        self.assertEqual(camp_resp.status_code, 200)
        names = [a.name for a in camp_resp.context["advertisements"]]
        self.assertIn("Matched", names)
        self.assertNotIn("Other", names)

        adset_resp = self.client.get(
            reverse("ads:advertisement_list"),
            {"ad_set_id": self.adset.pk},
        )
        self.assertEqual(adset_resp.status_code, 200)
        names = [a.name for a in adset_resp.context["advertisements"]]
        self.assertEqual(names, ["Matched"])
        self.assertEqual(adset_resp.context["filter_ad_set"].pk, matched.ad_set_id)

    def test_empty_filters_show_all(self):
        self._script_ad(name="A")
        self._script_ad(name="B", campaign=self.campaign)
        self.client.force_login(self.superuser)
        resp = self.client.get(reverse("ads:advertisement_list"))
        self.assertEqual(resp.status_code, 200)
        names = {a.name for a in resp.context["advertisements"]}
        self.assertIn("A", names)
        self.assertIn("B", names)

    def test_non_superuser_rejected(self):
        self.client.force_login(self.normal)
        resp = self.client.get(reverse("ads:advertisement_list"))
        self.assertEqual(resp.status_code, 404)

    def test_campaign_and_adset_crud_still_work(self):
        self.client.force_login(self.superuser)
        c_resp = self.client.post(
            reverse("ads:campaign_create"),
            {
                "name": "Still Campaign",
                "status": Campaign.STATUS_PAUSED,
                "priority": 1,
                "spent_amount": "0",
                "target_roles": ["user"],
            },
        )
        self.assertEqual(c_resp.status_code, 302)
        camp = Campaign.objects.get(name="Still Campaign")
        a_resp = self.client.post(
            reverse("ads:adset_create"),
            {
                "name": "Still AdSet",
                "campaign": camp.pk,
                "is_active": "on",
                "pricing_model": AdSet.PRICING_IMPRESSION,
                "placements": "[]",
                "target_urls": "[]",
                "target_roles": "[]",
                "target_locations": "[]",
            },
        )
        self.assertEqual(a_resp.status_code, 302)
        self.assertTrue(AdSet.objects.filter(name="Still AdSet", campaign=camp).exists())


@override_settings(ENABLE_CAMPAIGNS=False)
class AdvertisementHierarchyFlagOffTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            email="adv-hier-flagoff@example.com",
            password="test-pass-12345",
        )
        self.campaign = Campaign.objects.create(name="Hidden Camp", status=Campaign.STATUS_PAUSED)
        Advertisement.objects.create(
            name="Flag Off Ad",
            placement="top",
            slots=["top"],
            ad_type=Advertisement.AD_TYPE_SCRIPT,
            script_code="<div>x</div>",
            is_active=True,
            campaign=self.campaign,
        )

    def test_flag_off_list_ignores_campaign_filter(self):
        self.client.force_login(self.superuser)
        resp = self.client.get(
            reverse("ads:advertisement_list"),
            {"campaign_id": self.campaign.pk},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context["campaigns_enabled"])
        # Filter ignored when flag off — full list still returned.
        names = [a.name for a in resp.context["advertisements"]]
        self.assertIn("Flag Off Ad", names)
