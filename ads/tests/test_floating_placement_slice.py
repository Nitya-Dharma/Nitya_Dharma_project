"""Floating placement on existing Advertisement (presentation-only slice).

Does not add models, migrations, tracking endpoints, or a second ads engine.
"""

from datetime import timedelta
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from ads.constants import AD_POSITION_LABELS
from ads.context_processors import active_ads
from ads.forms import AdvertisementForm
from ads.models import Advertisement
from ads_analytics.models import AdClick, AdImpression

User = get_user_model()

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_EXISTING_PLACEMENTS = (
    "top",
    "sidebar",
    "footer",
    "in_content",
    "dashboard_top",
    "dashboard_sidebar",
)
_BASE_HTML = Path(__file__).resolve().parents[2] / "templates" / "base.html"


def _script_ad(**kwargs):
    defaults = {
        "name": "Floating Ad",
        "placement": "floating",
        "slots": ["floating"],
        "ad_type": Advertisement.AD_TYPE_SCRIPT,
        "script_code": "<div>floating-unit</div>",
        "is_active": True,
        "redirect_url": "https://advertiser.example/landing",
    }
    defaults.update(kwargs)
    return Advertisement.objects.create(**defaults)


def _request(path="/", user=None):
    request = RequestFactory().get(path)
    request.user = user if user is not None else AnonymousUser()
    return request


class FloatingPlacementContractTests(TestCase):
    def test_floating_is_an_accepted_placement(self):
        values = [value for value, _label in Advertisement.PLACEMENT_CHOICES]
        self.assertIn("floating", values)
        self.assertEqual(AD_POSITION_LABELS.get("floating"), "Floating")

    def test_existing_placements_remain_accepted(self):
        values = [value for value, _label in Advertisement.PLACEMENT_CHOICES]
        for placement in _EXISTING_PLACEMENTS:
            self.assertIn(placement, values)

    def test_form_offers_floating_from_existing_choices(self):
        form = AdvertisementForm()
        slot_values = [value for value, _label in form.fields["slots"].choices]
        self.assertIn("floating", slot_values)
        for placement in _EXISTING_PLACEMENTS:
            self.assertIn(placement, slot_values)

    def test_floating_uses_existing_slots_json_not_a_new_field(self):
        field_names = {field.name for field in Advertisement._meta.get_fields()}
        self.assertNotIn("image_floating", field_names)
        self.assertNotIn("floating", Advertisement.SLOT_IMAGE_FIELDS)
        ad = _script_ad()
        ad.refresh_from_db()
        self.assertEqual(ad.slots, ["floating"])
        self.assertEqual(ad.placement, "floating")


class FloatingActiveAdsTests(TestCase):
    def test_active_floating_ad_is_exposed(self):
        ad = _script_ad()
        result = active_ads(_request("/"))
        self.assertEqual(result["ads_floating"].pk, ad.pk)
        self.assertEqual(result["ads"]["floating"].pk, ad.pk)

    def test_inactive_floating_ad_is_not_rendered(self):
        _script_ad(is_active=False)
        result = active_ads(_request("/"))
        self.assertIsNone(result["ads_floating"])
        self.assertFalse(result["show_floating_ad"])

    def test_date_window_hides_future_and_expired_ads(self):
        now = timezone.now()
        _script_ad(name="Future", start_date=now + timedelta(days=1))
        result = active_ads(_request("/"))
        self.assertIsNone(result["ads_floating"])

        Advertisement.objects.all().delete()
        _script_ad(name="Expired", end_date=now - timedelta(days=1))
        result = active_ads(_request("/"))
        self.assertIsNone(result["ads_floating"])

    def test_role_targeting_still_applies(self):
        _script_ad(target_roles=["pandit"])
        result = active_ads(_request("/"))
        self.assertIsNone(result["ads_floating"])

        pandit = User.objects.create_user(
            email="float-pandit@example.com",
            password="test-pass-12345",
            role="pandit",
        )
        result = active_ads(_request("/", user=pandit))
        self.assertIsNotNone(result["ads_floating"])

    def test_exclude_urls_still_applies(self):
        _script_ad(exclude_urls="/search/\n")
        allowed = active_ads(_request("/"))
        blocked = active_ads(_request("/search/results/"))
        self.assertIsNotNone(allowed["ads_floating"])
        self.assertIsNone(blocked["ads_floating"])

    def test_existing_top_slot_unchanged_when_floating_present(self):
        floating = _script_ad()
        top = _script_ad(
            name="Top Ad",
            placement="top",
            slots=["top"],
            script_code="<div>top-unit</div>",
        )
        result = active_ads(_request("/"))
        self.assertEqual(result["ads_top"].pk, top.pk)
        self.assertEqual(result["ads_floating"].pk, floating.pk)
        self.assertIsNone(result["ads_sidebar"])
        self.assertIsNone(result["ads_footer"])
        self.assertIsNone(result["ads_in_content"])


@override_settings(ENABLE_FLOATING_ADS=False)
class FloatingFlagOffTests(TestCase):
    def test_disabled_flag_does_not_show_floating_chrome(self):
        _script_ad()
        result = active_ads(_request("/"))
        self.assertIsNotNone(result["ads_floating"])
        self.assertFalse(result["enable_floating_ads"])
        self.assertFalse(result["show_floating_ad"])


@override_settings(ENABLE_FLOATING_ADS=True)
class FloatingFlagOnTests(TestCase):
    def test_enabled_flag_shows_floating_on_public_path(self):
        ad = _script_ad()
        result = active_ads(_request("/"))
        self.assertTrue(result["enable_floating_ads"])
        self.assertTrue(result["show_floating_ad"])
        self.assertEqual(result["ads_floating"].pk, ad.pk)

    def test_dashboard_is_excluded(self):
        _script_ad(show_on_dashboard=True)
        result = active_ads(_request("/dashboard/user/"))
        self.assertFalse(result["show_floating_ad"])

    def test_login_is_excluded(self):
        _script_ad()
        result = active_ads(_request("/accounts/login/"))
        self.assertFalse(result["show_floating_ad"])

    def test_registration_is_excluded(self):
        _script_ad()
        result = active_ads(_request("/accounts/register/"))
        self.assertFalse(result["show_floating_ad"])

    def test_booking_intent_is_excluded(self):
        _script_ad()
        result = active_ads(_request("/booking-intent/create/abc123/"))
        self.assertFalse(result["show_floating_ad"])

    def test_expert_booking_intent_is_excluded(self):
        _script_ad()
        result = active_ads(_request("/services/expert/9/intent/"))
        self.assertFalse(result["show_floating_ad"])


class FloatingTemplateContractTests(TestCase):
    def test_base_html_has_one_guarded_floating_mount(self):
        text = _BASE_HTML.read_text(encoding="utf-8")
        self.assertEqual(text.count("show_floating_ad"), 1)
        self.assertEqual(text.count("slot='floating'"), 1)
        self.assertIn("partials/ad_unit.html", text)
        self.assertIn("slot='top'", text)
        self.assertIn("slot='sidebar'", text)
        self.assertIn("slot='footer'", text)
        self.assertIn("nd-floating-ad-close", text)
        self.assertIn("aria-label=\"Close advertisement\"", text)

    @override_settings(ENABLE_FLOATING_ADS=True)
    def test_home_renders_floating_via_existing_ad_unit(self):
        _script_ad()
        response = self.client.get(reverse("core:home"), HTTP_USER_AGENT=_BROWSER_UA)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn('id="nd-floating-ad"', html)
        self.assertIn('data-placement="floating"', html)
        self.assertIn("/track/ad/impression/", html)
        self.assertIn("placement=floating", html)
        self.assertIn("floating-unit", html)

    @override_settings(ENABLE_FLOATING_ADS=True)
    def test_login_page_does_not_render_floating_chrome(self):
        _script_ad()
        response = self.client.get(reverse("accounts:login"), HTTP_USER_AGENT=_BROWSER_UA)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertNotIn('id="nd-floating-ad"', html)

    @override_settings(ENABLE_FLOATING_ADS=False)
    def test_home_omits_floating_chrome_when_flag_off(self):
        _script_ad()
        response = self.client.get(reverse("core:home"), HTTP_USER_AGENT=_BROWSER_UA)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertNotIn('id="nd-floating-ad"', html)


class FloatingTrackingIntegrationTests(TestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.client = Client(HTTP_USER_AGENT=_BROWSER_UA)

    def test_click_with_floating_placement_uses_existing_tracker(self):
        ad = _script_ad()
        url = reverse("ads_analytics:track_click", kwargs={"ad_id": ad.pk})
        response = self.client.get(
            url,
            {"redirect": "/some/internal/path", "placement": "floating"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/some/internal/path")
        click = AdClick.objects.get()
        self.assertEqual(click.ad_id, ad.pk)
        self.assertEqual(click.placement_position, "floating")

    def test_impression_with_floating_placement_uses_existing_tracker(self):
        ad = _script_ad()
        url = reverse("ads_analytics:track_impression", kwargs={"ad_id": ad.pk})
        response = self.client.get(url, {"placement": "floating"})
        self.assertEqual(response.status_code, 204)
        impression = AdImpression.objects.get()
        self.assertEqual(impression.ad_id, ad.pk)
        self.assertEqual(impression.placement_position, "floating")
