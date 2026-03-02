"""
URL configuration for masterdata app.
"""

from django.urls import path
from . import views

app_name = 'masterdata'

urlpatterns = [
    path('management/', views.master_data_management, name='management'),
    path('upload/cities/', views.upload_cities, name='upload_cities'),
    path('upload/mandals/', views.upload_mandals, name='upload_mandals'),
    path('upload/local-areas/', views.upload_local_areas, name='upload_local_areas'),
    path('upload/pooja-categories/', views.upload_pooja_categories, name='upload_pooja_categories'),
    path('upload/poojas/', views.upload_poojas, name='upload_poojas'),
    path('download-sample/<str:entity_type>/', views.download_sample_csv, name='download_sample'),
    path('toggle-status/<str:entity_type>/<int:entity_id>/', views.toggle_status, name='toggle_status'),
]






