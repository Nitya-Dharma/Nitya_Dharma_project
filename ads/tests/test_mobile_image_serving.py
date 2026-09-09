"""Batch 2 slice: Advertisement.mobile_image served at max-width 768px.

Proves templates/partials/ad_unit.html emits a <picture>/<source> for IMAGE ads
when mobile_image is set, keeps desktop/slot img fallback, omits invalid mobile
sources when empty, and preserves click/impression + Batch 1A init-guard contracts.
Does not cover script ads redesign, floating-specific product policy, or sizing CSS.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from PIL import Image

from ads.models import Advertisement

_AD_UNIT = (
    Path(__file__).resolve().parents[2] / "templates" / "partials" / "ad_unit.html"
)


def _png(name: str, color: tuple[int, int, int]) -> SimpleUploadedFile:
    buf = BytesIO()
    Image.new("RGB", (40, 20), color).save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


def _image_ad(**kwargs) -> Advertisement:
    defaults = {
        "name": "Mobile Image Ad",
        "placement": "top",
        "slots": ["top"],
        "ad_type": Advertisement.AD_TYPE_IMAGE,
        "is_active": True,
        "redirect_url": "https://example.com/dest",
        "image": _png("desktop-ad.png", (0, 70, 180)),
    }
    defaults.update(kwargs)
    return Advertisement.objects.create(**defaults)


class MobileImageServingRenderTests(TestCase):
    def test_mobile_image_emits_picture_source_and_desktop_fallback(self):
        ad = _image_ad(mobile_image=_png("mobile-ad.png", (180, 40, 0)))
        ad.refresh_from_db()
        slot_image = ad.get_image_for_slot("top")
        html = render_to_string(
            "partials/ad_unit.html",
            {"ad": ad, "slot": "top"},
        )
        self.assertIn("<picture>", html)
        self.assertIn('media="(max-width: 768px)"', html)
        self.assertIn(ad.mobile_image.url, html)
        self.assertIn(f'src="{slot_image.url}"', html)
        self.assertIn("srcset=", html)

    def test_absent_mobile_image_keeps_desktop_img_without_source(self):
        ad = _image_ad()
        ad.refresh_from_db()
        slot_image = ad.get_image_for_slot("top")
        html = render_to_string(
            "partials/ad_unit.html",
            {"ad": ad, "slot": "top"},
        )
        self.assertNotIn("<picture>", html)
        self.assertNotIn('media="(max-width: 768px)"', html)
        self.assertNotIn("srcset=", html)
        self.assertIn(f'src="{slot_image.url}"', html)

    def test_click_tracking_structure_preserved(self):
        ad = _image_ad(mobile_image=_png("mobile-ad.png", (180, 40, 0)))
        html = render_to_string(
            "partials/ad_unit.html",
            {"ad": ad, "slot": "sidebar"},
        )
        click_path = reverse("ads_analytics:track_click", kwargs={"ad_id": ad.pk})
        self.assertIn(click_path, html)
        self.assertIn("placement=sidebar", html)
        self.assertIn('target="_blank"', html)
        # One clickable anchor wrapping the picture
        self.assertEqual(html.count("<a href="), 1)

    def test_impression_tracking_single_unit_preserved(self):
        ad = _image_ad(mobile_image=_png("mobile-ad.png", (180, 40, 0)))
        html = render_to_string(
            "partials/ad_unit.html",
            {"ad": ad, "slot": "top"},
        )
        self.assertEqual(html.count('class="ad-unit-track"'), 1)
        imp_path = reverse(
            "ads_analytics:track_impression", kwargs={"ad_id": ad.pk}
        )
        self.assertIn(imp_path, html)
        self.assertIn("data-impression-url=", html)
        self.assertIn("el._impressionInit", html)
        self.assertEqual(html.count("(function(){"), 1)

    def test_script_branch_unchanged_in_source(self):
        text = _AD_UNIT.read_text(encoding="utf-8")
        self.assertIn("{% elif ad.script_code %}", text)
        self.assertIn("ad-script-responsive", text)
        self.assertIn("ad-script-fixed", text)
        self.assertIn("{{ ad.script_code|safe }}", text)


class MobileImageTemplateContractTests(SimpleTestCase):
    def test_breakpoint_and_guards_in_source(self):
        text = _AD_UNIT.read_text(encoding="utf-8")
        self.assertIn('media="(max-width: 768px)"', text)
        self.assertIn("ad.mobile_image", text)
        self.assertIn("if (el._impressionInit) return;", text)
        self.assertIn("el._impressionInit = true;", text)
        self.assertIn("ads_analytics:track_click", text)
        self.assertIn("ads_analytics:track_impression", text)
