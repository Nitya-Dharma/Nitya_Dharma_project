"""
Template filters for phone number formatting.
Used for Call and WhatsApp buttons.
"""
from django import template
import re

register = template.Library()


@register.filter
def clean_phone(value):
    """
    Clean phone number for tel: protocol.
    Removes spaces, dashes, parentheses, but keeps + for country code.
    
    Example:
        "+91-98765-43210" -> "+919876543210"
        "(123) 456-7890" -> "1234567890"
    """
    if not value:
        return ""
    # Convert to string and remove spaces, dashes, parentheses
    cleaned = str(value).replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    return cleaned


@register.filter
def clean_whatsapp(value):
    """
    Clean phone number for WhatsApp URL.
    Removes all non-digit characters except keeps country code digits.
    WhatsApp format: https://wa.me/[country_code][number]
    
    Example:
        "+91-98765-43210" -> "919876543210"
        "+1 (234) 567-8900" -> "12345678900"
    """
    if not value:
        return ""
    # Remove all non-digit characters (including +, spaces, dashes, parentheses)
    cleaned = re.sub(r'\D', '', str(value))
    return cleaned






















