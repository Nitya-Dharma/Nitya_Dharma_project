"""
URL configuration for Super Admin advertisement management.

Mounted under dashboard/super-admin/advertisements/ (included from dashboards.urls).
"""

from django.urls import path
from . import views

app_name = 'ads'

urlpatterns = [
    path('', views.advertisement_list, name='advertisement_list'),
    path('create/', views.advertisement_create, name='advertisement_create'),
    path('<int:pk>/edit/', views.advertisement_edit, name='advertisement_edit'),
    path('<int:pk>/toggle/', views.advertisement_toggle, name='advertisement_toggle'),
    path('<int:pk>/delete/', views.advertisement_delete, name='advertisement_delete'),
    path('campaigns/', views.campaign_list, name='campaign_list'),
    path('campaigns/create/', views.campaign_create, name='campaign_create'),
    path('campaigns/<int:pk>/edit/', views.campaign_edit, name='campaign_edit'),
    path('campaigns/<int:pk>/toggle/', views.campaign_toggle, name='campaign_toggle'),
    path('adsets/', views.adset_list, name='adset_list'),
    path('adsets/create/', views.adset_create, name='adset_create'),
    path('adsets/<int:pk>/edit/', views.adset_edit, name='adset_edit'),
    path('adsets/<int:pk>/toggle/', views.adset_toggle, name='adset_toggle'),
]
