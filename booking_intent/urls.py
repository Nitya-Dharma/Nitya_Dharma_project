"""
URL configuration for booking_intent app.

Task 8.10: Booking Intent APIs & Services
Task 8.UI: Booking Intent UI (Template-based)

Backend-only APIs and UI templates for booking intent operations.
"""

from django.urls import path
from . import views
from . import views_ui

app_name = 'booking_intent'

urlpatterns = [
    # UI endpoints (HTML templates)
    path('history/', views_ui.booking_history, name='history'),
    path('inbox/', views_ui.booking_inbox, name='inbox'),
    path('create/<str:pandit_public_id>/', views_ui.create_booking_intent_form, name='create'),
    
    # API endpoints (JSON) - use public_id
    path('api/create/', views.create_intent, name='create_intent'),
    path('my-intents/', views.list_my_intents, name='list_my_intents'),
    path('received-intents/', views.list_received_intents, name='list_received_intents'),
    path('<str:public_id>/', views.get_intent, name='get_intent'),
    path('<str:public_id>/cancel/', views.cancel_intent, name='cancel_intent'),
    path('<str:public_id>/mark-viewed/', views.mark_as_viewed, name='mark_as_viewed'),
    path('governance/', views.list_all_for_governance, name='list_all_for_governance'),
    path('<str:public_id>/flag/', views.flag_intent, name='flag_intent'),
]


