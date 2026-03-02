"""
Security utilities for pages app.

Provides functions to check permissions and prevent unauthorized access.
"""
from django.http import Http404, HttpResponseForbidden
from django.contrib import messages
from django.shortcuts import redirect
from .models import Page


def can_view_page(user, page):
    """
    Check if a user can view a page.
    
    Rules:
    - Public pages: Anyone can view active pages
    - Inactive pages: Only page owner or admin can view
    
    Returns:
        bool: True if user can view, False otherwise
    """
    # Active pages are public
    if page.state == 'active':
        return True
    
    # Inactive pages: Only owner or admin can view
    if user.is_authenticated:
        if user.is_superuser or user.role == 'admin':
            return True
        
        # Check if user is page owner (for pandit pages)
        if page.page_type == 'pandit' and hasattr(user, 'pandit_profile'):
            if getattr(page, 'pandit_profile_id', None) == user.pandit_profile.id:
                return True
    
    return False


def can_edit_page(user, page):
    """
    Check if a user can edit a page.
    
    Rules:
    - Only page owner or admin can edit
    - User must be authenticated
    
    Returns:
        bool: True if user can edit, False otherwise
    """
    if not user.is_authenticated:
        return False
    
    # Admins can edit any page
    if user.is_superuser or user.role == 'admin':
        return True
    
    # Check if user is page owner (for pandit pages)
    if page.page_type == 'pandit' and hasattr(user, 'pandit_profile'):
        if getattr(page, 'pandit_profile_id', None) == user.pandit_profile.id:
            return True
    
    return False


def get_page_safely(page_id, user=None, require_active=False):
    """
    Safely get a page with security checks.
    
    Args:
        page_id: The page ID to retrieve
        user: Optional user to check permissions against
        require_active: If True, only return active pages
    
    Returns:
        Page: The page if accessible, None otherwise
    
    Raises:
        Http404: If page doesn't exist or is not accessible
    """
    try:
        page = Page.objects.get(pk=page_id)
    except Page.DoesNotExist:
        raise Http404("Page not found")
    
    # Check if page is accessible
    if require_active and page.state != 'active':
        if not (user and can_view_page(user, page)):
            raise Http404("Page not found")  # Don't reveal existence
    
    # Check permissions
    if not can_view_page(user, page):
        raise Http404("Page not found")  # Don't reveal existence
    
    return page






















