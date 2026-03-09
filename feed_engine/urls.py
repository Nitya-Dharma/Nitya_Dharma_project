"""
Phase 17A: Feed engine URLs. Independent of search and recommendation APIs.
"""
from django.urls import path
from feed_engine import views

app_name = "feed_engine"

urlpatterns = [
    path("", views.feed_page, name="feed_page"),
    path("personalized/", views.personalized_feed),
]
