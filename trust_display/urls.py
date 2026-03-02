"""
URL configuration for trust_display app.

Task 10.17: Trust Data Exposure APIs

Backend-only, read-only APIs for trust display.
"""

from django.urls import path
from . import views

app_name = 'trust_display'

urlpatterns = [
    # Trust display data
    path('pandit/<int:pandit_id>/', views.get_trust_display, name='get_trust_display'),
    path('pandit/<int:pandit_id>/badges/', views.get_trust_badges, name='get_trust_badges'),
]


























