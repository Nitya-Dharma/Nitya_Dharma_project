"""
Page core models for generic page system.

Supports:
- Temple pages
- Brand pages
- Trust pages
- Social Service pages

Architecture:
- Dual-ID Strategy: Internal BIGINT (joins) + Public UUIDv7 (exposure)
- Soft delete only: is_deleted always False (hard delete forbidden)
- Append-only audit logs for status changes
- INVISIBLE pages still accessible via direct URL
"""

# Import PageAccessRequest so Django can discover it
from .models_access_request import PageAccessRequest

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from core.public_id import generate_public_id
from core.audit import log_blocked_deletion
from core.validators import validate_image_file, validate_image_extension
from .constants import (
    PAGE_TYPE_CHOICES,
    PAGE_TYPES,
    OWNER_ROLE_CHOICES,
    OWNER_ROLES,
    PAGE_STATUS_CHOICES,
    PAGE_STATUSES,
    PAGE_STATUS_ACTIVE,
    AUDIT_ACTION_CHOICES,
    AUDIT_ACTIONS,
)


class Page(models.Model):
    """
    Generic page model supporting multiple page types.
    
    Rules:
    - NEVER hard-deleted (is_deleted always False)
    - INVISIBLE pages accessible via direct URL
    - Status changes logged in PageAuditLog
    - Slug unique per page_type
    """
    
    # Dual-ID Strategy
    id = models.BigAutoField(primary_key=True)  # Internal: for joins/performance
    public_id = models.CharField(
        max_length=36,
        unique=True,
        db_index=True,
        editable=False,
        null=True,
        blank=True,
        verbose_name='Public ID',
        help_text='Public-facing UUIDv7 identifier. Internal ID (id) is used for database joins.'
    )
    
    # Page Identity
    page_type = models.CharField(
        max_length=20,
        choices=PAGE_TYPE_CHOICES,
        db_index=True,
        verbose_name='Page Type',
        help_text='Type of page (TEMPLE, BRAND, TRUST, SOCIAL_SERVICE)'
    )
    
    title = models.TextField(
        verbose_name='Title',
        help_text='Page title (no length limit)'
    )
    
    slug = models.SlugField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Slug',
        help_text='URL-friendly identifier (auto-generated from title if empty, unique per page_type)'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='Description',
        help_text='Page description/content'
    )
    
    address = models.TextField(
        verbose_name='Address',
        help_text='Temple/Page address (required)'
    )
    
    # Location (FK to master data)
    city = models.ForeignKey(
        'masterdata.City',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='pages',
        verbose_name='City',
        help_text='City where the page/temple is located'
    )
    
    area = models.ForeignKey(
        'masterdata.LocalArea',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='pages',
        verbose_name='Area',
        help_text='Local area where the page/temple is located'
    )
    
    cover_image = models.ImageField(
        upload_to='pages/covers/',
        null=True,
        blank=True,
        validators=[validate_image_file, validate_image_extension],
        verbose_name='Cover Image',
        help_text='Cover image for the page'
    )
    
    profile_image = models.ImageField(
        upload_to='pages/profiles/',
        null=True,
        blank=True,
        validators=[validate_image_file, validate_image_extension],
        verbose_name='Profile Image',
        help_text='Profile image for the page'
    )
    
    # Ownership & Creation
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,  # Prevent deletion if page exists
        related_name='created_pages',
        verbose_name='Created By',
        help_text='User who created this page'
    )
    
    # TASK 4: Immutable snapshot of creator name (preserved even if creator is deactivated)
    created_by_display_name = models.TextField(
        null=True,
        blank=True,
        verbose_name='Creator Display Name',
        help_text='Immutable snapshot of the creator name at time of creation. Preserved even if creator is deactivated.'
    )
    
    owner_role = models.CharField(
        max_length=20,
        choices=OWNER_ROLE_CHOICES,
        db_index=True,
        verbose_name='Owner Role',
        help_text='Role of the page owner (ADMIN_PANDIT or SUPER_ADMIN)'
    )
    
    # Status & Lifecycle
    status = models.CharField(
        max_length=20,
        choices=PAGE_STATUS_CHOICES,
        default=PAGE_STATUS_ACTIVE,
        db_index=True,
        verbose_name='Status',
        help_text='Page status (ACTIVE, DEACTIVATED, INVISIBLE). INVISIBLE pages still accessible via direct URL.'
    )
    
    # TASK 6: Deactivation tracking
    visibility_reason = models.TextField(
        null=True,
        blank=True,
        verbose_name='Visibility Reason',
        help_text='Reason why page is INVISIBLE or DEACTIVATED'
    )
    
    deactivated_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Deactivated At',
        help_text='Timestamp when page was deactivated (null = active)'
    )
    
    reactivated_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Reactivated At',
        help_text='Timestamp when page was reactivated (null = never reactivated)'
    )
    
    is_deleted = models.BooleanField(
        default=False,
        editable=False,
        verbose_name='Is Deleted',
        help_text='ALWAYS False - hard delete is forbidden. Pages are soft-deleted via status changes only.'
    )
    
    # Followers & Slug Locking
    followers_count = models.PositiveIntegerField(
        default=0,
        db_index=True,
        verbose_name='Followers Count',
        help_text='Number of followers. When > 0, slug becomes immutable.'
    )
    
    # TASK 4: Page Custodian (Super Admin who manages page after creator deactivation)
    custodian = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='custodianship_pages',
        verbose_name='Page Custodian',
        help_text='Super Admin who manages this page after creator deactivation'
    )
    
    # SEO Metadata (DB-Stored, Editable, Auto-Generated)
    seo_title = models.CharField(
        max_length=60,
        blank=True,
        null=True,
        verbose_name='SEO Title',
        help_text='SEO title for search engines (max 60 characters, auto-generated from page data)'
    )
    seo_description = models.CharField(
        max_length=160,
        blank=True,
        null=True,
        verbose_name='SEO Description',
        help_text='SEO description for search engines (max 160 characters, auto-generated from page data)'
    )
    seo_keywords = models.TextField(
        blank=True,
        null=True,
        verbose_name='SEO Keywords',
        help_text='SEO keywords (comma-separated, unlimited length, auto-generated from page data)'
    )
    seo_autogenerated = models.BooleanField(
        default=True,
        verbose_name='SEO Auto-Generated',
        help_text='Whether SEO metadata was auto-generated (set to False when user manually edits)'
    )
    seo_last_updated_at = models.DateTimeField(
        auto_now=True,
        null=True,
        blank=True,
        verbose_name='SEO Last Updated At',
        help_text='Timestamp when SEO metadata was last updated'
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Created At',
        help_text='Timestamp when page was created'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        db_index=True,
        verbose_name='Updated At',
        help_text='Timestamp when page was last updated'
    )
    
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='updated_pages',
        verbose_name='Updated By',
        help_text='User who last updated this page'
    )
    
    class Meta:
        db_table = 'pages_page'
        verbose_name = 'Page'
        verbose_name_plural = 'Pages'
        ordering = ['-created_at']
        # Unique constraint: slug must be unique per page_type (only when slug is not null)
        # Note: unique_together doesn't work well with null values, so we handle uniqueness in save()
        indexes = [
            models.Index(fields=['page_type', 'status']),
            models.Index(fields=['owner_role', 'status']),
            models.Index(fields=['created_by', 'status']),
            models.Index(fields=['public_id']),
        ]
    
    def _get_creator_display_name(self, creator_user):
        """Get display name for page creator."""
        if creator_user.username:
            return creator_user.username
        elif creator_user.get_full_name():
            return creator_user.get_full_name()
        else:
            return creator_user.email
    
    def can_edit_slug(self):
        """
        Check if slug can be edited.
        
        Returns:
            True if followers_count == 0, False otherwise
        """
        return self.followers_count == 0
    
    def _get_creator_display_name(self, creator_user):
        """Get display name for page creator."""
        if creator_user.username:
            return creator_user.username
        elif creator_user.get_full_name():
            return creator_user.get_full_name()
        else:
            return creator_user.email
    
    def save(self, *args, **kwargs):
        """Auto-generate public_id and slug if not set. Enforce slug immutability."""
        from core.image_pipeline import optimize_image_if_new, process_derived_images_after_save
        optimize_image_if_new(self, 'cover_image')
        optimize_image_if_new(self, 'profile_image')
        if not self.public_id:
            self.public_id = generate_public_id()
        
        # TASK 4: Capture creator display name if not set
        if self.created_by and not self.created_by_display_name:
            self.created_by_display_name = self._get_creator_display_name(self.created_by)
        
        # Ensure is_deleted is always False
        self.is_deleted = False
        
        # Slug immutability: after first save, slug is never modified (source of truth for URLs/SEO).
        if self.pk:  # Existing page
            try:
                old_instance = Page.objects.get(pk=self.pk)
                # Always restore original slug; ignore any submitted change.
                self.slug = old_instance.slug
            except Page.DoesNotExist:
                pass  # New instance, no old slug to compare
        
        # Auto-generate SEO-optimized slug if empty
        if not self.slug or not self.slug.strip():
            from core.utils.slug_utils import generate_temple_slug, ensure_unique_slug
            base_slug = generate_temple_slug(self)
            
            # Ensure uniqueness per page_type
            slug = base_slug
            counter = 1
            while Page.objects.filter(page_type=self.page_type, slug=slug).exclude(pk=self.pk if self.pk else None).exists():
                # Append counter, ensuring we don't exceed max_length
                suffix = f"-{counter}"
                if len(base_slug) + len(suffix) > 255:
                    available_length = 255 - len(suffix)
                    slug = base_slug[:available_length] + suffix
                else:
                    slug = base_slug + suffix
                counter += 1
                
                # Safety: prevent infinite loop
                if counter > 1000:
                    slug = self.public_id or f"page-{self.id}"
                    break
            
            self.slug = slug
        
        # Auto-generate SEO metadata if enabled
        from .seo_services import auto_generate_page_seo
        auto_generate_page_seo(self, force=False)
        
        super().save(*args, **kwargs)
        process_derived_images_after_save(self, 'cover_image')
        process_derived_images_after_save(self, 'profile_image')
        
        # Handle legacy 'name' column if it exists (for backward compatibility)
        if hasattr(self, 'name'):
            try:
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("PRAGMA table_info(pages_page)")
                    columns = [row[1] for row in cursor.fetchall()]
                    if 'name' in columns:
                        # Update legacy name column
                        cursor.execute(
                            "UPDATE pages_page SET name = ? WHERE id = ?",
                            [self.title, self.id]
                        )
            except Exception:
                pass  # Ignore if legacy column doesn't exist
    
    def clean(self):
        """Validate model data."""
        if not self.title or not self.title.strip():
            raise ValidationError("title is required")
        
        if not self.address or not self.address.strip():
            raise ValidationError("address is required")
        
        if self.page_type not in PAGE_TYPES:
            raise ValidationError(f"Invalid page_type: {self.page_type}. Must be one of {PAGE_TYPES}")
        
        # TASK 30: Validate slug immutability if page exists
        if self.pk and self.followers_count > 0:
            try:
                old_instance = Page.objects.get(pk=self.pk)
                if old_instance.slug != self.slug:
                    from core.audit import log_blocked_deletion
                    log_blocked_deletion(
                        self,
                        actor=None,
                        reason=f"SLUG_LOCKED - Slug change blocked in clean(), page has {self.followers_count} follower(s)"
                    )
                    raise ValidationError({
                        'slug': 'Slug cannot be modified once the page has followers. '
                               f'Current followers: {self.followers_count}. '
                               f'Slug is locked to preserve shared URLs and bookmarks.'
                    })
            except Page.DoesNotExist:
                pass  # New instance, skip validation
        
        # Validate owner_role - it must be set and valid
        # For new instances (no pk), owner_role may not be set yet (will be set in service)
        # For existing instances, owner_role must be valid
        if self.pk:  # Existing instance - owner_role must be valid
            if not self.owner_role:
                raise ValidationError("owner_role is required. Must be one of {}".format(OWNER_ROLES))
            if self.owner_role not in OWNER_ROLES:
                raise ValidationError(f"Invalid owner_role: '{self.owner_role}'. Must be one of {OWNER_ROLES}")
        # For new instances (no pk), owner_role will be set in service before final save
        # So we skip validation here to avoid false errors during form validation
        
        if self.status not in PAGE_STATUSES:
            raise ValidationError(f"Invalid status: {self.status}")
        
        # Ensure is_deleted is always False
        if self.is_deleted:
            raise ValidationError("is_deleted must always be False. Use status changes for soft deletion.")
    
    def delete(self, using=None, keep_parents=False):
        """
        Override delete() to prevent hard deletion.
        
        TASK 6: Pages must never be hard-deleted. Use deactivate() for soft deletion.
        TASK 30: If page has followers, convert to INVISIBLE instead of deleting.
        """
        # TASK 30: If page has followers, convert to INVISIBLE
        if self.followers_count > 0:
            log_blocked_deletion(
                self,
                actor=None,
                reason=f"Page deletion blocked - page has {self.followers_count} follower(s). Converting to INVISIBLE."
            )
            # Automatically convert to INVISIBLE
            self.deactivate(
                reason=f"Page deletion attempted but page has {self.followers_count} follower(s). Converted to INVISIBLE.",
                status=PAGE_STATUS_INVISIBLE,
                actor=None
            )
            raise ValidationError(
                f"Hard deletion is not allowed for Page '{self.title}'. "
                f"This page has {self.followers_count} follower(s) and has been converted to INVISIBLE. "
                f"Slug and URL remain accessible. Use deactivate() method explicitly if needed."
            )
        
        # If no followers, still block deletion (use deactivate instead)
        log_blocked_deletion(self, actor=None, reason="Page hard deletion blocked - use deactivate() instead")
        raise ValidationError(
            f"Hard deletion is not allowed for Page. "
            f"Use deactivate() method to set status='INVISIBLE' or status='DEACTIVATED'."
        )
    
    def deactivate(self, reason=None, status=None, actor=None):
        """
        TASK 6: Deactivate this page (soft deletion).
        
        Sets page status to INVISIBLE or DEACTIVATED without deleting data.
        URL continues to resolve, content remains stored.
        
        Args:
            reason (str, optional): Reason for deactivation
            status (str, optional): Target status ('INVISIBLE' or 'DEACTIVATED'). Defaults to 'INVISIBLE'
            actor (User, optional): User performing deactivation (must be Super Admin)
        
        Returns:
            bool: True if deactivation was successful
        """
        from django.utils import timezone
        
        if status is None:
            status = PAGE_STATUS_INVISIBLE
        
        if status not in [PAGE_STATUS_INVISIBLE, PAGE_STATUS_DEACTIVATED]:
            raise ValidationError(f"Invalid deactivation status: {status}. Must be INVISIBLE or DEACTIVATED.")
        
        if self.status == status:
            return True  # Already in this state
        
        self.status = status
        self.visibility_reason = reason or "Page deactivated"
        self.deactivated_at = timezone.now()
        self.reactivated_at = None  # Clear reactivation timestamp
        self.save(update_fields=['status', 'visibility_reason', 'deactivated_at', 'reactivated_at'])
        
        # Log audit event
        from core.audit import log_deactivation
        log_deactivation(
            self,
            actor=actor,
            reason=f"PAGE_DEACTIVATED - Status: {status}, Reason: {reason or 'N/A'}"
        )
        
        return True
    
    def reactivate(self, reason=None, actor=None):
        """
        TASK 6: Reactivate this page.
        TASK 29: Followers are automatically restored on reactivation.
        
        Only Super Admin can reactivate pages.
        
        Args:
            reason (str, optional): Reason for reactivation
            actor (User, optional): User performing reactivation (must be Super Admin)
        
        Returns:
            bool: True if reactivation was successful
        """
        from django.utils import timezone
        
        if self.status == PAGE_STATUS_ACTIVE:
            return True  # Already active
        
        if actor and not actor.is_superuser:
            raise ValidationError("Only Super Admin can reactivate pages.")
        
        self.status = PAGE_STATUS_ACTIVE
        self.visibility_reason = None  # Clear deactivation reason
        self.reactivated_at = timezone.now()
        self.save(update_fields=['status', 'visibility_reason', 'reactivated_at'])
        
        # Log audit event
        from core.audit import log_deactivation
        log_deactivation(
            self,
            actor=actor,
            reason=f"PAGE_REACTIVATED - Reason: {reason or 'N/A'}"
        )
        
        # TASK 29: Followers are automatically restored (no action needed, they were never deleted)
        # The reactivation service will log this
        
        return True
    
    def __str__(self):
        return f"{self.get_page_type_display()}: {self.title} ({self.public_id[:8]}...)"


class PageGalleryImage(models.Model):
    """
    Gallery images for pages.
    
    Allows page owners (pandits/admins) to upload multiple images
    to showcase their temple/page.
    
    Rules:
    - No hard deletes (is_hidden flag only)
    - Admin Pandit can delete only their own images
    - Super Admin can hide/unhide any image
    - Hidden images invisible to end users
    """
    
    id = models.BigAutoField(primary_key=True)
    public_id = models.CharField(
        max_length=36,
        unique=True,
        db_index=True,
        editable=False,
        null=True,
        blank=True,
        verbose_name='Public ID',
        help_text='Public-facing UUIDv7 identifier'
    )
    
    page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        related_name='gallery_images',
        verbose_name='Page',
        help_text='Page this image belongs to'
    )
    
    image = models.ImageField(
        upload_to='pages/gallery/',
        validators=[validate_image_file, validate_image_extension],
        verbose_name='Image',
        help_text='Gallery image for the page'
    )
    
    caption = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Caption',
        help_text='Optional caption for the image'
    )
    
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='uploaded_gallery_images',
        verbose_name='Uploaded By',
        help_text='User who uploaded this image'
    )
    
    is_hidden = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name='Is Hidden',
        help_text='If True, image is hidden from public view. No hard deletes allowed.'
    )
    
    is_deleted = models.BooleanField(
        default=False,
        editable=False,
        verbose_name='Is Deleted',
        help_text='ALWAYS False - hard delete is forbidden. Use is_hidden for hiding.'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Created At',
        help_text='Timestamp when image was uploaded'
    )
    
    class Meta:
        db_table = 'pages_page_gallery_image'
        verbose_name = 'Page Gallery Image'
        verbose_name_plural = 'Page Gallery Images'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['page', 'created_at']),
        ]
    
    def save(self, *args, **kwargs):
        """Auto-generate public_id if not set and enforce is_deleted=False."""
        from core.image_pipeline import optimize_image_if_new, process_derived_images_after_save
        optimize_image_if_new(self, 'image')
        if not self.public_id:
            self.public_id = generate_public_id()
        # Enforce: is_deleted is ALWAYS False (hard delete forbidden)
        self.is_deleted = False
        super().save(*args, **kwargs)
        process_derived_images_after_save(self, 'image')
    
    def __str__(self):
        return f"Gallery image for {self.page.title}"


class PagePost(models.Model):
    """
    Posts for Temple Pages (Announcements, Events, Updates).
    
    Rules:
    - Admin Pandit: Create/edit/delete own posts, pin/unpin
    - Super Admin: Hide posts
    - Max 5 pinned posts per page
    - No hard deletes (is_hidden flag only)
    """
    
    # Post Types
    POST_TYPE_ANNOUNCEMENT = 'ANNOUNCEMENT'
    POST_TYPE_EVENT = 'EVENT'
    POST_TYPE_UPDATE = 'UPDATE'
    
    POST_TYPES = [
        POST_TYPE_ANNOUNCEMENT,
        POST_TYPE_EVENT,
        POST_TYPE_UPDATE,
    ]
    
    POST_TYPE_CHOICES = [
        (POST_TYPE_ANNOUNCEMENT, 'Announcement'),
        (POST_TYPE_EVENT, 'Event'),
        (POST_TYPE_UPDATE, 'Update'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    public_id = models.CharField(
        max_length=36,
        unique=True,
        db_index=True,
        editable=False,
        null=True,
        blank=True,
        verbose_name='Public ID',
        help_text='Public-facing UUIDv7 identifier'
    )
    
    page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        related_name='posts',
        verbose_name='Page',
        help_text='Page this post belongs to'
    )
    
    post_type = models.CharField(
        max_length=20,
        choices=POST_TYPE_CHOICES,
        db_index=True,
        verbose_name='Post Type',
        help_text='Type of post (ANNOUNCEMENT, EVENT, UPDATE)'
    )
    
    title = models.CharField(
        max_length=255,
        verbose_name='Title',
        help_text='Post title'
    )
    
    content = models.TextField(
        verbose_name='Content',
        help_text='Post content'
    )
    
    # Event-specific fields (optional)
    event_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Event Date',
        help_text='Date/time for events (optional)'
    )
    
    event_location = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Event Location',
        help_text='Location for events (optional)'
    )
    
    # Pinning
    is_pinned = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name='Is Pinned',
        help_text='If True, post is pinned (max 5 per page)'
    )
    
    pinned_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Pinned At',
        help_text='Timestamp when post was pinned'
    )
    
    # TASK 8: Who pinned this post (preserved even if Pandit is deactivated)
    pinned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pinned_page_posts',
        verbose_name='Pinned By',
        help_text='User who pinned this post (preserved even if deactivated)'
    )
    
    # Visibility (TASK 7: Enhanced with status field)
    is_hidden = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name='Is Hidden',
        help_text='If True, post is hidden from public view (deprecated - use status field)'
    )
    
    # TASK 7: Post status (VISIBLE/HIDDEN)
    POST_STATUS_VISIBLE = 'VISIBLE'
    POST_STATUS_HIDDEN = 'HIDDEN'
    
    POST_STATUS_CHOICES = [
        (POST_STATUS_VISIBLE, 'Visible'),
        (POST_STATUS_HIDDEN, 'Hidden'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=POST_STATUS_CHOICES,
        default=POST_STATUS_VISIBLE,
        db_index=True,
        verbose_name='Status',
        help_text='Post visibility status (VISIBLE, HIDDEN). Only Super Admin can hide posts.'
    )
    
    is_deleted = models.BooleanField(
        default=False,
        editable=False,
        verbose_name='Is Deleted',
        help_text='ALWAYS False - hard delete is forbidden. Use status=HIDDEN for hiding.'
    )
    
    # Author
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,  # TASK 27: Never delete posts when author is deactivated
        related_name='created_page_posts',
        verbose_name='Created By',
        help_text='User who created this post (preserved even if deactivated)'
    )
    
    # TASK 27: Immutable snapshot of author name for display when user is deactivated
    created_by_display_name = models.TextField(
        null=True,
        blank=True,
        verbose_name='Author Display Name',
        help_text='Immutable snapshot of author name at time of creation. Preserved even if author is deactivated.'
    )
    
    # TASK 7: Immutable snapshot of creator name (preserved even if creator is deactivated)
    created_by_display_name = models.TextField(
        null=True,
        blank=True,
        verbose_name='Creator Display Name',
        help_text='Immutable snapshot of the creator name at time of creation. Preserved even if creator is deactivated.'
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Created At',
        help_text='Timestamp when post was created'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At',
        help_text='Timestamp when post was last updated'
    )
    
    class Meta:
        db_table = 'pages_page_post'
        verbose_name = 'Page Post'
        verbose_name_plural = 'Page Posts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['page', 'is_hidden', '-created_at']),
            models.Index(fields=['post_type', 'is_hidden']),
            models.Index(fields=['is_pinned', '-pinned_at']),
        ]
    
    def _get_creator_display_name(self, creator_user):
        """Get display name for post creator."""
        if creator_user.username:
            return creator_user.username
        elif creator_user.get_full_name():
            return creator_user.get_full_name()
        else:
            return creator_user.email
    
    def save(self, *args, **kwargs):
        """
        Auto-generate public_id, enforce is_deleted=False, validate pin limit.
        
        TASK 7: Captures creator display name for immutable attribution.
        """
        if not self.public_id:
            self.public_id = generate_public_id()
        
        # TASK 7: Capture creator display name if not set
        if self.created_by and not self.created_by_display_name:
            self.created_by_display_name = self._get_creator_display_name(self.created_by)
        
        # Enforce: is_deleted is ALWAYS False
        self.is_deleted = False
        
        # Sync status with is_hidden for backward compatibility
        if self.is_hidden and self.status == self.POST_STATUS_VISIBLE:
            self.status = self.POST_STATUS_HIDDEN
        elif not self.is_hidden and self.status == self.POST_STATUS_HIDDEN:
            self.is_hidden = True  # Keep is_hidden in sync
        
        # Validate pin limit (max 5 per page)
        if self.is_pinned:
            # Count existing pinned posts for this page (excluding self)
            existing_pinned = PagePost.objects.filter(
                page=self.page,
                is_pinned=True
            ).exclude(pk=self.pk if self.pk else None).count()
            
            if existing_pinned >= 5:
                raise ValidationError(f"Maximum 5 pinned posts allowed per page. Currently {existing_pinned} posts are pinned.")
            
            # Set pinned_at if not set
            if not self.pinned_at:
                from django.utils import timezone
                self.pinned_at = timezone.now()
            # TASK 8: Set pinned_by if not set (use created_by as default)
            if not self.pinned_by:
                self.pinned_by = self.created_by
        else:
            # Clear pinned_at if unpinned (but preserve pinned_by for history)
            self.pinned_at = None
        
        super().save(*args, **kwargs)
    
    def delete(self, using=None, keep_parents=False):
        """
        Override delete() to prevent hard deletion.
        
        TASK 7: PagePosts must never be hard-deleted. Use status=HIDDEN for hiding.
        """
        log_blocked_deletion(self, actor=None, reason="PagePost hard deletion blocked - use status=HIDDEN instead")
        raise ValidationError(
            f"Hard deletion is not allowed for PagePost. "
            f"Use status='HIDDEN' to hide the post from public view. Only Super Admin can hide posts."
        )
    
    def hide(self, reason=None, actor=None):
        """
        TASK 7: Hide this post (only Super Admin can do this).
        
        Posts remain in database, attribution preserved, engagement intact.
        
        Args:
            reason (str, optional): Reason for hiding
            actor (User, optional): User performing hide action (must be Super Admin)
        
        Returns:
            bool: True if hiding was successful
        """
        if actor and not actor.is_superuser:
            raise ValidationError("Only Super Admin can hide posts.")
        
        if self.status == self.POST_STATUS_HIDDEN:
            return True  # Already hidden
        
        self.status = self.POST_STATUS_HIDDEN
        self.is_hidden = True  # Keep in sync
        self.save(update_fields=['status', 'is_hidden'])
        
        # Log audit event
        from core.audit import log_deactivation
        log_deactivation(
            self,
            actor=actor,
            reason=f"POST_HIDDEN_BY_SUPER_ADMIN - Reason: {reason or 'N/A'}"
        )
        
        return True
    
    def unpin(self, reason=None, actor=None):
        """
        TASK 8: Unpin this post (only Super Admin can do this).
        
        Pinned posts remain pinned even if the Pandit who pinned them is deactivated.
        Only Super Admin can unpin afterward.
        
        Args:
            reason (str, optional): Reason for unpinning
            actor (User, optional): User performing unpin action (must be Super Admin)
        
        Returns:
            bool: True if unpinning was successful
        """
        if actor and not actor.is_superuser:
            raise ValidationError("Only Super Admin can unpin posts.")
        
        if not self.is_pinned:
            return True  # Already unpinned
        
        self.is_pinned = False
        self.pinned_at = None
        # TASK 8: Preserve pinned_by for history (do not clear it)
        self.save(update_fields=['is_pinned', 'pinned_at'])
        
        # Log audit event
        from core.audit import log_deactivation
        log_deactivation(
            self,
            actor=actor,
            reason=f"POST_UNPINNED_BY_SUPER_ADMIN - Reason: {reason or 'N/A'}"
        )
        
        return True
    
    def __str__(self):
        return f"{self.get_post_type_display()}: {self.title} ({self.page.title})"


class PageAuditLog(models.Model):
    """
    Append-only audit log for page status changes and actions.
    
    Rules:
    - Never updated or deleted
    - Logs all status changes
    - Tracks who performed each action
    """
    
    id = models.BigAutoField(primary_key=True)
    
    page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        related_name='audit_logs',
        verbose_name='Page',
        help_text='Page this audit log entry refers to'
    )
    
    action = models.CharField(
        max_length=30,
        choices=AUDIT_ACTION_CHOICES,
        db_index=True,
        verbose_name='Action',
        help_text='Action performed (CREATE, UPDATE, DEACTIVATE, ACTIVATE, VISIBILITY_CHANGE)'
    )
    
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='page_audit_actions',
        verbose_name='Performed By',
        help_text='User who performed this action'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Created At',
        help_text='Timestamp when action was performed'
    )
    
    class Meta:
        db_table = 'pages_page_audit_log'
        verbose_name = 'Page Audit Log'
        verbose_name_plural = 'Page Audit Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['page', 'created_at']),
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['performed_by', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_action_display()} on {self.page.title} by {self.performed_by.email} at {self.created_at}"


class PageReview(models.Model):
    """
    Reviews for Temple Pages.
    
    Rules:
    - End users can submit reviews
    - Admin Pandit cannot edit/hide reviews
    - Super Admin visibility only (no moderation UI)
    - No verified badge
    - No ranking or sorting logic
    - Immutable after submission
    """
    
    # Visibility states
    VISIBLE = 'visible'
    HIDDEN = 'hidden'
    
    VISIBILITY_STATE_CHOICES = [
        (VISIBLE, 'Visible'),
        (HIDDEN, 'Hidden'),
    ]
    
    # Dual-ID Strategy
    id = models.BigAutoField(primary_key=True)
    public_id = models.CharField(
        max_length=36,
        unique=True,
        db_index=True,
        editable=False,
        null=True,
        blank=True,
        verbose_name='Public ID',
        help_text='Public-facing UUIDv7 identifier'
    )
    
    page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Page',
        help_text='Page this review is for'
    )
    
    # TASK 9: Changed to SET_NULL to preserve review when user is deactivated
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='page_reviews',
        verbose_name='Reviewer',
        help_text='User who submitted this review (null if user was deactivated)'
    )
    
    # TASK 9: Immutable snapshot of reviewer name (preserved even if user is deactivated)
    reviewer_display_name = models.TextField(
        null=True,
        blank=True,
        verbose_name='Reviewer Display Name',
        help_text='Immutable snapshot of the reviewer name at time of submission. Preserved even if user is deactivated.'
    )
    
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Rating',
        help_text='Rating (1-5 stars)'
    )
    
    review_text = models.TextField(
        verbose_name='Review Text',
        help_text='Review content'
    )
    
    visibility_state = models.CharField(
        max_length=20,
        choices=VISIBILITY_STATE_CHOICES,
        default=VISIBLE,
        db_index=True,
        verbose_name='Visibility State',
        help_text='Visibility state (visible, hidden). Only governance can change this.'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Created At',
        help_text='Timestamp when review was submitted'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At',
        help_text='Timestamp when review was last updated'
    )
    
    # Advanced Review System Fields
    helpful_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Helpful Count',
        help_text='Number of users who found this review helpful'
    )
    reported_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Reported Count',
        help_text='Number of times this review has been reported'
    )
    is_hidden = models.BooleanField(
        default=False,
        verbose_name='Is Hidden',
        help_text='Whether this review is hidden from public view due to moderation'
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name='Is Verified',
        help_text='Whether this review is verified (e.g., from completed booking)'
    )
    
    class Meta:
        db_table = 'pages_page_review'
        verbose_name = 'Page Review'
        verbose_name_plural = 'Page Reviews'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['page', 'visibility_state']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['visibility_state', 'created_at']),
        ]
        # One review per user per page (TASK 9: user can be null, so we need to handle this)
        constraints = [
            models.UniqueConstraint(
                fields=['page', 'user'],
                condition=models.Q(user__isnull=False),
                name='unique_user_page_review',
            ),
        ]
    
    def _get_reviewer_display_name(self, reviewer_user):
        """Get display name for reviewer."""
        if reviewer_user.username:
            return reviewer_user.username
        elif reviewer_user.get_full_name():
            return reviewer_user.get_full_name()
        else:
            return reviewer_user.email
    
    def save(self, *args, **kwargs):
        """
        Auto-generate public_id if not set.
        TASK 9: Capture reviewer display name for immutable attribution.
        """
        if not self.public_id:
            self.public_id = generate_public_id()
        
        # TASK 9: Capture reviewer display name if not set
        if self.user and not self.reviewer_display_name:
            self.reviewer_display_name = self._get_reviewer_display_name(self.user)
        
        super().save(*args, **kwargs)
    
    def delete(self, using=None, keep_parents=False):
        """
        Override delete() to prevent hard deletion.
        
        TASK 9: Reviews must never be hard-deleted. Use visibility_state=HIDDEN for hiding.
        """
        log_blocked_deletion(self, actor=None, reason="PageReview hard deletion blocked - use visibility_state=HIDDEN instead")
        raise ValidationError(
            f"Hard deletion is not allowed for PageReview. "
            f"Use visibility_state='HIDDEN' to hide the review. Only Super Admin can hide reviews."
        )
    
    def clean(self):
        """Validate review data."""
        if self.rating < 1 or self.rating > 5:
            raise ValidationError("Rating must be between 1 and 5.")
        
        if not self.review_text or not self.review_text.strip():
            raise ValidationError("Review text is required.")
        
        # User cannot review their own page
        if self.page and self.user and self.page.created_by == self.user:
            raise ValidationError("You cannot review your own page.")
    
    def __str__(self):
        reviewer_name = self.reviewer_display_name or (self.user.email if self.user else "Deleted User")
        return f"Review by {reviewer_name} for {self.page.title} ({self.rating}/5)"


class PageRole(models.Model):
    """
    Page-level roles for Pandits (Owner/Moderator).
    
    Rules:
    - One OWNER per page (the page creator)
    - Multiple MODERATORs allowed per page
    - A pandit can have only one role per page
    - End users cannot have page roles
    """
    
    # Role choices
    ROLE_OWNER = 'OWNER'
    ROLE_MODERATOR = 'MODERATOR'
    
    ROLE_CHOICES = [
        (ROLE_OWNER, 'Owner'),
        (ROLE_MODERATOR, 'Moderator'),
    ]
    
    # Dual-ID Strategy
    id = models.BigAutoField(primary_key=True)
    public_id = models.CharField(
        max_length=36,
        unique=True,
        db_index=True,
        editable=False,
        null=True,
        blank=True,
        verbose_name='Public ID',
        help_text='Public-facing UUIDv7 identifier'
    )
    
    page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        related_name='page_roles',
        verbose_name='Page',
        help_text='Page this role is for'
    )
    
    pandit = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='page_roles',
        verbose_name='Pandit',
        help_text='Pandit user with this role'
    )
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        db_index=True,
        verbose_name='Role',
        help_text='Role type (OWNER or MODERATOR)'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Created At',
        help_text='Timestamp when role was assigned'
    )
    
    class Meta:
        db_table = 'pages_page_role'
        verbose_name = 'Page Role'
        verbose_name_plural = 'Page Roles'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['page', 'pandit']),
            models.Index(fields=['role', 'created_at']),
            models.Index(fields=['pandit', 'role']),
        ]
        # One role per pandit per page
        constraints = [
            models.UniqueConstraint(
                fields=['page', 'pandit'],
                name='unique_pandit_page_role',
            ),
        ]
    
    def save(self, *args, **kwargs):
        """Auto-generate public_id if not set. Validate role constraints."""
        if not self.public_id:
            self.public_id = generate_public_id()
        
        # Validate: Only one OWNER per page
        if self.role == self.ROLE_OWNER:
            existing_owner = PageRole.objects.filter(
                page=self.page,
                role=self.ROLE_OWNER
            ).exclude(pk=self.pk if self.pk else None).first()
            
            if existing_owner:
                raise ValidationError(
                    f"Page {self.page.title} already has an owner: {existing_owner.pandit.email}"
                )
        
        # Validate: Pandit must have pandit role
        if self.pandit.role != 'pandit':
            raise ValidationError(
                f"User {self.pandit.email} must have 'pandit' role to be assigned a page role"
            )
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate role assignment."""
        # Validate role value
        if self.role not in [self.ROLE_OWNER, self.ROLE_MODERATOR]:
            raise ValidationError(f"Invalid role: {self.role}")
        
        # Validate pandit role
        if self.pandit.role != 'pandit':
            raise ValidationError({
                'pandit': 'Only users with pandit role can be assigned page roles'
            })
        
        # Validate owner uniqueness
        if self.role == self.ROLE_OWNER:
            existing_owner = PageRole.objects.filter(
                page=self.page,
                role=self.ROLE_OWNER
            ).exclude(pk=self.pk if self.pk else None).first()
            
            if existing_owner:
                raise ValidationError({
                    'role': f'Page already has an owner: {existing_owner.pandit.email}'
                })
    
    def __str__(self):
        return f"{self.get_role_display()} - {self.pandit.email} on {self.page.title}"


class PageFollow(models.Model):
    """
    Page Follow model for tracking user follows of Pages.
    
    TASK 29: Followers of a Deactivated Page
    
    This model tracks which users follow which pages.
    Follow relationships are preserved even when pages are deactivated.
    """
    
    # Dual-ID Strategy
    id = models.BigAutoField(primary_key=True)
    public_id = models.CharField(
        max_length=36,
        unique=True,
        db_index=True,
        editable=False,
        null=True,
        blank=True,
        verbose_name='Public ID',
        help_text='Public-facing UUIDv7 identifier'
    )
    
    # Follow relationship
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,  # If user is deleted, remove follow
        related_name='page_follows',
        verbose_name='Follower',
        help_text='User following the Page'
    )
    
    page = models.ForeignKey(
        Page,
        on_delete=models.PROTECT,  # TASK 29: Never delete follow records when page is deactivated
        related_name='followers',  # TASK 29: Use 'followers' for reverse lookup (matches migration)
        verbose_name='Page',
        help_text='Page being followed (preserved even if page is INVISIBLE)'
    )
    
    # Timestamp
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Created At',
        help_text='Timestamp when user started following the page'
    )
    
    class Meta:
        verbose_name = 'Page Follow'
        verbose_name_plural = 'Page Follows'
        db_table = 'pages_pagefollow'
        ordering = ['-created_at']
        unique_together = [['follower', 'page']]  # One follow per user per page
        indexes = [
            models.Index(fields=['follower', 'page']),
            models.Index(fields=['page', 'created_at']),
        ]
    
    def save(self, *args, **kwargs):
        """Auto-generate public_id if not set."""
        if not self.public_id:
            self.public_id = generate_public_id()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.follower.email} follows {self.page.title}"
    
    def delete(self, using=None, keep_parents=False):
        """
        TASK 29: Override delete() to prevent hard deletion.
        
        PageFollow records must never be deleted automatically when page is deactivated.
        They are only removed if user explicitly unfollows or user account is deleted.
        """
        from core.audit import log_blocked_deletion
        log_blocked_deletion(
            self,
            actor=None,
            reason="PageFollow hard deletion blocked - follow relationships are preserved"
        )
        raise ValidationError(
            f"Hard deletion is not allowed for PageFollow. "
            f"Follow relationships are preserved even when pages are deactivated. "
            f"Use unfollow() method to remove follow relationship."
        )