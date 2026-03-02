from django.apps import AppConfig


class TrackingConfigConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tracking_config'
    
    def ready(self):
        """Register signals when app is ready."""
        import tracking_config.signals  # noqa