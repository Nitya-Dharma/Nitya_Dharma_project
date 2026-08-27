"""
URL configuration for nityadharma project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from django.views.defaults import page_not_found, server_error
from django.views.generic import TemplateView
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import user_passes_test
from core import views as core_views
from pages import views_static
from branding import views as branding_views


def custom_404(request, exception):
    return page_not_found(request, exception, template_name='errors/404.html')


def custom_500(request):
    return server_error(request, template_name='errors/500.html')


handler404 = custom_404
handler500 = custom_500

# 🔐 Secure admin path (change as needed)
SECURE_ADMIN_PATH = 'restricted-django-admin-page-of-nityadharma-secure-admin-portal-2k25/'


def superuser_required(view):
    decorated_view = user_passes_test(
        lambda u: u.is_active and u.is_superuser,
        login_url='/'
    )(view)
    return decorated_view


# Enforce superuser-only admin access globally.
# NOTE: Django's admin URLConf is a resolver, so decorator wrapping is not applied directly here.
admin.site.has_permission = lambda request: bool(
    request.user.is_active and request.user.is_superuser
)

urlpatterns = [
    path(SECURE_ADMIN_PATH, admin.site.urls),
    path('admin/', lambda request: HttpResponseForbidden("Admin access is blocked")),
    path('nd-control-panel/', RedirectView.as_view(url='/' + SECURE_ADMIN_PATH, permanent=False)),
    path(
        'service-worker.js',
        TemplateView.as_view(
            template_name='pwa/service-worker.js',
            content_type='application/javascript',
        ),
        name='service-worker',
    ),
    path('manifest.json', branding_views.manifest_json, name='manifest_json'),
    path('', include('core.urls')),
    path('offline/', core_views.offline, name='offline'),
    path('accounts/', include('accounts.urls')),
    path('profiles/', include('profiles.urls')),  # Profiles app URLs
    path('api/pandit/', include('profiles.api.urls')),  # STEP-2: Pandit location update API
    path('referrals/', include('referrals.urls')),
    path('dashboard/', include('dashboards.urls')),
    path('dashboard/super-admin/advertisements/', include(('ads.urls', 'ads'))),
    path('track/ad/', include('ads_analytics.urls')),
    path('search/', include(('search.urls', 'search'), namespace='search_ui')),  # UI search pages
    path('api/search/', include(('search.urls', 'search'), namespace='search_api')),  # API search endpoints
    path('api/recommendations/', include(('search.urls', 'search'), namespace='recommendations_api')),  # Phase 11F recommendation API
    path('booking-intent/', include(('booking_intent.urls', 'booking_intent'), namespace='booking_intent_ui')),  # UI booking intent pages
    path('api/booking-intent/', include(('booking_intent.urls', 'booking_intent'), namespace='booking_intent_api')),  # API booking intent endpoints
    path('reviews/', include(('reviews.urls', 'reviews'), namespace='reviews_ui')),  # UI reviews pages
    path('api/reviews/', include(('reviews.urls', 'reviews'), namespace='reviews_api')),  # API reviews endpoints
    path('api/trust-display/', include('trust_display.urls')),
    path('api/analytics/', include('analytics.urls')),
    path('behavior/', include('behavior_engine.urls')),
    path('notifications/', include('notifications.urls')),  # UI notifications pages
    path('pages/', include('pages.urls')),  # Pages app URLs (Temple/Pandit Pages)
    path('masterdata/', include('masterdata.urls')),  # Master data management (Super Admin only)
    
    # Static SEO pages (must be before catch-all patterns)
    path('about-us/', views_static.about_us, name='about_us'),
    path('terms-and-conditions/', views_static.terms_conditions, name='terms_conditions'),
    path('privacy-policy/', views_static.privacy_policy, name='privacy_policy'),
    
    path('', include('support.urls')),  # Support app URLs (Contact Us)
    path('branding/', include('branding.urls')),  # Branding management
    path('monitoring/', include('monitoring.urls')),  # Phase 12: observability (health, metrics)
    path('admin-analytics/', include('analytics_dashboard.urls')),  # Phase 13: admin analytics (read-only)
    path('recommendations/', include('recommendation_engine.urls')),  # Phase 15: recommendation engine (read-only)
    # path('admin-intelligence/', include('admin_intelligence.urls')),  # Phase 16: moved to /dashboard/super-admin/intelligence/ (platform UI)
    path('feed/', include('feed_engine.urls')),  # Phase 17A: personalized feed
    path('bureaus/', include('bureaus.urls')),
    path('services/', include('services.urls')),
    path('otp/', include(('otp_verification.urls', 'otp_verification'), namespace='otp_verification')),
]

# Serve media files (dev always; prod for testing - e.g. Railway ephemeral disk)
# In production with persistent storage (S3/Volume), use that instead of serving from app.
if settings.DEBUG or getattr(settings, 'SERVE_MEDIA_IN_PROD', False):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
