"""Campaign identity on AdClick / AdImpression and click attribution session.

Proves track_click / track_impression populate existing campaign_id from
Advertisement.campaign, and that the existing ads_last_click_attribution
session carries optional campaign_id. Does not cover AdSet, booking/WhatsApp
campaign consumption, billing, or Native Ads.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from ads.models import Advertisement, Campaign
from ads_analytics.models import AdClick, AdConversionIntent, AdImpression
from ads_analytics.services.attribution_bridge import (
    SESSION_KEY,
    record_booking_conversion_from_session,
)

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _script_ad(**kwargs) -> Advertisement:
    defaults = {
        "name": "Campaign ID Attr Ad",
        "placement": "top",
        "slots": ["top"],
        "ad_type": Advertisement.AD_TYPE_SCRIPT,
        "script_code": "<div>ad</div>",
        "is_active": True,
        "redirect_url": "https://example.com/dest",
    }
    defaults.update(kwargs)
    return Advertisement.objects.create(**defaults)


class CampaignIdEventAttributionTests(TestCase):
    def setUp(self):
        # LocMem protection keys survive DB rollback; clear so duplicate-impression
        # guards cannot skip recording when ad PKs recycle across tests.
        from django.core.cache import cache

        cache.clear()
        self.client = Client(HTTP_USER_AGENT=_BROWSER_UA)

    def test_click_with_campaign_populates_campaign_id(self):
        campaign = Campaign.objects.create(
            name="Attr Camp",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(name="Linked click", campaign=campaign)
        url = reverse("ads_analytics:track_click", kwargs={"ad_id": ad.pk})
        response = self.client.get(
            url,
            {"redirect": "https://example.com/dest", "placement": "top"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "https://example.com/dest")
        click = AdClick.objects.get(ad_id=ad.pk)
        self.assertEqual(click.campaign_id, str(campaign.pk))
        self.assertEqual(
            self.client.session.get(SESSION_KEY),
            {"ad_id": ad.pk, "campaign_id": str(campaign.pk)},
        )

    def test_impression_with_campaign_populates_campaign_id(self):
        campaign = Campaign.objects.create(
            name="Attr Camp Imp",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(name="Linked imp", campaign=campaign)
        url = reverse("ads_analytics:track_impression", kwargs={"ad_id": ad.pk})
        response = self.client.get(url, {"placement": "top"})
        self.assertEqual(response.status_code, 204)
        imp = AdImpression.objects.get(ad_id=ad.pk)
        self.assertEqual(imp.campaign_id, str(campaign.pk))

    def test_click_without_campaign_keeps_campaign_id_null(self):
        ad = _script_ad(name="Orphan click", campaign=None)
        url = reverse("ads_analytics:track_click", kwargs={"ad_id": ad.pk})
        response = self.client.get(
            url,
            {"redirect": "https://example.com/dest", "placement": "top"},
        )
        self.assertEqual(response.status_code, 302)
        click = AdClick.objects.get(ad_id=ad.pk)
        self.assertIsNone(click.campaign_id)
        payload = self.client.session.get(SESSION_KEY)
        self.assertEqual(payload, {"ad_id": ad.pk})
        self.assertNotIn("campaign_id", payload)

    def test_impression_without_campaign_keeps_campaign_id_null(self):
        ad = _script_ad(name="Orphan imp", campaign=None)
        url = reverse("ads_analytics:track_impression", kwargs={"ad_id": ad.pk})
        response = self.client.get(url, {"placement": "top"})
        self.assertEqual(response.status_code, 204)
        imp = AdImpression.objects.get(ad_id=ad.pk)
        self.assertIsNone(imp.campaign_id)

    def test_click_session_attribution_includes_campaign_id_when_linked(self):
        campaign = Campaign.objects.create(
            name="Session Camp",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(name="Session linked", campaign=campaign)
        url = reverse("ads_analytics:track_click", kwargs={"ad_id": ad.pk})
        response = self.client.get(
            url,
            {"redirect": "https://example.com/dest", "placement": "top"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "https://example.com/dest")
        payload = self.client.session.get(SESSION_KEY)
        self.assertEqual(
            payload,
            {"ad_id": ad.pk, "campaign_id": str(campaign.pk)},
        )

    def test_booking_reader_tolerates_extra_campaign_id_in_session(self):
        """Booking bridge persists session campaign_id when present; session cleared."""
        ad = _script_ad(name="Reader compat ad", campaign=None)
        user = get_user_model().objects.create_user(
            email="session-reader@example.com",
            password="SessionReaderPass123!",
            username="session_reader",
            role="user",
            status="active",
            is_active=True,
        )
        request = RequestFactory().get("/")
        request.session = self.client.session
        request.session[SESSION_KEY] = {
            "ad_id": ad.pk,
            "campaign_id": "456",
        }
        request.session.save()
        ok = record_booking_conversion_from_session(request, user_id=user.pk)
        self.assertTrue(ok)
        intent = AdConversionIntent.objects.get(ad_id=ad.pk)
        self.assertEqual(
            intent.conversion_type,
            AdConversionIntent.CONVERSION_BOOKING_INTENT,
        )
        self.assertEqual(intent.campaign_id, "456")
        self.assertNotIn(SESSION_KEY, request.session)
