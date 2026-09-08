"""Focused tests for track_click query-string open-redirect hardening.

Query-string redirect= is attacker-controlled and must stay same-origin /
relative. Stored Advertisement.redirect_url remains the trusted Super Admin
advertiser destination (including external URLs). Does not cover WhatsApp,
Lead, Campaign/AdSet, or script-ad rendering.
"""

from __future__ import annotations

from django.test import Client, TestCase
from django.urls import reverse

from ads.models import Advertisement
from ads_analytics.models import AdClick
from ads_analytics.services.attribution_bridge import SESSION_KEY

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_TRUSTED_EXTERNAL = "https://advertiser.example/landing"


def _image_ad(**kwargs) -> Advertisement:
    defaults = {
        "name": "Click Redirect Ad",
        "placement": "top",
        "slots": ["top"],
        "ad_type": Advertisement.AD_TYPE_IMAGE,
        "is_active": True,
        "redirect_url": _TRUSTED_EXTERNAL,
    }
    defaults.update(kwargs)
    return Advertisement.objects.create(**defaults)


class AdClickOpenRedirectTests(TestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.client = Client(HTTP_USER_AGENT=_BROWSER_UA)

    def _click(self, ad, params=None, path_query=""):
        url = reverse("ads_analytics:track_click", kwargs={"ad_id": ad.pk})
        if path_query:
            return self.client.get(url + path_query)
        return self.client.get(url, params or {})

    def test_relative_internal_redirect_is_accepted(self):
        ad = _image_ad()
        resp = self._click(ad, {"redirect": "/some/internal/path", "placement": "top"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "/some/internal/path")

    def test_same_origin_absolute_redirect_is_accepted(self):
        ad = _image_ad()
        resp = self._click(
            ad,
            {"redirect": "http://testserver/safe-path", "placement": "top"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "http://testserver/safe-path")

    def test_external_attacker_url_is_rejected(self):
        ad = _image_ad()
        resp = self._click(ad, {"redirect": "https://evil.example/", "placement": "top"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], _TRUSTED_EXTERNAL)
        self.assertNotIn("evil.example", resp["Location"])

    def test_http_external_attacker_url_is_rejected(self):
        ad = _image_ad()
        resp = self._click(ad, {"redirect": "http://evil.example/", "placement": "top"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], _TRUSTED_EXTERNAL)

    def test_protocol_relative_attacker_url_is_rejected(self):
        ad = _image_ad()
        resp = self._click(ad, {"redirect": "//evil.example/", "placement": "top"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], _TRUSTED_EXTERNAL)
        self.assertFalse(resp["Location"].startswith("//"))

    def test_triple_slash_protocol_relative_is_rejected(self):
        ad = _image_ad()
        resp = self._click(ad, {"redirect": "///evil.example/", "placement": "top"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], _TRUSTED_EXTERNAL)

    def test_userinfo_external_url_is_rejected(self):
        ad = _image_ad()
        resp = self._click(
            ad,
            {
                "redirect": "https://trusted-looking.example@evil.example/",
                "placement": "top",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], _TRUSTED_EXTERNAL)
        self.assertNotIn("evil.example", resp["Location"])

    def test_userinfo_only_host_is_rejected(self):
        ad = _image_ad()
        resp = self._click(
            ad,
            {"redirect": "https://user@evil.example/", "placement": "top"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], _TRUSTED_EXTERNAL)

    def test_encoded_protocol_relative_cannot_bypass(self):
        ad = _image_ad()
        resp = self._click(ad, path_query="?redirect=%2F%2Fevil.example%2F&placement=top")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], _TRUSTED_EXTERNAL)
        self.assertNotIn("evil.example", resp["Location"])

    def test_backslash_confusion_cannot_bypass(self):
        ad = _image_ad()
        resp = self._click(
            ad,
            {"redirect": "https://evil.example\\@testserver", "placement": "top"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn("evil.example", resp["Location"])

    def test_no_query_uses_stored_external_advertiser_url(self):
        ad = _image_ad(redirect_url=_TRUSTED_EXTERNAL)
        resp = self._click(ad, {"placement": "top"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], _TRUSTED_EXTERNAL)

    def test_no_query_and_no_stored_url_falls_back_to_root(self):
        ad = _image_ad(redirect_url="")
        resp = self._click(ad, {"placement": "top"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "/")

    def test_unsafe_query_falls_back_to_stored_external_url(self):
        ad = _image_ad(redirect_url=_TRUSTED_EXTERNAL)
        resp = self._click(
            ad,
            {"redirect": "https://evil.example/phish", "placement": "top"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], _TRUSTED_EXTERNAL)

    def test_unsafe_query_without_stored_url_falls_back_to_root(self):
        ad = _image_ad(redirect_url="")
        resp = self._click(ad, {"redirect": "https://evil.example/", "placement": "top"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "/")

    def test_click_tracking_still_occurs_for_unsafe_query(self):
        ad = _image_ad()
        resp = self._click(ad, {"redirect": "https://evil.example/", "placement": "top"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(AdClick.objects.filter(ad_id=ad.pk).count(), 1)
        click = AdClick.objects.get(ad_id=ad.pk)
        self.assertEqual(click.placement_position, "top")
        self.assertEqual(
            self.client.session.get(SESSION_KEY),
            {"ad_id": ad.pk},
        )

    def test_legacy_query_matching_stored_external_still_lands_on_stored(self):
        """Templates currently pass stored URL via redirect=; fallback preserves it."""
        ad = _image_ad(redirect_url=_TRUSTED_EXTERNAL)
        resp = self._click(
            ad,
            {"redirect": _TRUSTED_EXTERNAL, "placement": "top"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], _TRUSTED_EXTERNAL)
        self.assertEqual(AdClick.objects.filter(ad_id=ad.pk).count(), 1)
