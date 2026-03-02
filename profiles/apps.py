from django.apps import AppConfig


class ProfilesConfig(AppConfig):
    name = 'profiles'
    
    def ready(self):
        """Import signals when app is ready."""
        import profiles.signals  # noqa