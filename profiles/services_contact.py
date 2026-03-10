"""
Service functions for generating secure contact URLs for Pandits.

SECURITY RULES:
- Phone numbers are NEVER exposed in HTML text
- Only clickable action URLs are generated server-side
- URLs are only generated if Pandit allows contact
- URLs are hidden if Pandit is deactivated
"""

import logging
from urllib.parse import quote
from django.conf import settings
from .models import PanditProfile

logger = logging.getLogger(__name__)


def get_call_url(pandit_profile: PanditProfile) -> str | None:
    """
    Generate secure tel: URL for calling a Pandit.
    
    PRIORITY ORDER:
    1. call_mobile_number (NEW - primary field)
    2. primary_mobile_number (legacy fallback)
    3. phone_country_code + phone_national_number (normalized fields)
    4. phone_number (legacy field)
    
    SECURITY: Phone number is never exposed in HTML, only in tel: link.
    
    Args:
        pandit_profile: PanditProfile instance
    
    Returns:
        tel: URL string or None if not allowed/available
    """
    # Visibility rules
    if not pandit_profile.user.is_active or pandit_profile.user.status != 'active':
        return None
    
    if not pandit_profile.allow_call:
        return None
    
    # PRIORITY 1: Use NEW call_mobile_number field (primary)
    if pandit_profile.call_mobile_number:
        phone_clean = pandit_profile.call_mobile_number.strip()
        # Remove spaces and dashes if any
        phone_clean = phone_clean.replace(' ', '').replace('-', '')
        # Ensure E.164 format (starts with +)
        if phone_clean and not phone_clean.startswith('+'):
            # If it's 10 digits, assume India (+91)
            if len(phone_clean) == 10 and phone_clean.isdigit():
                phone_clean = f"+91{phone_clean}"
            elif phone_clean.isdigit():
                phone_clean = f"+{phone_clean}"
        if phone_clean:
            return f"tel:{phone_clean}"
    
    # PRIORITY 2: Fallback to legacy primary_mobile_number
    if pandit_profile.primary_mobile_number:
        phone_clean = pandit_profile.primary_mobile_number.strip()
        phone_clean = phone_clean.replace(' ', '').replace('-', '')
        if phone_clean and not phone_clean.startswith('+'):
            if len(phone_clean) == 10 and phone_clean.isdigit():
                phone_clean = f"+91{phone_clean}"
            elif phone_clean.isdigit():
                phone_clean = f"+{phone_clean}"
        if phone_clean:
            return f"tel:{phone_clean}"
    
    # PRIORITY 3: Use normalized fields (phone_country_code + phone_national_number)
    if pandit_profile.phone_country_code and pandit_profile.phone_national_number:
        # Use normalized fields
        dial_code = pandit_profile.phone_country_code.dial_code
        national_number = ''.join(filter(str.isdigit, pandit_profile.phone_national_number))
        if national_number:
            return f"tel:{dial_code}{national_number}"
    
    # PRIORITY 4: Fallback to legacy phone_number field
    if pandit_profile.phone_number:
        # Clean phone number (remove spaces, dashes, etc.)
        phone_clean = ''.join(filter(str.isdigit, pandit_profile.phone_number))
        
        # Ensure E.164 format (starts with +)
        if not phone_clean.startswith('+'):
            # Try to find country code from master data (default to India if 10 digits)
            if len(phone_clean) == 10:
                # Default to India (+91) for 10-digit numbers (backward compatibility)
                from masterdata.models import CountryCode
                india = CountryCode.objects.filter(iso_code='IN', is_active=True).first()
                if india:
                    phone_clean = f"{india.dial_code}{phone_clean}"
                else:
                    phone_clean = f"+91{phone_clean}"  # Fallback if India not in DB
            else:
                phone_clean = f"+{phone_clean}"
        
        return f"tel:{phone_clean}"
    
    return None


def get_whatsapp_url(pandit_profile: PanditProfile, message: str = None) -> str | None:
    """
    Generate secure WhatsApp URL for contacting a Pandit.
    
    PRIORITY ORDER:
    1. whatsapp_mobile_number (NEW - primary field)
    2. call_mobile_number (if use_same_number_for_call_and_whatsapp is True)
    3. primary_mobile_number (legacy fallback)
    4. phone_country_code + phone_national_number (normalized fields)
    5. phone_number (legacy field)
    
    SECURITY: Phone number is never exposed in HTML, only in WhatsApp link.
    
    Args:
        pandit_profile: PanditProfile instance
        message: Optional pre-filled message (default: generic greeting)
    
    Returns:
        WhatsApp URL string or None if not allowed/available
    """
    # Visibility rules
    if not pandit_profile.user.is_active or pandit_profile.user.status != 'active':
        return None
    
    # Allow WhatsApp if explicitly enabled, or if "use same number for Call & WhatsApp" is set (so button shows)
    allow_whatsapp = getattr(pandit_profile, 'allow_whatsapp', False) or getattr(pandit_profile, 'enable_whatsapp', False)
    use_same = getattr(pandit_profile, 'use_same_number_for_call_and_whatsapp', False)
    if not allow_whatsapp and not (use_same and pandit_profile.call_mobile_number):
        return None
    
    whatsapp_number = None
    
    # PRIORITY 1: Use NEW whatsapp_mobile_number field (primary)
    if pandit_profile.whatsapp_mobile_number:
        phone_clean = pandit_profile.whatsapp_mobile_number.strip()
        phone_clean = phone_clean.replace(' ', '').replace('-', '')
        if phone_clean:
            whatsapp_number = phone_clean.replace('+', '')  # Remove + for WhatsApp URL
    # PRIORITY 2: If use_same_number checkbox is checked, use call_mobile_number
    elif getattr(pandit_profile, 'use_same_number_for_call_and_whatsapp', False) and pandit_profile.call_mobile_number:
        phone_clean = pandit_profile.call_mobile_number.strip()
        phone_clean = phone_clean.replace(' ', '').replace('-', '')
        if phone_clean:
            whatsapp_number = phone_clean.replace('+', '')  # Remove + for WhatsApp URL
    # PRIORITY 3: Fallback to legacy primary_mobile_number
    elif pandit_profile.primary_mobile_number:
        phone_clean = pandit_profile.primary_mobile_number.strip()
        phone_clean = phone_clean.replace(' ', '').replace('-', '')
        if phone_clean:
            whatsapp_number = phone_clean.replace('+', '')
    # PRIORITY 4: Use normalized fields (phone_country_code + phone_national_number)
    elif pandit_profile.phone_country_code and pandit_profile.phone_national_number:
        dial_code = pandit_profile.phone_country_code.dial_code
        national_number = ''.join(filter(str.isdigit, pandit_profile.phone_national_number))
        if national_number:
            whatsapp_number = dial_code.replace('+', '') + national_number
    # PRIORITY 5: Fallback to legacy phone_number field
    elif pandit_profile.phone_number:
        phone_clean = ''.join(filter(str.isdigit, pandit_profile.phone_number))
        
        # Ensure E.164 format (starts with +)
        if not phone_clean.startswith('+'):
            if len(phone_clean) == 10:
                from masterdata.models import CountryCode
                india = CountryCode.objects.filter(iso_code='IN', is_active=True).first()
                if india:
                    phone_clean = f"{india.dial_code}{phone_clean}"
                else:
                    phone_clean = f"+91{phone_clean}"
            else:
                phone_clean = f"+{phone_clean}"
        
        whatsapp_number = phone_clean.replace('+', '')
    
    if not whatsapp_number:
        return None
    
    # Default message if not provided
    if message is None:
        pandit_name = pandit_profile.get_display_name()
        message = f"Hello Pandit {pandit_name}, I found your profile on Nitya Dharma"
    
    # URL encode the message
    encoded_message = quote(message)
    
    return f"https://wa.me/{whatsapp_number}?text={encoded_message}"


def get_contact_info(pandit_profile: PanditProfile) -> dict:
    """
    Get contact information for a Pandit (URLs only, no raw numbers).
    
    SECURITY: This function returns only URLs, never raw phone numbers.
    
    Args:
        pandit_profile: PanditProfile instance (can be None)
    
    Returns:
        dict with keys:
            - call_url: tel: URL or None
            - whatsapp_url: WhatsApp URL or None
            - has_call: bool
            - has_whatsapp: bool
    """
    if not pandit_profile:
        return {
            'call_url': None,
            'whatsapp_url': None,
            'has_call': False,
            'has_whatsapp': False,
        }
    
    call_url = get_call_url(pandit_profile)
    whatsapp_url = get_whatsapp_url(pandit_profile)
    
    return {
        'call_url': call_url,
        'whatsapp_url': whatsapp_url,
        'has_call': call_url is not None,
        'has_whatsapp': whatsapp_url is not None,
    }


def log_contact_click(pandit_profile: PanditProfile, contact_type: str, user=None):
    """
    Log engagement event when user clicks Call or WhatsApp button.
    
    SECURITY: Does NOT log phone numbers or message content.
    
    Args:
        pandit_profile: PanditProfile instance
        contact_type: 'call' or 'whatsapp'
        user: User who clicked (optional, can be anonymous)
    """
    try:
        from engagement.models import UserInteractionEvent
        
        action_type = f'CONTACT_{contact_type.upper()}_CLICK'
        
        UserInteractionEvent.objects.create(
            user=user if user and user.is_authenticated else None,
            event_type=action_type,
            entity_type='PanditProfile',
            entity_public_id=pandit_profile.public_id,
            metadata={
                'pandit_id': pandit_profile.public_id,
                'pandit_name': pandit_profile.get_display_name(),
                # NOTE: Phone number is NOT logged for privacy
            }
        )
        
        logger.info(
            f"Contact click logged - Type: {contact_type}, "
            f"Pandit: {pandit_profile.public_id}, "
            f"User: {user.email if user and user.is_authenticated else 'Anonymous'}"
        )
    except Exception as e:
        logger.warning(f"Failed to log contact click: {e}")

