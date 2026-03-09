"""
Phase 15: Recommendation API routes. Read-only.
"""
from django.urls import path
from recommendation_engine import views

app_name = "recommendation_engine"

urlpatterns = [
    path("trending-pandits/", views.trending_pandits),
    path("popular-poojas/", views.popular_poojas),
    path("trending-searches/", views.trending_searches),
    path("similar-pandits/<int:pandit_id>/", views.similar_pandits),
    path("recently-viewed/", views.recently_viewed),
]
