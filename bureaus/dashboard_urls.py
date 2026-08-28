from django.urls import path

from .views import bureau_dashboard_view

app_name = "bureaus_dashboard"

urlpatterns = [
    path("", bureau_dashboard_view, name="bureau_dashboard"),
]
