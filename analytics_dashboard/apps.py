from django.apps import AppConfig


class AnalyticsDashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analytics_dashboard'
    verbose_name = 'Admin Analytics Dashboard'
    # No models — read-only analytics from existing tables only.
