"""Bureau dashboard shared dashboard_* Ads slot parity.

Proves the Bureau dashboard includes existing shared ad_unit markup for
dashboard_top and dashboard_sidebar (same path as Pandit/Expert via
active_ads + partials/ad_unit.html). Does not exercise Campaign/AdSet,
billing, or Native Ads.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ads.models import Advertisement
from bureaus.models import BureauProfile

User = get_user_model()


def _eligible_bureau(*, email: str) -> BureauProfile:
    user = User.objects.create_user(
        email=email,
        password="BureauAdsParityPass123!",
        username=f"u_{email.split('@')[0][:20]}",
        role="user",
        status="active",
        is_active=True,
    )
    return BureauProfile.objects.create(
        user=user,
        bureau_name="Ads Parity Bureau",
        phone_number="9876543210",
        whatsapp_number="",
        address="12 Test Street",
        city="Hyderabad",
        description="Full bureau description for dashboard access.",
        caste_data={"OC": ["brahmin"]},
        is_active=True,
        is_approved=True,
        is_email_verified=True,
    )


def _script_dashboard_ad(*, name: str, slot: str) -> Advertisement:
    return Advertisement.objects.create(
        name=name,
        placement=slot,
        slots=[slot],
        ad_type=Advertisement.AD_TYPE_SCRIPT,
        script_code=f'<div id="marker-{slot}">marker-{slot}</div>',
        is_active=True,
        show_on_dashboard=True,
    )


@override_settings(ENABLE_CAMPAIGNS=False)
class BureauDashboardAdsParityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.profile = _eligible_bureau(email="bureau-ads-parity@example.com")
        self.client.force_login(self.profile.user)
        self.url = reverse("bureaus_dashboard:bureau_dashboard")

    def test_dashboard_top_slot_renders_shared_ad_unit(self):
        ad = _script_dashboard_ad(name="Bureau Dash Top", slot="dashboard_top")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8", errors="ignore")
        self.assertIn('data-placement="dashboard_top"', body)
        self.assertIn(f'data-ad-id="{ad.pk}"', body)
        self.assertIn("marker-dashboard_top", body)
        self.assertEqual(body.count('data-placement="dashboard_top"'), 1)

    def test_dashboard_sidebar_slot_renders_shared_ad_unit(self):
        ad = _script_dashboard_ad(
            name="Bureau Dash Sidebar", slot="dashboard_sidebar"
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8", errors="ignore")
        self.assertIn('data-placement="dashboard_sidebar"', body)
        self.assertIn(f'data-ad-id="{ad.pk}"', body)
        self.assertIn("marker-dashboard_sidebar", body)
        self.assertEqual(body.count('data-placement="dashboard_sidebar"'), 1)

    def test_both_dashboard_slots_render_once_each(self):
        top = _script_dashboard_ad(name="Both Top", slot="dashboard_top")
        side = _script_dashboard_ad(name="Both Side", slot="dashboard_sidebar")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8", errors="ignore")
        self.assertEqual(body.count('data-placement="dashboard_top"'), 1)
        self.assertEqual(body.count('data-placement="dashboard_sidebar"'), 1)
        self.assertIn(f'data-ad-id="{top.pk}"', body)
        self.assertIn(f'data-ad-id="{side.pk}"', body)
        # Global base slots must not be accidentally re-included as dashboard slots.
        self.assertNotIn('data-placement="top"', body)
        self.assertNotIn('data-placement="sidebar"', body)
        self.assertNotIn('data-placement="footer"', body)
