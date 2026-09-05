"""Public-profile WhatsApp ad-attributed prefill parity with listing card.

Reuses released attribution getter + get_whatsapp_url path via
ad_aware_pandit_contact_info. No new builders, migrations, or CRM.
"""

from __future__ import annotations

from html import unescape
from urllib.parse import parse_qs, unquote, urlsplit

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ads.models import Advertisement, Campaign
from ads_analytics.services.attribution_bridge import SESSION_KEY
from profiles.models import PanditProfile

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

HERO_WA_BTN = 'class="btn btn-success btn-lg whatsapp-btn-hero"'
SIDEBAR_WA_BTN = 'class="btn w-100 mb-3 whatsapp-btn"'


def _approved_pandit(*, email, **profile_fields):
    user = get_user_model().objects.create_user(
        email=email,
        password="ParityPanditPass123!",
        first_name="Parity",
        last_name="Pandit",
        role="pandit",
        status="active",
        is_active=True,
        email_verified=True,
    )
    profile, _ = PanditProfile.objects.get_or_create(user=user)
    profile.is_profile_approved = True
    profile.enable_call = True
    profile.allow_call = True
    profile.enable_whatsapp = True
    profile.allow_whatsapp = True
    for key, value in profile_fields.items():
        setattr(profile, key, value)
    profile.save()
    return user, profile


def _script_ad(**kwargs) -> Advertisement:
    defaults = {
        "name": "Parity Prefill Ad",
        "placement": "top",
        "slots": ["top"],
        "ad_type": Advertisement.AD_TYPE_SCRIPT,
        "script_code": "<div>ad</div>",
        "is_active": True,
        "redirect_url": "https://example.com/dest",
    }
    defaults.update(kwargs)
    return Advertisement.objects.create(**defaults)


def _extract_track_redirects(html: str) -> list[str]:
    """Collect decoded redirect= values from track_whatsapp hrefs."""
    needle = reverse("ads_analytics:track_whatsapp")
    redirects = []
    search_from = 0
    while True:
        idx = html.find(needle, search_from)
        if idx < 0:
            break
        href_start = html.rfind("href=", 0, idx)
        if href_start < 0:
            search_from = idx + len(needle)
            continue
        quote = html[href_start + 5]
        if quote not in ('"', "'"):
            search_from = idx + len(needle)
            continue
        href_end = html.find(quote, href_start + 6)
        if href_end < 0:
            break
        href = unescape(html[href_start + 6 : href_end])
        parsed = urlsplit(href)
        qs = parse_qs(parsed.query)
        if "redirect" in qs:
            redirects.append(qs["redirect"][0])
        search_from = href_end
    return redirects


class PublicProfileWhatsappAdPrefillParityTests(TestCase):
    def setUp(self):
        self.client = Client(HTTP_USER_AGENT=_BROWSER_UA)
        self.user, self.profile = _approved_pandit(
            email="profile-wa-parity@example.com",
            call_mobile_number="9123456811",
            whatsapp_mobile_number="9123456812",
            primary_mobile_number=None,
            phone_number=None,
        )

    def _get_public(self):
        return self.client.get(
            reverse(
                "profiles:profile_public_by_id",
                kwargs={"public_id": self.profile.public_id},
            )
        )

    def _seed_attribution(self, *, ad_id: int, campaign_id=None):
        session = self.client.session
        payload = {"ad_id": int(ad_id)}
        if campaign_id is not None:
            payload["campaign_id"] = str(campaign_id)
        session[SESSION_KEY] = payload
        session.save()

    def test_no_attribution_uses_generic_greeting_on_both_ctas(self):
        resp = self._get_public()
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode("utf-8")
        self.assertIn(HERO_WA_BTN, content)
        self.assertIn(SIDEBAR_WA_BTN, content)
        self.assertIn("/track/ad/whatsapp/", content)
        # pandit_id preserved on track wrapper
        self.assertIn(f"pandit_id={self.user.pk}", content)

        redirects = _extract_track_redirects(content)
        self.assertEqual(len(redirects), 2)
        for wa in redirects:
            self.assertTrue(wa.startswith("https://wa.me/9123456812"))
            text = parse_qs(urlsplit(wa).query)["text"][0]
            self.assertIn("I found your profile on Nitya Dharma", text)
            self.assertNotIn("NityaDharma Ad", text)
            self.assertNotIn("Campaign:", text)
            self.assertNotIn("Location:", text)
            self.assertNotIn("Price:", text)

        # Call CTA unchanged (raw tel from template fields)
        self.assertIn('href="tel:9123456811"', content)
        # Session untouched
        self.assertIsNone(self.client.session.get(SESSION_KEY))

    def test_ad_only_prefill_both_ctas_no_campaign_location_price(self):
        ad = _script_ad()
        self._seed_attribution(ad_id=ad.pk)
        before = dict(self.client.session.get(SESSION_KEY))

        resp = self._get_public()
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode("utf-8")
        redirects = _extract_track_redirects(content)
        self.assertEqual(len(redirects), 2)
        for wa in redirects:
            text = parse_qs(urlsplit(wa).query)["text"][0]
            self.assertIn("NityaDharma Ad", text)
            self.assertNotIn("Campaign:", text)
            self.assertNotIn("Location:", text)
            self.assertNotIn("Price:", text)
            self.assertNotIn("None", text)

        self.assertEqual(self.client.session.get(SESSION_KEY), before)
        self.assertIn(f"pandit_id={self.user.pk}", content)
        self.assertIn('href="tel:9123456811"', content)

    def test_ad_plus_campaign_prefill_both_ctas(self):
        campaign = Campaign.objects.create(
            name="Profile Parity Camp",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(campaign=campaign)
        self._seed_attribution(ad_id=ad.pk, campaign_id=campaign.pk)
        before = dict(self.client.session.get(SESSION_KEY))

        resp = self._get_public()
        content = resp.content.decode("utf-8")
        redirects = _extract_track_redirects(content)
        self.assertEqual(len(redirects), 2)
        for wa in redirects:
            text = parse_qs(urlsplit(wa).query)["text"][0]
            self.assertIn("NityaDharma Ad", text)
            self.assertIn("Campaign: Profile Parity Camp", text)
            self.assertNotIn("Location:", text)
            self.assertNotIn("Price:", text)

        self.assertEqual(self.client.session.get(SESSION_KEY), before)

    def test_malformed_attribution_falls_back_to_generic(self):
        session = self.client.session
        session[SESSION_KEY] = {"ad_id": "not-an-int"}
        session.save()

        resp = self._get_public()
        redirects = _extract_track_redirects(resp.content.decode("utf-8"))
        self.assertEqual(len(redirects), 2)
        for wa in redirects:
            text = parse_qs(urlsplit(wa).query)["text"][0]
            self.assertIn("I found your profile on Nitya Dharma", text)
            self.assertNotIn("NityaDharma Ad", text)

    def test_stale_campaign_omits_campaign_line(self):
        ad = _script_ad()
        self._seed_attribution(ad_id=ad.pk, campaign_id="999999999")

        resp = self._get_public()
        redirects = _extract_track_redirects(resp.content.decode("utf-8"))
        self.assertEqual(len(redirects), 2)
        for wa in redirects:
            text = parse_qs(urlsplit(wa).query)["text"][0]
            self.assertIn("NityaDharma Ad", text)
            self.assertNotIn("Campaign:", text)
            self.assertNotIn("999999999", unquote(urlsplit(wa).query))

    def test_text_param_is_url_encoded(self):
        ad = _script_ad()
        self._seed_attribution(ad_id=ad.pk)
        resp = self._get_public()
        redirects = _extract_track_redirects(resp.content.decode("utf-8"))
        self.assertTrue(redirects)
        raw_href = resp.content.decode("utf-8")
        # Encoded spaces expected in the track redirect query embedding
        self.assertIn("text%3D", raw_href.replace("&amp;", "&"))
        text = parse_qs(urlsplit(redirects[0]).query)["text"][0]
        self.assertIn("\n", text)
