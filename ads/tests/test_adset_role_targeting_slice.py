"""Batch I: AdSet.target_roles as additional AND restriction (flag-gated).

Does not change Advertisement.is_allowed_for_user semantics.
Does not enforce AdSet URL/location/placement/pricing.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase, override_settings

from ads.context_processors import active_ads
from ads.models import Advertisement, AdSet, Campaign


def _script_ad(**kwargs):
    defaults = {
        "name": "Role Ad",
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
        email=f"adset-role-{suffix}@example.com",
        password="AdSetRolePass123!",
        username=f"adset_role_{suffix}",
        role=role,
        status="active",
        is_active=True,
    )


def _linked_ad(*, adset_roles=None, ad_roles=None, adset_active=True, **ad_kwargs):
    campaign = Campaign.objects.create(
        name=f"Camp {ad_kwargs.get('name', 'x')}",
        status=Campaign.STATUS_ACTIVE,
    )
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
class AdSetRoleTargetingFlagOnTests(TestCase):
    def test_both_roles_empty_allows_anonymous(self):
        ad, _, _ = _linked_ad(name="both empty", adset_roles=[], ad_roles=[])
        result = active_ads(_request())
        self.assertEqual(result["ads_top"].pk, ad.pk)

    def test_adset_pandit_only_denies_anonymous_allows_pandit(self):
        ad, _, _ = _linked_ad(
            name="adset pandit",
            adset_roles=["pandit"],
            ad_roles=[],
        )
        anon = active_ads(_request())
        self.assertIsNone(anon["ads_top"])
        pandit = _user("pandit1", role="pandit")
        ok = active_ads(_request(user=pandit))
        self.assertEqual(ok["ads_top"].pk, ad.pk)

    def test_advertisement_pandit_only_unchanged(self):
        ad, _, _ = _linked_ad(
            name="ad pandit",
            adset_roles=[],
            ad_roles=["pandit"],
        )
        self.assertIsNone(active_ads(_request())["ads_top"])
        pandit = _user("pandit2", role="pandit")
        self.assertEqual(active_ads(_request(user=pandit))["ads_top"].pk, ad.pk)
        regular = _user("user2", role="user")
        self.assertIsNone(active_ads(_request(user=regular))["ads_top"])

    def test_and_intersection_pandit_vs_user_allows_nobody(self):
        _linked_ad(
            name="and conflict",
            adset_roles=["user"],
            ad_roles=["pandit"],
        )
        pandit = _user("pandit3", role="pandit")
        regular = _user("user3", role="user")
        self.assertIsNone(active_ads(_request(user=pandit))["ads_top"])
        self.assertIsNone(active_ads(_request(user=regular))["ads_top"])
        self.assertIsNone(active_ads(_request())["ads_top"])

    def test_and_intersection_matching_pandit_allows(self):
        ad, _, _ = _linked_ad(
            name="and match",
            adset_roles=["pandit"],
            ad_roles=["pandit"],
        )
        pandit = _user("pandit4", role="pandit")
        self.assertEqual(active_ads(_request(user=pandit))["ads_top"].pk, ad.pk)
        regular = _user("user4", role="user")
        self.assertIsNone(active_ads(_request(user=regular))["ads_top"])

    def test_no_adset_unchanged(self):
        ad = _script_ad(name="orphan role", target_roles=[], slots=["top"])
        self.assertEqual(active_ads(_request())["ads_top"].pk, ad.pk)
        gated = _script_ad(
            name="orphan pandit",
            target_roles=["pandit"],
            slots=["sidebar"],
        )
        self.assertIsNone(active_ads(_request())["ads_sidebar"])
        pandit = _user("pandit5", role="pandit")
        self.assertEqual(active_ads(_request(user=pandit))["ads_sidebar"].pk, gated.pk)

    def test_inactive_adset_still_blocked_regardless_of_roles(self):
        _linked_ad(
            name="inactive set",
            adset_roles=["pandit"],
            ad_roles=[],
            adset_active=False,
        )
        pandit = _user("pandit6", role="pandit")
        self.assertIsNone(active_ads(_request(user=pandit))["ads_top"])


@override_settings(ENABLE_CAMPAIGNS=False)
class AdSetRoleTargetingFlagOffTests(TestCase):
    def test_adset_roles_ignored_when_flag_off(self):
        ad, _, _ = _linked_ad(
            name="flag off",
            adset_roles=["pandit"],
            ad_roles=[],
        )
        # Hierarchy bypassed: non-empty AdSet roles must not suppress anonymous.
        result = active_ads(_request())
        self.assertEqual(result["ads_top"].pk, ad.pk)
