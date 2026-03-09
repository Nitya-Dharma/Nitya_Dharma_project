from django.urls import path
from .views import track_behavior, track_event
from .admin_dashboard_views import super_admin_analytics_dashboard

urlpatterns = [
    path("track/", track_behavior, name="behavior_track"),
    path("track-event/", track_event, name="behavior_track_event"),  # Phase 14: UserBehaviorEvent
    path(
        "super-admin-dashboard/",
        super_admin_analytics_dashboard,
        name="super_admin_analytics_dashboard",
    ),
]
