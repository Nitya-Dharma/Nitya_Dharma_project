from django.urls import path
from . import views
from .views import (
    bureau_booking_intent_view,
    bureau_detail_view,
    bureau_list_view,
    bureau_profile_edit_view,
    bureau_review_submit_view,
    bureau_register_view,
)

app_name = "bureaus"

urlpatterns = [
    path("", bureau_list_view, name="bureau_list"),
    path("register/", bureau_register_view, name="bureau_register"),
    path("profile/edit/", bureau_profile_edit_view, name="bureau_profile_edit"),
    path(
        "intent/<int:intent_id>/mark-viewed/",
        views.mark_intent_viewed,
        name="mark_intent_viewed"
    ),
    path("<uuid:public_id>/intent/", bureau_booking_intent_view, name="bureau_intent"),
    path("<uuid:public_id>/review/", bureau_review_submit_view, name="bureau_review"),
    path("<uuid:public_id>/", bureau_detail_view, name="bureau_detail"),
    path("<str:city>/", views.bureau_city_view, name="bureau_city"),
]
