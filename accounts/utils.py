"""
Utility functions for role checking.

These are pure Python functions for checking user roles.
Used by decorators and views to enforce role-based access control.
"""


def is_admin(user):
    """
    Check if user has admin role.
    
    Args:
        user: User instance or AnonymousUser
        
    Returns:
        bool: True if user is authenticated and has admin role
        
    Example:
        if is_admin(request.user):
            # Allow admin access
    """
    if not user or not user.is_authenticated:
        return False
    return user.role == 'admin'


def is_pandit(user):
    """
    Check if user has pandit role.
    
    Args:
        user: User instance or AnonymousUser
        
    Returns:
        bool: True if user is authenticated and has pandit role
        
    Example:
        if is_pandit(request.user):
            # Allow pandit access
    """
    if not user or not user.is_authenticated:
        return False
    return user.role == 'pandit'


def is_user(user):
    """
    Check if user has regular user role.
    
    Args:
        user: User instance or AnonymousUser
        
    Returns:
        bool: True if user is authenticated and has user role
        
    Example:
        if is_user(request.user):
            # Allow regular user access
    """
    if not user or not user.is_authenticated:
        return False
    return user.role == 'user'







































