"""
API Constants for Security Hardening (PART 3)

These constants enforce non-bypassable limits and make implicit guarantees explicit.
Optional overrides via Django settings; defaults preserve previous behavior.
"""

from django.conf import settings

# Pagination Limits (Non-Bypassable); overridable via settings
_DEFAULT_MAX_PAGE = 50
_DEFAULT_PAGE_SIZE = 25
_DEFAULT_SEARCH_PAGE = 20
MAX_PAGE_SIZE = getattr(settings, 'API_MAX_PAGE_SIZE', _DEFAULT_MAX_PAGE)
DEFAULT_PAGE_SIZE = getattr(settings, 'API_DEFAULT_PAGE_SIZE', _DEFAULT_PAGE_SIZE)
DEFAULT_SEARCH_PAGE_SIZE = getattr(settings, 'API_DEFAULT_SEARCH_PAGE_SIZE', _DEFAULT_SEARCH_PAGE)

# Dashboard operational limits; lazy-resolved (not import-time frozen)
_DEFAULT_DASHBOARD_PAGES_PREVIEW = 50
_DEFAULT_DASHBOARD_AUDIT_EXPORT = 1000


def get_dashboard_pages_preview_limit():
    from django.conf import settings
    return getattr(settings, 'DASHBOARD_PAGES_PREVIEW_LIMIT', _DEFAULT_DASHBOARD_PAGES_PREVIEW)


def get_dashboard_audit_export_limit():
    from django.conf import settings
    return getattr(settings, 'DASHBOARD_AUDIT_EXPORT_LIMIT', _DEFAULT_DASHBOARD_AUDIT_EXPORT)

# State Transition Rules
# These define allowed state transitions for various entities

# User Status Transitions
USER_STATUS_TRANSITIONS = {
    'pending': ['active', 'rejected'],
    'active': ['deactivated', 'suspended'],
    'rejected': [],  # Rejected users cannot transition
    'deactivated': ['active'],  # Can be reactivated
    'suspended': ['active'],  # Can be reinstated
}

# Booking Intent Status Transitions
BOOKING_INTENT_STATUS_TRANSITIONS = {
    'submitted': ['viewed', 'cancelled', 'closed_system'],
    'viewed': ['cancelled', 'closed_system'],
    'cancelled': [],  # Final state
    'closed_system': [],  # Final state
}

# Page Status Transitions
PAGE_STATUS_TRANSITIONS = {
    'ACTIVE': ['DEACTIVATED', 'INVISIBLE'],
    'DEACTIVATED': ['ACTIVE'],
    'INVISIBLE': ['ACTIVE'],
}

# Review Visibility Transitions
REVIEW_VISIBILITY_TRANSITIONS = {
    'visible': ['hidden'],
    'hidden': ['visible'],
}




















