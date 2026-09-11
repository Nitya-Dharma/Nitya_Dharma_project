"""Batch A: banner AdClick → allowlisted WhatsApp gets contextual text=.

Focused regression only. No model/migration/serving/CTA template changes.
"""

from __future__ import annotations

from urllib.parse import parse_qs, unquote, urlsplit

from django.test import Client, TestCase
from django.urls import reverse

from ads.models import Advertisement, Campaign
from ads_analytics.models import AdClick
from ads_analytics.services.attribution_bridge import SESSION_KEY
from profiles.whatsapp_ad_prefill import build_ad_attributed_whatsapp_message

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_WA = "https://wa.me/919876543210"
_WA_WITH_PARAMS = "https://wa.me/919876543210?foo=1&text=old&bar=2"
_SITE = "https://advertiser.example/landing"
_INTERNAL = "/pandits/some-profile/"


def _image_ad(**kwargs) -> Advertisement:
    defaults = {
        "name": "Banner WA Prefill Ad",
        "placement": "top",
        "slots": ["top"],
        "ad_type": Advertisement.AD_TYPE_IMAGE,
        "is_active": True,
        "redirect_url": _WA,
    }
    defaults.update(kwargs)
    return Advertisement.objects.create(**defaults)


class BannerWhatsappClickPrefillTests(TestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.client = Client(HTTP_USER_AGENT=_BROWSER_UA)

    def _click(self, ad, params=None):
        url = reverse("ads_analytics:track_click", kwargs={"ad_id": ad.pk})
        return self.client.get(url, params or {"placement": "top"})

    def test_whatsapp_destination_gets_contextual_text(self):
        ad = _image_ad(redirect_url=_WA)
        resp = self._click(ad, {"redirect": _WA, "placement": "top"})
        self.assertEqual(resp.status_code, 302)
        location = resp["Location"]
        parsed = urlsplit(location)
        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.netloc, "wa.me")
        qs = parse_qs(parsed.query)
        self.assertIn("text", qs)
        text = qs["text"][0]
        self.assertIn("NityaDharma Ad", text)
        self.assertIn("interested in this advertisement", text)
        self.assertNotIn("Campaign:", text)
        self.assertEqual(AdClick.objects.filter(ad_id=ad.pk).count(), 1)
        self.assertEqual(
            self.client.session.get(SESSION_KEY),
            {"ad_id": ad.pk},
        )

    def test_campaign_name_included_and_encoded(self):
        campaign = Campaign.objects.create(
            name="BR Dream Homes & Garudadri? テスト",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _image_ad(redirect_url=_WA, campaign=campaign)
        resp = self._click(ad, {"placement": "top"})
        self.assertEqual(resp.status_code, 302)
        location = resp["Location"]
        qs = parse_qs(urlsplit(location).query)
        text = qs["text"][0]
        self.assertIn("Campaign: BR Dream Homes & Garudadri? テスト", text)
        self.assertIn("%", urlsplit(location).query)
        self.assertNotIn("None", unquote(urlsplit(location).query))
        self.assertEqual(AdClick.objects.filter(ad_id=ad.pk).count(), 1)
        self.assertEqual(
            self.client.session.get(SESSION_KEY),
            {"ad_id": ad.pk, "campaign_id": str(campaign.pk)},
        )

    def test_whatsapp_without_campaign_omits_campaign_line(self):
        ad = _image_ad(redirect_url=_WA, campaign=None)
        resp = self._click(ad, {"placement": "top"})
        text = parse_qs(urlsplit(resp["Location"]).query)["text"][0]
        self.assertNotIn("Campaign:", text)
        self.assertNotIn("None", text)

    def test_non_whatsapp_external_unchanged(self):
        ad = _image_ad(redirect_url=_SITE)
        resp = self._click(ad, {"redirect": _SITE, "placement": "top"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], _SITE)
        self.assertNotIn("text=", resp["Location"])
        self.assertEqual(AdClick.objects.filter(ad_id=ad.pk).count(), 1)

    def test_internal_destination_unchanged(self):
        ad = _image_ad(redirect_url=_SITE)
        resp = self._click(ad, {"redirect": _INTERNAL, "placement": "top"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], _INTERNAL)
        self.assertNotIn("text=", resp["Location"])

    def test_preserves_existing_query_params_and_replaces_text(self):
        ad = _image_ad(redirect_url=_WA_WITH_PARAMS)
        resp = self._click(ad, {"placement": "top"})
        qs = parse_qs(urlsplit(resp["Location"]).query)
        self.assertEqual(qs.get("foo"), ["1"])
        self.assertEqual(qs.get("bar"), ["2"])
        self.assertEqual(len(qs.get("text", [])), 1)
        self.assertIn("NityaDharma Ad", qs["text"][0])
        self.assertNotEqual(qs["text"][0], "old")

    def test_unsafe_query_falls_back_to_stored_whatsapp_and_enriches(self):
        ad = _image_ad(redirect_url=_WA)
        resp = self._click(
            ad,
            {"redirect": "https://evil.example/phish", "placement": "top"},
        )
        self.assertEqual(resp.status_code, 302)
        location = resp["Location"]
        self.assertNotIn("evil.example", location)
        self.assertTrue(location.startswith("https://wa.me/"))
        self.assertIn("text=", location)
        self.assertEqual(AdClick.objects.filter(ad_id=ad.pk).count(), 1)

    def test_api_whatsapp_com_also_enriched(self):
        wa_api = "https://api.whatsapp.com/send?phone=919876543210"
        ad = _image_ad(redirect_url=wa_api)
        resp = self._click(ad, {"placement": "top"})
        location = resp["Location"]
        parsed = urlsplit(location)
        self.assertEqual(parsed.netloc, "api.whatsapp.com")
        qs = parse_qs(parsed.query)
        self.assertEqual(qs.get("phone"), ["919876543210"])
        self.assertIn("NityaDharma Ad", qs["text"][0])

    def test_explicit_ids_builder_matches_session_builder_content(self):
        campaign = Campaign.objects.create(
            name="Shared Campaign",
            status=Campaign.STATUS_ACTIVE,
        )
        from_ids = build_ad_attributed_whatsapp_message(
            ad_id=99,
            campaign_id=str(campaign.pk),
        )
        self.assertIsNotNone(from_ids)
        self.assertIn("Campaign: Shared Campaign", from_ids)
        self.assertIn("NityaDharma Ad", from_ids)
