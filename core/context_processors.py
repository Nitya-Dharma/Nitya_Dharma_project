"""
Context processors for global template context.
Makes pooja categories available on all pages for navbar.

ACCESSIBLE TO ALL ROLES:
- Users (role='user')
- Pandits (role='pandit')
- Admin Pandits (role='admin')
- Super Admins (is_superuser=True)
- Anonymous users

Poojas are master data and visible to everyone for:
- Navigation (navbar dropdown)
- Search filters
- Profile selection (Pandits)
- Booking selection (Users)
"""
from masterdata.models import Pooja
from notifications.models import Notification
from pages.models_cms import SiteBranding
from branding.models import BrandingLogo


def navbar_context(request):
    """
    Provides navbar context (pooja categories) to all templates.
    
    This ensures the Poojas dropdown works on every page for ALL users:
    - No role restrictions - poojas are public master data
    - Available to: Users, Pandits, Admin Pandits, Super Admins, Anonymous
    
    Uses the authoritative category field from Pooja model.
    
    CRITICAL: This context processor MUST always return pooja_categories and poojas,
    even if there are errors, to prevent template failures.
    """
    # Initialize defaults to ensure context is always available
    all_poojas = []
    pooja_categories = {}
    ordered_categories = {}
    
    try:
        # Get all active poojas ordered by pooja_category (FK) then name
        # TASK 2.1: Use PoojaCategory FK instead of hardcoded enum
        # NO ROLE RESTRICTIONS - poojas are public master data
        all_poojas = list(Pooja.objects.filter(
            is_active=True,
            status=Pooja.STATUS_ACTIVE
        ).select_related('pooja_category').order_by('pooja_category__display_order', 'pooja_category__name', 'name'))
        
        # Group poojas by PoojaCategory (master data) for navigation
        pooja_categories = {}
        for pooja in all_poojas:
            if pooja.pooja_category and pooja.pooja_category.is_active:
                category_name = pooja.pooja_category.name
                if category_name not in pooja_categories:
                    pooja_categories[category_name] = []
                pooja_categories[category_name].append(pooja)
            elif pooja.category:
                # Fallback: Use deprecated category enum if pooja_category FK is not set
                category_display = pooja.get_category_display()
                if category_display not in pooja_categories:
                    pooja_categories[category_display] = []
                pooja_categories[category_display].append(pooja)
            else:
                # Fallback for poojas without any category
                fallback_category = 'Uncategorized'
                if fallback_category not in pooja_categories:
                    pooja_categories[fallback_category] = []
                pooja_categories[fallback_category].append(pooja)
        
        # Sort categories by display_order (from PoojaCategory master data)
        # Categories with display_order come first, then by name
        sorted_category_items = sorted(
            pooja_categories.items(),
            key=lambda x: (
                x[1][0].pooja_category.display_order if x[1] and x[1][0].pooja_category and x[1][0].pooja_category.display_order is not None else 999,
                x[0]  # Fallback to name if no display_order
            )
        )
        
        # Sort poojas within each category by name
        ordered_categories = {}
        for cat_name, poojas in sorted_category_items:
            poojas.sort(key=lambda p: p.name)
            ordered_categories[cat_name] = poojas
    except Exception as e:
        # Log error but ensure context is still returned
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error loading poojas in navbar_context: {e}", exc_info=True)
        # Return empty dicts to prevent template errors
        all_poojas = []
        ordered_categories = {}
    
    # Get unread notification count for authenticated users
    unread_notification_count = 0
    if request and hasattr(request, 'user') and request.user and request.user.is_authenticated:
        from django.utils import timezone
        from django.db.models import Q
        try:
            unread_notification_count = Notification.objects.filter(
                recipient=request.user,
                is_read=False
            ).filter(
                Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
            ).count()
        except Exception:
            unread_notification_count = 0
    
    # Determine user role for template context
    user_role = None
    is_super_admin = False  # UNIT 2: Super Admin visibility isolation
    if request and hasattr(request, 'user') and request.user and request.user.is_authenticated:
        if request.user.is_superuser:
            user_role = 'super_admin'
            is_super_admin = True  # UNIT 2: Only True for Super Admin
        elif request.user.role == 'admin':
            user_role = 'admin_pandit'
        elif request.user.role == 'pandit':
            user_role = 'pandit'
        elif request.user.role == 'user':
            user_role = 'user'
    
    # UI Flags - Future-ready toggle for Trust/Brand/Social visibility
    # Set to False to hide Trust/Brand/Social buttons from End User UI
    SHOW_TRUST_BRAND_SOCIAL = False
    
    # Get site branding (Super Admin managed, but visible to all for display)
    site_branding = None
    try:
        site_branding = SiteBranding.objects.first()
    except Exception:
        # If model doesn't exist yet (migration pending), return None
        site_branding = None
    
    # Get active branding logos (new system)
    active_navbar_logo = None
    active_favicon = None
    try:
        active_navbar_logo = BrandingLogo.objects.filter(
            logo_type='navbar_logo',
            is_active=True
        ).first()
        
        # Get favicon from active navbar logo or separate favicon logo
        if active_navbar_logo and active_navbar_logo.favicon_image:
            active_favicon = active_navbar_logo
        else:
            active_favicon = BrandingLogo.objects.filter(
                logo_type='favicon',
                is_active=True
            ).first()
    except Exception:
        # If model doesn't exist yet (migration pending), return None
        active_navbar_logo = None
        active_favicon = None
    
    # Return context - poojas available to ALL roles (no restrictions)
    # Remove empty categories
    return {
        'pooja_categories': {k: v for k, v in ordered_categories.items() if v},
        'poojas': all_poojas,  # All poojas (flat list) for other uses - accessible to ALL roles
        'unread_notification_count': unread_notification_count,
        'user_role': user_role,
        'is_super_admin': is_super_admin,  # UNIT 2: Super Admin visibility isolation (read-only)
        'SHOW_TRUST_BRAND_SOCIAL': SHOW_TRUST_BRAND_SOCIAL,  # UI Flag for Trust/Brand/Social visibility
        'site_branding': site_branding,  # Site branding (legacy - logos, favicon, site name)
        'active_navbar_logo': active_navbar_logo,  # Active navbar logo (new system)
        'active_favicon': active_favicon,  # Active favicon (new system)
    }
