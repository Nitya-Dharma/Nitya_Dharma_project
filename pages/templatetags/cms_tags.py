"""
CMS Template Tags for SEO Configuration.
"""
from django import template
from django.conf import settings
from pages.models_cms import SiteSEOConfig

register = template.Library()


@register.simple_tag
def get_seo_config(field_name, default=''):
    """Get SEO config field value."""
    try:
        config = SiteSEOConfig.objects.first()
        if config:
            return getattr(config, field_name, default)
    except:
        pass
    return default


@register.simple_tag
def get_seo_config_logo(request):
    """Get SEO config logo URL."""
    try:
        config = SiteSEOConfig.objects.first()
        if config and config.organization_logo:
            if request:
                return request.build_absolute_uri(config.organization_logo.url)
            return config.organization_logo.url
    except:
        pass
    # Fallback to default logo
    from django.templatetags.static import static
    if request:
        return request.build_absolute_uri('/') + static('images/logo.png')
    return static('images/logo.png')











