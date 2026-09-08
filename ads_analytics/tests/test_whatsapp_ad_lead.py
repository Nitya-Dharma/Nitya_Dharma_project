"""Focused tests for attributed WhatsApp CTA → AdLead.

Lead is additive after AdConversionIntent(other). Does not cover booking
wiring, Lead UI, CRM, or LeadEvent. Uses Django's disposable test database.
"""

from __future__ import annotations

from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from ads.models import Advertisement, Campaign
from ads_analytics.models import AdClick, AdConversionIntent, AdImpression, AdLead
from ads_analytics.services.attribution_bridge import (
    SESSION_KEY,
    record_whatsapp_contact_from_session,
    store_last_click_attribution,
)
from ads_analytics.views import _is_allowed_whatsapp_redirect
from profiles.models import PanditProfile
from profiles.services_contact import get_whatsapp_url
from profiles.whatsapp_ad_prefill import apply_whatsapp_text_param

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_WA_TARGET = "https://wa.me/919999999999"


def _script_ad(**kwargs) -> Advertisement:
    defaults = {
        "name": "WA Lead Ad",
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
        "email": f"wa-lead-{suffix}@example.com",
        "password": "WaLeadPass123!",
        "username": f"wa_lead_{suffix}",
        "role": "user",
        "status": "active",
        "is_active": True,
    }
    defaults.update(kwargs)
    return get_user_model().objects.create_user(**defaults)


def _attach_session(request):
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    request.session.save()
    return request


class WhatsappAdLeadTests(TestCase):
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

    def test_attributed_whatsapp_creates_other_conversion_and_whatsapp_lead(self):
        campaign = Campaign.objects.create(
            name="WA Lead Camp",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(campaign=campaign)
        request = self._session_request(
            {"ad_id": ad.pk, "campaign_id": str(campaign.pk)}
        )
        ok = record_whatsapp_contact_from_session(request)
        self.assertTrue(ok)
        conversion = AdConversionIntent.objects.get()
        self.assertEqual(conversion.conversion_type, AdConversionIntent.CONVERSION_OTHER)
        lead = AdLead.objects.get()
        self.assertEqual(lead.source, AdLead.SOURCE_WHATSAPP_CTA)
        self.assertEqual(lead.source_conversion_id, conversion.pk)
        self.assertEqual(lead.status, AdLead.STATUS_NEW)

    def test_anonymous_attributed_whatsapp_lead_user_is_null(self):
        ad = _script_ad()
        request = self._session_request({"ad_id": ad.pk})
        ok = record_whatsapp_contact_from_session(request, user_id=None)
        self.assertTrue(ok)
        conversion = AdConversionIntent.objects.get()
        lead = AdLead.objects.get()
        self.assertIsNone(conversion.user_id)
        self.assertIsNone(lead.user_id)

    def test_authenticated_attributed_whatsapp_copies_user(self):
        ad = _script_ad()
        user = _user("auth")
        request = self._session_request({"ad_id": ad.pk})
        ok = record_whatsapp_contact_from_session(request, user_id=user.pk)
        self.assertTrue(ok)
        conversion = AdConversionIntent.objects.get()
        lead = AdLead.objects.get()
        self.assertEqual(conversion.user_id, user.pk)
        self.assertEqual(lead.user_id, conversion.user_id)

    def test_lead_advertisement_matches_conversion_ad(self):
        ad = _script_ad(name="Exact Ad")
        request = self._session_request({"ad_id": ad.pk})
        record_whatsapp_contact_from_session(request)
        conversion = AdConversionIntent.objects.get()
        lead = AdLead.objects.get()
        self.assertEqual(lead.advertisement_id, conversion.ad_id)
        self.assertEqual(lead.advertisement_id, ad.pk)

    def test_lead_campaign_id_matches_conversion_campaign_id(self):
        campaign = Campaign.objects.create(
            name="Snap Camp",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(campaign=campaign)
        request = self._session_request(
            {"ad_id": ad.pk, "campaign_id": str(campaign.pk)}
        )
        record_whatsapp_contact_from_session(request)
        conversion = AdConversionIntent.objects.get()
        lead = AdLead.objects.get()
        self.assertEqual(lead.campaign_id, conversion.campaign_id)
        self.assertEqual(lead.campaign_id, str(campaign.pk))

    def test_campaign_snapshot_is_historical_not_live_advertisement_campaign(self):
        click_campaign = Campaign.objects.create(
            name="Click Time Camp",
            status=Campaign.STATUS_ACTIVE,
        )
        later_campaign = Campaign.objects.create(
            name="Later Camp",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(campaign=click_campaign)
        click_url = reverse("ads_analytics:track_click", kwargs={"ad_id": ad.pk})
        self.client.get(
            click_url,
            {"redirect": "https://example.com/dest", "placement": "top"},
        )
        ad.campaign = later_campaign
        ad.save(update_fields=["campaign"])

        request = self.factory.get("/")
        request.session = self.client.session
        ok = record_whatsapp_contact_from_session(request)
        self.assertTrue(ok)
        conversion = AdConversionIntent.objects.get()
        lead = AdLead.objects.get()
        self.assertEqual(conversion.campaign_id, str(click_campaign.pk))
        self.assertEqual(lead.campaign_id, str(click_campaign.pk))
        self.assertNotEqual(lead.campaign_id, str(later_campaign.pk))
        self.assertEqual(ad.campaign_id, later_campaign.pk)

    def test_repeated_whatsapp_cta_creates_two_conversions_and_two_leads(self):
        ad = _script_ad()
        request = self._session_request({"ad_id": ad.pk, "campaign_id": "camp-1"})
        self.assertTrue(record_whatsapp_contact_from_session(request))
        self.assertTrue(record_whatsapp_contact_from_session(request))
        self.assertEqual(AdConversionIntent.objects.count(), 2)
        self.assertEqual(AdLead.objects.count(), 2)
        self.assertEqual(
            AdConversionIntent.objects.filter(
                conversion_type=AdConversionIntent.CONVERSION_OTHER
            ).count(),
            2,
        )
        self.assertEqual(
            AdLead.objects.filter(source=AdLead.SOURCE_WHATSAPP_CTA).count(),
            2,
        )
        self.assertEqual(
            request.session.get(SESSION_KEY),
            {"ad_id": ad.pk, "campaign_id": "camp-1"},
        )

    def test_no_attribution_creates_no_conversion_or_lead_and_redirects(self):
        resp = self.client.get(
            reverse("ads_analytics:track_whatsapp"),
            {"redirect": _WA_TARGET},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], _WA_TARGET)
        self.assertEqual(AdConversionIntent.objects.count(), 0)
        self.assertEqual(AdLead.objects.count(), 0)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_malformed_attribution_creates_no_lead(self):
        request = self._session_request({"ad_id": "not-an-id"})
        ok = record_whatsapp_contact_from_session(request)
        self.assertFalse(ok)
        self.assertEqual(AdConversionIntent.objects.count(), 0)
        self.assertEqual(AdLead.objects.count(), 0)

        request = self._session_request("not-a-dict")
        ok = record_whatsapp_contact_from_session(request)
        self.assertFalse(ok)
        self.assertEqual(AdConversionIntent.objects.count(), 0)
        self.assertEqual(AdLead.objects.count(), 0)

    def test_missing_campaign_still_creates_lead_with_snapshot(self):
        ad = _script_ad(campaign=None)
        request = self._session_request({"ad_id": ad.pk, "campaign_id": "stale-999"})
        ok = record_whatsapp_contact_from_session(request)
        self.assertTrue(ok)
        conversion = AdConversionIntent.objects.get()
        lead = AdLead.objects.get()
        self.assertEqual(conversion.campaign_id, "stale-999")
        self.assertEqual(lead.campaign_id, "stale-999")
        self.assertIsNone(ad.campaign_id)

    def test_lead_failure_keeps_conversion_and_whatsapp_redirect(self):
        campaign = Campaign.objects.create(
            name="Fail Camp",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(campaign=campaign)
        click_url = reverse("ads_analytics:track_click", kwargs={"ad_id": ad.pk})
        self.client.get(
            click_url,
            {"redirect": "https://example.com/dest", "placement": "top"},
        )
        session_before = dict(self.client.session.get(SESSION_KEY))
        wa = apply_whatsapp_text_param(_WA_TARGET, "hello")
        self.assertTrue(_is_allowed_whatsapp_redirect(wa))

        with patch(
            "ads_analytics.services.lead_service.create_ad_lead_from_conversion",
            side_effect=RuntimeError("lead write failed"),
        ):
            resp = self.client.get(
                reverse("ads_analytics:track_whatsapp"),
                {"redirect": wa},
            )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], wa)
        self.assertEqual(AdConversionIntent.objects.count(), 1)
        self.assertEqual(
            AdConversionIntent.objects.get().conversion_type,
            AdConversionIntent.CONVERSION_OTHER,
        )
        self.assertEqual(AdLead.objects.count(), 0)
        self.assertEqual(self.client.session.get(SESSION_KEY), session_before)

    def test_no_extra_ad_click_or_impression_from_whatsapp(self):
        ad = _script_ad()
        request = self._session_request({"ad_id": ad.pk})
        record_whatsapp_contact_from_session(request)
        self.assertEqual(AdClick.objects.count(), 0)
        self.assertEqual(AdImpression.objects.count(), 0)
        self.assertEqual(AdConversionIntent.objects.count(), 1)
        self.assertEqual(AdLead.objects.count(), 1)

    def test_attribution_session_not_cleared_after_whatsapp_lead(self):
        ad = _script_ad()
        payload = {"ad_id": ad.pk, "campaign_id": "keep-me"}
        request = self._session_request(payload)
        record_whatsapp_contact_from_session(request)
        self.assertEqual(request.session.get(SESSION_KEY), payload)

    def test_track_whatsapp_http_creates_lead_and_preserves_redirect(self):
        campaign = Campaign.objects.create(
            name="HTTP Camp",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(campaign=campaign)
        self.client.get(
            reverse("ads_analytics:track_click", kwargs={"ad_id": ad.pk}),
            {"redirect": "https://example.com/dest", "placement": "top"},
        )
        clicks_after_click = AdClick.objects.count()
        wa = apply_whatsapp_text_param(_WA_TARGET, "NityaDharma Ad")
        resp = self.client.get(
            reverse("ads_analytics:track_whatsapp"),
            {"redirect": wa},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], wa)
        self.assertEqual(AdClick.objects.count(), clicks_after_click)
        self.assertEqual(AdImpression.objects.count(), 0)
        conversion = AdConversionIntent.objects.get()
        lead = AdLead.objects.get()
        self.assertEqual(conversion.conversion_type, AdConversionIntent.CONVERSION_OTHER)
        self.assertEqual(lead.source, AdLead.SOURCE_WHATSAPP_CTA)
        self.assertEqual(
            self.client.session.get(SESSION_KEY),
            {"ad_id": ad.pk, "campaign_id": str(campaign.pk)},
        )

    def test_existing_prefill_still_works_with_lead_path(self):
        User = get_user_model()
        pandit = User.objects.create_user(
            email="wa-lead-prefill-pandit@example.com",
            password="PrefillPass123!",
            username="wa_lead_prefill_pandit",
            role="pandit",
            status="active",
            is_active=True,
            email_verified=True,
        )
        profile, _ = PanditProfile.objects.get_or_create(user=pandit)
        profile.enable_whatsapp = True
        profile.allow_whatsapp = True
        profile.whatsapp_mobile_number = "919876543210"
        profile.save()

        campaign = Campaign.objects.create(
            name="Prefill Camp",
            status=Campaign.STATUS_ACTIVE,
        )
        request = _attach_session(self.factory.get("/"))
        store_last_click_attribution(
            request, ad_id=3, campaign_id=str(campaign.pk)
        )
        url = get_whatsapp_url(profile, request=request)
        text = parse_qs(urlsplit(url).query)["text"][0]
        self.assertIn("NityaDharma Ad", text)
        self.assertIn("Campaign: Prefill Camp", text)
        self.assertTrue(_is_allowed_whatsapp_redirect(url))
        self.assertEqual(AdLead.objects.count(), 0)
        self.assertEqual(AdConversionIntent.objects.count(), 0)
        self.assertEqual(
            request.session.get(SESSION_KEY),
            {"ad_id": 3, "campaign_id": str(campaign.pk)},
        )

    def test_bool_conversion_api_still_returns_bool(self):
        from ads_analytics.services.event_recording import record_ad_conversion_intent

        ad = _script_ad()
        result = record_ad_conversion_intent(
            ad.pk,
            AdConversionIntent.CONVERSION_OTHER,
        )
        self.assertIs(result, True)
        self.assertEqual(AdConversionIntent.objects.count(), 1)
        self.assertEqual(AdLead.objects.count(), 0)
