"""Focused tests for attributed booking → AdLead.

Lead is additive after AdConversionIntent(booking_intent). Does not cover
Lead UI, CRM, LeadEvent, or WhatsApp changes. Uses Django's disposable
test database.
"""

from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from ads.models import Advertisement, Campaign
from ads_analytics.models import AdClick, AdConversionIntent, AdImpression, AdLead
from ads_analytics.services.attribution_bridge import (
    SESSION_KEY,
    record_booking_conversion_from_session,
)
from ads_analytics.services.lead_service import create_ad_lead_from_conversion

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _script_ad(**kwargs) -> Advertisement:
    defaults = {
        "name": "Booking Lead Ad",
        "placement": "top",
        "slots": ["top"],
        "ad_type": Advertisement.AD_TYPE_SCRIPT,
        "script_code": "<div>ad</div>",
        "is_active": True,
        "redirect_url": "https://example.com/dest",
    }
    defaults.update(kwargs)
    return Advertisement.objects.create(**defaults)


def _user(suffix: str, **kwargs):
    defaults = {
        "email": f"booking-lead-{suffix}@example.com",
        "password": "BookingLeadPass123!",
        "username": f"booking_lead_{suffix}",
        "role": "user",
        "status": "active",
        "is_active": True,
    }
    defaults.update(kwargs)
    return get_user_model().objects.create_user(**defaults)


class BookingAdLeadTests(TestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.client = Client(HTTP_USER_AGENT=_BROWSER_UA)
        self.factory = RequestFactory()

    def _session_request(self, payload=None):
        request = self.factory.get("/")
        request.session = self.client.session
        if payload is not None:
            request.session[SESSION_KEY] = payload
            request.session.save()
        return request

    def test_attributed_booking_creates_booking_intent_conversion_and_lead(self):
        campaign = Campaign.objects.create(
            name="Booking Lead Camp",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(campaign=campaign)
        user = _user("attr")
        request = self._session_request(
            {"ad_id": ad.pk, "campaign_id": str(campaign.pk)}
        )
        ok = record_booking_conversion_from_session(request, user_id=user.pk)
        self.assertTrue(ok)
        conversion = AdConversionIntent.objects.get()
        self.assertEqual(
            conversion.conversion_type,
            AdConversionIntent.CONVERSION_BOOKING_INTENT,
        )
        lead = AdLead.objects.get()
        self.assertEqual(lead.source, AdLead.SOURCE_BOOKING_INTENT)
        self.assertEqual(lead.source_conversion_id, conversion.pk)
        self.assertEqual(lead.status, AdLead.STATUS_NEW)

    def test_anonymous_booking_lead_user_is_null(self):
        ad = _script_ad()
        request = self._session_request({"ad_id": ad.pk})
        ok = record_booking_conversion_from_session(request, user_id=None)
        self.assertTrue(ok)
        conversion = AdConversionIntent.objects.get()
        lead = AdLead.objects.get()
        self.assertIsNone(conversion.user_id)
        self.assertIsNone(lead.user_id)

    def test_authenticated_booking_lead_copies_user(self):
        ad = _script_ad()
        user = _user("auth")
        request = self._session_request({"ad_id": ad.pk})
        ok = record_booking_conversion_from_session(request, user_id=user.pk)
        self.assertTrue(ok)
        conversion = AdConversionIntent.objects.get()
        lead = AdLead.objects.get()
        self.assertEqual(conversion.user_id, user.pk)
        self.assertEqual(lead.user_id, conversion.user_id)

    def test_lead_advertisement_matches_conversion_ad(self):
        ad = _script_ad(name="Exact Booking Ad")
        request = self._session_request({"ad_id": ad.pk})
        record_booking_conversion_from_session(request)
        conversion = AdConversionIntent.objects.get()
        lead = AdLead.objects.get()
        self.assertEqual(lead.advertisement_id, conversion.ad_id)
        self.assertEqual(lead.advertisement_id, ad.pk)

    def test_lead_campaign_id_matches_conversion_campaign_id(self):
        campaign = Campaign.objects.create(
            name="Snap Booking Camp",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(campaign=campaign)
        request = self._session_request(
            {"ad_id": ad.pk, "campaign_id": str(campaign.pk)}
        )
        record_booking_conversion_from_session(request)
        conversion = AdConversionIntent.objects.get()
        lead = AdLead.objects.get()
        self.assertEqual(lead.campaign_id, conversion.campaign_id)
        self.assertEqual(lead.campaign_id, str(campaign.pk))

    def test_lead_user_matches_conversion_user(self):
        ad = _script_ad()
        user = _user("match")
        request = self._session_request({"ad_id": ad.pk})
        record_booking_conversion_from_session(request, user_id=user.pk)
        conversion = AdConversionIntent.objects.get()
        lead = AdLead.objects.get()
        self.assertEqual(lead.user_id, conversion.user_id)

    def test_campaign_snapshot_is_historical_not_live_advertisement_campaign(self):
        click_campaign = Campaign.objects.create(
            name="Click Time Booking Camp",
            status=Campaign.STATUS_ACTIVE,
        )
        later_campaign = Campaign.objects.create(
            name="Later Booking Camp",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(campaign=click_campaign)
        self.client.get(
            reverse("ads_analytics:track_click", kwargs={"ad_id": ad.pk}),
            {"redirect": "https://example.com/dest", "placement": "top"},
        )
        ad.campaign = later_campaign
        ad.save(update_fields=["campaign"])

        request = self.factory.get("/")
        request.session = self.client.session
        ok = record_booking_conversion_from_session(request)
        self.assertTrue(ok)
        conversion = AdConversionIntent.objects.get()
        lead = AdLead.objects.get()
        self.assertEqual(conversion.campaign_id, str(click_campaign.pk))
        self.assertEqual(lead.campaign_id, str(click_campaign.pk))
        self.assertNotEqual(lead.campaign_id, str(later_campaign.pk))
        self.assertEqual(ad.campaign_id, later_campaign.pk)

    def test_successful_booking_clears_attribution_session(self):
        ad = _script_ad()
        request = self._session_request({"ad_id": ad.pk, "campaign_id": "keep-until-clear"})
        ok = record_booking_conversion_from_session(request)
        self.assertTrue(ok)
        self.assertTrue(AdLead.objects.exists())
        self.assertNotIn(SESSION_KEY, request.session)

    def test_lead_failure_keeps_conversion_and_clears_session(self):
        ad = _script_ad()
        request = self._session_request({"ad_id": ad.pk, "campaign_id": "fail-lead"})
        with patch(
            "ads_analytics.services.lead_service.create_ad_lead_from_conversion",
            side_effect=RuntimeError("lead write failed"),
        ):
            ok = record_booking_conversion_from_session(request)
        self.assertTrue(ok)
        self.assertEqual(AdConversionIntent.objects.count(), 1)
        self.assertEqual(
            AdConversionIntent.objects.get().conversion_type,
            AdConversionIntent.CONVERSION_BOOKING_INTENT,
        )
        self.assertEqual(AdLead.objects.count(), 0)
        self.assertNotIn(SESSION_KEY, request.session)

    def test_no_attribution_creates_no_conversion_or_lead(self):
        request = self._session_request()
        ok = record_booking_conversion_from_session(request, user_id=_user("none").pk)
        self.assertFalse(ok)
        self.assertEqual(AdConversionIntent.objects.count(), 0)
        self.assertEqual(AdLead.objects.count(), 0)
        self.assertNotIn(SESSION_KEY, request.session)

    def test_malformed_attribution_creates_no_lead(self):
        request = self._session_request({"ad_id": "not-an-id"})
        ok = record_booking_conversion_from_session(request)
        self.assertFalse(ok)
        self.assertEqual(AdConversionIntent.objects.count(), 0)
        self.assertEqual(AdLead.objects.count(), 0)
        self.assertEqual(request.session.get(SESSION_KEY), {"ad_id": "not-an-id"})

        request = self._session_request("not-a-dict")
        ok = record_booking_conversion_from_session(request)
        self.assertFalse(ok)
        self.assertEqual(AdConversionIntent.objects.count(), 0)
        self.assertEqual(AdLead.objects.count(), 0)

    def test_stale_campaign_snapshot_still_creates_lead(self):
        ad = _script_ad(campaign=None)
        request = self._session_request({"ad_id": ad.pk, "campaign_id": "stale-888"})
        ok = record_booking_conversion_from_session(request)
        self.assertTrue(ok)
        conversion = AdConversionIntent.objects.get()
        lead = AdLead.objects.get()
        self.assertEqual(conversion.campaign_id, "stale-888")
        self.assertEqual(lead.campaign_id, "stale-888")
        self.assertIsNone(ad.campaign_id)
        self.assertNotIn(SESSION_KEY, request.session)

    def test_repeated_booking_after_reattribution_creates_two_rows(self):
        ad = _script_ad()
        payload = {"ad_id": ad.pk, "campaign_id": "repeat-1"}
        request = self._session_request(payload)
        self.assertTrue(record_booking_conversion_from_session(request))
        self.assertNotIn(SESSION_KEY, request.session)

        request.session[SESSION_KEY] = payload
        request.session.save()
        self.assertTrue(record_booking_conversion_from_session(request))
        self.assertEqual(AdConversionIntent.objects.count(), 2)
        self.assertEqual(AdLead.objects.count(), 2)
        self.assertEqual(
            AdConversionIntent.objects.filter(
                conversion_type=AdConversionIntent.CONVERSION_BOOKING_INTENT
            ).count(),
            2,
        )
        self.assertEqual(
            AdLead.objects.filter(source=AdLead.SOURCE_BOOKING_INTENT).count(),
            2,
        )
        self.assertNotIn(SESSION_KEY, request.session)

    def test_same_conversion_cannot_create_two_leads(self):
        ad = _script_ad()
        request = self._session_request({"ad_id": ad.pk})
        self.assertTrue(record_booking_conversion_from_session(request))
        conversion = AdConversionIntent.objects.get()
        first = AdLead.objects.get()
        second = create_ad_lead_from_conversion(
            conversion, AdLead.SOURCE_BOOKING_INTENT
        )
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(AdLead.objects.filter(source_conversion=conversion).count(), 1)

    def test_no_extra_ad_click_or_impression_from_booking(self):
        ad = _script_ad()
        request = self._session_request({"ad_id": ad.pk})
        record_booking_conversion_from_session(request)
        self.assertEqual(AdClick.objects.count(), 0)
        self.assertEqual(AdImpression.objects.count(), 0)
        self.assertEqual(AdConversionIntent.objects.count(), 1)
        self.assertEqual(AdLead.objects.count(), 1)

    def test_bool_api_still_returns_bool(self):
        ad = _script_ad()
        request = self._session_request({"ad_id": ad.pk})
        result = record_booking_conversion_from_session(request)
        self.assertIs(result, True)
        self.assertFalse(record_booking_conversion_from_session(request))
