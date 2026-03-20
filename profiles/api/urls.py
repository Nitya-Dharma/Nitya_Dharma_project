"""
URL configuration for profiles API (STEP-2: location update).
Mounted at /api/pandit/ in main urlconf.
"""
from django.urls import path

from .location_update_api import update_pandit_location

app_name = "profiles_api"

urlpatterns = [
    path("update-location/", update_pandit_location, name="update_pandit_location"),
]
