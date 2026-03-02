"""
JSON-LD schema builders for Pandit Profiles and Pages.

Identity-only schemas. No ratings, reviews, offers, or analytics.
These schemas are auto-generated and NOT editable.
"""

from django.urls import reverse


def build_pandit_schema(pandit, request=None):
    """
    Returns JSON-LD dict for Pandit Profile.
    
    Schema type: Person
    Identity-only. No ratings, reviews, offers, or analytics.
    
    Args:
        pandit: PanditProfile instance
        request: HttpRequest instance (optional, for URL building)
        
    Returns:
        dict: JSON-LD schema structure
    """
    schema = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": pandit.get_display_name(),
    }
    
    # URL to profile
    try:
        if request:
            schema["url"] = request.build_absolute_uri(
                reverse('profiles:profile_public', args=[pandit.public_id])
            )
        else:
            from django.conf import settings
            if hasattr(settings, 'SITE_URL') and settings.SITE_URL:
                schema["url"] = settings.SITE_URL.rstrip('/') + reverse(
                    'profiles:profile_public',
                    args=[pandit.public_id]
                )
            else:
                # Fallback: relative URL
                schema["url"] = reverse('profiles:profile_public', args=[pandit.public_id])
    except Exception:
        pass  # Fail silently if URL generation fails
    
    # Address (city, country)
    address_parts = []
    if pandit.city:
        address_parts.append(pandit.city.name)
    if pandit.city and pandit.city.state:
        address_parts.append(pandit.city.state.name)
    if pandit.city and pandit.city.state and pandit.city.state.country:
        address_parts.append(pandit.city.state.country.name)
    
    if address_parts:
        schema["address"] = {
            "@type": "PostalAddress",
            "addressLocality": ", ".join(address_parts),
        }
    
    # Languages spoken
    languages = pandit.languages.all()
    if languages.exists():
        schema["inLanguage"] = [lang.name for lang in languages]
    
    # Poojas performed (knowsAbout)
    poojas = pandit.poojas_performed.all()
    if poojas.exists():
        schema["knowsAbout"] = [pooja.name for pooja in poojas[:10]]  # Limit to 10
    
    # Description (from about_description if available)
    if pandit.about_description:
        schema["description"] = pandit.about_description[:500]  # Limit length
    
    return schema


def build_page_schema(page, request=None):
    """
    Returns JSON-LD dict for Page.
    
    Schema type: Place (for TEMPLE) or Organization (for others)
    Identity-only. No ratings, reviews, offers, or analytics.
    
    Args:
        page: Page instance
        request: HttpRequest instance (optional, for URL building)
        
    Returns:
        dict: JSON-LD schema structure
    """
    # Determine schema type based on page_type
    if page.page_type == 'TEMPLE':
        schema_type = "Place"
    else:
        schema_type = "Organization"
    
    schema = {
        "@context": "https://schema.org",
        "@type": schema_type,
        "name": page.title,
    }
    
    # URL to page
    try:
        if request:
            schema["url"] = request.build_absolute_uri(
                reverse('pages:page_detail', args=[page.public_id])
            )
        else:
            from django.conf import settings
            if hasattr(settings, 'SITE_URL') and settings.SITE_URL:
                schema["url"] = settings.SITE_URL.rstrip('/') + reverse(
                    'pages:page_detail',
                    args=[page.public_id]
                )
            else:
                # Fallback: relative URL
                schema["url"] = reverse('pages:page_detail', args=[page.public_id])
    except Exception:
        pass  # Fail silently if URL generation fails
    
    # Address
    address_parts = []
    if page.address:
        address_parts.append(page.address)
    if page.city:
        address_parts.append(page.city.name)
    if page.city and page.city.state:
        address_parts.append(page.city.state.name)
    if page.city and page.city.state and page.city.state.country:
        address_parts.append(page.city.state.country.name)
    
    if address_parts:
        schema["address"] = {
            "@type": "PostalAddress",
            "streetAddress": page.address if page.address else None,
            "addressLocality": page.city.name if page.city else None,
            "addressRegion": page.city.state.name if page.city and page.city.state else None,
            "addressCountry": page.city.state.country.name if page.city and page.city.state and page.city.state.country else None,
        }
        # Remove None values
        schema["address"] = {k: v for k, v in schema["address"].items() if v is not None}
    
    # Description
    if page.description:
        schema["description"] = page.description[:500]  # Limit length
    
    # For TEMPLE pages, add additional Place properties
    if page.page_type == 'TEMPLE':
        # Can add geo coordinates if available in future
        pass
    
    return schema

