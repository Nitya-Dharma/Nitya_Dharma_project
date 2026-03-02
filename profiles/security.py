"""
Security utilities for profiles app.

Provides functions to check permissions and prevent unauthorized access.
"""
from django.http import Http404, HttpResponseForbidden
from django.contrib import messages
from django.shortcuts import redirect
from .models import PanditProfile


def can_view_profile(user, profile):
    """
    Check if a user can view a profile.
    
    Rules:
    - Public profiles: Anyone can view approved profiles
    - Private profiles: Only profile owner can view
    - Unapproved profiles: Only profile owner can view
    
    Returns:
        bool: True if user can view, False otherwise
    """
    # Profile owner can always view
    if user.is_authenticated and profile.user == user:
        return True
    
    # Public profiles: Only approved and active profiles
    if profile.is_profile_approved and profile.user.status == 'active' and profile.user.is_active:
        return True
    
    # Unapproved profiles: Only owner can view
    return False


def can_edit_profile(user, profile):
    """
    Check if a user can edit a profile.
    
    Rules:
    - Only profile owner can edit
    - User must be a pandit
    - Profile must belong to the user
    
    Returns:
        bool: True if user can edit, False otherwise
    """
    if not user.is_authenticated:
        return False
    
    if user.role != 'pandit':
        return False
    
    if profile.user != user:
        return False
    
    return True


def require_profile_owner(view_func):
    """
    Decorator to ensure user owns the profile.
    
    Usage:
        @require_profile_owner
        def my_view(request, profile_id):
            ...
    """
    def wrapper(request, *args, **kwargs):
        from .models import PanditProfile
        
        profile_id = kwargs.get('profile_id') or kwargs.get('pk')
        if not profile_id:
            messages.error(request, "Profile ID is required.")
            return redirect('core:home')
        
        try:
            profile = PanditProfile.objects.get(pk=profile_id)
        except PanditProfile.DoesNotExist:
            raise Http404("Profile not found")
        
        if not can_edit_profile(request.user, profile):
            messages.error(request, "You don't have permission to access this profile.")
            return redirect('core:home')
        
        # Add profile to kwargs for use in view
        kwargs['profile'] = profile
        return view_func(request, *args, **kwargs)
    
    return wrapper


def get_profile_safely(profile_id, user=None, require_approval=False):
    """
    Safely get a profile with security checks.
    
    Args:
        profile_id: The profile ID to retrieve
        user: Optional user to check permissions against
        require_approval: If True, only return approved profiles
    
    Returns:
        PanditProfile: The profile if accessible, None otherwise
    
    Raises:
        Http404: If profile doesn't exist or is not accessible
    """
    try:
        profile = PanditProfile.objects.get(pk=profile_id)
    except PanditProfile.DoesNotExist:
        raise Http404("Profile not found")
    
    # Check if profile is accessible
    if require_approval and not profile.is_profile_approved:
        if not (user and user.is_authenticated and profile.user == user):
            raise Http404("Profile not found")  # Don't reveal existence
    
    # Check if user is active
    if profile.user.status != 'active' or not profile.user.is_active:
        if not (user and user.is_authenticated and profile.user == user):
            raise Http404("Profile not found")  # Don't reveal existence
    
    return profile






















