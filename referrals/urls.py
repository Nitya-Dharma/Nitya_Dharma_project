"""
URL configuration for referrals app.

This module defines URL patterns for referral link generation and management.
All endpoints require Admin Pandit or Super Admin access.
"""

from django.urls import path
from . import views

app_name = 'referrals'

urlpatterns = [
    path('generate/', views.generate_referral_link, name='generate_referral_link'),
    path('policy/', views.get_referral_policy, name='get_referral_policy'),
    path('policy/edit/', views.referral_policy_edit, name='referral_policy_edit'),
    path('<int:referral_link_id>/deactivate/', views.deactivate_referral_link, name='deactivate_referral_link'),
]






































