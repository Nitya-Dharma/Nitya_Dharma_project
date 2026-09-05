"""Campaign-level conversion reporting via AdConversionIntent.campaign_id.

Proves historical Campaign conversion aggregates use the persisted
campaign_id field, not live Advertisement.campaign. Does not cover
AdSet targeting, billing, Lead/CRM, or serving changes.
"""

from __future__ import annotations

from django.test import TestCase, override_settings
from django.urls import reverse

from ads.models import Advertisement, Campaign
from ads_analytics.models import AdConversionIntent
from ads_analytics.services.dashboard_service import (
    get_ad_conversion_funnel,
    get_campaign_conversion_metrics,
)


def _script_ad(**kwargs) -> Advertisement:
    defaults = {
        "name": "Camp Conv Report Ad",
        "placement": "top",
        "slots": ["top"],
        "ad_type": Advertisement.AD_TYPE_SCRIPT,
        "script_code": "<div>ad</div>",
        "is_active": True,
        "redirect_url": "https://example.com/dest",
    }
    defaults.update(kwargs)
    return Advertisement.objects.create(**defaults)


def _intent(ad, *, campaign_id, conversion_type):
    return AdConversionIntent.objects.create(
        ad=ad,
        campaign_id=campaign_id,
        conversion_type=conversion_type,
    )


class CampaignConversionReportingTests(TestCase):
    def test_campaign_conversion_count(self):
        campaign = Campaign.objects.create(
            name="Report Camp A",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(name="Linked A", campaign=campaign)
        _intent(
            ad,
            campaign_id=str(campaign.pk),
            conversion_type=AdConversionIntent.CONVERSION_BOOKING_INTENT,
        )
        metrics = get_campaign_conversion_metrics(str(campaign.pk), days=30)
        self.assertEqual(metrics["campaign_id"], str(campaign.pk))
        self.assertEqual(metrics["conversion_count"], 1)
        self.assertEqual(metrics["booking_intent_count"], 1)

    def test_multiple_conversions_aggregate(self):
        campaign = Campaign.objects.create(
            name="Report Camp Multi",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(name="Multi ad", campaign=campaign)
        for _ in range(3):
            _intent(
                ad,
                campaign_id=str(campaign.pk),
                conversion_type=AdConversionIntent.CONVERSION_BOOKING_INTENT,
            )
        metrics = get_campaign_conversion_metrics(str(campaign.pk), days=30)
        self.assertEqual(metrics["conversion_count"], 3)
        self.assertEqual(metrics["booking_intent_count"], 3)

    def test_conversion_types_split(self):
        campaign = Campaign.objects.create(
            name="Report Camp Types",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(name="Types ad", campaign=campaign)
        _intent(
            ad,
            campaign_id=str(campaign.pk),
            conversion_type=AdConversionIntent.CONVERSION_BOOKING_INTENT,
        )
        _intent(
            ad,
            campaign_id=str(campaign.pk),
            conversion_type=AdConversionIntent.CONVERSION_OTHER,
        )
        metrics = get_campaign_conversion_metrics(str(campaign.pk), days=30)
        self.assertEqual(metrics["conversion_count"], 2)
        self.assertEqual(metrics["booking_intent_count"], 1)
        self.assertEqual(metrics["other_count"], 1)
        self.assertEqual(metrics["profile_view_count"], 0)

    def test_historical_attribution_ignores_live_advertisement_campaign(self):
        campaign_a = Campaign.objects.create(
            name="Historical A",
            status=Campaign.STATUS_ACTIVE,
        )
        campaign_b = Campaign.objects.create(
            name="Live B",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(name="Reassigned ad", campaign=campaign_a)
        _intent(
            ad,
            campaign_id=str(campaign_a.pk),
            conversion_type=AdConversionIntent.CONVERSION_BOOKING_INTENT,
        )
        ad.campaign = campaign_b
        ad.save(update_fields=["campaign"])

        metrics_a = get_campaign_conversion_metrics(str(campaign_a.pk), days=30)
        metrics_b = get_campaign_conversion_metrics(str(campaign_b.pk), days=30)
        self.assertEqual(metrics_a["conversion_count"], 1)
        self.assertEqual(metrics_b["conversion_count"], 0)
        ad.refresh_from_db()
        self.assertEqual(ad.campaign_id, campaign_b.pk)

    def test_null_campaign_id_excluded(self):
        campaign = Campaign.objects.create(
            name="Null exclude",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(name="Null camp ad", campaign=campaign)
        _intent(
            ad,
            campaign_id=None,
            conversion_type=AdConversionIntent.CONVERSION_BOOKING_INTENT,
        )
        metrics = get_campaign_conversion_metrics(str(campaign.pk), days=30)
        self.assertEqual(metrics["conversion_count"], 0)
        self.assertEqual(metrics["booking_intent_count"], 0)

    def test_campaign_isolation(self):
        campaign_a = Campaign.objects.create(
            name="Isolate A",
            status=Campaign.STATUS_ACTIVE,
        )
        campaign_b = Campaign.objects.create(
            name="Isolate B",
            status=Campaign.STATUS_ACTIVE,
        )
        ad_a = _script_ad(name="Iso ad A", campaign=campaign_a)
        ad_b = _script_ad(name="Iso ad B", campaign=campaign_b)
        _intent(
            ad_a,
            campaign_id=str(campaign_a.pk),
            conversion_type=AdConversionIntent.CONVERSION_BOOKING_INTENT,
        )
        _intent(
            ad_b,
            campaign_id=str(campaign_b.pk),
            conversion_type=AdConversionIntent.CONVERSION_OTHER,
        )
        metrics_a = get_campaign_conversion_metrics(str(campaign_a.pk), days=30)
        metrics_b = get_campaign_conversion_metrics(str(campaign_b.pk), days=30)
        self.assertEqual(metrics_a["conversion_count"], 1)
        self.assertEqual(metrics_a["booking_intent_count"], 1)
        self.assertEqual(metrics_a["other_count"], 0)
        self.assertEqual(metrics_b["conversion_count"], 1)
        self.assertEqual(metrics_b["other_count"], 1)
        self.assertEqual(metrics_b["booking_intent_count"], 0)

    def test_existing_ad_funnel_unchanged(self):
        campaign = Campaign.objects.create(
            name="Funnel Camp",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(name="Funnel ad", campaign=campaign)
        _intent(
            ad,
            campaign_id=str(campaign.pk),
            conversion_type=AdConversionIntent.CONVERSION_BOOKING_INTENT,
        )
        funnel = get_ad_conversion_funnel(ad.pk, days=30)
        self.assertEqual(funnel["booking_intents"], 1)
        self.assertEqual(funnel["impressions"], 0)
        self.assertEqual(funnel["clicks"], 0)
        self.assertIn("profile_views", funnel)
        self.assertIn("click_rate", funnel)


@override_settings(ENABLE_CAMPAIGNS=True)
class CampaignListConversionSurfaceTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model

        self.admin = get_user_model().objects.create_superuser(
            email="camp-report-admin@example.com",
            password="CampReportAdmin123!",
        )
        self.client.force_login(self.admin)

    def test_campaign_list_shows_attributed_conversion_counts(self):
        campaign = Campaign.objects.create(
            name="List Surface Camp",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(name="List ad", campaign=campaign)
        _intent(
            ad,
            campaign_id=str(campaign.pk),
            conversion_type=AdConversionIntent.CONVERSION_BOOKING_INTENT,
        )
        response = self.client.get(reverse("ads:campaign_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Attributed conversions")
        self.assertContains(response, "Total: 1")
        self.assertContains(response, "Booking: 1")
