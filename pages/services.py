"""
Page service layer for role-based page creation and lifecycle management.

STRICT RULES:
- NO views, NO serializers, NO frontend assumptions
- Backend-only service functions
- Role-based permission enforcement
- All actions logged in PageAuditLog
"""

import logging
from django.db import transaction
from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib.auth import get_user_model
from core.public_id import resolve_public_id, reject_bigint_id, generate_public_id
from .models import Page, PageAuditLog
from .constants import (
    PAGE_TYPE_TEMPLE,
    PAGE_TYPE_BRAND,
    PAGE_TYPE_TRUST,
    PAGE_TYPE_SOCIAL_SERVICE,
    PAGE_TYPES,
    OWNER_ROLE_ADMIN_PANDIT,
    OWNER_ROLE_SUPER_ADMIN,
    PAGE_STATUS_ACTIVE,
    PAGE_STATUS_DEACTIVATED,
    PAGE_STATUS_INVISIBLE,
    AUDIT_ACTION_CREATE,
    AUDIT_ACTION_UPDATE,
    AUDIT_ACTION_DEACTIVATE,
    AUDIT_ACTION_ACTIVATE,
    AUDIT_ACTION_VISIBILITY_CHANGE,
)

User = get_user_model()
logger = logging.getLogger(__name__)


def _is_admin_pandit(user):
    """
    Check if user is Admin Pandit.
    
    Admin Pandit: role='admin' and is_superuser=False
    """
    return user.is_authenticated and user.role == 'admin' and not user.is_superuser


def _is_super_admin(user):
    """Check if user is Super Admin."""
    return user.is_authenticated and user.is_superuser


def _can_create_page_type(user, page_type):
    """
    Check if user can create a page of the given type.
    
    Rules:
    - ADMIN_PANDIT: Can create ONLY TEMPLE pages
    - SUPER_ADMIN: Can create ANY page type
    
    Args:
        user: User instance
        page_type: Page type to create
    
    Returns:
        bool: True if user can create this page type
    """
    if not user or not user.is_authenticated:
        return False
    
    if _is_super_admin(user):
        return True  # Super Admin can create any page type
    
    if _is_admin_pandit(user):
        return page_type == PAGE_TYPE_TEMPLE  # Admin Pandit can only create TEMPLE
    
    return False  # Other users cannot create pages


def _can_modify_page(user, page):
    """
    Check if user can modify a page.
    
    Rules:
    - ADMIN_PANDIT: Can modify ONLY pages they created
    - SUPER_ADMIN: Can modify any page
    
    Args:
        user: User instance
        page: Page instance
    
    Returns:
        bool: True if user can modify this page
    """
    if not user or not user.is_authenticated:
        return False
    
    if _is_super_admin(user):
        return True  # Super Admin can modify any page
    
    if _is_admin_pandit(user):
        return page.created_by == user  # Admin Pandit can only modify their own pages
    
    return False


def _determine_owner_role(user):
    """
    Determine owner_role based on user's role.
    
    Args:
        user: User instance
    
    Returns:
        str: OWNER_ROLE_ADMIN_PANDIT or OWNER_ROLE_SUPER_ADMIN
    """
    if _is_super_admin(user):
        return OWNER_ROLE_SUPER_ADMIN
    elif _is_admin_pandit(user):
        return OWNER_ROLE_ADMIN_PANDIT
    else:
        raise PermissionDenied("User does not have permission to create pages")


def create_page(user, page_type, payload):
    """
    Create a new page with role-based permission checks.
    
    Rules:
    - ADMIN_PANDIT: Can create ONLY page_type = TEMPLE
    - SUPER_ADMIN: Can create ANY page_type
    
    Validations:
    - Slug must be unique per page_type
    - Title required
    - Description optional
    
    Args:
        user: User instance (must be authenticated)
        page_type: Page type (TEMPLE, BRAND, TRUST, SOCIAL_SERVICE)
        payload: Dictionary with:
            - title (required): Page title
            - slug (optional): URL-friendly identifier (auto-generated if not provided)
            - description (optional): Page description
    
    Returns:
        Page: Created page instance
    
    Raises:
        PermissionDenied: If user cannot create this page type
        ValidationError: If validation fails
    """
    if not user or not user.is_authenticated:
        raise PermissionDenied("User must be authenticated to create pages")
    
    # Validate page_type
    if page_type not in PAGE_TYPES:
        raise ValidationError(f"Invalid page_type: {page_type}. Must be one of {PAGE_TYPES}")
    
    # Check permission
    if not _can_create_page_type(user, page_type):
        raise PermissionDenied(
            f"User does not have permission to create {page_type} pages. "
            f"Admin Pandit can only create TEMPLE pages."
        )
    
    # Extract payload
    title = payload.get('title', '').strip()
    description = payload.get('description', '').strip()
    
    # Validate title (required)
    if not title:
        raise ValidationError("title is required")
    
    try:
        with transaction.atomic():
            # Determine owner_role - this should never be None
            owner_role = _determine_owner_role(user)
            if not owner_role or owner_role not in [OWNER_ROLE_ADMIN_PANDIT, OWNER_ROLE_SUPER_ADMIN]:
                raise ValidationError(f"Failed to determine valid owner_role for user {user.email}. Got: {owner_role}")
            
            # Enforce page_type for Admin Pandit (backend sync with frontend)
            if owner_role == OWNER_ROLE_ADMIN_PANDIT:
                if page_type != PAGE_TYPE_TEMPLE:
                    raise ValidationError(
                        f"Admin Pandit can only create TEMPLE pages. "
                        f"Requested page_type: {page_type}"
                    )
                # Ensure page_type is TEMPLE (even if frontend somehow sent different value)
                page_type = PAGE_TYPE_TEMPLE
            
            # Extract additional fields
            address = payload.get('address', '').strip() or None
            city_id = payload.get('city')
            area_id = payload.get('area')
            profile_image = payload.get('profile_image')
            cover_image = payload.get('cover_image')
            
            # Resolve city and area FKs if provided
            # Handle both ID (int) and object instances
            city = None
            area = None
            if city_id:
                try:
                    from masterdata.models import City
                    # If city_id is already a City object, extract its ID
                    if isinstance(city_id, City):
                        city = city_id
                    else:
                        # city_id is an integer ID
                        city = City.objects.get(pk=city_id)
                except (City.DoesNotExist, ValueError, TypeError):
                    pass  # Invalid city_id, leave as None
            if area_id:
                try:
                    from masterdata.models import LocalArea
                    # If area_id is already a LocalArea object, use it directly
                    if isinstance(area_id, LocalArea):
                        area = area_id
                    else:
                        # area_id is an integer ID
                        area = LocalArea.objects.get(pk=area_id)
                except (LocalArea.DoesNotExist, ValueError, TypeError):
                    pass  # Invalid area_id, leave as None
            
            # Generate public_id and slug first
            public_id = generate_public_id()
            
            # Slug: always generate from full title (backend source of truth). Do not use payload slug.
            from django.utils.text import slugify
            base_slug = slugify(title)
            if not base_slug or not base_slug.strip():
                base_slug = f"page-{public_id[:8]}"
            slug = base_slug
            # Ensure uniqueness per page_type
            counter = 1
            while Page.objects.filter(page_type=page_type, slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            # Create page - handle legacy 'name' column if it exists
            from django.db import connection
            
            # Check if legacy 'name' column exists
            has_name_column = False
            try:
                with connection.cursor() as check_cursor:
                    check_cursor.execute("PRAGMA table_info(pages_page)")
                    columns = [row[1] for row in check_cursor.fetchall()]
                    has_name_column = 'name' in columns
            except Exception:
                pass
            
            if has_name_column:
                # Legacy 'name' column exists with NOT NULL constraint
                # Must use raw SQL INSERT to set all required legacy columns at once
                try:
                    with connection.cursor() as cursor:
                        # Get column info
                        cursor.execute("PRAGMA table_info(pages_page)")
                        columns_info = cursor.fetchall()
                        column_names = [col[1] for col in columns_info]
                        
                        # Build INSERT with all required columns
                        # Use simple string concatenation to avoid f-string % issues
                        insert_cols = ['public_id', 'page_type', 'name', 'title', 'slug', 'description', 'address', 'created_by_id', 'owner_role', 'status', 'is_deleted']
                        insert_vals = ['?'] * 11
                        
                        # Add legacy required columns
                        if 'state' in column_names:
                            insert_cols.append('state')
                            insert_vals.append('?')
                        if 'owner_status_at_creation' in column_names:
                            insert_cols.append('owner_status_at_creation')
                            insert_vals.append('?')
                        if 'owner_role_at_creation' in column_names:
                            insert_cols.append('owner_role_at_creation')
                            insert_vals.append('?')
                        
                        # Add timestamps (SQL functions, not placeholders)
                        insert_cols.extend(['created_at', 'updated_at'])
                        insert_vals.extend(["datetime('now')", "datetime('now')"])
                        
                        # Build SQL string
                        cols_str = ', '.join(insert_cols)
                        vals_str = ', '.join(insert_vals)
                        sql = "INSERT INTO pages_page (" + cols_str + ") VALUES (" + vals_str + ")"
                        
                        # Build parameters
                        params_list = [
                            str(public_id), str(page_type), str(title), str(title), 
                            str(slug) if slug else '', str(description) if description else '',
                            str(address) if address else '', int(user.id), str(owner_role),
                            str(PAGE_STATUS_ACTIVE), int(0)
                        ]
                        
                        # Add legacy column values
                        if 'state' in column_names:
                            params_list.append(str(PAGE_STATUS_ACTIVE))
                        if 'owner_status_at_creation' in column_names:
                            user_status = 'active'
                            if hasattr(user, 'status'):
                                user_status = str(user.status)
                            params_list.append(user_status)
                        if 'owner_role_at_creation' in column_names:
                            params_list.append(str(owner_role))
                        
                        # Execute using database connection directly (bypass Django debug formatter)
                        db_conn = connection.connection
                        db_cursor = db_conn.cursor()
                        db_cursor.execute(sql, tuple(params_list))
                        page_id = db_cursor.lastrowid
                        db_conn.commit()
                        db_cursor.close()
                    
                    # Get page instance
                    page = Page.objects.get(pk=page_id)
                    # Refresh to ensure all fields including owner_role are loaded from database
                    page.refresh_from_db()
                    
                    # Verify owner_role is set correctly (it should be from raw SQL)
                    if not page.owner_role or page.owner_role not in [OWNER_ROLE_ADMIN_PANDIT, OWNER_ROLE_SUPER_ADMIN]:
                        # If somehow not set, set it now using update() to avoid triggering validation
                        Page.objects.filter(pk=page.pk).update(owner_role=owner_role)
                        page.refresh_from_db()
                    
                    # Update file fields if provided
                    if cover_image:
                        page.cover_image = cover_image
                        page.save(update_fields=['cover_image'])
                    if profile_image:
                        page.profile_image = profile_image
                        page.save(update_fields=['profile_image'])
                        
                except Exception as sql_error:
                    # Use f-string to avoid % formatting issues
                    error_detail = f"Database insert failed: {type(sql_error).__name__}: {str(sql_error)}"
                    logger.error(error_detail, exc_info=True)
                    # Show actual error to help debug
                    error_msg = str(sql_error)
                    if "NOT NULL constraint" in error_msg:
                        raise ValidationError(f"Required fields missing: {error_msg}")
                    else:
                        raise ValidationError(f"Database error: {error_msg}")
            else:
                # No legacy 'name' column, use standard Django ORM
                # Create page instance and set owner_role explicitly before save
                # This ensures owner_role is set before full_clean() validation
                page = Page(
                    page_type=page_type,
                    title=title,
                    slug=slug,
                    description=description,
                    address=address,
                    city=city,
                    area=area,
                    profile_image=profile_image,
                    cover_image=cover_image,
                    created_by=user,
                    owner_role=owner_role,  # Set explicitly before save
                    status=PAGE_STATUS_ACTIVE,
                    is_deleted=False,
                    public_id=public_id
                )
                # Ensure owner_role is set before validation (should already be set, but double-check)
                if not page.owner_role:
                    page.owner_role = owner_role
                # Ensure page_type is correct for Admin Pandit (backend enforcement)
                if owner_role == OWNER_ROLE_ADMIN_PANDIT:
                    page.page_type = PAGE_TYPE_TEMPLE
                # Save the page (this will trigger full_clean() which validates owner_role)
                page.save()
            
            # Create audit log (optional - table may not exist yet)
            try:
                PageAuditLog.objects.create(
                    page=page,
                    action=AUDIT_ACTION_CREATE,
                    performed_by=user
                )
            except Exception:
                # Audit log table may not exist yet - log but don't fail
                logger.warning(f"Could not create audit log for page {page.public_id} - table may not exist")
            
            logger.info(f"Page created: {page.public_id} ({page_type}) by {user.email}")
            return page
    
    except ValidationError:
        # Re-raise validation errors as-is
        raise
    except PermissionDenied:
        # Re-raise permission errors as-is
        raise
    except Exception as e:
        # Log the error with full details
        error_msg = str(e)
        logger.error(f"Error creating page: {error_msg}", exc_info=True)
        # Re-raise as ValidationError with clear message
        raise ValidationError(f"Failed to create page: {error_msg}")


def deactivate_page(user, page_public_id):
    """
    Deactivate a page (soft delete via status change).
    
    Rules:
    - ADMIN_PANDIT: Can deactivate ONLY pages they created
    - SUPER_ADMIN: Can deactivate any page
    
    Effects:
    - Status changes to DEACTIVATED
    - Page visible publicly with banner "This page is deactivated"
    
    Args:
        user: User instance (must be authenticated)
        page_public_id: Public ID (UUIDv7) of the page
    
    Returns:
        Page: Updated page instance
    
    Raises:
        PermissionDenied: If user cannot deactivate this page
        ValidationError: If page not found or invalid state
    """
    if not user or not user.is_authenticated:
        raise PermissionDenied("User must be authenticated to deactivate pages")
    
    if reject_bigint_id(page_public_id):
        raise ValidationError("Invalid page_public_id format")
    
    page = resolve_public_id(Page, page_public_id)
    if not page:
        raise ValidationError(f"Page not found: {page_public_id}")
    
    # Check permission
    if not _can_modify_page(user, page):
        raise PermissionDenied(
            f"User does not have permission to deactivate this page. "
            f"Admin Pandit can only deactivate pages they created."
        )
    
    # Check if already deactivated
    if page.status == PAGE_STATUS_DEACTIVATED:
        logger.warning(f"Page {page.public_id} is already deactivated")
        return page
    
    try:
        with transaction.atomic():
            # Update status
            old_status = page.status
            page.status = PAGE_STATUS_DEACTIVATED
            page.save(update_fields=['status'])
            
            # Create audit log (optional - table may not exist yet)
            try:
                PageAuditLog.objects.create(
                    page=page,
                    action=AUDIT_ACTION_DEACTIVATE,
                    performed_by=user
                )
            except Exception:
                logger.warning(f"Could not create audit log for page {page.public_id} - table may not exist")
            
            logger.info(f"Page deactivated: {page.public_id} by {user.email} (was {old_status})")
            return page
    
    except Exception as e:
        logger.error(f"Error deactivating page: {str(e)}", exc_info=True)
        raise


def activate_page(user, page_public_id):
    """
    Activate a page (change status to ACTIVE).
    
    Rules:
    - ADMIN_PANDIT: Can activate ONLY pages they created
    - SUPER_ADMIN: Can activate any page
    
    Effects:
    - Status changes to ACTIVE
    - Page fully visible and functional
    
    Args:
        user: User instance (must be authenticated)
        page_public_id: Public ID (UUIDv7) of the page
    
    Returns:
        Page: Updated page instance
    
    Raises:
        PermissionDenied: If user cannot activate this page
        ValidationError: If page not found or invalid state
    """
    if not user or not user.is_authenticated:
        raise PermissionDenied("User must be authenticated to activate pages")
    
    if reject_bigint_id(page_public_id):
        raise ValidationError("Invalid page_public_id format")
    
    page = resolve_public_id(Page, page_public_id)
    if not page:
        raise ValidationError(f"Page not found: {page_public_id}")
    
    # Check permission
    if not _can_modify_page(user, page):
        raise PermissionDenied(
            f"User does not have permission to activate this page. "
            f"Admin Pandit can only activate pages they created."
        )
    
    # Check if already active
    if page.status == PAGE_STATUS_ACTIVE:
        logger.warning(f"Page {page.public_id} is already active")
        return page
    
    try:
        with transaction.atomic():
            # Update status
            old_status = page.status
            page.status = PAGE_STATUS_ACTIVE
            page.save(update_fields=['status'])
            
            # Create audit log (optional - table may not exist yet)
            try:
                PageAuditLog.objects.create(
                    page=page,
                    action=AUDIT_ACTION_ACTIVATE,
                    performed_by=user
                )
            except Exception:
                logger.warning(f"Could not create audit log for page {page.public_id} - table may not exist")
            
            logger.info(f"Page activated: {page.public_id} by {user.email} (was {old_status})")
            return page
    
    except Exception as e:
        logger.error(f"Error activating page: {str(e)}", exc_info=True)
        raise


def make_page_invisible(user, page):
    """
    Make a page invisible (hidden from listings/search, accessible via direct URL).
    
    Rules:
    - ADMIN_PANDIT: CANNOT make pages invisible
    - SUPER_ADMIN: Can make any page invisible
    
    Effects:
    - Status changes to INVISIBLE
    - Hidden from listings/search
    - Still accessible via direct URL
    - Banner shown indicating page is invisible
    
    Args:
        user: User instance (must be authenticated)
        page: Page instance
    
    Returns:
        Page: Updated page instance
    
    Raises:
        PermissionDenied: If user cannot make page invisible (Admin Pandit cannot)
        ValidationError: If page not found or invalid state
    """
    if not user or not user.is_authenticated:
        raise PermissionDenied("User must be authenticated to make pages invisible")
    
    if not page:
        raise ValidationError("Page instance required")
    
    # Check permission: Only Super Admin can make pages invisible
    if not _is_super_admin(user):
        raise PermissionDenied(
            "Only Super Admin can make pages invisible. "
            "Admin Pandit does not have this permission."
        )
    
    # Check if already invisible
    if page.status == PAGE_STATUS_INVISIBLE:
        logger.warning(f"Page {page.public_id} is already invisible")
        return page
    
    try:
        with transaction.atomic():
            # Update status
            old_status = page.status
            page.status = PAGE_STATUS_INVISIBLE
            page.save(update_fields=['status'])
            
            # Create audit log (optional - table may not exist yet)
            try:
                PageAuditLog.objects.create(
                    page=page,
                    action=AUDIT_ACTION_VISIBILITY_CHANGE,
                    performed_by=user
                )
            except Exception:
                logger.warning(f"Could not create audit log for page {page.public_id} - table may not exist")
            
            logger.info(f"Page made invisible: {page.public_id} by {user.email} (was {old_status})")
            return page
    
    except Exception as e:
        logger.error(f"Error making page invisible: {str(e)}", exc_info=True)
        raise


def make_page_visible(user, page):
    """
    Make an invisible page visible (change status from INVISIBLE to ACTIVE).
    
    TASK SA-2: Super Admin visibility toggle
    
    Rules:
    - Only Super Admin can make pages visible
    - Status changes from INVISIBLE to ACTIVE
    
    Args:
        user: User instance (must be authenticated)
        page: Page instance
    
    Returns:
        Page: Updated page instance
    
    Raises:
        PermissionDenied: If user cannot make page visible
        ValidationError: If page not found or invalid state
    """
    if not user or not user.is_authenticated:
        raise PermissionDenied("User must be authenticated to make pages visible")
    
    if not page:
        raise ValidationError("Page instance required")
    
    # Check permission: Only Super Admin can make pages visible
    if not _is_super_admin(user):
        raise PermissionDenied(
            "Only Super Admin can make pages visible. "
            "Admin Pandit does not have this permission."
        )
    
    # Check if already visible (not INVISIBLE)
    if page.status != PAGE_STATUS_INVISIBLE:
        logger.warning(f"Page {page.public_id} is not invisible (status: {page.status})")
        return page
    
    try:
        with transaction.atomic():
            # Update status to ACTIVE
            old_status = page.status
            page.status = PAGE_STATUS_ACTIVE
            page.save(update_fields=['status'])
            
            # Create audit log (optional - table may not exist yet)
            try:
                PageAuditLog.objects.create(
                    page=page,
                    action=AUDIT_ACTION_VISIBILITY_CHANGE,
                    performed_by=user
                )
            except Exception:
                logger.warning(f"Could not create audit log for page {page.public_id} - table may not exist")
            
            logger.info(f"Page made visible: {page.public_id} by {user.email} (was {old_status})")
            return page
    
    except Exception as e:
        logger.error(f"Error making page visible: {str(e)}", exc_info=True)
        raise
