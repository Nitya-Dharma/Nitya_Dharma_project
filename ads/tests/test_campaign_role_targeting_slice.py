"""Batch J: Campaign.target_roles as additional AND restriction (flag-gated).

Does not change Advertisement.is_allowed_for_user semantics.
Does not change AdSet.target_roles (Batch I) semantics.
Does not modify CampaignForm empty-role default quirk.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone

from ads.context_processors import active_ads
from ads.models import Advertisement, AdSet, Campaign


def _script_ad(**kwargs):
    defaults = {
        "name": "Camp Role Ad",
        "placement": "top",
        "slots": ["top"],
        "ad_type": Advertisement.AD_TYPE_SCRIPT,
        "script_code": "<div>x</div>",
        "is_active": True,
    }
    defaults.update(kwargs)
    return Advertisement.objects.create(**defaults)


def _request(path="/", user=None):
    request = RequestFactory().get(path)
    request.user = user if user is not None else AnonymousUser()
    return request


def _user(suffix, role="user"):
    return get_user_model().objects.create_user(
        email=f"camp-role-{suffix}@example.com",
        password="CampRolePass123!",
        username=f"camp_role_{suffix}",
        role=role,
        status="active",
        is_active=True,
    )


def _linked_ad(
    *,
    campaign_roles=None,
    adset_roles=None,
    ad_roles=None,
    adset_active=True,
    campaign_status=Campaign.STATUS_ACTIVE,
    campaign_kwargs=None,
    **ad_kwargs,
):
    camp_kw = {
        "name": f"Camp {ad_kwargs.get('name', 'x')}",
        "status": campaign_status,
        "target_roles": list(campaign_roles or []),
    }
    if campaign_kwargs:
        camp_kw.update(campaign_kwargs)
    campaign = Campaign.objects.create(**camp_kw)
    adset = AdSet.objects.create(
        name=f"Set {ad_kwargs.get('name', 'x')}",
        campaign=campaign,
        is_active=adset_active,
        target_roles=list(adset_roles or []),
    )
    kwargs = {
        "campaign": campaign,
        "ad_set": adset,
        "target_roles": list(ad_roles or []),
    }
    kwargs.update(ad_kwargs)
    return _script_ad(**kwargs), campaign, adset


@override_settings(ENABLE_CAMPAIGNS=True)
class CampaignRoleTargetingFlagOnTests(TestCase):
    def test_empty_campaign_roles_allows_anonymous(self):
        ad, _, _ = _linked_ad(name="empty camp roles", campaign_roles=[], adset_roles=[], ad_roles=[])
        result = active_ads(_request())
        self.assertEqual(result["ads_top"].pk, ad.pk)

    def test_matching_campaign_role_allows_pandit(self):
        ad, _, _ = _linked_ad(
            name="camp pandit match",
            campaign_roles=["pandit"],
            adset_roles=[],
            ad_roles=[],
        )
        pandit = _user("pandit1", role="pandit")
        result = active_ads(_request(user=pandit))
        self.assertEqual(result["ads_top"].pk, ad.pk)

    def test_non_matching_campaign_role_blocks_user(self):
        _linked_ad(
            name="camp pandit mismatch",
            campaign_roles=["pandit"],
            adset_roles=[],
            ad_roles=[],
        )
        regular = _user("user1", role="user")
        self.assertIsNone(active_ads(_request(user=regular))["ads_top"])

    def test_anonymous_blocked_when_campaign_roles_non_empty(self):
        _linked_ad(
            name="camp user anon",
            campaign_roles=["user"],
            adset_roles=[],
            ad_roles=[],
        )
        self.assertIsNone(active_ads(_request())["ads_top"])

    def test_campaign_match_advertisement_mismatch_blocked(self):
        _linked_ad(
            name="camp ok ad fail",
            campaign_roles=["pandit"],
            adset_roles=[],
            ad_roles=["user"],
        )
        pandit = _user("pandit2", role="pandit")
        self.assertIsNone(active_ads(_request(user=pandit))["ads_top"])

    def test_campaign_match_adset_mismatch_blocked(self):
        _linked_ad(
            name="camp ok adset fail",
            campaign_roles=["pandit"],
            adset_roles=["user"],
            ad_roles=[],
        )
        pandit = _user("pandit3", role="pandit")
        self.assertIsNone(active_ads(_request(user=pandit))["ads_top"])

    def test_all_three_layers_matching_allows(self):
        ad, _, _ = _linked_ad(
            name="all three ok",
            campaign_roles=["pandit"],
            adset_roles=["pandit"],
            ad_roles=["pandit"],
        )
        pandit = _user("pandit4", role="pandit")
        self.assertEqual(active_ads(_request(user=pandit))["ads_top"].pk, ad.pk)
        regular = _user("user4", role="user")
        self.assertIsNone(active_ads(_request(user=regular))["ads_top"])

    def test_all_three_layers_campaign_fail_blocked(self):
        _linked_ad(
            name="camp fail three",
            campaign_roles=["user"],
            adset_roles=["pandit"],
            ad_roles=["pandit"],
        )
        pandit = _user("pandit5", role="pandit")
        self.assertIsNone(active_ads(_request(user=pandit))["ads_top"])

    def test_no_campaign_unchanged(self):
        ad = _script_ad(name="orphan camp role", target_roles=[], slots=["top"])
        self.assertEqual(active_ads(_request())["ads_top"].pk, ad.pk)
        gated = _script_ad(
            name="orphan pandit camp role",
            target_roles=["pandit"],
            slots=["sidebar"],
        )
        self.assertIsNone(active_ads(_request())["ads_sidebar"])
        pandit = _user("pandit6", role="pandit")
        self.assertEqual(active_ads(_request(user=pandit))["ads_sidebar"].pk, gated.pk)

    def test_paused_campaign_still_blocked_despite_matching_roles(self):
        _linked_ad(
            name="paused camp roles",
            campaign_roles=["pandit"],
            adset_roles=[],
            ad_roles=[],
            campaign_status=Campaign.STATUS_PAUSED,
        )
        pandit = _user("pandit7", role="pandit")
        self.assertIsNone(active_ads(_request(user=pandit))["ads_top"])

    def test_future_campaign_still_blocked_despite_matching_roles(self):
        now = timezone.now()
        _linked_ad(
            name="future camp roles",
            campaign_roles=["pandit"],
            adset_roles=[],
            ad_roles=[],
            campaign_kwargs={"start_date": now + timedelta(days=2)},
        )
        pandit = _user("pandit8", role="pandit")
        self.assertIsNone(active_ads(_request(user=pandit))["ads_top"])

    def test_expired_campaign_still_blocked_despite_matching_roles(self):
        now = timezone.now()
        _linked_ad(
            name="expired camp roles",
            campaign_roles=["pandit"],
            adset_roles=[],
            ad_roles=[],
            campaign_kwargs={"end_date": now - timedelta(days=1)},
        )
        pandit = _user("pandit9", role="pandit")
        self.assertIsNone(active_ads(_request(user=pandit))["ads_top"])

    def test_budget_soft_cap_still_blocked_despite_matching_roles(self):
        _linked_ad(
            name="budget camp roles",
            campaign_roles=["pandit"],
            adset_roles=[],
            ad_roles=[],
            campaign_kwargs={
                "total_budget": Decimal("100.00"),
                "spent_amount": Decimal("100.00"),
            },
        )
        pandit = _user("pandit10", role="pandit")
        self.assertIsNone(active_ads(_request(user=pandit))["ads_top"])


@override_settings(ENABLE_CAMPAIGNS=False)
class CampaignRoleTargetingFlagOffTests(TestCase):
    def test_campaign_roles_ignored_when_flag_off(self):
        ad, _, _ = _linked_ad(
            name="flag off camp roles",
            campaign_roles=["pandit"],
            adset_roles=[],
            ad_roles=[],
        )
        result = active_ads(_request())
        self.assertEqual(result["ads_top"].pk, ad.pk)
