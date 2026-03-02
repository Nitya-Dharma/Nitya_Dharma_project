from django.apps import AppConfig


class PagesConfig(AppConfig):
    """
    Pages app configuration.
    
    Handles generic page system for Temple, Brand, Trust, and Social Service pages.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pages'
    verbose_name = 'Pages'
    
    def ready(self):
        """Import models from subdirectories to ensure they're registered."""
        # Import role assignment models to ensure Django discovers them
        try:
            import pages.models_role_assignment  # noqa
        except ImportError:
            pass
        
        # TASK 29: Import signals to update followers_count
        try:
            import pages.signals_followers  # noqa
        except ImportError:
            pass
