"""
URL configuration for search app.

Task 7.14: Search API (Read-Only)
Task 7.UI: Search UI (Template-based)

Read-only GET endpoints only.
"""

from django.urls import path
from . import views
from . import views_ui

app_name = 'search'

urlpatterns = [
    # API endpoints (JSON)
    path('pandits/', views.search_pandits, name='search_pandits'),
    
    # UI endpoints (HTML templates)
    path('results/', views_ui.search_results, name='search_results'),
]


