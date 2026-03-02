"""
URL configuration for notifications app.

Task 17.UI: Notification UI (Template-based)
"""
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # UI endpoints (HTML templates)
    path('', views.notifications_list, name='list'),
    path('<int:notification_id>/mark-read/', views.mark_notification_read, name='mark_read'),
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
]
























