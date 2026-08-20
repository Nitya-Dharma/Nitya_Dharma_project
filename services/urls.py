from django.urls import path

from .views import (
    astrology_city_view,
    expert_booking_intent_view,
    numerology_city_view,
    palmistry_city_view,
)
from .views_astrology import astrology_service_view
from .views_expert_ui import expert_pending_page, expert_profile_page, expert_register_page
from .views_numerology import numerology_service_view
from .views_palmistry import palmistry_service_view

urlpatterns = [
    path("astrology/", astrology_service_view, name="astrology_service"),
    path("numerology/", numerology_service_view, name="numerology_service"),
    path("palmistry/", palmistry_service_view, name="palmistry_service"),
    path("astrology/<str:city>/", astrology_city_view, name="astrology_city"),
    path("numerology/<str:city>/", numerology_city_view, name="numerology_city"),
    path("palmistry/<str:city>/", palmistry_city_view, name="palmistry_city"),
    path("expert/register/", expert_register_page, name="expert_register"),
    path("expert/pending/", expert_pending_page, name="expert_pending"),
    path(
        "expert/<int:expert_id>/intent/",
        expert_booking_intent_view,
        name="expert_booking_intent",
    ),
    path("expert/<int:id>/", expert_profile_page, name="expert_profile"),
]
