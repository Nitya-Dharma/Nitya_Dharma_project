"""Persist optional session campaign_id onto AdConversionIntent.

Proves booking/WhatsApp attribution bridges pass click-time campaign_id from
the existing ads_last_click_attribution session into record_ad_conversion_intent.
Does not cover AdSet, Lead/CRM, billing, Native Ads, or reporting redesign.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from ads.models import Advertisement, Campaign
from ads_analytics.models import AdConversionIntent
from ads_analytics.services.attribution_bridge import (
    SESSION_KEY,
    record_booking_conversion_from_session,
    record_whatsapp_contact_from_session,
)

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _script_ad(**kwargs) -> Advertisement:
    defaults = {
        "name": "Conversion Camp Ad",
        "placement": "top",
        "slots": ["top"],
        "ad_type": Advertisement.AD_TYPE_SCRIPT,
        "script_code": "<div>ad</div>",
        "is_active": True,
        "redirect_url": "https://example.com/dest",
    }
    defaults.update(kwargs)
    return Advertisement.objects.create(**defaults)


def _user(suffix: str):
    return get_user_model().objects.create_user(
        email=f"conv-camp-{suffix}@example.com",
        password="ConvCampPass123!",
        username=f"conv_camp_{suffix}",
        role="user",
        status="active",
        is_active=True,
    )


class ConversionCampaignIdPersistenceTests(TestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.client = Client(HTTP_USER_AGENT=_BROWSER_UA)
        self.factory = RequestFactory()

    def test_booking_conversion_persists_session_campaign_id(self):
        campaign = Campaign.objects.create(
            name="Conv Camp Present",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(name="Conv linked", campaign=campaign)
        click_url = reverse("ads_analytics:track_click", kwargs={"ad_id": ad.pk})
        click_resp = self.client.get(
            click_url,
            {"redirect": "https://example.com/dest", "placement": "top"},
        )
        self.assertEqual(click_resp.status_code, 302)
        self.assertEqual(
            self.client.session.get(SESSION_KEY),
            {"ad_id": ad.pk, "campaign_id": str(campaign.pk)},
        )

        user = _user("booking_present")
        request = self.factory.get("/")
        request.session = self.client.session
        ok = record_booking_conversion_from_session(request, user_id=user.pk)
        self.assertTrue(ok)
        intent = AdConversionIntent.objects.get(ad_id=ad.pk)
        self.assertEqual(intent.ad_id, ad.pk)
        self.assertEqual(
            intent.conversion_type,
            AdConversionIntent.CONVERSION_BOOKING_INTENT,
        )
        self.assertEqual(intent.campaign_id, str(campaign.pk))
        self.assertNotIn(SESSION_KEY, request.session)

    def test_booking_conversion_without_campaign_keeps_campaign_id_null(self):
        ad = _script_ad(name="Conv orphan", campaign=None)
        click_url = reverse("ads_analytics:track_click", kwargs={"ad_id": ad.pk})
        click_resp = self.client.get(
            click_url,
            {"redirect": "https://example.com/dest", "placement": "top"},
        )
        self.assertEqual(click_resp.status_code, 302)
        self.assertEqual(self.client.session.get(SESSION_KEY), {"ad_id": ad.pk})

        user = _user("booking_absent")
        request = self.factory.get("/")
        request.session = self.client.session
        ok = record_booking_conversion_from_session(request, user_id=user.pk)
        self.assertTrue(ok)
        intent = AdConversionIntent.objects.get(ad_id=ad.pk)
        self.assertEqual(
            intent.conversion_type,
            AdConversionIntent.CONVERSION_BOOKING_INTENT,
        )
        self.assertIsNone(intent.campaign_id)
        self.assertNotIn(SESSION_KEY, request.session)

    def test_booking_legacy_session_ad_id_only_keeps_campaign_id_null(self):
        ad = _script_ad(name="Legacy session ad", campaign=None)
        user = _user("legacy")
        request = self.factory.get("/")
        request.session = self.client.session
        request.session[SESSION_KEY] = {"ad_id": ad.pk}
        request.session.save()
        ok = record_booking_conversion_from_session(request, user_id=user.pk)
        self.assertTrue(ok)
        intent = AdConversionIntent.objects.get(ad_id=ad.pk)
        self.assertEqual(
            intent.conversion_type,
            AdConversionIntent.CONVERSION_BOOKING_INTENT,
        )
        self.assertIsNone(intent.campaign_id)
        self.assertNotIn(SESSION_KEY, request.session)

    def test_whatsapp_conversion_persists_session_campaign_id(self):
        campaign = Campaign.objects.create(
            name="WA Camp",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(name="WA linked", campaign=campaign)
        user = _user("whatsapp")
        request = self.factory.get("/")
        request.session = self.client.session
        request.session[SESSION_KEY] = {
            "ad_id": ad.pk,
            "campaign_id": str(campaign.pk),
        }
        request.session.save()
        ok = record_whatsapp_contact_from_session(request, user_id=user.pk)
        self.assertTrue(ok)
        intent = AdConversionIntent.objects.get(ad_id=ad.pk)
        self.assertEqual(intent.conversion_type, AdConversionIntent.CONVERSION_OTHER)
        self.assertEqual(intent.campaign_id, str(campaign.pk))
        self.assertEqual(
            request.session.get(SESSION_KEY),
            {"ad_id": ad.pk, "campaign_id": str(campaign.pk)},
        )

    def test_no_session_does_not_create_conversion(self):
        user = _user("no_session")
        request = self.factory.get("/")
        request.session = self.client.session
        ok = record_booking_conversion_from_session(request, user_id=user.pk)
        self.assertFalse(ok)
        self.assertEqual(AdConversionIntent.objects.count(), 0)
