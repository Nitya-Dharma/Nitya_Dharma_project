"""Focused tests for the read-only Super Admin AdLead list.

Does not cover status mutation, Lead detail, filters, CRM, or LeadEvent.
Uses Django's disposable test database only.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ads.models import Advertisement, Campaign
from ads_analytics.models import AdConversionIntent, AdLead

User = get_user_model()
LIST_URL_NAME = "ads_leads:ad_lead_list"
PAGE_SIZE = 20


def _script_ad(**kwargs) -> Advertisement:
    defaults = {
        "name": "Lead List Ad",
        "placement": "top",
        "slots": ["top"],
        "ad_type": Advertisement.AD_TYPE_SCRIPT,
        "script_code": "<div>ad</div>",
        "is_active": True,
        "redirect_url": "https://example.com/dest",
    }
    defaults.update(kwargs)
    return Advertisement.objects.create(**defaults)


def _make_lead(
    *,
    ad,
    source=AdLead.SOURCE_WHATSAPP_CTA,
    user=None,
    campaign_id=None,
    status=AdLead.STATUS_NEW,
    conversion_type=None,
):
    conversion = AdConversionIntent.objects.create(
        ad=ad,
        user=user,
        campaign_id=campaign_id,
        conversion_type=conversion_type or AdConversionIntent.CONVERSION_OTHER,
    )
    return AdLead.objects.create(
        source_conversion=conversion,
        advertisement=ad,
        campaign_id=campaign_id,
        user=user,
        source=source,
        status=status,
    )


class AdLeadListTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            email="adlead-list-admin@example.com",
            password="test-pass-12345",
        )
        self.normal = User.objects.create_user(
            email="adlead-list-user@example.com",
            password="test-pass-12345",
        )
        self.ad = _script_ad()

    def _login_super(self):
        self.client.force_login(self.superuser)

    def test_url_is_super_admin_advertisements_leads(self):
        self.assertEqual(
            reverse(LIST_URL_NAME),
            "/dashboard/super-admin/advertisements/leads/",
        )
        self.assertEqual(
            reverse("ads_analytics:track_click", kwargs={"ad_id": 1}),
            "/track/ad/click/1/",
        )

    def test_super_admin_can_access_lead_list(self):
        self._login_super()
        resp = self.client.get(reverse(LIST_URL_NAME))
        self.assertEqual(resp.status_code, 200)

    def test_non_super_admin_cannot_access_lead_list(self):
        self.client.force_login(self.normal)
        resp = self.client.get(reverse(LIST_URL_NAME))
        self.assertEqual(resp.status_code, 404)
        self.assertNotContains(resp, "Ads Leads", status_code=404)

    def test_pandit_cannot_access_lead_list(self):
        pandit = User.objects.create_user(
            email="adlead-list-pandit@example.com",
            password="test-pass-12345",
            role="pandit",
            status="active",
        )
        self.client.force_login(pandit)
        resp = self.client.get(reverse(LIST_URL_NAME))
        self.assertEqual(resp.status_code, 404)

    def test_anonymous_user_cannot_access_lead_list(self):
        resp = self.client.get(reverse(LIST_URL_NAME))
        self.assertEqual(resp.status_code, 404)

    def test_existing_lead_records_appear(self):
        lead = _make_lead(ad=self.ad, campaign_id="camp-1")
        self._login_super()
        resp = self.client.get(reverse(LIST_URL_NAME))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, str(lead.pk))
        self.assertContains(resp, self.ad.name)

    def test_leads_ordered_newest_first(self):
        older = _make_lead(ad=self.ad, source=AdLead.SOURCE_WHATSAPP_CTA)
        newer = _make_lead(ad=_script_ad(name="Newer Ad"), source=AdLead.SOURCE_BOOKING_INTENT)
        self._login_super()
        resp = self.client.get(reverse(LIST_URL_NAME))
        leads = list(resp.context["leads"])
        self.assertEqual([lead.pk for lead in leads], [newer.pk, older.pk])

    def test_pagination_is_twenty_per_page(self):
        for i in range(PAGE_SIZE + 1):
            _make_lead(ad=_script_ad(name=f"Paged Ad {i}"))
        self._login_super()
        page1 = self.client.get(reverse(LIST_URL_NAME))
        self.assertEqual(page1.status_code, 200)
        self.assertEqual(len(page1.context["leads"]), PAGE_SIZE)
        self.assertTrue(page1.context["page_obj"].has_next())
        page2 = self.client.get(reverse(LIST_URL_NAME), {"page": "2"})
        self.assertEqual(page2.status_code, 200)
        self.assertEqual(len(page2.context["leads"]), 1)

    def test_empty_lead_database_renders_safely(self):
        self._login_super()
        resp = self.client.get(reverse(LIST_URL_NAME))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "No Ads Leads yet.")
        self.assertNotContains(resp, "<tbody>")

    def test_anonymous_lead_displays_safely(self):
        _make_lead(ad=self.ad, user=None)
        self._login_super()
        resp = self.client.get(reverse(LIST_URL_NAME))
        self.assertContains(resp, "Anonymous")

    def test_authenticated_lead_user_displays_safely(self):
        visitor = User.objects.create_user(
            email="adlead-list-visitor@example.com",
            password="test-pass-12345",
        )
        _make_lead(ad=self.ad, user=visitor)
        self._login_super()
        resp = self.client.get(reverse(LIST_URL_NAME))
        self.assertContains(resp, visitor.email)
        self.assertNotContains(resp, visitor.password)

    def test_whatsapp_source_displays_correctly(self):
        _make_lead(ad=self.ad, source=AdLead.SOURCE_WHATSAPP_CTA)
        self._login_super()
        resp = self.client.get(reverse(LIST_URL_NAME))
        self.assertContains(resp, "WhatsApp CTA")
        self.assertNotContains(resp, "whatsapp_cta")

    def test_booking_source_displays_correctly(self):
        _make_lead(
            ad=self.ad,
            source=AdLead.SOURCE_BOOKING_INTENT,
            conversion_type=AdConversionIntent.CONVERSION_BOOKING_INTENT,
        )
        self._login_super()
        resp = self.client.get(reverse(LIST_URL_NAME))
        self.assertContains(resp, "Booking Intent")

    def test_post_to_list_does_not_mutate_status(self):
        lead = _make_lead(ad=self.ad, status=AdLead.STATUS_NEW)
        self._login_super()
        resp = self.client.get(reverse(LIST_URL_NAME))
        self.assertContains(resp, "New")
        post = self.client.post(reverse(LIST_URL_NAME), {"status": "contacted"})
        self.assertEqual(post.status_code, 405)
        lead.refresh_from_db()
        self.assertEqual(lead.status, AdLead.STATUS_NEW)

    def test_stored_campaign_id_snapshot_is_displayed(self):
        _make_lead(ad=self.ad, campaign_id="snap-campaign-77")
        self._login_super()
        resp = self.client.get(reverse(LIST_URL_NAME))
        self.assertContains(resp, "snap-campaign-77")

    def test_historical_campaign_snapshot_survives_advertisement_reassignment(self):
        click_campaign = Campaign.objects.create(
            name="Click Time Camp",
            status=Campaign.STATUS_ACTIVE,
        )
        later_campaign = Campaign.objects.create(
            name="SHOULD-NOT-APPEAR",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(name="Reassigned Ad", campaign=click_campaign)
        lead = _make_lead(ad=ad, campaign_id=str(click_campaign.pk))
        ad.campaign = later_campaign
        ad.save(update_fields=["campaign"])
        self._login_super()
        resp = self.client.get(reverse(LIST_URL_NAME))
        self.assertContains(resp, str(click_campaign.pk))
        self.assertContains(resp, ad.name)
        self.assertNotContains(resp, "SHOULD-NOT-APPEAR")
        self.assertNotContains(resp, later_campaign.name)
        lead.refresh_from_db()
        self.assertEqual(lead.campaign_id, str(click_campaign.pk))

    def test_blank_campaign_id_displays_placeholder(self):
        _make_lead(ad=self.ad, campaign_id=None)
        self._login_super()
        resp = self.client.get(reverse(LIST_URL_NAME))
        self.assertContains(resp, "—")

    def test_advertisement_information_displays_correctly(self):
        ad = _script_ad(name="Visible Banner Name")
        _make_lead(ad=ad)
        self._login_super()
        resp = self.client.get(reverse(LIST_URL_NAME))
        self.assertContains(resp, "Visible Banner Name")

    def test_conversion_id_displays_correctly(self):
        lead = _make_lead(ad=self.ad)
        self._login_super()
        resp = self.client.get(reverse(LIST_URL_NAME))
        self.assertContains(resp, str(lead.source_conversion_id))

    def test_get_does_not_create_or_modify_leads(self):
        lead = _make_lead(ad=self.ad, status=AdLead.STATUS_CONTACTED)
        before = AdLead.objects.count()
        self._login_super()
        resp = self.client.get(reverse(LIST_URL_NAME))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(AdLead.objects.count(), before)
        lead.refresh_from_db()
        self.assertEqual(lead.status, AdLead.STATUS_CONTACTED)
        self.assertEqual(lead.source, AdLead.SOURCE_WHATSAPP_CTA)
