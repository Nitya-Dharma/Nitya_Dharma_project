"""Batch B: Expert WhatsApp CTA uses existing Ads session attribution prefill.

Focused regression only. No model/migration/serving redesign.
"""

from __future__ import annotations

from urllib.parse import parse_qs, unquote, urlsplit

from django.contrib.sessions.middleware import SessionMiddleware
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from ads.models import Advertisement, Campaign
from ads_analytics.models import AdClick, AdConversionIntent, AdLead
from ads_analytics.services.attribution_bridge import (
    SESSION_KEY,
    store_last_click_attribution,
)
from core.models import ExpertProfile
from services.expert_contact import get_expert_contact_info, get_expert_whatsapp_url
from services.templatetags.expert_contact_tags import (
    ad_aware_expert_contact_info,
    expert_contact_info,
)

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_PHONE = "9876543210"
_WA_BARE = "https://wa.me/919876543210"


def _attach_session(request):
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    request.session.save()
    return request


def _active_expert(**kwargs) -> ExpertProfile:
    defaults = {
        "name": "Batch B Expert",
        "expert_type": "ASTROLOGER",
        "phone": _PHONE,
        "is_active": True,
    }
    defaults.update(kwargs)
    return ExpertProfile.objects.create(**defaults)


def _script_ad(**kwargs) -> Advertisement:
    defaults = {
        "name": "Expert Prefill Ad",
        "placement": "top",
        "slots": ["top"],
        "ad_type": Advertisement.AD_TYPE_SCRIPT,
        "script_code": "<div>ad</div>",
        "is_active": True,
        "redirect_url": "https://example.com/dest",
    }
    defaults.update(kwargs)
    return Advertisement.objects.create(**defaults)


class ExpertWhatsappNonAdCompatibilityTests(TestCase):
    def test_no_request_keeps_bare_wa_me(self):
        expert = _active_expert()
        url = get_expert_whatsapp_url(expert)
        self.assertEqual(url, _WA_BARE)
        info = get_expert_contact_info(expert)
        self.assertEqual(info["whatsapp_url"], _WA_BARE)
        self.assertTrue(info["has_whatsapp"])

    def test_request_without_attribution_keeps_bare_wa_me(self):
        expert = _active_expert()
        request = _attach_session(RequestFactory().get("/"))
        url = get_expert_whatsapp_url(expert, request=request)
        self.assertEqual(url, _WA_BARE)
        self.assertNotIn("text=", url)

    def test_filter_without_request_unchanged(self):
        expert = _active_expert()
        info = expert_contact_info(expert)
        self.assertEqual(info["whatsapp_url"], _WA_BARE)


class ExpertWhatsappAdPrefillTests(TestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.factory = RequestFactory()
        self.client = Client(HTTP_USER_AGENT=_BROWSER_UA)
        self.expert = _active_expert()

    def test_session_attribution_adds_contextual_text(self):
        ad = _script_ad()
        request = _attach_session(self.factory.get("/"))
        store_last_click_attribution(request, ad_id=ad.pk)
        url = get_expert_whatsapp_url(self.expert, request=request)
        parsed = urlsplit(url)
        self.assertEqual(parsed.netloc, "wa.me")
        self.assertEqual(parsed.path, "/919876543210")
        text = parse_qs(parsed.query)["text"][0]
        self.assertIn("NityaDharma Ad", text)
        self.assertIn("interested in this advertisement", text)
        self.assertNotIn("Campaign:", text)
        self.assertNotIn("None", text)

    def test_campaign_context_when_session_has_campaign(self):
        campaign = Campaign.objects.create(
            name="Expert Campaign & Test? テスト",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(campaign=campaign)
        request = _attach_session(self.factory.get("/"))
        store_last_click_attribution(
            request, ad_id=ad.pk, campaign_id=str(campaign.pk)
        )
        url = get_expert_whatsapp_url(self.expert, request=request)
        text = parse_qs(urlsplit(url).query)["text"][0]
        self.assertIn("Campaign: Expert Campaign & Test? テスト", text)
        self.assertIn("%", urlsplit(url).query)
        self.assertNotIn("None", unquote(urlsplit(url).query))

    def test_missing_campaign_omits_campaign_line(self):
        ad = _script_ad(campaign=None)
        request = _attach_session(self.factory.get("/"))
        store_last_click_attribution(request, ad_id=ad.pk)
        url = get_expert_whatsapp_url(self.expert, request=request)
        text = parse_qs(urlsplit(url).query)["text"][0]
        self.assertNotIn("Campaign:", text)

    def test_ad_aware_tag_uses_request_session(self):
        ad = _script_ad()
        request = _attach_session(self.factory.get("/"))
        store_last_click_attribution(request, ad_id=ad.pk)
        context = {"request": request}
        info = ad_aware_expert_contact_info(context, self.expert)
        self.assertTrue(info["has_whatsapp"])
        self.assertIn("text=", info["whatsapp_url"])
        self.assertIn("NityaDharma Ad", parse_qs(urlsplit(info["whatsapp_url"]).query)["text"][0])

    def test_track_whatsapp_records_intent_without_new_adclick(self):
        campaign = Campaign.objects.create(
            name="WA Intent Campaign",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(campaign=campaign)
        session = self.client.session
        session[SESSION_KEY] = {
            "ad_id": ad.pk,
            "campaign_id": str(campaign.pk),
        }
        session.save()

        clicks_before = AdClick.objects.count()
        request = _attach_session(self.factory.get("/"))
        store_last_click_attribution(
            request, ad_id=ad.pk, campaign_id=str(campaign.pk)
        )
        wa = get_expert_whatsapp_url(self.expert, request=request)
        self.assertIsNotNone(wa)

        resp = self.client.get(
            reverse("ads_analytics:track_whatsapp"),
            {"redirect": wa},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].startswith("https://wa.me/"))
        self.assertIn("text=", resp["Location"])
        self.assertEqual(AdClick.objects.count(), clicks_before)
        self.assertEqual(
            AdConversionIntent.objects.filter(
                ad_id=ad.pk,
                conversion_type=AdConversionIntent.CONVERSION_OTHER,
            ).count(),
            1,
        )
        self.assertEqual(
            AdLead.objects.filter(
                advertisement_id=ad.pk,
                source=AdLead.SOURCE_WHATSAPP_CTA,
            ).count(),
            1,
        )
        # Session attribution preserved for possible later booking (existing semantics).
        self.assertEqual(
            self.client.session.get(SESSION_KEY),
            {"ad_id": ad.pk, "campaign_id": str(campaign.pk)},
        )

    def test_profile_template_whatsapp_href_includes_prefill_when_attributed(self):
        ad = _script_ad()
        session = self.client.session
        session[SESSION_KEY] = {"ad_id": ad.pk}
        session.save()
        resp = self.client.get(reverse("expert_profile", kwargs={"id": self.expert.pk}))
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode("utf-8", errors="ignore")
        self.assertIn("track/ad/whatsapp", body)
        self.assertIn("NityaDharma", body)
        self.assertIn("text%3D", body)  # urlencoded redirect query embeds text=
