"""
Template tags for pages app.
"""
from django import template
from pages.page_permissions import get_pages_for_user

register = template.Library()


@register.filter
def has_page_role(user):
    """
    Check if user has any page role (owner or moderator).
    
    Usage: {% if user|has_page_role %}
    """
    if not user or not user.is_authenticated:
        return False
    
    pages = get_pages_for_user(user)
    return pages.exists()

















