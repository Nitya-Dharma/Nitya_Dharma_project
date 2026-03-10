"""
Role-based access control decorators.

These decorators enforce role-based access to views.
They require authentication and check user roles before allowing access.
"""
from functools import wraps
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .utils import is_admin, is_pandit


def admin_required(view_func):
    """
    Decorator that requires the user to be authenticated and have admin role.
    
    Usage:
        @admin_required
        def admin_view(request):
            # Only admins can access this
            return JsonResponse({'message': 'Admin access granted'})
    
    Behavior:
        - Anonymous users → Redirect to login
        - Authenticated non-admin users → HTTP 403 Forbidden
        - Admin users → Allow access
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not is_admin(request.user):
            # Return 403 Forbidden with JSON body (JsonResponse with status=403)
            return JsonResponse({
                'error': 'Access denied',
                'message': 'Admin role required',
                'user_role': request.user.role if request.user.is_authenticated else 'anonymous'
            }, status=403)
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def pandit_required(view_func):
    """
    Decorator that requires the user to be authenticated and have pandit role.
    
    Usage:
        @pandit_required
        def pandit_view(request):
            # Only pandits can access this
            return JsonResponse({'message': 'Pandit access granted'})
    
    Behavior:
        - Anonymous users → Redirect to login
        - Authenticated non-pandit users → HTTP 403 Forbidden
        - Pandit users → Allow access
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not is_pandit(request.user):
            # Return 403 Forbidden with JSON body (JsonResponse with status=403)
            return JsonResponse({
                'error': 'Access denied',
                'message': 'Pandit role required',
                'user_role': request.user.role if request.user.is_authenticated else 'anonymous'
            }, status=403)
        return view_func(request, *args, **kwargs)
    return _wrapped_view

