"""
Template tags for Pandit contact information.

SECURITY: These tags only return URLs, never raw phone numbers.
"""

from django import template
from profiles.services_contact import get_call_url, get_whatsapp_url, get_contact_info

register = template.Library()


@register.filter
def pandit_call_url(pandit_profile):
    """
    Get tel: URL for calling a Pandit.
    
    SECURITY: Returns URL only, never raw phone number.
    """
    return get_call_url(pandit_profile)


@register.filter
def pandit_whatsapp_url(pandit_profile):
    """
    Get WhatsApp URL for contacting a Pandit.
    
    SECURITY: Returns URL only, never raw phone number.
    """
    return get_whatsapp_url(pandit_profile)


@register.filter
def pandit_contact_info(pandit_profile):
    """
    Get all contact information for a Pandit.
    
    Returns dict with: call_url, whatsapp_url, has_call, has_whatsapp
    """
    if not pandit_profile:
        return {
            'call_url': None,
            'whatsapp_url': None,
            'has_call': False,
            'has_whatsapp': False,
        }
    return get_contact_info(pandit_profile)

