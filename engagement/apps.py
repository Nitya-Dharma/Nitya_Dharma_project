from django.apps import AppConfig


class EngagementConfig(AppConfig):
    """
    Engagement app configuration.
    
    Handles user behavior capture for future news feed intelligence.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'engagement'
    verbose_name = 'Engagement & Behavior Capture'
