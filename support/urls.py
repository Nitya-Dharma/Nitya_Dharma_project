"""
URL configuration for support app.
"""
from django.urls import path
from . import views

app_name = 'support'

urlpatterns = [
    path('contact-us/', views.contact_us, name='contact_us'),
    path('support/admin/contact-requests/', views.contact_requests_admin, name='contact_requests_admin'),
]

