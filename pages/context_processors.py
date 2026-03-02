"""
Context processors for pages app.
Provides global context to all templates.
"""
from .models_cms import SocialMediaSettings


def social_links(request):
    """
    Inject global social media links into template context.
    Available in all templates as 'global_social_links'.
    """
    try:
        social_settings = SocialMediaSettings.load()
        return {
            'global_social_links': social_settings
        }
    except Exception:
        # Handle cases where model might not exist yet (e.g., during initial migration)
        return {
            'global_social_links': None
        }





