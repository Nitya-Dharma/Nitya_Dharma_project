"""
SEO-optimized slug generation utilities.

Generates clean, SEO-friendly slugs for Pandit profiles and Temple pages.
Format: <id>-<name>-<location>-<city>-<state>[-<pincode>]
"""
import re
from django.utils.text import slugify


def clean_slug_part(value):
    """
    Clean and slugify a single value.
    
    Args:
        value: String value to clean
        
    Returns:
        Clean slugified string or empty string if value is None/empty
    """
    if not value:
        return ""
    value = str(value).strip()
    # Remove extra spaces
    value = re.sub(r"\s+", " ", value)
    # Slugify (lowercase, hyphen-separated, special chars removed)
    return slugify(value)


def generate_pandit_slug(pandit_profile):
    """
    Generate SEO-optimized slug for Pandit profile.
    
    Format: <public_id>-<first-name>-<last-name>-<local-area>-<city>-<state>
    
    Args:
        pandit_profile: PanditProfile instance
        
    Returns:
        SEO-friendly slug string
    """
    user = pandit_profile.user
    
    # 🔒 CRITICAL: Only access M2M fields if profile has been saved (has primary key)
    # M2M relationships require the instance to have an ID in the database
    primary_city = None
    primary_area = None
    
    if pandit_profile.pk is not None:
        # Profile is saved - safe to access M2M fields
        try:
            if pandit_profile.cities_served.exists():
                primary_city = pandit_profile.cities_served.first()
            if pandit_profile.areas_served.exists():
                primary_area = pandit_profile.areas_served.first()
        except (ValueError, AttributeError):
            # If M2M access fails for any reason, use None (safe fallback)
            primary_city = None
            primary_area = None
    # If profile.pk is None, skip M2M access (will use only basic fields)
    
    # Build slug parts
    # Fallback to safe "Others" custom fields when M2M selections are empty.
    parts = [
        pandit_profile.public_id or (str(pandit_profile.id) if pandit_profile.id else ""),
        clean_slug_part(user.first_name if user else ""),
        clean_slug_part(user.last_name if user else ""),
        clean_slug_part((primary_area.name if primary_area else None) or (getattr(pandit_profile, 'custom_area_name', None) or None)),
        clean_slug_part((primary_city.name if primary_city else None) or (getattr(pandit_profile, 'custom_city_name', None) or None)),
        clean_slug_part((primary_city.state.name if primary_city and hasattr(primary_city, 'state') and primary_city.state else None) or (getattr(pandit_profile, 'custom_state_name', None) or None)),
    ]
    
    # Filter out empty parts and join
    slug = "-".join(filter(None, parts))
    
    # Ensure slug is not empty (fallback to public_id or basic identifier)
    if not slug or len(slug) < 3:
        if pandit_profile.public_id:
            slug = pandit_profile.public_id
        elif pandit_profile.id:
            slug = f"pandit-{pandit_profile.id}"
        else:
            # Last resort: use user email or generate temporary slug
            if user and user.email:
                slug = clean_slug_part(user.email.split('@')[0])
            else:
                slug = "pandit-profile"
    
    return slug


def generate_temple_slug(page):
    """
    Generate SEO-optimized slug for Temple/Page.
    
    Format: <public_id>-<temple-name>-<local-area>-<city>-<state>[-<pincode>]
    
    Args:
        page: Page instance
        
    Returns:
        SEO-friendly slug string
    """
    parts = [
        page.public_id or str(page.id),  # Use public_id or fallback to id
        clean_slug_part(page.name),
        clean_slug_part(page.area.name if page.area else ""),
        clean_slug_part(page.city.name if page.city else ""),
        clean_slug_part(page.city.state if page.city and hasattr(page.city, 'state') and page.city.state else ""),
    ]
    
    # Add pincode if available (check if field exists)
    if hasattr(page, 'pincode') and page.pincode:
        parts.append(clean_slug_part(str(page.pincode)))
    
    # Filter out empty parts and join
    slug = "-".join(filter(None, parts))
    
    # Ensure slug is not empty (fallback to public_id or name)
    if not slug or len(slug) < 3:
        if page.name:
            slug = clean_slug_part(page.name)
        else:
            slug = page.public_id or f"page-{page.id}"
    
    return slug


def ensure_unique_slug(model_instance, base_slug, max_length=255):
    """
    Ensure slug is unique by appending counter if needed.
    
    Args:
        model_instance: Model instance (for checking uniqueness)
        base_slug: Base slug to make unique
        max_length: Maximum slug length
        
    Returns:
        Unique slug string
    """
    Model = model_instance.__class__
    slug = base_slug[:max_length]  # Truncate to max length
    counter = 1
    
    # Check if slug already exists (excluding current instance)
    while Model.objects.filter(slug=slug).exclude(pk=model_instance.pk).exists():
        # Append counter, ensuring we don't exceed max_length
        suffix = f"-{counter}"
        if len(slug) + len(suffix) > max_length:
            # Truncate base slug to make room for suffix
            available_length = max_length - len(suffix)
            slug = base_slug[:available_length] + suffix
        else:
            slug = base_slug[:max_length - len(suffix)] + suffix
        counter += 1
        
        # Safety: prevent infinite loop
        if counter > 1000:
            # Fallback: use public_id or id
            if hasattr(model_instance, 'public_id') and model_instance.public_id:
                slug = model_instance.public_id
            else:
                slug = f"{base_slug[:max_length-10]}-{model_instance.id}"
            break
    
    return slug


