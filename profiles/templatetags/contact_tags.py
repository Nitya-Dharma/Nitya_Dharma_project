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
    Get WhatsApp URL for contacting a Pandit (no request → no ad prefill).
    
    SECURITY: Returns URL only, never raw phone number.
    """
    return get_whatsapp_url(pandit_profile)


@register.filter
def pandit_contact_info(pandit_profile):
    """
    Get all contact information for a Pandit (no request → no ad prefill).

    Prefer the ad_aware_pandit_contact_info simple_tag when request is available.
    
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


@register.simple_tag(takes_context=True)
def ad_aware_pandit_contact_info(context, pandit_profile):
    """
    Contact info with optional ad-attributed WhatsApp prefill from request session.
    """
    if not pandit_profile:
        return {
            'call_url': None,
            'whatsapp_url': None,
            'has_call': False,
            'has_whatsapp': False,
        }
    request = context.get("request")
    return get_contact_info(pandit_profile, request=request)
