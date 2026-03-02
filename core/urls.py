"""
URL configuration for core app.
"""
from django.urls import path
from . import views
from . import health_checks
from . import views_follow

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('health/', health_checks.health_check, name='health_check'),
    
    # Follow system
    path('follow/pandit/<str:pandit_public_id>/', views_follow.follow_pandit, name='follow_pandit'),
    path('unfollow/pandit/<str:pandit_public_id>/', views_follow.unfollow_pandit, name='unfollow_pandit'),
    path('follow/temple/<str:page_public_id>/', views_follow.follow_temple, name='follow_temple'),
    path('unfollow/temple/<str:page_public_id>/', views_follow.unfollow_temple, name='unfollow_temple'),
    path('follow/status/<str:entity_type>/<str:entity_public_id>/', views_follow.check_follow_status, name='check_follow_status'),
]
