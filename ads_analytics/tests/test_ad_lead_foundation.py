"""Focused tests for AdLead model and create_ad_lead_from_conversion.

Does not cover WhatsApp/booking wiring, admin UI, CRM, or LeadEvent.
Uses Django's disposable test database only.
"""

from __future__ import annotations

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from ads.models import Advertisement, Campaign
from ads_analytics.models import AdConversionIntent, AdLead
from ads_analytics.services.lead_service import create_ad_lead_from_conversion


def _script_ad(**kwargs) -> Advertisement:
    defaults = {
        "name": "Lead Foundation Ad",
        "placement": "top",
        "slots": ["top"],
        "ad_type": Advertisement.AD_TYPE_SCRIPT,
        "script_code": "<div>ad</div>",
        "is_active": True,
        "redirect_url": "https://example.com/dest",
    }
    defaults.update(kwargs)
    return Advertisement.objects.create(**defaults)


def _user(suffix: str):
    return get_user_model().objects.create_user(
        email=f"adlead-{suffix}@example.com",
        password="AdLeadPass123!",
        username=f"adlead_{suffix}",
        role="user",
        status="active",
        is_active=True,
    )


def _conversion(*, ad, user=None, campaign_id=None, conversion_type=None):
    return AdConversionIntent.objects.create(
        ad=ad,
        user=user,
        campaign_id=campaign_id,
        conversion_type=conversion_type or AdConversionIntent.CONVERSION_OTHER,
    )


class AdLeadFoundationTests(TestCase):
    def setUp(self):
        self.ad = _script_ad()

    def test_create_ad_lead_from_valid_conversion(self):
        conversion = _conversion(ad=self.ad, campaign_id="camp-1")
        lead = create_ad_lead_from_conversion(
            conversion, AdLead.SOURCE_WHATSAPP_CTA
        )
        self.assertIsNotNone(lead.pk)
        self.assertEqual(lead.source_conversion_id, conversion.pk)
        self.assertEqual(AdLead.objects.count(), 1)

    def test_advertisement_is_copied_from_conversion(self):
        conversion = _conversion(ad=self.ad)
        lead = create_ad_lead_from_conversion(
            conversion, AdLead.SOURCE_BOOKING_INTENT
        )
        self.assertEqual(lead.advertisement_id, self.ad.pk)
        self.assertEqual(lead.advertisement_id, conversion.ad_id)

    def test_campaign_id_snapshot_is_copied_from_conversion(self):
        live_campaign = Campaign.objects.create(
            name="Live Campaign Must Not Replace Snapshot",
            status=Campaign.STATUS_ACTIVE,
        )
        ad = _script_ad(name="Snap Ad", campaign=live_campaign)
        conversion = _conversion(ad=ad, campaign_id="historical-snap-99")
        lead = create_ad_lead_from_conversion(
            conversion, AdLead.SOURCE_WHATSAPP_CTA
        )
        self.assertEqual(lead.campaign_id, "historical-snap-99")
        self.assertEqual(lead.campaign_id, conversion.campaign_id)
        self.assertNotEqual(lead.campaign_id, str(live_campaign.pk))

    def test_authenticated_user_is_copied_from_conversion(self):
        user = _user("auth")
        conversion = _conversion(ad=self.ad, user=user)
        lead = create_ad_lead_from_conversion(
            conversion, AdLead.SOURCE_WHATSAPP_CTA
        )
        self.assertEqual(lead.user_id, user.pk)

    def test_anonymous_user_is_allowed(self):
        conversion = _conversion(ad=self.ad, user=None)
        lead = create_ad_lead_from_conversion(
            conversion, AdLead.SOURCE_BOOKING_INTENT
        )
        self.assertIsNone(lead.user_id)

    def test_source_choices_work(self):
        wa = create_ad_lead_from_conversion(
            _conversion(ad=self.ad), AdLead.SOURCE_WHATSAPP_CTA
        )
        booking = create_ad_lead_from_conversion(
            _conversion(ad=_script_ad(name="Booking Ad")),
            AdLead.SOURCE_BOOKING_INTENT,
        )
        self.assertEqual(wa.source, "whatsapp_cta")
        self.assertEqual(booking.source, "booking_intent")
        labels = dict(AdLead.SOURCE_CHOICES)
        self.assertEqual(labels["whatsapp_cta"], "WhatsApp CTA")
        self.assertEqual(labels["booking_intent"], "Booking Intent")

    def test_default_status_is_new(self):
        lead = create_ad_lead_from_conversion(
            _conversion(ad=self.ad), AdLead.SOURCE_WHATSAPP_CTA
        )
        self.assertEqual(lead.status, AdLead.STATUS_NEW)
        self.assertEqual(lead.status, "new")

    def test_timestamps_exist(self):
        lead = create_ad_lead_from_conversion(
            _conversion(ad=self.ad), AdLead.SOURCE_WHATSAPP_CTA
        )
        self.assertIsNotNone(lead.created_at)
        self.assertIsNotNone(lead.updated_at)

    def test_source_conversion_is_unique(self):
        conversion = _conversion(ad=self.ad)
        AdLead.objects.create(
            source_conversion=conversion,
            advertisement=self.ad,
            source=AdLead.SOURCE_WHATSAPP_CTA,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                AdLead.objects.create(
                    source_conversion=conversion,
                    advertisement=self.ad,
                    source=AdLead.SOURCE_BOOKING_INTENT,
                )
        self.assertEqual(AdLead.objects.filter(source_conversion=conversion).count(), 1)

    def test_deleting_conversion_does_not_delete_lead(self):
        conversion = _conversion(ad=self.ad)
        lead = create_ad_lead_from_conversion(
            conversion, AdLead.SOURCE_WHATSAPP_CTA
        )
        lead_id = lead.pk
        conversion.delete()
        lead.refresh_from_db()
        self.assertEqual(lead.pk, lead_id)
        self.assertIsNone(lead.source_conversion_id)

    def test_deleting_user_sets_lead_user_to_null(self):
        user = _user("delete")
        conversion = _conversion(ad=self.ad, user=user)
        lead = create_ad_lead_from_conversion(
            conversion, AdLead.SOURCE_WHATSAPP_CTA
        )
        # accounts.User.delete() blocks hard delete; queryset delete exercises
        # the FK on_delete=SET_NULL path that would run if the row is removed.
        get_user_model().objects.filter(pk=user.pk).delete()
        lead.refresh_from_db()
        self.assertIsNone(lead.user_id)
        self.assertTrue(AdLead.objects.filter(pk=lead.pk).exists())

    def test_deleting_advertisement_cascades_to_lead(self):
        conversion = _conversion(ad=self.ad)
        lead = create_ad_lead_from_conversion(
            conversion, AdLead.SOURCE_WHATSAPP_CTA
        )
        lead_id = lead.pk
        self.ad.delete()
        self.assertFalse(AdLead.objects.filter(pk=lead_id).exists())

    def test_same_conversion_twice_does_not_create_duplicate(self):
        conversion = _conversion(ad=self.ad)
        first = create_ad_lead_from_conversion(
            conversion, AdLead.SOURCE_WHATSAPP_CTA
        )
        second = create_ad_lead_from_conversion(
            conversion, AdLead.SOURCE_BOOKING_INTENT
        )
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(AdLead.objects.filter(source_conversion=conversion).count(), 1)

    def test_invalid_source_is_rejected(self):
        conversion = _conversion(ad=self.ad)
        with self.assertRaises(ValueError):
            create_ad_lead_from_conversion(conversion, "profile_view")
        with self.assertRaises(ValueError):
            create_ad_lead_from_conversion(conversion, "other")
        self.assertEqual(AdLead.objects.count(), 0)

    def test_no_pii_or_session_fields_on_ad_lead(self):
        names = {field.name for field in AdLead._meta.get_fields()}
        forbidden = {
            "phone",
            "email",
            "name",
            "ip",
            "fingerprint",
            "device_id",
            "session_id",
            "session",
        }
        self.assertTrue(forbidden.isdisjoint(names))

    def test_ad_conversion_intent_fields_unchanged(self):
        local = {field.name for field in AdConversionIntent._meta.local_fields}
        self.assertEqual(
            local,
            {
                "id",
                "ad",
                "campaign_id",
                "user",
                "pandit_id",
                "conversion_type",
                "timestamp",
            },
        )
        self.assertEqual(
            AdConversionIntent.CONVERSION_TYPES,
            [
                ("booking_intent", "Booking intent"),
                ("profile_view", "Profile view"),
                ("other", "Other"),
            ],
        )

    def test_no_lead_event_model_exists(self):
        with self.assertRaises(LookupError):
            apps.get_model("ads_analytics", "LeadEvent")
        model_names = {model.__name__ for model in apps.get_models()}
        self.assertNotIn("LeadEvent", model_names)

    def test_model_indexes_exist_as_intended(self):
        index_fields = [tuple(index.fields) for index in AdLead._meta.indexes]
        self.assertIn(("status", "created_at"), index_fields)
        self.assertIn(("advertisement", "created_at"), index_fields)
        self.assertTrue(AdLead._meta.get_field("campaign_id").db_index)
        self.assertEqual(len(AdLead._meta.indexes), 2)
