"""Script advertisement placement-fit contract (create/edit validation).

Covers responsive-first + fit-required fixed scripts for approved numeric budgets
(sidebar 300px, in_content 336px) and responsive-only slots (dashboard_sidebar,
floating). Does not cover serving/CSS changes, fluid placement pixel budgets,
Campaigns, tracking, Lead, WhatsApp, or mobile_image redesign.
"""

from __future__ import annotations

from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from PIL import Image

from ads.forms import AdvertisementForm
from ads.models import Advertisement
from ads.script_placement_policy import (
    SCRIPT_FIXED_MAX_WIDTH_PX,
    SCRIPT_FIXED_RESPONSIVE_ONLY_SLOTS,
    validate_fixed_script_placement_fit,
)


def _png(name: str = "ad.png", size=(40, 20)) -> SimpleUploadedFile:
    buf = BytesIO()
    Image.new("RGB", size, (10, 20, 30)).save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


def _script_form_data(**overrides):
    data = {
        "name": "Script Contract Ad",
        "ad_type": Advertisement.AD_TYPE_SCRIPT,
        "script_code": "<div>script-unit</div>",
        "is_active": "on",
        "redirect_url": "https://example.com/landing",
        "slots": ["sidebar"],
        "is_responsive": "on",
        "show_on_dashboard": "",
        "exclude_urls": "",
        "target_roles": "",
        "banner_width": "",
        "banner_height": "",
    }
    data.update(overrides)
    return data


class ScriptPlacementPolicyUnitTests(SimpleTestCase):
    def test_approved_numeric_budgets_and_responsive_only_slots(self):
        self.assertEqual(SCRIPT_FIXED_MAX_WIDTH_PX["sidebar"], 300)
        self.assertEqual(SCRIPT_FIXED_MAX_WIDTH_PX["in_content"], 336)
        self.assertNotIn("top", SCRIPT_FIXED_MAX_WIDTH_PX)
        self.assertNotIn("footer", SCRIPT_FIXED_MAX_WIDTH_PX)
        self.assertNotIn("dashboard_top", SCRIPT_FIXED_MAX_WIDTH_PX)
        self.assertEqual(
            SCRIPT_FIXED_RESPONSIVE_ONLY_SLOTS,
            frozenset({"dashboard_sidebar", "floating"}),
        )

    def test_helper_rejects_oversized_sidebar_and_responsive_only(self):
        errs = validate_fixed_script_placement_fit(["sidebar"], 301, 90)
        self.assertTrue(any("300" in e for e in errs))
        errs = validate_fixed_script_placement_fit(["floating"], 300, 90)
        self.assertTrue(any("Floating" in e or "floating" in e.lower() for e in errs))


class ScriptAdvertisementFormContractTests(TestCase):
    def test_responsive_script_accepted_sidebar(self):
        form = AdvertisementForm(data=_script_form_data(slots=["sidebar"]))
        self.assertTrue(form.is_valid(), form.errors)

    def test_responsive_script_accepted_in_content(self):
        form = AdvertisementForm(data=_script_form_data(slots=["in_content"]))
        self.assertTrue(form.is_valid(), form.errors)

    def test_responsive_script_accepted_dashboard_sidebar(self):
        form = AdvertisementForm(
            data=_script_form_data(slots=["dashboard_sidebar"], show_on_dashboard="on")
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_responsive_script_accepted_floating(self):
        form = AdvertisementForm(data=_script_form_data(slots=["floating"]))
        self.assertTrue(form.is_valid(), form.errors)

    def test_fixed_script_accepted_sidebar_at_300(self):
        form = AdvertisementForm(
            data=_script_form_data(
                slots=["sidebar"],
                is_responsive="",
                banner_width="300",
                banner_height="250",
            )
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_fixed_script_rejected_sidebar_over_300(self):
        form = AdvertisementForm(
            data=_script_form_data(
                slots=["sidebar"],
                is_responsive="",
                banner_width="301",
                banner_height="90",
            )
        )
        self.assertFalse(form.is_valid())
        self.assertTrue(any("300" in e for e in form.non_field_errors()))

    def test_fixed_script_accepted_in_content_at_336(self):
        form = AdvertisementForm(
            data=_script_form_data(
                slots=["in_content"],
                is_responsive="",
                banner_width="336",
                banner_height="280",
            )
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_fixed_script_rejected_in_content_over_336(self):
        form = AdvertisementForm(
            data=_script_form_data(
                slots=["in_content"],
                is_responsive="",
                banner_width="337",
                banner_height="90",
            )
        )
        self.assertFalse(form.is_valid())
        self.assertTrue(any("336" in e for e in form.non_field_errors()))

    def test_fixed_script_rejected_dashboard_sidebar(self):
        form = AdvertisementForm(
            data=_script_form_data(
                slots=["dashboard_sidebar"],
                is_responsive="",
                banner_width="250",
                banner_height="250",
                show_on_dashboard="on",
            )
        )
        self.assertFalse(form.is_valid())
        joined = " ".join(form.non_field_errors())
        self.assertIn("Dashboard Sidebar", joined)

    def test_fixed_script_rejected_floating(self):
        form = AdvertisementForm(
            data=_script_form_data(
                slots=["floating"],
                is_responsive="",
                banner_width="280",
                banner_height="90",
            )
        )
        self.assertFalse(form.is_valid())
        joined = " ".join(form.non_field_errors())
        self.assertIn("Floating", joined)

    def test_multi_placement_fixed_rejected_when_one_slot_incompatible(self):
        form = AdvertisementForm(
            data=_script_form_data(
                slots=["top", "sidebar"],
                is_responsive="",
                banner_width="728",
                banner_height="90",
            )
        )
        self.assertFalse(form.is_valid())
        joined = " ".join(form.non_field_errors())
        self.assertIn("300", joined)
        self.assertIn("every selected placement", joined)

    def test_multi_placement_fixed_accepted_when_all_numeric_slots_fit(self):
        form = AdvertisementForm(
            data=_script_form_data(
                slots=["sidebar", "in_content"],
                is_responsive="",
                banner_width="300",
                banner_height="90",
            )
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_fixed_script_non_positive_width_rejected(self):
        form = AdvertisementForm(
            data=_script_form_data(
                slots=["top"],
                is_responsive="",
                banner_width="0",
                banner_height="90",
            )
        )
        self.assertFalse(form.is_valid())
        # PositiveIntegerField and/or our contract must reject.
        self.assertTrue(form.errors)

    def test_fixed_script_non_positive_height_rejected(self):
        form = AdvertisementForm(
            data=_script_form_data(
                slots=["top"],
                is_responsive="",
                banner_width="300",
                banner_height="0",
            )
        )
        self.assertFalse(form.is_valid())
        self.assertTrue(form.errors)

    def test_fixed_script_missing_dimensions_rejected(self):
        form = AdvertisementForm(
            data=_script_form_data(
                slots=["top"],
                is_responsive="",
                banner_width="",
                banner_height="",
            )
        )
        self.assertFalse(form.is_valid())
        joined = " ".join(str(e) for e in form.non_field_errors())
        self.assertIn("positive banner width", joined)
        self.assertIn("positive banner height", joined)

    def test_fixed_script_allowed_on_fluid_top_without_invented_budget(self):
        """Fluid top has no approved pixel max; fixed with explicit dims is accepted."""
        form = AdvertisementForm(
            data=_script_form_data(
                slots=["top"],
                is_responsive="",
                banner_width="728",
                banner_height="90",
            )
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_image_advertisement_unaffected_by_script_contract(self):
        form = AdvertisementForm(
            data={
                "name": "Image Ad",
                "ad_type": Advertisement.AD_TYPE_IMAGE,
                "script_code": "",
                "is_active": "on",
                "redirect_url": "https://example.com/img",
                "slots": ["sidebar"],
                "is_responsive": "",
                "banner_width": "728",
                "banner_height": "90",
                "exclude_urls": "",
                "target_roles": "",
            },
            files={"image_sidebar": _png("sidebar.png", size=(300, 250))},
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_mobile_image_template_contract_unchanged(self):
        from pathlib import Path

        text = (
            Path(__file__).resolve().parents[2]
            / "templates"
            / "partials"
            / "ad_unit.html"
        ).read_text(encoding="utf-8")
        self.assertIn("ad.mobile_image", text)
        self.assertIn('media="(max-width: 768px)"', text)
        self.assertIn("el._impressionInit", text)
        self.assertIn("{% elif ad.script_code %}", text)

    def test_edit_path_applies_validation_to_existing_instance(self):
        ad = Advertisement.objects.create(
            name="Legacy Fixed",
            placement="sidebar",
            slots=["sidebar"],
            ad_type=Advertisement.AD_TYPE_SCRIPT,
            script_code="<div>legacy</div>",
            is_active=True,
            is_responsive=False,
            banner_width=728,
            banner_height=90,
        )
        # Grandfathered in DB; editing with same invalid config must fail validation.
        form = AdvertisementForm(
            data=_script_form_data(
                name="Legacy Fixed Edited",
                slots=["sidebar"],
                is_responsive="",
                banner_width="728",
                banner_height="90",
            ),
            instance=ad,
        )
        self.assertFalse(form.is_valid())
        self.assertTrue(any("300" in e for e in form.non_field_errors()))
