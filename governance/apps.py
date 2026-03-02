from django.apps import AppConfig


class GovernanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'governance'
    
    def ready(self):
        """Import models from subdirectories to ensure they're registered."""
        # Import sub-module models to ensure Django discovers them
        try:
            import governance.appeals.models  # noqa
            import governance.audit.models  # noqa
            import governance.approvals.models  # noqa
        except ImportError:
            pass