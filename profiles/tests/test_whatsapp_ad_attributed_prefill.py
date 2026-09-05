"""Focused tests for WhatsApp ad-attributed contextual prefill.

Covers URL encoding, optional campaign context, query preservation,
session read-only access, allowlist + conversion regression.
No Lead/CRM, migrations, billing, or serving changes.
"""

from __future__ import annotations

from urllib.parse import parse_qs, unquote, urlsplit

from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from ads.models import Advertisement, Campaign
from ads_analytics.models import AdConversionIntent
from ads_analytics.services.attribution_bridge import (
    SESSION_KEY,
    get_last_click_attribution,
    store_last_click_attribution,
)
from ads_analytics.views import _is_allowed_whatsapp_redirect
from profiles.models import PanditProfile
from profiles.services_contact import get_whatsapp_url
from profiles.whatsapp_ad_prefill import (
    apply_whatsapp_text_param,
    build_ad_attributed_whatsapp_message,
)

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _attach_session(request):
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    request.session.save()
    return request


def _script_ad(**kwargs) -> Advertisement:
    defaults = {
        "name": "Prefill Ad",
        "placement": "top",
        "slots": ["top"],
        "ad_type": Advertisement.AD_TYPE_SCRIPT,
        "script_code": "<div>ad</div>",
        "is_active": True,
        "redirect_url": "https://example.com/dest",
    }
    defaults.update(kwargs)
    return Advertisement.objects.create(**defaults)


class ApplyWhatsappTextParamTests(TestCase):
    def test_sets_text_on_bare_wa_me(self):
        url = apply_whatsapp_text_param("https://wa.me/919876543210", "Hello world")
        parsed = urlsplit(url)
        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.netloc, "wa.me")
        self.assertEqual(parsed.path, "/919876543210")
        qs = parse_qs(parsed.query)
        self.assertEqual(qs["text"], ["Hello world"])

    def test_encodes_spaces_ampersands_unicode_and_newlines(self):
        msg = "Hello & welcome?\nनमस्ते"
        url = apply_whatsapp_text_param("https://wa.me/919876543210", msg)
        qs = parse_qs(urlsplit(url).query)
        self.assertEqual(qs["text"][0], msg)
        self.assertIn("%", urlsplit(url).query)
        self.assertNotIn("None", unquote(urlsplit(url).query))

    def test_preserves_existing_non_text_params_and_replaces_text(self):
        base = "https://wa.me/919876543210?foo=1&text=old&bar=2"
        url = apply_whatsapp_text_param(base, "new message")
        qs = parse_qs(urlsplit(url).query)
        self.assertEqual(qs["foo"], ["1"])
        self.assertEqual(qs["bar"], ["2"])
        self.assertEqual(qs["text"], ["new message"])
        self.assertEqual(len(qs["text"]), 1)


class AdAttributedMessageTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_no_session_returns_none(self):
        request = _attach_session(self.factory.get("/"))
        self.assertIsNone(build_ad_attributed_whatsapp_message(request))

    def test_ad_only_message_has_no_none_or_blank_labels(self):
        request = _attach_session(self.factory.get("/"))
        store_last_click_attribution(request, ad_id=42)
        msg = build_ad_attributed_whatsapp_message(request)
        self.assertIsNotNone(msg)
        self.assertIn("NityaDharma Ad", msg)
        self.assertIn("interested in this advertisement", msg)
        self.assertNotIn("Campaign:", msg)
        self.assertNotIn("Location:", msg)
        self.assertNotIn("Price:", msg)
        self.assertNotIn("None", msg)
        self.assertNotIn("null", msg)
        self.assertNotIn("undefined", msg)
        self.assertNotIn("42", msg)

    def test_campaign_line_when_session_campaign_resolves(self):
        campaign = Campaign.objects.create(
            name="Spring Puja Promo",
            status=Campaign.STATUS_ACTIVE,
        )
        request = _attach_session(self.factory.get("/"))
        store_last_click_attribution(
            request, ad_id=7, campaign_id=str(campaign.pk)
        )
        msg = build_ad_attributed_whatsapp_message(request)
        self.assertIn("Campaign: Spring Puja Promo", msg)
        self.assertNotIn(str(campaign.pk), msg.split("Campaign:")[0])

    def test_missing_campaign_row_omits_campaign_line(self):
        request = _attach_session(self.factory.get("/"))
        store_last_click_attribution(request, ad_id=7, campaign_id="999999")
        msg = build_ad_attributed_whatsapp_message(request)
        self.assertIsNotNone(msg)
        self.assertNotIn("Campaign:", msg)
        self.assertNotIn("None", msg)

    def test_getter_does_not_mutate_session(self):
        request = _attach_session(self.factory.get("/"))
        store_last_click_attribution(request, ad_id=11, campaign_id="22")
        before = dict(request.session.get(SESSION_KEY))
        modified_before = request.session.modified
        request.session.modified = False
        payload = get_last_click_attribution(request)
        build_ad_attributed_whatsapp_message(request)
        self.assertEqual(payload, {"ad_id": 11, "campaign_id": "22"})
        self.assertEqual(request.session.get(SESSION_KEY), before)
        self.assertFalse(request.session.modified)
        # restore expectation that store set modified earlier is orthogonal
        self.assertIs(modified_before, True)


class GetWhatsappUrlPrefillTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="prefill-pandit@example.com",
            password="PrefillPass123!",
            username="prefill_pandit",
            role="pandit",
            status="active",
            is_active=True,
            email_verified=True,
        )
        self.profile, _ = PanditProfile.objects.get_or_create(user=self.user)
        self.profile.enable_whatsapp = True
        self.profile.allow_whatsapp = True
        self.profile.whatsapp_mobile_number = "919876543210"
        self.profile.save()

    def test_non_ad_flow_keeps_generic_greeting(self):
        request = _attach_session(self.factory.get("/"))
        url = get_whatsapp_url(self.profile, request=request)
        self.assertIsNotNone(url)
        text = parse_qs(urlsplit(url).query)["text"][0]
        self.assertIn("I found your profile on Nitya Dharma", text)
        self.assertNotIn("NityaDharma Ad", text)

    def test_ad_attributed_prefill_when_session_present(self):
        campaign = Campaign.objects.create(
            name="Listing Camp",
            status=Campaign.STATUS_ACTIVE,
        )
        request = _attach_session(self.factory.get("/"))
        store_last_click_attribution(
            request, ad_id=3, campaign_id=str(campaign.pk)
        )
        url = get_whatsapp_url(self.profile, request=request)
        text = parse_qs(urlsplit(url).query)["text"][0]
        self.assertIn("NityaDharma Ad", text)
        self.assertIn("Campaign: Listing Camp", text)
        self.assertTrue(_is_allowed_whatsapp_redirect(url))

    def test_explicit_message_wins_over_attribution(self):
        request = _attach_session(self.factory.get("/"))
        store_last_click_attribution(request, ad_id=3, campaign_id="1")
        url = get_whatsapp_url(
            self.profile, message="Custom only", request=request
        )
        text = parse_qs(urlsplit(url).query)["text"][0]
        self.assertEqual(text, "Custom only")


class TrackWhatsappRegressionTests(TestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.client = Client(HTTP_USER_AGENT=_BROWSER_UA)

    def test_allowlist_rejects_unsafe_hosts(self):
        self.assertFalse(_is_allowed_whatsapp_redirect("http://wa.me/1"))
        self.assertFalse(
            _is_allowed_whatsapp_redirect("https://evil.example/wa")
        )
        self.assertFalse(_is_allowed_whatsapp_redirect("javascript:alert(1)"))

    def test_track_whatsapp_still_records_other_with_campaign_id(self):
        campaign = Campaign.objects.create(
            name="Track Camp",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(name="Track linked", campaign=campaign)
        click_url = reverse("ads_analytics:track_click", kwargs={"ad_id": ad.pk})
        self.client.get(
            click_url,
            {"redirect": "https://example.com/dest", "placement": "top"},
        )
        self.assertEqual(
            self.client.session.get(SESSION_KEY),
            {"ad_id": ad.pk, "campaign_id": str(campaign.pk)},
        )

        msg = "NityaDharma Ad\n\nHello! I'm interested in this advertisement"
        wa = apply_whatsapp_text_param("https://wa.me/919999999999", msg)
        self.assertTrue(_is_allowed_whatsapp_redirect(wa))

        track_url = reverse("ads_analytics:track_whatsapp")
        resp = self.client.get(track_url, {"redirect": wa, "pandit_id": "0"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], wa)

        intent = AdConversionIntent.objects.get()
        self.assertEqual(intent.conversion_type, AdConversionIntent.CONVERSION_OTHER)
        self.assertEqual(intent.campaign_id, str(campaign.pk))
        self.assertEqual(intent.ad_id, ad.pk)
        # WhatsApp path must not clear session
        self.assertEqual(
            self.client.session.get(SESSION_KEY),
            {"ad_id": ad.pk, "campaign_id": str(campaign.pk)},
        )
