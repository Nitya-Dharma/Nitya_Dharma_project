"""Batch E: direct WhatsApp AdClick → existing AdConversionIntent + AdLead.

Reuses record_whatsapp_contact_from_session after store_last_click_attribution.
No new models, session keys, endpoints, or migrations.
"""

from __future__ import annotations

from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.test import Client, TestCase
from django.urls import reverse

from ads.models import Advertisement, Campaign
from ads_analytics.models import AdClick, AdConversionIntent, AdLead
from ads_analytics.services.attribution_bridge import SESSION_KEY

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_WA = "https://wa.me/919876543210"
_WA_API = "https://api.whatsapp.com/send?phone=919876543210"
_SITE = "https://advertiser.example/landing"
_INTERNAL = "/pandits/some-profile/"


def _image_ad(**kwargs) -> Advertisement:
    defaults = {
        "name": "Direct WA Intent Ad",
        "placement": "top",
        "slots": ["top"],
        "ad_type": Advertisement.AD_TYPE_IMAGE,
        "is_active": True,
        "redirect_url": _WA,
    }
    defaults.update(kwargs)
    return Advertisement.objects.create(**defaults)


class DirectWhatsappClickContactIntentTests(TestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.client = Client(HTTP_USER_AGENT=_BROWSER_UA)

    def _click(self, ad, params=None):
        url = reverse("ads_analytics:track_click", kwargs={"ad_id": ad.pk})
        return self.client.get(url, params or {"placement": "top"})

    def test_direct_whatsapp_click_creates_other_conversion_and_lead(self):
        ad = _image_ad(redirect_url=_WA)
        resp = self._click(ad, {"placement": "top"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(AdClick.objects.filter(ad_id=ad.pk).count(), 1)
        conversion = AdConversionIntent.objects.get()
        self.assertEqual(conversion.ad_id, ad.pk)
        self.assertEqual(conversion.conversion_type, AdConversionIntent.CONVERSION_OTHER)
        lead = AdLead.objects.get()
        self.assertEqual(lead.advertisement_id, ad.pk)
        self.assertEqual(lead.source, AdLead.SOURCE_WHATSAPP_CTA)
        self.assertEqual(lead.source_conversion_id, conversion.pk)
        self.assertEqual(lead.status, AdLead.STATUS_NEW)

    def test_campaign_id_snapshotted_on_conversion_and_lead(self):
        campaign = Campaign.objects.create(
            name="Direct WA Camp",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _image_ad(redirect_url=_WA, campaign=campaign)
        self._click(ad, {"placement": "top"})
        conversion = AdConversionIntent.objects.get()
        lead = AdLead.objects.get()
        self.assertEqual(conversion.campaign_id, str(campaign.pk))
        self.assertEqual(lead.campaign_id, str(campaign.pk))
        self.assertEqual(
            self.client.session.get(SESSION_KEY),
            {"ad_id": ad.pk, "campaign_id": str(campaign.pk)},
        )

    def test_prefill_still_applied_on_direct_whatsapp_click(self):
        ad = _image_ad(redirect_url=_WA)
        resp = self._click(ad, {"placement": "top"})
        location = resp["Location"]
        self.assertTrue(location.startswith("https://wa.me/"))
        qs = parse_qs(urlsplit(location).query)
        self.assertIn("text", qs)
        self.assertIn("NityaDharma Ad", qs["text"][0])
        self.assertEqual(AdLead.objects.count(), 1)

    def test_api_whatsapp_com_also_creates_lead(self):
        ad = _image_ad(redirect_url=_WA_API)
        resp = self._click(ad, {"placement": "top"})
        self.assertEqual(urlsplit(resp["Location"]).netloc, "api.whatsapp.com")
        self.assertEqual(AdConversionIntent.objects.count(), 1)
        self.assertEqual(AdLead.objects.count(), 1)

    def test_non_whatsapp_external_creates_no_conversion_or_lead(self):
        ad = _image_ad(redirect_url=_SITE)
        resp = self._click(ad, {"redirect": _SITE, "placement": "top"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], _SITE)
        self.assertEqual(AdClick.objects.filter(ad_id=ad.pk).count(), 1)
        self.assertEqual(AdConversionIntent.objects.count(), 0)
        self.assertEqual(AdLead.objects.count(), 0)

    def test_internal_destination_creates_no_whatsapp_lead(self):
        ad = _image_ad(redirect_url=_SITE)
        resp = self._click(ad, {"redirect": _INTERNAL, "placement": "top"})
        self.assertEqual(resp["Location"], _INTERNAL)
        self.assertEqual(AdConversionIntent.objects.count(), 0)
        self.assertEqual(AdLead.objects.count(), 0)

    def test_unsafe_query_falls_back_to_stored_whatsapp_and_creates_lead(self):
        ad = _image_ad(redirect_url=_WA)
        resp = self._click(
            ad,
            {"redirect": "https://evil.example/phish", "placement": "top"},
        )
        self.assertNotIn("evil.example", resp["Location"])
        self.assertTrue(resp["Location"].startswith("https://wa.me/"))
        self.assertEqual(AdLead.objects.count(), 1)
        self.assertEqual(AdLead.objects.get().advertisement_id, ad.pk)

    def test_unsafe_query_with_non_wa_fallback_creates_no_lead(self):
        ad = _image_ad(redirect_url=_SITE)
        resp = self._click(
            ad,
            {"redirect": "https://evil.example/phish", "placement": "top"},
        )
        self.assertEqual(resp["Location"], _SITE)
        self.assertEqual(AdConversionIntent.objects.count(), 0)
        self.assertEqual(AdLead.objects.count(), 0)

    def test_word_whatsapp_in_name_or_path_does_not_create_lead(self):
        ad = _image_ad(
            name="WhatsApp Promo Banner",
            redirect_url="https://advertiser.example/whatsapp-landing",
        )
        resp = self._click(ad, {"placement": "top"})
        self.assertEqual(resp["Location"], "https://advertiser.example/whatsapp-landing")
        self.assertEqual(AdConversionIntent.objects.count(), 0)
        self.assertEqual(AdLead.objects.count(), 0)

    def test_tracking_skip_creates_no_click_session_conversion_or_lead(self):
        ad = _image_ad(redirect_url=_WA)
        with patch(
            "ads_analytics.views.should_skip_tracking",
            return_value=(True, "bot"),
        ):
            resp = self._click(ad, {"placement": "top"})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].startswith("https://wa.me/"))
        self.assertEqual(AdClick.objects.count(), 0)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertEqual(AdConversionIntent.objects.count(), 0)
        self.assertEqual(AdLead.objects.count(), 0)

    def test_last_touch_second_whatsapp_ad_gets_new_lead(self):
        ad_a = _image_ad(name="Ad A", redirect_url=_WA)
        ad_b = _image_ad(name="Ad B", redirect_url=_WA)
        self._click(ad_a, {"placement": "top"})
        self._click(ad_b, {"placement": "top"})
        self.assertEqual(AdClick.objects.count(), 2)
        self.assertEqual(AdConversionIntent.objects.count(), 2)
        self.assertEqual(AdLead.objects.count(), 2)
        last_lead = AdLead.objects.order_by("-id").first()
        self.assertEqual(last_lead.advertisement_id, ad_b.pk)
        self.assertEqual(
            self.client.session.get(SESSION_KEY),
            {"ad_id": ad_b.pk},
        )

    def test_repeat_direct_whatsapp_click_matches_existing_cta_semantics(self):
        """Same as track_whatsapp: each invocation may create another conversion+lead."""
        ad = _image_ad(redirect_url=_WA)
        self._click(ad, {"placement": "top"})
        self._click(ad, {"placement": "top"})
        self.assertEqual(AdClick.objects.filter(ad_id=ad.pk).count(), 2)
        self.assertEqual(AdConversionIntent.objects.count(), 2)
        self.assertEqual(AdLead.objects.count(), 2)

    def test_track_whatsapp_without_prior_click_still_creates_no_lead(self):
        resp = self.client.get(
            reverse("ads_analytics:track_whatsapp"),
            {"redirect": _WA},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], _WA)
        self.assertEqual(AdConversionIntent.objects.count(), 0)
        self.assertEqual(AdLead.objects.count(), 0)
