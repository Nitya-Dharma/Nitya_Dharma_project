"""Template tags for Expert public contact URLs."""

from django import template

from services.expert_contact import get_expert_contact_info

register = template.Library()


@register.filter
def expert_contact_info(expert_profile):
    """Return call/WhatsApp contact metadata for an Expert."""
    if not expert_profile:
        return {
            "call_url": None,
            "whatsapp_url": None,
            "has_call": False,
            "has_whatsapp": False,
        }
    return get_expert_contact_info(expert_profile)
