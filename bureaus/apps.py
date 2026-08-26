from django.apps import AppConfig


class BureausConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bureaus'

    def ready(self):
        import bureaus.signals  # noqa: F401
