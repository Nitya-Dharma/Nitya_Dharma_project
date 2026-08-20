from django.test import TestCase

from core.models import ExpertService
from services.expert_service_selection import (
    ExpertServiceSelectionError,
    primary_expert_type,
    resolve_active_services_by_ids,
    resolve_active_services_by_slugs,
    service_slugs,
)


class ExpertServiceSelectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.astrology, _ = ExpertService.objects.get_or_create(
            slug="astrology",
            defaults={"name": "Astrology", "display_order": 1},
        )
        cls.numerology, _ = ExpertService.objects.get_or_create(
            slug="numerology",
            defaults={"name": "Numerology", "display_order": 2},
        )
        cls.palmistry, _ = ExpertService.objects.get_or_create(
            slug="palmistry",
            defaults={"name": "Palmistry", "display_order": 3},
        )

    def test_ids_are_resolved_in_priority_order(self):
        services = resolve_active_services_by_ids(
            [self.palmistry.id, self.astrology.id, self.numerology.id]
        )
        self.assertEqual(
            service_slugs(services),
            ["astrology", "numerology", "palmistry"],
        )
        self.assertEqual(primary_expert_type(services), "ASTROLOGER")

    def test_slugs_are_resolved_in_priority_order(self):
        services = resolve_active_services_by_slugs(["palmistry", "numerology"])
        self.assertEqual(service_slugs(services), ["numerology", "palmistry"])
        self.assertEqual(primary_expert_type(services), "NUMEROLOGIST")

    def test_zero_services_is_rejected(self):
        with self.assertRaisesMessage(
            ExpertServiceSelectionError,
            "Please select at least one service.",
        ):
            resolve_active_services_by_ids([])

    def test_invalid_id_is_rejected_without_partial_resolution(self):
        with self.assertRaisesMessage(
            ExpertServiceSelectionError,
            "Please select valid active services.",
        ):
            resolve_active_services_by_ids([self.astrology.id, 999999])

    def test_inactive_service_is_rejected(self):
        self.numerology.is_active = False
        self.numerology.save(update_fields=["is_active"])
        with self.assertRaisesMessage(
            ExpertServiceSelectionError,
            "Please select valid active services.",
        ):
            resolve_active_services_by_ids([self.numerology.id])

    def test_unknown_slug_is_rejected(self):
        with self.assertRaisesMessage(
            ExpertServiceSelectionError,
            "Please select valid active services.",
        ):
            resolve_active_services_by_slugs(["astrology", "unknown"])
