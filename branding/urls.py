"""
URL configuration for branding app.
"""
from django.urls import path
from . import views

app_name = 'branding'

urlpatterns = [
    path('manage/', views.manage_logos, name='manage_logos'),
    path('activate/<int:logo_id>/', views.activate_logo, name='activate_logo'),
]









