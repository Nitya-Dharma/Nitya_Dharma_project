from django.urls import path
from .views import track_behavior
from .admin_dashboard_views import super_admin_analytics_dashboard

urlpatterns = [
    path("track/", track_behavior, name="behavior_track"),
    path(
        "super-admin-dashboard/",
        super_admin_analytics_dashboard,
        name="super_admin_analytics_dashboard",
    ),
]
