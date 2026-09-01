from django.urls import path

from .views import (
    astrology_city_view,
    expert_booking_intent_view,
    mark_expert_intent_viewed,
    numerology_city_view,
    palmistry_city_view,
)
from .views_astrology import astrology_service_view
from .views_expert_ui import become_expert_home, expert_type_page, expert_pending_page, expert_profile_page, expert_register_page, expert_register_skip_phone_otp
from .views_numerology import numerology_service_view
from .views_palmistry import palmistry_service_view

urlpatterns = [
    path("astrology/", astrology_service_view, name="astrology_service"),
    path("numerology/", numerology_service_view, name="numerology_service"),
    path("palmistry/", palmistry_service_view, name="palmistry_service"),
    path("astrology/<str:city>/", astrology_city_view, name="astrology_city"),
    path("numerology/<str:city>/", numerology_city_view, name="numerology_city"),
    path("palmistry/<str:city>/", palmistry_city_view, name="palmistry_city"),
    path("become-expert/", become_expert_home, name="become_expert"),
    path("become-expert/<str:expert_type>/", expert_type_page, name="expert_type_page"),
    path("expert/register/", expert_register_page, name="expert_register"),
    path(
        "expert/register/skip-phone-otp/",
        expert_register_skip_phone_otp,
        name="expert_register_skip_phone_otp",
    ),
    path("expert/pending/", expert_pending_page, name="expert_pending"),
    path(
        "expert/intent/<int:intent_id>/mark-viewed/",
        mark_expert_intent_viewed,
        name="mark_expert_intent_viewed",
    ),
    path(
        "expert/<int:expert_id>/intent/",
        expert_booking_intent_view,
        name="expert_booking_intent",
    ),
    path("expert/<int:id>/", expert_profile_page, name="expert_profile"),
]
