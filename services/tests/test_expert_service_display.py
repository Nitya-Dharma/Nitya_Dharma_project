from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.db.models import Prefetch
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase
from django.urls import reverse

from core.models import ExpertProfile, ExpertService
from services.views import _experts_for_city_slug


class ExpertServiceDisplayTests(TestCase):
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
        cls.hidden_service = ExpertService.objects.create(
            slug="hidden-display-service",
            name="Hidden Service",
            is_active=False,
            display_order=0,
        )
        cls.factory = RequestFactory()

    def create_expert(self, name, services, *, experience_years=8):
        expert = ExpertProfile.objects.create(
            name=name,
            expert_type="ASTROLOGER",
            experience_years=experience_years,
            description="Existing profile information",
            is_active=True,
        )
        expert.services.set(services)
        return expert

    def active_service_expert(self, expert):
        return (
            ExpertProfile.objects.filter(pk=expert.pk)
            .prefetch_related(
                Prefetch(
                    "services",
                    queryset=ExpertService.objects.filter(is_active=True),
                    to_attr="active_services",
                )
            )
            .get()
        )

    def render_card(self, expert):
        request = self.factory.get("/")
        request.user = AnonymousUser()
        return render_to_string(
            "services/_card.html",
            {"expert": expert, "user": request.user},
            request=request,
        )

    @staticmethod
    def services_section(response):
        html = response.content.decode()
        start = html.index("<h5>Services Offered</h5>")
        end = html.index('<div class="tab-pane fade" id="location">', start)
        return html[start:end]

    def test_card_displays_one_active_service_and_existing_content(self):
        expert = self.create_expert("Single Service Expert", [self.astrology])
        html = self.render_card(self.active_service_expert(expert))

        self.assertIn("Single Service Expert", html)
        self.assertIn("8 yrs experience", html)
        self.assertIn("Astrology", html)
        self.assertNotIn("Numerology", html)
        self.assertIn("Send Booking Intent", html)

    def test_card_displays_multiple_services_once_in_catalog_order(self):
        expert = self.create_expert(
            "Multi Service Expert",
            [
                self.palmistry,
                self.hidden_service,
                self.astrology,
                self.numerology,
            ],
        )
        html = self.render_card(self.active_service_expert(expert))

        self.assertEqual(html.count("Astrology"), 1)
        self.assertEqual(html.count("Numerology"), 1)
        self.assertEqual(html.count("Palmistry"), 1)
        self.assertNotIn("Hidden Service", html)
        self.assertLess(html.index("Astrology"), html.index("Numerology"))
        self.assertLess(html.index("Numerology"), html.index("Palmistry"))

    def test_card_omits_services_for_service_less_expert(self):
        expert = self.create_expert("No Services", [])
        html = self.render_card(self.active_service_expert(expert))

        self.assertNotIn(">Services<", html)
        self.assertNotIn("Astrologer", html)

    def test_card_query_sources_attach_prefetched_active_services(self):
        from search.views_ui import search_results
        from services.views_astrology import astrology_service_view
        from services.views_numerology import numerology_service_view
        from services.views_palmistry import palmistry_service_view

        expert = self.create_expert(
            "All Service Sources",
            [self.astrology, self.numerology, self.palmistry],
        )
        cases = (
            (
                astrology_service_view,
                "/services/astrology/",
                "services.views_astrology.render",
            ),
            (
                numerology_service_view,
                "/services/numerology/",
                "services.views_numerology.render",
            ),
            (
                palmistry_service_view,
                "/services/palmistry/",
                "services.views_palmistry.render",
            ),
            (
                search_results,
                "/search/results/?tab=astrology",
                "search.views_ui.render",
            ),
        )

        for view, path, render_target in cases:
            request = self.factory.get(path)
            request.user = AnonymousUser()
            with patch(render_target, return_value=HttpResponse()) as mocked_render:
                view(request)
            page_experts = list(mocked_render.call_args.args[2]["experts"])
            rendered_expert = next(item for item in page_experts if item.pk == expert.pk)
            self.assertEqual(
                [service.name for service in rendered_expert.active_services],
                ["Astrology", "Numerology", "Palmistry"],
            )

        city_expert = next(
            item
            for item in _experts_for_city_slug("astrology", "profile")
            if item.pk == expert.pk
        )
        self.assertEqual(
            [service.name for service in city_expert.active_services],
            ["Astrology", "Numerology", "Palmistry"],
        )

    def test_prefetched_service_access_does_not_issue_per_expert_queries(self):
        for index in range(3):
            self.create_expert(f"Prefetched {index}", [self.astrology])

        from services.views_astrology import astrology_service_view

        request = self.factory.get("/services/astrology/")
        request.user = AnonymousUser()
        with patch(
            "services.views_astrology.render",
            return_value=HttpResponse(),
        ) as mocked_render:
            astrology_service_view(request)
        experts = list(mocked_render.call_args.args[2]["experts"])

        with self.assertNumQueries(0):
            displayed_services = [
                [service.name for service in expert.active_services]
                for expert in experts
            ]
        self.assertEqual(displayed_services, [["Astrology"]] * 3)

    def test_public_profile_displays_active_services_and_preserves_controls(self):
        expert = self.create_expert(
            "Public Multi Expert",
            [
                self.palmistry,
                self.hidden_service,
                self.astrology,
                self.numerology,
            ],
            experience_years=12,
        )
        expert.phone = "9876543210"
        expert.save(update_fields=["phone"])
        response = self.client.get(reverse("expert_profile", args=[expert.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Public Multi Expert")
        self.assertContains(response, "12 years experience")
        self.assertContains(response, "Existing profile information")
        # Anonymous visitors see the existing login-to-book control, not the
        # authenticated booking form that posts to expert_booking_intent.
        self.assertContains(response, "Please login to send booking request.")
        self.assertContains(response, "Login to Send Booking Intent")
        self.assertContains(response, reverse("accounts:login"))
        self.assertContains(response, "%23booking")
        self.assertNotContains(
            response,
            reverse("expert_booking_intent", args=[expert.pk]),
        )
        self.assertContains(response, "https://wa.me/919876543210")

        section = self.services_section(response)
        self.assertNotIn("Hidden Service", section)
        self.assertEqual(section.count("Astrology"), 1)
        self.assertEqual(section.count("Numerology"), 1)
        self.assertEqual(section.count("Palmistry"), 1)
        self.assertLess(section.index("Astrology"), section.index("Numerology"))
        self.assertLess(section.index("Numerology"), section.index("Palmistry"))

    def test_public_profile_does_not_invent_service_for_empty_m2m(self):
        expert = self.create_expert("Service-less Expert", [])
        response = self.client.get(reverse("expert_profile", args=[expert.pk]))

        self.assertEqual(response.status_code, 200)
        section = self.services_section(response)
        self.assertNotIn("Astrologer", section)
        self.assertNotIn("Expert Service", section)
        self.assertNotContains(response, '<i class="bi bi-stars"></i>', html=False)
