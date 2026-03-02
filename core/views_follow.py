"""
Follow System Views

Views for following/unfollowing entities (pandits and temples).
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from accounts.utils import is_user
from .follow_service import follow_entity, unfollow_entity, is_following, get_follower_count
import logging

logger = logging.getLogger(__name__)


@login_required
@csrf_protect
@require_http_methods(["POST"])
def follow_pandit(request, pandit_public_id):
    """
    Follow a pandit.
    
    Args:
        request: HTTP request
        pandit_public_id: Public ID of the pandit profile
    
    Returns:
        JsonResponse with success status
    """
    # Only End Users can follow
    if not is_user(request.user):
        return JsonResponse({
            'success': False,
            'error': 'Only End Users can follow pandits'
        }, status=403)
    
    # Resolve pandit from public_id
    from core.public_id import resolve_public_id
    from profiles.models import PanditProfile
    
    pandit_profile = resolve_public_id(PanditProfile, pandit_public_id)
    if not pandit_profile:
        return JsonResponse({
            'success': False,
            'error': 'Pandit not found'
        }, status=404)
    
    # Follow the pandit
    success, follow_instance, message = follow_entity(
        user=request.user,
        entity_type='pandit',
        entity_id=pandit_profile.id
    )
    
    if success:
        follower_count = get_follower_count('pandit', pandit_profile.id)
        return JsonResponse({
            'success': True,
            'message': message,
            'is_following': True,
            'follower_count': follower_count
        })
    else:
        return JsonResponse({
            'success': False,
            'error': message
        }, status=400)


@login_required
@csrf_protect
@require_http_methods(["POST"])
def unfollow_pandit(request, pandit_public_id):
    """
    Unfollow a pandit.
    
    Args:
        request: HTTP request
        pandit_public_id: Public ID of the pandit profile
    
    Returns:
        JsonResponse with success status
    """
    # Resolve pandit from public_id
    from core.public_id import resolve_public_id
    from profiles.models import PanditProfile
    
    pandit_profile = resolve_public_id(PanditProfile, pandit_public_id)
    if not pandit_profile:
        return JsonResponse({
            'success': False,
            'error': 'Pandit not found'
        }, status=404)
    
    # Unfollow the pandit
    success, message = unfollow_entity(
        user=request.user,
        entity_type='pandit',
        entity_id=pandit_profile.id
    )
    
    if success:
        follower_count = get_follower_count('pandit', pandit_profile.id)
        return JsonResponse({
            'success': True,
            'message': message,
            'is_following': False,
            'follower_count': follower_count
        })
    else:
        return JsonResponse({
            'success': False,
            'error': message
        }, status=400)


@login_required
@csrf_protect
@require_http_methods(["POST"])
def follow_temple(request, page_public_id):
    """
    Follow a temple page.
    
    Args:
        request: HTTP request
        page_public_id: Public ID of the page
    
    Returns:
        JsonResponse with success status
    """
    # Any authenticated user can follow temples (Admin Pandit, Pandit, End User)
    # Resolve page from public_id
    from core.public_id import resolve_public_id
    from pages.models import Page
    
    page = resolve_public_id(Page, page_public_id)
    if not page:
        return JsonResponse({
            'success': False,
            'error': 'Temple not found'
        }, status=404)
    
    # Follow the temple
    success, follow_instance, message = follow_entity(
        user=request.user,
        entity_type='temple',
        entity_id=page.id
    )
    
    if success:
        follower_count = get_follower_count('temple', page.id)
        return JsonResponse({
            'success': True,
            'message': message,
            'is_following': True,
            'follower_count': follower_count
        })
    else:
        return JsonResponse({
            'success': False,
            'error': message
        }, status=400)


@login_required
@csrf_protect
@require_http_methods(["POST"])
def unfollow_temple(request, page_public_id):
    """
    Unfollow a temple page.
    
    Args:
        request: HTTP request
        page_public_id: Public ID of the page
    
    Returns:
        JsonResponse with success status
    """
    # Resolve page from public_id
    from core.public_id import resolve_public_id
    from pages.models import Page
    
    page = resolve_public_id(Page, page_public_id)
    if not page:
        return JsonResponse({
            'success': False,
            'error': 'Temple not found'
        }, status=404)
    
    # Unfollow the temple
    success, message = unfollow_entity(
        user=request.user,
        entity_type='temple',
        entity_id=page.id
    )
    
    if success:
        follower_count = get_follower_count('temple', page.id)
        return JsonResponse({
            'success': True,
            'message': message,
            'is_following': False,
            'follower_count': follower_count
        })
    else:
        return JsonResponse({
            'success': False,
            'error': message
        }, status=400)


@require_http_methods(["GET"])
def check_follow_status(request, entity_type, entity_public_id):
    """
    Check if current user is following an entity.
    
    Args:
        request: HTTP request
        entity_type: 'pandit' or 'temple'
        entity_public_id: Public ID of the entity
    
    Returns:
        JsonResponse with follow status
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'is_following': False,
            'follower_count': 0
        })
    
    # Resolve entity from public_id
    from core.public_id import resolve_public_id
    
    if entity_type == 'pandit':
        from profiles.models import PanditProfile
        entity = resolve_public_id(PanditProfile, entity_public_id)
        if not entity:
            return JsonResponse({
                'success': False,
                'error': 'Pandit not found'
            }, status=404)
        entity_id = entity.id
    elif entity_type == 'temple':
        from pages.models import Page
        entity = resolve_public_id(Page, entity_public_id)
        if not entity:
            return JsonResponse({
                'success': False,
                'error': 'Temple not found'
            }, status=404)
        entity_id = entity.id
    else:
        return JsonResponse({
            'success': False,
            'error': 'Invalid entity type'
        }, status=400)
    
    is_following_entity = is_following(request.user, entity_type, entity_id)
    follower_count = get_follower_count(entity_type, entity_id)
    
    return JsonResponse({
        'is_following': is_following_entity,
        'follower_count': follower_count
    })















