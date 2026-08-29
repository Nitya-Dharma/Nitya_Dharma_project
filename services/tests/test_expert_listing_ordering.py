"""Deterministic default ordering for paginated Expert service listings."""

import warnings
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.core.paginator import UnorderedObjectListWarning
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from core.models import ExpertProfile, ExpertService
from services.views_astrology import astrology_service_view
from services.views_numerology import numerology_service_view
from services.views_palmistry import palmistry_service_view


class ExpertListingOrderingTests(TestCase):
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
        cls.factory = RequestFactory()
        cls.cases = (
            (
                astrology_service_view,
                "/services/astrology/",
                "services.views_astrology.render",
                cls.astrology,
            ),
            (
                numerology_service_view,
                "/services/numerology/",
                "services.views_numerology.render",
                cls.numerology,
            ),
            (
                palmistry_service_view,
                "/services/palmistry/",
                "services.views_palmistry.render",
                cls.palmistry,
            ),
        )

    def create_expert(self, name, service, *, experience_years, expert_type):
        expert = ExpertProfile.objects.create(
            name=name,
            expert_type=expert_type,
            experience_years=experience_years,
            is_active=True,
        )
        expert.services.set([service])
        return expert

    def render_listing(self, view, path, render_target, query=""):
        request = self.factory.get(f"{path}{query}")
        request.user = AnonymousUser()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", UnorderedObjectListWarning)
            with patch(render_target, return_value=HttpResponse()) as mocked_render:
                view(request)
        unordered = [
            item
            for item in caught
            if issubclass(item.category, UnorderedObjectListWarning)
        ]
        page = mocked_render.call_args.args[2]["experts"]
        return page, unordered

    def test_default_listing_is_ordered_and_paginated_without_warning(self):
        type_by_service = {
            self.astrology: "ASTROLOGER",
            self.numerology: "NUMEROLOGIST",
            self.palmistry: "PALMIST",
        }
        for view, path, render_target, service in self.cases:
            with self.subTest(path=path):
                ExpertProfile.objects.all().delete()
                expert_type = type_by_service[service]
                low = self.create_expert(
                    "Low Exp", service, experience_years=2, expert_type=expert_type
                )
                high_b = self.create_expert(
                    "High B", service, experience_years=10, expert_type=expert_type
                )
                high_a = self.create_expert(
                    "High A", service, experience_years=10, expert_type=expert_type
                )
                page, unordered = self.render_listing(view, path, render_target)
                self.assertEqual(unordered, [])
                self.assertEqual(page.paginator.per_page, 6)
                self.assertEqual(
                    page.paginator.object_list.query.order_by,
                    ("-experience_years", "pk"),
                )
                ordered_pks = list(
                    page.paginator.object_list.values_list("pk", flat=True)
                )
                # Same experience → pk ASC tie-break, then lower experience.
                tie_sorted = sorted([high_a.pk, high_b.pk])
                self.assertEqual(ordered_pks, tie_sorted + [low.pk])

    def test_explicit_exp_sorts_preserve_prior_order_by(self):
        for view, path, render_target, service in self.cases:
            with self.subTest(path=path, sort="exp_desc"):
                page, unordered = self.render_listing(
                    view, path, render_target, "?sort=exp_desc"
                )
                self.assertEqual(unordered, [])
                self.assertEqual(
                    page.paginator.object_list.query.order_by,
                    ("-experience_years",),
                )
            with self.subTest(path=path, sort="exp_asc"):
                page, unordered = self.render_listing(
                    view, path, render_target, "?sort=exp_asc"
                )
                self.assertEqual(unordered, [])
                self.assertEqual(
                    page.paginator.object_list.query.order_by,
                    ("experience_years",),
                )
