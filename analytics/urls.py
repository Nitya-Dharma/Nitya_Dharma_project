"""
Analytics URL Configuration

Internal-only APIs for dashboard consumption (Module 5).
"""

from django.urls import path
from analytics.views import (
    analytics_events_list,
    analytics_aggregated,
    analytics_summary,
    analytics_access_logs_list,
)

urlpatterns = [
    path('events/', analytics_events_list, name='analytics-events-list'),
    path('events/aggregated/', analytics_aggregated, name='analytics-aggregated'),
    path('events/summary/', analytics_summary, name='analytics-summary'),
    path('access-logs/', analytics_access_logs_list, name='analytics-access-logs-list'),
]
