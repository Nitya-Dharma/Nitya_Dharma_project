"""
Page Permission Service Layer

Provides backend-authoritative permission checks for page operations.
All permission logic is centralized here - templates should NOT contain permission checks.

Rules:
- Owner: All permissions except delete
- Moderator: Media + posts only
- Super Admin: Visibility + system override
- End User: Read-only
"""

from typing import Optional, List, Dict, Any
from django.contrib.auth import get_user_model
from .models import Page, PageRole

User = get_user_model()


def is_page_owner(user: User, page: Page) -> bool:
    """
    Check if user is the owner of the page.
    
    Args:
        user: User to check
        page: Page to check ownership for
    
    Returns:
        True if user created the page, False otherwise
    """
    if not user or not user.is_authenticated:
        return False
    
    # Owner is the page creator
    return page.created_by == user


def is_page_moderator(user: User, page: Page) -> bool:
    """
    Check if user is a moderator for the page.
    
    Args:
        user: User to check
        page: Page to check moderator status for
    
    Returns:
        True if user has MODERATOR role on the page, False otherwise
    """
    if not user or not user.is_authenticated:
        return False
    
    # Check if user has moderator role
    return PageRole.objects.filter(
        page=page,
        pandit=user,
        role=PageRole.ROLE_MODERATOR
    ).exists()


def has_page_role(user: User, page: Page) -> bool:
    """
    Check if user has any role (owner or moderator) on the page.
    
    Args:
        user: User to check
        page: Page to check role for
    
    Returns:
        True if user is owner or moderator, False otherwise
    """
    return is_page_owner(user, page) or is_page_moderator(user, page)


def is_super_admin(user: User) -> bool:
    """
    Check if user is a super admin.
    
    Args:
        user: User to check
    
    Returns:
        True if user is superuser, False otherwise
    """
    if not user or not user.is_authenticated:
        return False
    
    return user.is_superuser


def can_edit_page_media(user: User, page: Page) -> bool:
    """
    Check if user can edit page media (cover image, profile image, gallery).
    
    Allowed:
    - Page owner
    - Page moderator
    - Super admin
    
    Args:
        user: User to check
        page: Page to check permissions for
    
    Returns:
        True if user can edit media, False otherwise
    """
    if not user or not user.is_authenticated:
        return False
    
    # Super admin can do everything
    if is_super_admin(user):
        return True
    
    # Owner and moderator can edit media
    return is_page_owner(user, page) or is_page_moderator(user, page)


def can_upload_gallery(user: User, page: Page) -> bool:
    """
    Check if user can upload gallery images.
    
    PART 4: Gallery Upload Visibility Rules
    
    Allowed:
    - Moderate Pandit (page moderator)
    - Admin Pandit (role='admin')
    - Super Admin
    
    Hidden for:
    - End Users
    - Normal Pandits (unless they are moderators)
    
    Args:
        user: User to check
        page: Page to check permissions for
    
    Returns:
        True if user can upload gallery, False otherwise
    """
    if not user or not user.is_authenticated:
        return False
    
    # Super Admin can upload
    if is_super_admin(user):
        return True
    
    # Admin Pandit can upload
    if user.role == 'admin':
        return True
    
    # Moderate Pandit (page moderator) can upload
    if is_page_moderator(user, page):
        return True
    
    # End Users and Normal Pandits cannot upload
    return False


def can_manage_visibility(user: User, page: Page) -> bool:
    """
    Check if user can manage page visibility (hide/unhide, deactivate).
    
    Allowed:
    - Page owner (can deactivate/reactivate)
    - Super admin (can hide/unhide globally)
    
    NOT Allowed:
    - Moderator (cannot change visibility)
    - End users
    
    Args:
        user: User to check
        page: Page to check permissions for
    
    Returns:
        True if user can manage visibility, False otherwise
    """
    if not user or not user.is_authenticated:
        return False
    
    # Super admin can do everything
    if is_super_admin(user):
        return True
    
    # Only owner can manage visibility (deactivate/reactivate)
    return is_page_owner(user, page)


def can_edit_page_slug(user: User, page: Page) -> bool:
    """
    Check if user can edit page slug.
    
    Rules:
    - Only owner can edit slug
    - Slug is locked if followers_count > 0
    - Super admin cannot override slug lock
    
    Args:
        user: User to check
        page: Page to check permissions for
    
    Returns:
        True if user can edit slug, False otherwise
    """
    if not user or not user.is_authenticated:
        return False
    
    # Only owner can edit slug
    if not is_page_owner(user, page):
        return False
    
    # Slug is locked if page has followers
    return page.can_edit_slug()


def can_create_post(user: User, page: Page) -> bool:
    """
    Check if user can create posts on the page.
    
    Allowed:
    - Page owner
    - Page moderator
    - Super admin
    
    Args:
        user: User to check
        page: Page to check permissions for
    
    Returns:
        True if user can create posts, False otherwise
    """
    if not user or not user.is_authenticated:
        return False
    
    # Super admin can do everything
    if is_super_admin(user):
        return True
    
    # Owner and moderator can create posts
    return is_page_owner(user, page) or is_page_moderator(user, page)


def can_edit_post(user: User, page: Page, post_creator: Optional[User] = None) -> bool:
    """
    Check if user can edit a post on the page.
    
    Allowed:
    - Post creator (if owner or moderator)
    - Page owner
    - Super admin
    
    Args:
        user: User to check
        page: Page the post belongs to
        post_creator: User who created the post (optional)
    
    Returns:
        True if user can edit the post, False otherwise
    """
    if not user or not user.is_authenticated:
        return False
    
    # Super admin can do everything
    if is_super_admin(user):
        return True
    
    # Owner can edit any post
    if is_page_owner(user, page):
        return True
    
    # Moderator can only edit their own posts
    if is_page_moderator(user, page) and post_creator == user:
        return True
    
    return False


def can_pin_post(user: User, page: Page) -> bool:
    """
    Check if user can pin/unpin posts on the page.
    
    Allowed:
    - Page owner
    - Page moderator
    - Super admin
    
    Args:
        user: User to check
        page: Page to check permissions for
    
    Returns:
        True if user can pin posts, False otherwise
    """
    if not user or not user.is_authenticated:
        return False
    
    # Super admin can do everything
    if is_super_admin(user):
        return True
    
    # Owner and moderator can pin posts
    return is_page_owner(user, page) or is_page_moderator(user, page)


def can_assign_moderator(user: User, page: Page) -> bool:
    """
    Check if user can assign/remove moderators for the page.
    
    Allowed:
    - Page owner only
    - Super admin
    
    Args:
        user: User to check
        page: Page to check permissions for
    
    Returns:
        True if user can assign moderators, False otherwise
    """
    if not user or not user.is_authenticated:
        return False
    
    # Super admin can do everything
    if is_super_admin(user):
        return True
    
    # Only owner can assign moderators
    return is_page_owner(user, page)


def can_delete_page(user: User, page: Page) -> bool:
    """
    Check if user can delete the page.
    
    Returns:
        False - Pages cannot be deleted (soft delete only via status)
    """
    # Hard delete is forbidden - pages are soft-deleted via status changes
    return False


def get_user_page_role(user: User, page: Page) -> Optional[str]:
    """
    Get the user's role on the page.
    
    Args:
        user: User to check
        page: Page to check role for
    
    Returns:
        'OWNER', 'MODERATOR', or None
    """
    if not user or not user.is_authenticated:
        return None
    
    # Check if owner
    if is_page_owner(user, page):
        return PageRole.ROLE_OWNER
    
    # Check if moderator
    if is_page_moderator(user, page):
        return PageRole.ROLE_MODERATOR
    
    return None


def get_pages_for_user(user: User):
    """
    Get all pages where user has a role (owner or moderator).
    
    Args:
        user: User to get pages for
    
    Returns:
        QuerySet of Page objects
    """
    if not user or not user.is_authenticated:
        return Page.objects.none()
    
    # Get pages where user is owner (created_by)
    owner_pages = Page.objects.filter(created_by=user)
    
    # Get pages where user is moderator
    moderator_role_ids = PageRole.objects.filter(
        pandit=user,
        role=PageRole.ROLE_MODERATOR
    ).values_list('page_id', flat=True)
    moderator_pages = Page.objects.filter(id__in=moderator_role_ids)
    
    # Combine and return unique pages
    from django.db.models import Q
    return Page.objects.filter(
        Q(id__in=owner_pages.values_list('id', flat=True)) |
        Q(id__in=moderator_pages.values_list('id', flat=True))
    ).distinct()


def get_pages_for_pandit(user: User) -> List[Dict[str, Any]]:
    """
    Get pages for a Pandit with role information.
    
    TASK 5: Page access resolution logic for Pandits
    
    Logic:
    - If user.role != Pandit → return empty
    - Fetch pages where:
       Page.owner = user
       OR
       PageRole(pandit=user, role=MODERATOR)
    
    Returns:
        List of dicts with:
        - page_public_id
        - title
        - status
        - role (OWNER or MODERATOR)
    """
    if not user or not user.is_authenticated:
        return []
    
    # Only for Pandits
    if user.role != 'pandit':
        return []
    
    # Get pages where user is owner
    owner_pages = Page.objects.filter(created_by=user)
    
    # Get pages where user is moderator
    moderator_role_ids = PageRole.objects.filter(
        pandit=user,
        role=PageRole.ROLE_MODERATOR
    ).values_list('page_id', flat=True)
    moderator_pages = Page.objects.filter(id__in=moderator_role_ids)
    
    # Combine pages
    from django.db.models import Q
    all_pages = Page.objects.filter(
        Q(id__in=owner_pages.values_list('id', flat=True)) |
        Q(id__in=moderator_pages.values_list('id', flat=True))
    ).distinct()
    
    # Build result list with role information
    results = []
    for page in all_pages:
        role = get_user_page_role(user, page)
        results.append({
            'page_public_id': page.public_id,
            'title': page.title,
            'status': page.status,
            'role': role,
        })
    
    return results

