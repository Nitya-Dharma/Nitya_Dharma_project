"""
Phase 12: Monitoring URL routes. Observational endpoints only.
"""
from django.urls import path
from . import views

app_name = "monitoring"

urlpatterns = [
    path("health/", views.system_health_view, name="system_health"),
    path("metrics/", views.metrics_view, name="metrics"),
]
