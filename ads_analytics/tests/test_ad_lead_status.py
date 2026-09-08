"""Focused tests for Super Admin AdLead status mutation.

Does not cover Lead detail, filters, CRM, LeadEvent, or history.
Uses Django's disposable test database only.
"""

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from ads_analytics.models import AdClick, AdConversionIntent, AdImpression, AdLead
from ads_analytics.services.attribution_bridge import SESSION_KEY
from ads_analytics.tests.test_ad_lead_list import _make_lead, _script_ad

User = get_user_model()
LIST_URL_NAME = "ads_leads:ad_lead_list"
STATUS_URL_NAME = "ads_leads:update_ad_lead_status"


class AdLeadStatusUpdateTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            email="adlead-status-admin@example.com",
            password="test-pass-12345",
        )
        self.normal = User.objects.create_user(
            email="adlead-status-user@example.com",
            password="test-pass-12345",
        )
        self.ad = _script_ad(name="Status Ad")
        self.visitor = User.objects.create_user(
            email="adlead-status-visitor@example.com",
            password="test-pass-12345",
        )
        self.lead = _make_lead(
            ad=self.ad,
            user=self.visitor,
            campaign_id="status-snap-1",
            source=AdLead.SOURCE_WHATSAPP_CTA,
            status=AdLead.STATUS_NEW,
        )

    def _login_super(self):
        self.client.force_login(self.superuser)

    def _status_url(self, lead=None):
        return reverse(STATUS_URL_NAME, kwargs={"lead_id": (lead or self.lead).pk})

    def _snapshot(self, lead):
        return {
            "advertisement_id": lead.advertisement_id,
            "campaign_id": lead.campaign_id,
            "user_id": lead.user_id,
            "source": lead.source,
            "source_conversion_id": lead.source_conversion_id,
        }

    def test_super_admin_can_update_new_to_contacted(self):
        self._login_super()
        resp = self.client.post(self._status_url(), {"status": AdLead.STATUS_CONTACTED})
        self.assertRedirects(resp, reverse(LIST_URL_NAME))
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, AdLead.STATUS_CONTACTED)

    def test_super_admin_can_update_to_follow_up(self):
        self._login_super()
        resp = self.client.post(self._status_url(), {"status": AdLead.STATUS_FOLLOW_UP})
        self.assertEqual(resp.status_code, 302)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, AdLead.STATUS_FOLLOW_UP)

    def test_super_admin_can_update_to_converted(self):
        self._login_super()
        self.client.post(self._status_url(), {"status": AdLead.STATUS_CONVERTED})
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, AdLead.STATUS_CONVERTED)

    def test_super_admin_can_update_to_lost(self):
        self._login_super()
        self.client.post(self._status_url(), {"status": AdLead.STATUS_LOST})
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, AdLead.STATUS_LOST)

    def test_all_existing_valid_status_choices_are_accepted(self):
        self._login_super()
        values = [value for value, _label in AdLead._meta.get_field("status").choices]
        self.assertEqual(
            set(values),
            {
                AdLead.STATUS_NEW,
                AdLead.STATUS_CONTACTED,
                AdLead.STATUS_FOLLOW_UP,
                AdLead.STATUS_CONVERTED,
                AdLead.STATUS_LOST,
            },
        )
        for value in values:
            resp = self.client.post(self._status_url(), {"status": value})
            self.assertEqual(resp.status_code, 302, msg=value)
            self.lead.refresh_from_db()
            self.assertEqual(self.lead.status, value)

    def test_invalid_status_is_rejected(self):
        before = self._snapshot(self.lead)
        self._login_super()
        resp = self.client.post(self._status_url(), {"status": "not-a-status"})
        self.assertEqual(resp.status_code, 400)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, AdLead.STATUS_NEW)
        self.assertEqual(self._snapshot(self.lead), before)

    def test_blank_and_missing_status_are_rejected(self):
        self._login_super()
        blank = self.client.post(self._status_url(), {"status": ""})
        self.assertEqual(blank.status_code, 400)
        missing = self.client.post(self._status_url(), {})
        self.assertEqual(missing.status_code, 400)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, AdLead.STATUS_NEW)

    def test_get_to_status_endpoint_returns_405_and_does_not_mutate(self):
        self._login_super()
        resp = self.client.get(self._status_url())
        self.assertEqual(resp.status_code, 405)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, AdLead.STATUS_NEW)

    def test_anonymous_user_cannot_update_lead(self):
        resp = self.client.post(self._status_url(), {"status": AdLead.STATUS_CONTACTED})
        self.assertEqual(resp.status_code, 404)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, AdLead.STATUS_NEW)

    def test_non_super_admin_cannot_update_lead(self):
        self.client.force_login(self.normal)
        resp = self.client.post(self._status_url(), {"status": AdLead.STATUS_CONTACTED})
        self.assertEqual(resp.status_code, 404)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, AdLead.STATUS_NEW)

    def test_pandit_cannot_update_lead(self):
        pandit = User.objects.create_user(
            email="adlead-status-pandit@example.com",
            password="test-pass-12345",
            role="pandit",
            status="active",
        )
        self.client.force_login(pandit)
        resp = self.client.post(self._status_url(), {"status": AdLead.STATUS_CONTACTED})
        self.assertEqual(resp.status_code, 404)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, AdLead.STATUS_NEW)

    def test_existing_lead_fields_remain_unchanged(self):
        before = self._snapshot(self.lead)
        created_at = self.lead.created_at
        self._login_super()
        self.client.post(self._status_url(), {"status": AdLead.STATUS_CONTACTED})
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, AdLead.STATUS_CONTACTED)
        self.assertEqual(self._snapshot(self.lead), before)
        self.assertEqual(self.lead.created_at, created_at)

    def test_successful_status_update_redirects_to_lead_list(self):
        self._login_super()
        resp = self.client.post(self._status_url(), {"status": AdLead.STATUS_LOST})
        self.assertRedirects(resp, reverse(LIST_URL_NAME))

    def test_status_is_persisted(self):
        self._login_super()
        self.client.post(self._status_url(), {"status": AdLead.STATUS_CONVERTED})
        persisted = AdLead.objects.get(pk=self.lead.pk)
        self.assertEqual(persisted.status, AdLead.STATUS_CONVERTED)

    def test_updated_at_follows_existing_model_behavior(self):
        AdLead.objects.filter(pk=self.lead.pk).update(
            updated_at=timezone.now() - timedelta(days=1)
        )
        self.lead.refresh_from_db()
        previous = self.lead.updated_at
        self._login_super()
        self.client.post(self._status_url(), {"status": AdLead.STATUS_CONTACTED})
        self.lead.refresh_from_db()
        self.assertGreater(self.lead.updated_at, previous)

    def test_missing_lead_id_returns_404(self):
        self._login_super()
        missing_url = reverse(STATUS_URL_NAME, kwargs={"lead_id": 999999})
        resp = self.client.post(missing_url, {"status": AdLead.STATUS_CONTACTED})
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(AdLead.objects.count(), 1)

    def test_resubmitting_same_status_is_safe(self):
        before = self._snapshot(self.lead)
        clicks = AdClick.objects.count()
        impressions = AdImpression.objects.count()
        conversions = AdConversionIntent.objects.count()
        leads = AdLead.objects.count()
        self._login_super()
        resp = self.client.post(self._status_url(), {"status": AdLead.STATUS_NEW})
        self.assertEqual(resp.status_code, 302)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, AdLead.STATUS_NEW)
        self.assertEqual(self._snapshot(self.lead), before)
        self.assertEqual(AdClick.objects.count(), clicks)
        self.assertEqual(AdImpression.objects.count(), impressions)
        self.assertEqual(AdConversionIntent.objects.count(), conversions)
        self.assertEqual(AdLead.objects.count(), leads)

    def test_status_update_creates_no_analytics_or_leads(self):
        self._login_super()
        self.client.post(self._status_url(), {"status": AdLead.STATUS_CONTACTED})
        self.assertEqual(AdClick.objects.count(), 0)
        self.assertEqual(AdImpression.objects.count(), 0)
        self.assertEqual(AdConversionIntent.objects.count(), 1)
        self.assertEqual(AdLead.objects.count(), 1)

    def test_attribution_session_is_unchanged_by_status_update(self):
        self._login_super()
        session = self.client.session
        payload = {"ad_id": self.ad.pk, "campaign_id": "keep-session"}
        session[SESSION_KEY] = payload
        session.save()
        self.client.post(self._status_url(), {"status": AdLead.STATUS_CONTACTED})
        self.assertEqual(self.client.session.get(SESSION_KEY), payload)

    def test_lead_list_still_renders_after_update(self):
        self._login_super()
        resp = self.client.post(
            self._status_url(),
            {"status": AdLead.STATUS_FOLLOW_UP},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Follow up")
        self.assertContains(resp, 'name="status"')
        self.assertContains(resp, "csrfmiddlewaretoken")

    def test_csrf_is_enforced_on_status_post(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.superuser)
        resp = csrf_client.post(
            self._status_url(), {"status": AdLead.STATUS_CONTACTED}
        )
        self.assertEqual(resp.status_code, 403)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, AdLead.STATUS_NEW)

    def test_list_shows_current_status_selected(self):
        self.lead.status = AdLead.STATUS_CONTACTED
        self.lead.save(update_fields=["status", "updated_at"])
        self._login_super()
        resp = self.client.get(reverse(LIST_URL_NAME))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(
            resp,
            f'action="{reverse(STATUS_URL_NAME, kwargs={"lead_id": self.lead.pk})}"',
        )
        self.assertRegex(
            resp.content.decode(),
            r'<option value="contacted" selected>Contacted</option>',
        )
        self.assertContains(resp, "csrfmiddlewaretoken")
        self.assertContains(resp, "Update")
