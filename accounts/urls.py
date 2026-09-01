"""
URL configuration for accounts app.

This file defines URL patterns for user authentication and account management.
"""
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views_password_reset import EnhancedPasswordResetView, EnhancedPasswordResetConfirmView

app_name = 'accounts'

urlpatterns = [
    # User authentication endpoints
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Password reset endpoints (using enhanced views with security features)
    path('password-reset/', EnhancedPasswordResetView.as_view(), name='password_reset'),
    
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='password_reset_done'),
    
    # Password reset confirmation - handles both valid tokens and 'set-password' for invalid tokens
    path('password-reset-confirm/<uidb64>/<token>/', EnhancedPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    # Pandit registration endpoint (referral-based)
    # URL format: /accounts/pandit/register/<referral_token>/
    path(
        'pandit/register/skip-phone-otp/',
        views.pandit_register_skip_phone_otp,
        name='pandit_register_skip_phone_otp',
    ),
    path('pandit/register/<str:referral_token>/', views.pandit_register, name='pandit_register'),
    
    # Pandit approval workflow (Admin & Super Admin only)
    # URL format: /accounts/pandit/<user_id>/approve/
    path('pandit/<int:user_id>/approve/', views.approve_pandit, name='approve_pandit'),
    
    # Pandit rejection workflow (Admin & Super Admin only)
    # URL format: /accounts/pandit/<user_id>/reject/
    path('pandit/<int:user_id>/reject/', views.reject_pandit, name='reject_pandit'),
    
    # Account Settings (My Account)
    path('settings/', views.account_settings_base, name='account_settings'),
    path('settings/profile/', views.profile_settings, name='profile_settings'),
    path('settings/security/', views.security_settings, name='security_settings'),
    path('settings/notifications/', views.account_notifications, name='account_notifications'),
    path('settings/delete/', views.account_delete, name='account_delete'),
    
    # Role-specific notification settings with user_id
    path('user/<int:user_id>/settings/notifications/', views.user_notification_settings, name='user_notification_settings'),
    path('pandit/<int:user_id>/settings/notifications/', views.pandit_notification_settings, name='pandit_notification_settings'),
    path('admin/<int:user_id>/settings/notifications/', views.admin_notification_settings, name='admin_notification_settings'),
    
    # Account Settings with user_id identifiers
    path('user/<int:user_id>/settings/profile/', views.profile_settings_with_id, name='profile_settings_with_id'),
    path('user/<int:user_id>/settings/security/', views.security_settings_with_id, name='security_settings_with_id'),
    
    # Admin Pandit Notification List (with tabs for users, pandits, temples)
    path('admin/<int:user_id>/notifications/', views.admin_notification_list, name='admin_notification_list'),
    
    # Email verification (TASK 3)
    path('verify-email/<str:token>/', views.verify_email_view, name='verify_email'),
    
    # Email verification resend (TASK 4: Resend capability)
    path(
        'pandits/<str:pandit_public_id>/resend-verification/',
        views.resend_pandit_verification,
        name='resend_pandit_verification'
    ),
    
    # Theme preference update (AJAX endpoint)
    path('update-theme-preference/', views.update_theme_preference, name='update_theme_preference'),
]

