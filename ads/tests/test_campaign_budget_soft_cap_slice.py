"""Campaign total-budget soft-cap serving eligibility slice tests."""

from decimal import Decimal

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from datetime import timedelta

from ads.context_processors import active_ads
from ads.models import Advertisement, AdSet, Campaign


def _script_ad(**kwargs):
    defaults = {
        "name": "Budget Ad",
        "placement": "top",
        "slots": ["top"],
        "ad_type": Advertisement.AD_TYPE_SCRIPT,
        "script_code": "<div>x</div>",
        "is_active": True,
    }
    defaults.update(kwargs)
    return Advertisement.objects.create(**defaults)


def _request(path="/"):
    request = RequestFactory().get(path)
    request.user = AnonymousUser()
    return request


@override_settings(ENABLE_CAMPAIGNS=False)
class BudgetSoftCapFlagOffTests(TestCase):
    def test_flag_off_at_budget_still_serves(self):
        campaign = Campaign.objects.create(
            name="At Cap Off",
            status=Campaign.STATUS_ACTIVE,
            total_budget=Decimal("100.00"),
            spent_amount=Decimal("100.00"),
        )
        ad = _script_ad(name="At cap off", campaign=campaign)
        result = active_ads(_request())
        self.assertEqual(result["ads_top"].pk, ad.pk)

    def test_flag_off_over_budget_still_serves(self):
        campaign = Campaign.objects.create(
            name="Over Cap Off",
            status=Campaign.STATUS_ACTIVE,
            total_budget=Decimal("50.00"),
            spent_amount=Decimal("75.00"),
        )
        ad = _script_ad(name="Over cap off", campaign=campaign)
        result = active_ads(_request())
        self.assertEqual(result["ads_top"].pk, ad.pk)


@override_settings(ENABLE_CAMPAIGNS=True)
class BudgetSoftCapFlagOnTests(TestCase):
    def test_under_budget_serves(self):
        campaign = Campaign.objects.create(
            name="Under",
            status=Campaign.STATUS_ACTIVE,
            total_budget=Decimal("100.00"),
            spent_amount=Decimal("40.00"),
        )
        ad = _script_ad(name="Under ad", campaign=campaign)
        result = active_ads(_request())
        self.assertEqual(result["ads_top"].pk, ad.pk)

    def test_exactly_at_budget_blocked(self):
        campaign = Campaign.objects.create(
            name="Exact",
            status=Campaign.STATUS_ACTIVE,
            total_budget=Decimal("100.00"),
            spent_amount=Decimal("100.00"),
        )
        _script_ad(name="Exact ad", campaign=campaign, slots=["top"])
        result = active_ads(_request())
        self.assertIsNone(result["ads_top"])

    def test_over_budget_blocked(self):
        campaign = Campaign.objects.create(
            name="Over",
            status=Campaign.STATUS_ACTIVE,
            total_budget=Decimal("100.00"),
            spent_amount=Decimal("120.00"),
        )
        _script_ad(name="Over ad", campaign=campaign, slots=["sidebar"])
        result = active_ads(_request())
        self.assertIsNone(result["ads_sidebar"])

    def test_null_total_budget_serves(self):
        campaign = Campaign.objects.create(
            name="No Cap",
            status=Campaign.STATUS_ACTIVE,
            total_budget=None,
            spent_amount=Decimal("999.00"),
        )
        ad = _script_ad(name="No cap ad", campaign=campaign)
        result = active_ads(_request())
        self.assertEqual(result["ads_top"].pk, ad.pk)

    def test_orphan_ad_unaffected(self):
        ad = _script_ad(name="Orphan budget")
        result = active_ads(_request())
        self.assertEqual(result["ads_top"].pk, ad.pk)

    def test_active_adset_under_budget_serves(self):
        campaign = Campaign.objects.create(
            name="Camp OK",
            status=Campaign.STATUS_ACTIVE,
            total_budget=Decimal("200.00"),
            spent_amount=Decimal("10.00"),
        )
        adset = AdSet.objects.create(
            name="Set OK",
            campaign=campaign,
            is_active=True,
        )
        ad = _script_ad(
            name="Full under",
            campaign=campaign,
            ad_set=adset,
        )
        result = active_ads(_request())
        self.assertEqual(result["ads_top"].pk, ad.pk)

    def test_budget_exceeded_otherwise_valid_hierarchy_blocked(self):
        campaign = Campaign.objects.create(
            name="Camp Cap",
            status=Campaign.STATUS_ACTIVE,
            total_budget=Decimal("10.00"),
            spent_amount=Decimal("10.00"),
        )
        adset = AdSet.objects.create(
            name="Set Active",
            campaign=campaign,
            is_active=True,
        )
        _script_ad(
            name="Cap blocked",
            campaign=campaign,
            ad_set=adset,
            slots=["top"],
        )
        result = active_ads(_request())
        self.assertIsNone(result["ads_top"])

    def test_paused_campaign_still_blocked(self):
        campaign = Campaign.objects.create(
            name="Paused under budget",
            status=Campaign.STATUS_PAUSED,
            total_budget=Decimal("100.00"),
            spent_amount=Decimal("1.00"),
        )
        _script_ad(name="Paused ad", campaign=campaign, slots=["footer"])
        result = active_ads(_request())
        self.assertIsNone(result["ads_footer"])

    def test_campaign_outside_end_window_still_blocked(self):
        now = timezone.now()
        campaign = Campaign.objects.create(
            name="Ended window",
            status=Campaign.STATUS_ACTIVE,
            end_date=now - timedelta(days=1),
            total_budget=Decimal("100.00"),
            spent_amount=Decimal("1.00"),
        )
        _script_ad(name="Past end", campaign=campaign, slots=["in_content"])
        result = active_ads(_request())
        self.assertIsNone(result["ads_in_content"])

    def test_inactive_adset_still_blocked(self):
        campaign = Campaign.objects.create(
            name="Camp Active Cap OK",
            status=Campaign.STATUS_ACTIVE,
            total_budget=Decimal("100.00"),
            spent_amount=Decimal("1.00"),
        )
        adset = AdSet.objects.create(
            name="Set Off",
            campaign=campaign,
            is_active=False,
        )
        _script_ad(
            name="Inactive set",
            campaign=campaign,
            ad_set=adset,
            slots=["top"],
        )
        result = active_ads(_request())
        self.assertIsNone(result["ads_top"])
