"""Batch 1A: ad_unit impression observer init-guard contract.

Proves templates/partials/ad_unit.html marks each .ad-unit-track as initialized
before attaching IntersectionObserver, so repeated include IIFEs cannot re-observe
the same element. Does not change server tracking, attribution, Lead, or selection.
"""

from __future__ import annotations

from pathlib import Path

from django.test import TestCase

_AD_UNIT = (
    Path(__file__).resolve().parents[2] / "templates" / "partials" / "ad_unit.html"
)


class AdUnitImpressionInitGuardContractTests(TestCase):
    def setUp(self):
        self.text = _AD_UNIT.read_text(encoding="utf-8")

    def test_init_guard_exists_and_is_set(self):
        self.assertIn("el._impressionInit", self.text)
        self.assertIn("if (el._impressionInit) return;", self.text)
        self.assertIn("el._impressionInit = true;", self.text)

    def test_init_guard_precedes_observer_attach(self):
        init_check = self.text.index("if (el._impressionInit) return;")
        init_set = self.text.index("el._impressionInit = true;")
        observe = self.text.index("io.observe(el);")
        self.assertLess(init_check, init_set)
        self.assertLess(init_set, observe)

    def test_impression_sent_guard_still_present(self):
        self.assertIn("if (el._impressionSent) return;", self.text)
        self.assertIn("el._impressionSent = true;", self.text)

    def test_existing_impression_endpoint_contract_unchanged(self):
        self.assertIn("querySelectorAll('.ad-unit-track')", self.text)
        self.assertIn("data-impression-url", self.text)
        self.assertIn("ads_analytics:track_impression", self.text)
        self.assertIn(
            "fetch(url, { method: 'GET', keepalive: true, credentials: 'same-origin' });",
            self.text,
        )
        self.assertIn("typeof IntersectionObserver !== 'undefined'", self.text)
