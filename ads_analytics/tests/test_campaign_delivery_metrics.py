"""Campaign-level delivery metrics via AdImpression/AdClick.campaign_id.

Proves historical Campaign impressions/clicks/CTR use the persisted
campaign_id field, not live Advertisement.campaign. Does not cover
AdSet targeting, billing, Lead/CRM, WhatsApp, or serving changes.
"""

from __future__ import annotations

from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from ads.models import Advertisement, Campaign
from ads_analytics.models import AdClick, AdConversionIntent, AdImpression
from ads_analytics.services.dashboard_service import (
    get_campaign_conversion_metrics,
    get_campaign_delivery_metrics,
)


def _script_ad(**kwargs) -> Advertisement:
    defaults = {
        "name": "Camp Delivery Report Ad",
        "placement": "top",
        "slots": ["top"],
        "ad_type": Advertisement.AD_TYPE_SCRIPT,
        "script_code": "<div>ad</div>",
        "is_active": True,
        "redirect_url": "https://example.com/dest",
    }
    defaults.update(kwargs)
    return Advertisement.objects.create(**defaults)


def _impression(ad, *, campaign_id):
    return AdImpression.objects.create(
        ad=ad,
        campaign_id=campaign_id,
        placement_position="top",
    )


def _click(ad, *, campaign_id):
    return AdClick.objects.create(
        ad=ad,
        campaign_id=campaign_id,
        placement_position="top",
    )


class CampaignDeliveryMetricsTests(TestCase):
    def test_campaign_a_impressions_and_clicks_isolated(self):
        campaign_a = Campaign.objects.create(
            name="Delivery Camp A",
            status=Campaign.STATUS_ACTIVE,
        )
        campaign_b = Campaign.objects.create(
            name="Delivery Camp B",
            status=Campaign.STATUS_ACTIVE,
        )
        ad_a = _script_ad(name="Ad A", campaign=campaign_a)
        ad_b = _script_ad(name="Ad B", campaign=campaign_b)
        cid_a = str(campaign_a.pk)
        cid_b = str(campaign_b.pk)

        _impression(ad_a, campaign_id=cid_a)
        _impression(ad_a, campaign_id=cid_a)
        _click(ad_a, campaign_id=cid_a)
        _impression(ad_b, campaign_id=cid_b)
        _click(ad_b, campaign_id=cid_b)
        _click(ad_b, campaign_id=cid_b)

        metrics_a = get_campaign_delivery_metrics(cid_a, days=30)
        metrics_b = get_campaign_delivery_metrics(cid_b, days=30)
        self.assertEqual(metrics_a["impressions"], 2)
        self.assertEqual(metrics_a["clicks"], 1)
        self.assertEqual(metrics_a["ctr"], 50.0)
        self.assertEqual(metrics_b["impressions"], 1)
        self.assertEqual(metrics_b["clicks"], 2)
        self.assertEqual(metrics_b["ctr"], 200.0)

    def test_historical_campaign_id_survives_ad_reassignment(self):
        campaign_a = Campaign.objects.create(
            name="Hist Camp A",
            status=Campaign.STATUS_ACTIVE,
        )
        campaign_b = Campaign.objects.create(
            name="Hist Camp B",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(name="Reassign ad", campaign=campaign_a)
        _impression(ad, campaign_id=str(campaign_a.pk))
        _click(ad, campaign_id=str(campaign_a.pk))

        ad.campaign = campaign_b
        ad.save(update_fields=["campaign"])

        metrics_a = get_campaign_delivery_metrics(str(campaign_a.pk), days=30)
        metrics_b = get_campaign_delivery_metrics(str(campaign_b.pk), days=30)
        self.assertEqual(metrics_a["impressions"], 1)
        self.assertEqual(metrics_a["clicks"], 1)
        self.assertEqual(metrics_b["impressions"], 0)
        self.assertEqual(metrics_b["clicks"], 0)

    def test_null_and_blank_campaign_id_excluded(self):
        campaign = Campaign.objects.create(
            name="Exclude Camp",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(name="Exclude ad", campaign=campaign)
        _impression(ad, campaign_id=str(campaign.pk))
        _click(ad, campaign_id=str(campaign.pk))
        _impression(ad, campaign_id=None)
        _click(ad, campaign_id="")
        _impression(ad, campaign_id="")

        metrics = get_campaign_delivery_metrics(str(campaign.pk), days=30)
        self.assertEqual(metrics["impressions"], 1)
        self.assertEqual(metrics["clicks"], 1)

    def test_zero_impressions_ctr_safe(self):
        campaign = Campaign.objects.create(
            name="Zero Imp Camp",
            status=Campaign.STATUS_ACTIVE,
        )
        metrics = get_campaign_delivery_metrics(str(campaign.pk), days=30)
        self.assertEqual(metrics["impressions"], 0)
        self.assertEqual(metrics["clicks"], 0)
        self.assertEqual(metrics["ctr"], 0.0)

    def test_ctr_calculation(self):
        campaign = Campaign.objects.create(
            name="CTR Camp",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(name="CTR ad", campaign=campaign)
        cid = str(campaign.pk)
        for _ in range(4):
            _impression(ad, campaign_id=cid)
        for _ in range(1):
            _click(ad, campaign_id=cid)
        metrics = get_campaign_delivery_metrics(cid, days=30)
        self.assertEqual(metrics["impressions"], 4)
        self.assertEqual(metrics["clicks"], 1)
        self.assertEqual(metrics["ctr"], 25.0)

    def test_date_range_excludes_old_events(self):
        campaign = Campaign.objects.create(
            name="Date Camp",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(name="Date ad", campaign=campaign)
        cid = str(campaign.pk)
        old_imp = _impression(ad, campaign_id=cid)
        old_click = _click(ad, campaign_id=cid)
        old_ts = timezone.now() - timedelta(days=60)
        AdImpression.objects.filter(pk=old_imp.pk).update(timestamp=old_ts)
        AdClick.objects.filter(pk=old_click.pk).update(timestamp=old_ts)
        _impression(ad, campaign_id=cid)
        _click(ad, campaign_id=cid)

        metrics = get_campaign_delivery_metrics(cid, days=30)
        self.assertEqual(metrics["impressions"], 1)
        self.assertEqual(metrics["clicks"], 1)

    def test_blank_requested_campaign_id_returns_zeros(self):
        metrics = get_campaign_delivery_metrics("   ", days=30)
        self.assertEqual(metrics["impressions"], 0)
        self.assertEqual(metrics["clicks"], 0)
        self.assertEqual(metrics["ctr"], 0.0)

    def test_conversion_metrics_still_independent(self):
        campaign = Campaign.objects.create(
            name="Both Metrics Camp",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(name="Both ad", campaign=campaign)
        cid = str(campaign.pk)
        _impression(ad, campaign_id=cid)
        _click(ad, campaign_id=cid)
        AdConversionIntent.objects.create(
            ad=ad,
            campaign_id=cid,
            conversion_type=AdConversionIntent.CONVERSION_BOOKING_INTENT,
        )
        delivery = get_campaign_delivery_metrics(cid, days=30)
        conversion = get_campaign_conversion_metrics(cid, days=30)
        self.assertEqual(delivery["impressions"], 1)
        self.assertEqual(delivery["clicks"], 1)
        self.assertEqual(conversion["conversion_count"], 1)
        self.assertEqual(conversion["booking_intent_count"], 1)


@override_settings(ENABLE_CAMPAIGNS=True)
class CampaignListDeliverySurfaceTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model

        self.admin = get_user_model().objects.create_superuser(
            email="camp-delivery-admin@example.com",
            password="CampDeliveryAdmin123!",
        )
        self.client.force_login(self.admin)

    def test_campaign_list_shows_delivery_and_conversion_metrics(self):
        campaign = Campaign.objects.create(
            name="List Delivery Camp",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(name="List delivery ad", campaign=campaign)
        cid = str(campaign.pk)
        _impression(ad, campaign_id=cid)
        _impression(ad, campaign_id=cid)
        _click(ad, campaign_id=cid)
        AdConversionIntent.objects.create(
            ad=ad,
            campaign_id=cid,
            conversion_type=AdConversionIntent.CONVERSION_BOOKING_INTENT,
        )
        response = self.client.get(reverse("ads:campaign_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Delivery")
        self.assertContains(response, "Impressions: 2")
        self.assertContains(response, "Clicks: 1")
        self.assertContains(response, "CTR: 50.0%")
        self.assertContains(response, "Attributed conversions")
        self.assertContains(response, "Total: 1")
        self.assertContains(response, "Booking: 1")

    @override_settings(ENABLE_CAMPAIGNS=False)
    def test_campaign_list_disabled_redirects(self):
        response = self.client.get(reverse("ads:campaign_list"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("ads:advertisement_list"))
