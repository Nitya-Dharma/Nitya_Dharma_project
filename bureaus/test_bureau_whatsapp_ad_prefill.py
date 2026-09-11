"""Batch C: Bureau WhatsApp CTA uses existing Ads session attribution prefill."""

from __future__ import annotations

from urllib.parse import parse_qs, unquote, urlparse, urlsplit

from django.contrib.sessions.middleware import SessionMiddleware
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from ads.models import Advertisement, Campaign
from ads_analytics.models import AdClick, AdConversionIntent, AdLead
from ads_analytics.services.attribution_bridge import (
    SESSION_KEY,
    store_last_click_attribution,
)
from bureaus.tests import _make_bureau
from bureaus.whatsapp_contact import get_bureau_whatsapp_url

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_STORED_WA = "9123456792"
_WA_BARE = f"https://wa.me/{_STORED_WA}"


def _attach_session(request):
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    request.session.save()
    return request


def _script_ad(**kwargs) -> Advertisement:
    defaults = {
        "name": "Bureau Prefill Ad",
        "placement": "top",
        "slots": ["top"],
        "ad_type": Advertisement.AD_TYPE_SCRIPT,
        "script_code": "<div>ad</div>",
        "is_active": True,
        "redirect_url": "https://example.com/dest",
    }
    defaults.update(kwargs)
    return Advertisement.objects.create(**defaults)


class BureauWhatsappHelperTests(TestCase):
    def test_no_request_keeps_bare_wa_me_with_stored_digits(self):
        self.assertEqual(get_bureau_whatsapp_url(_STORED_WA), _WA_BARE)

    def test_empty_number_returns_none(self):
        self.assertIsNone(get_bureau_whatsapp_url(""))
        self.assertIsNone(get_bureau_whatsapp_url(None))

    def test_does_not_normalize_stored_value(self):
        # Preserve stored form even if unusual; Ads task must not rewrite phone data.
        self.assertEqual(
            get_bureau_whatsapp_url("91 98765"),
            "https://wa.me/91 98765",
        )

    def test_request_without_attribution_keeps_bare(self):
        request = _attach_session(RequestFactory().get("/"))
        self.assertEqual(get_bureau_whatsapp_url(_STORED_WA, request=request), _WA_BARE)


class BureauWhatsappAdPrefillTests(TestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.factory = RequestFactory()
        self.client = Client(HTTP_USER_AGENT=_BROWSER_UA)
        self.bureau = _make_bureau(
            email="bureau-wa-prefill@example.com",
            bureau_name="Prefill Bureau",
            is_active=True,
            is_approved=True,
            is_email_verified=True,
        )
        self.bureau.whatsapp_number = _STORED_WA
        self.bureau.save(update_fields=["whatsapp_number"])

    def test_session_attribution_adds_contextual_text(self):
        ad = _script_ad()
        request = _attach_session(self.factory.get("/"))
        store_last_click_attribution(request, ad_id=ad.pk)
        url = get_bureau_whatsapp_url(_STORED_WA, request=request)
        parsed = urlsplit(url)
        self.assertEqual(parsed.netloc, "wa.me")
        self.assertEqual(parsed.path, f"/{_STORED_WA}")
        text = parse_qs(parsed.query)["text"][0]
        self.assertIn("NityaDharma Ad", text)
        self.assertNotIn("Campaign:", text)
        self.assertNotIn("None", text)

    def test_campaign_context_when_present(self):
        campaign = Campaign.objects.create(
            name="Bureau Campaign & Test? テスト",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(campaign=campaign)
        request = _attach_session(self.factory.get("/"))
        store_last_click_attribution(
            request, ad_id=ad.pk, campaign_id=str(campaign.pk)
        )
        url = get_bureau_whatsapp_url(_STORED_WA, request=request)
        text = parse_qs(urlsplit(url).query)["text"][0]
        self.assertIn("Campaign: Bureau Campaign & Test? テスト", text)
        self.assertIn("%", urlsplit(url).query)
        self.assertNotIn("None", unquote(urlsplit(url).query))

    def test_missing_campaign_row_omits_campaign_line(self):
        ad = _script_ad()
        request = _attach_session(self.factory.get("/"))
        store_last_click_attribution(request, ad_id=ad.pk, campaign_id="999999")
        url = get_bureau_whatsapp_url(_STORED_WA, request=request)
        text = parse_qs(urlsplit(url).query)["text"][0]
        self.assertIn("NityaDharma Ad", text)
        self.assertNotIn("Campaign:", text)

    def test_detail_page_no_attribution_uses_track_whatsapp_bare(self):
        resp = self.client.get(
            reverse("bureaus:bureau_detail", kwargs={"public_id": self.bureau.public_id})
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode("utf-8", errors="ignore")
        track = reverse("ads_analytics:track_whatsapp")
        self.assertIn(track, body)
        # Django |urlencode keeps "/" safe by default → https%3A//wa.me/9123456792
        self.assertIn(f"wa.me/{_STORED_WA}", body)
        self.assertNotIn("text%3D", body)
        self.assertIn(_STORED_WA, body)

    def test_detail_page_with_attribution_embeds_prefill_in_redirect(self):
        ad = _script_ad()
        session = self.client.session
        session[SESSION_KEY] = {"ad_id": ad.pk}
        session.save()
        resp = self.client.get(
            reverse("bureaus:bureau_detail", kwargs={"public_id": self.bureau.public_id})
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode("utf-8", errors="ignore")
        self.assertIn(reverse("ads_analytics:track_whatsapp"), body)
        self.assertIn("NityaDharma", body)
        self.assertIn("text%3D", body)

    def test_track_whatsapp_intent_without_new_adclick(self):
        campaign = Campaign.objects.create(
            name="Bureau Intent Campaign",
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
        wa = get_bureau_whatsapp_url(_STORED_WA, request=request)

        resp = self.client.get(
            reverse("ads_analytics:track_whatsapp"),
            {"redirect": wa},
        )
        self.assertEqual(resp.status_code, 302)
        location = resp["Location"]
        self.assertTrue(location.startswith("https://wa.me/"))
        self.assertIn(_STORED_WA, urlparse(location).path)
        self.assertIn("text=", location)
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
        self.assertEqual(
            self.client.session.get(SESSION_KEY),
            {"ad_id": ad.pk, "campaign_id": str(campaign.pk)},
        )

    def test_unsafe_track_whatsapp_redirect_rejected(self):
        resp = self.client.get(
            reverse("ads_analytics:track_whatsapp"),
            {"redirect": "https://evil.example/phish"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "/")
