"""Campaign/AdSet hierarchy serving eligibility (active_ads) slice tests."""

from datetime import timedelta

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone

from ads.context_processors import active_ads
from ads.models import Advertisement, AdSet, Campaign


def _script_ad(**kwargs):
    defaults = {
        "name": "Serve Ad",
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
class HierarchyServingFlagOffTests(TestCase):
    def test_paused_campaign_still_serves_when_flag_off(self):
        campaign = Campaign.objects.create(
            name="Paused Camp",
            status=Campaign.STATUS_PAUSED,
        )
        ad = _script_ad(name="Linked paused", campaign=campaign)
        result = active_ads(_request())
        self.assertEqual(result["ads_top"].pk, ad.pk)

    def test_inactive_adset_still_serves_when_flag_off(self):
        campaign = Campaign.objects.create(
            name="Active Camp",
            status=Campaign.STATUS_ACTIVE,
        )
        adset = AdSet.objects.create(
            name="Inactive Set",
            campaign=campaign,
            is_active=False,
        )
        ad = _script_ad(
            name="Linked inactive set",
            campaign=campaign,
            ad_set=adset,
        )
        result = active_ads(_request())
        self.assertEqual(result["ads_top"].pk, ad.pk)


@override_settings(ENABLE_CAMPAIGNS=True)
class HierarchyServingFlagOnTests(TestCase):
    def test_orphan_ad_still_serves(self):
        ad = _script_ad(name="Orphan")
        result = active_ads(_request())
        self.assertEqual(result["ads_top"].pk, ad.pk)

    def test_active_campaign_within_schedule_serves(self):
        now = timezone.now()
        campaign = Campaign.objects.create(
            name="Active Window",
            status=Campaign.STATUS_ACTIVE,
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=1),
        )
        ad = _script_ad(name="Camp linked", campaign=campaign)
        result = active_ads(_request())
        self.assertEqual(result["ads_top"].pk, ad.pk)

    def test_paused_campaign_does_not_serve(self):
        campaign = Campaign.objects.create(
            name="Paused",
            status=Campaign.STATUS_PAUSED,
        )
        _script_ad(name="Paused linked", campaign=campaign, slots=["top"])
        result = active_ads(_request())
        self.assertIsNone(result["ads_top"])

    def test_ended_campaign_does_not_serve(self):
        campaign = Campaign.objects.create(
            name="Ended",
            status=Campaign.STATUS_ENDED,
        )
        _script_ad(name="Ended linked", campaign=campaign, slots=["sidebar"])
        result = active_ads(_request())
        self.assertIsNone(result["ads_sidebar"])

    def test_campaign_before_start_does_not_serve(self):
        now = timezone.now()
        campaign = Campaign.objects.create(
            name="Future",
            status=Campaign.STATUS_ACTIVE,
            start_date=now + timedelta(days=2),
        )
        _script_ad(name="Future linked", campaign=campaign, slots=["footer"])
        result = active_ads(_request())
        self.assertIsNone(result["ads_footer"])

    def test_campaign_after_end_does_not_serve(self):
        now = timezone.now()
        campaign = Campaign.objects.create(
            name="Past",
            status=Campaign.STATUS_ACTIVE,
            end_date=now - timedelta(days=1),
        )
        _script_ad(name="Past linked", campaign=campaign, slots=["in_content"])
        result = active_ads(_request())
        self.assertIsNone(result["ads_in_content"])

    def test_campaign_plus_active_adset_serves(self):
        campaign = Campaign.objects.create(
            name="Camp OK",
            status=Campaign.STATUS_ACTIVE,
        )
        adset = AdSet.objects.create(
            name="Set OK",
            campaign=campaign,
            is_active=True,
        )
        ad = _script_ad(
            name="Full hierarchy",
            campaign=campaign,
            ad_set=adset,
            slots=["top"],
        )
        result = active_ads(_request())
        self.assertEqual(result["ads_top"].pk, ad.pk)

    def test_campaign_plus_inactive_adset_does_not_serve(self):
        campaign = Campaign.objects.create(
            name="Camp OK2",
            status=Campaign.STATUS_ACTIVE,
        )
        adset = AdSet.objects.create(
            name="Set Off",
            campaign=campaign,
            is_active=False,
        )
        _script_ad(
            name="Inactive set linked",
            campaign=campaign,
            ad_set=adset,
            slots=["top"],
        )
        result = active_ads(_request())
        self.assertIsNone(result["ads_top"])

    def test_campaign_without_adset_follows_campaign_only(self):
        active = Campaign.objects.create(
            name="Active only",
            status=Campaign.STATUS_ACTIVE,
        )
        paused = Campaign.objects.create(
            name="Paused only",
            status=Campaign.STATUS_PAUSED,
        )
        ad_ok = _script_ad(
            name="Camp no set OK",
            campaign=active,
            slots=["top"],
        )
        _script_ad(
            name="Camp no set blocked",
            campaign=paused,
            slots=["sidebar"],
        )
        result = active_ads(_request())
        self.assertEqual(result["ads_top"].pk, ad_ok.pk)
        self.assertIsNone(result["ads_sidebar"])

    def test_advertisement_inactive_still_blocks(self):
        campaign = Campaign.objects.create(
            name="Active",
            status=Campaign.STATUS_ACTIVE,
        )
        _script_ad(
            name="Ad off",
            campaign=campaign,
            is_active=False,
            slots=["top"],
        )
        result = active_ads(_request())
        self.assertIsNone(result["ads_top"])

    def test_advertisement_schedule_still_blocks(self):
        campaign = Campaign.objects.create(
            name="Active sched",
            status=Campaign.STATUS_ACTIVE,
        )
        now = timezone.now()
        _script_ad(
            name="Ad future",
            campaign=campaign,
            start_date=now + timedelta(days=3),
            slots=["top"],
        )
        result = active_ads(_request())
        self.assertIsNone(result["ads_top"])

    def test_url_eligibility_intact(self):
        campaign = Campaign.objects.create(
            name="Active URL",
            status=Campaign.STATUS_ACTIVE,
        )
        _script_ad(
            name="Excluded path",
            campaign=campaign,
            exclude_urls="/secret/",
            slots=["top"],
        )
        result = active_ads(_request("/secret/page/"))
        self.assertIsNone(result["ads_top"])

    def test_role_eligibility_intact(self):
        campaign = Campaign.objects.create(
            name="Active Role",
            status=Campaign.STATUS_ACTIVE,
        )
        _script_ad(
            name="Role gated",
            campaign=campaign,
            target_roles=["pandit"],
            slots=["top"],
        )
        result = active_ads(_request())
        self.assertIsNone(result["ads_top"])

    def test_multiple_ads_only_eligible_returned(self):
        good = Campaign.objects.create(name="Good", status=Campaign.STATUS_ACTIVE)
        bad = Campaign.objects.create(name="Bad", status=Campaign.STATUS_PAUSED)
        ad_good = _script_ad(name="Good ad", campaign=good, slots=["top"])
        _script_ad(name="Bad ad", campaign=bad, slots=["sidebar"])
        orphan = _script_ad(name="Orphan multi", slots=["footer"])
        result = active_ads(_request())
        self.assertEqual(result["ads_top"].pk, ad_good.pk)
        self.assertIsNone(result["ads_sidebar"])
        self.assertEqual(result["ads_footer"].pk, orphan.pk)
