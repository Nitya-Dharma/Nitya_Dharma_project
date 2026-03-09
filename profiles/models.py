from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from core.public_id import generate_public_id
from core.deletion_guard import DeletionGuardMixin


class PanditProfile(DeletionGuardMixin, models.Model):
    """
    Pandit Profile model.
    
    One-to-One relationship with User (role='pandit').
    Contains profile-specific data separate from identity (User model).
    
    This model:
    - Stores profile data (bio, experience, etc.)
    - References master data (cities, areas, poojas)
    - Stores SEO template text (placeholders only)
    - Does NOT contain: referral logic, blocking logic, reviews, availability, media files
    - Does NOT store: profile completion flags (computed via signals), visibility flags (governance-owned)
    """
    
    # Identity Link
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pandit_profile',
        verbose_name='User',
        help_text='The Pandit user this profile belongs to'
    )
    
    # Public ID: UUIDv7 for external-facing URLs/APIs
    # Internal ID (id) remains BIGINT for performance (joins, indexes)
    # Security: Never expose internal BIGINT IDs in URLs, templates, or APIs
    public_id = models.CharField(
        max_length=36,  # UUID format length
        unique=True,
        db_index=True,
        null=True,  # Nullable initially for existing records
        blank=True,
        editable=False,  # Auto-generated, never manually set
        verbose_name='Public ID',
        help_text='Public-facing UUIDv7 identifier for URLs and APIs. Internal ID (id) is used for database joins.'
    )
    
    # SEO-optimized slug for URLs
    # Format: <public_id>-<first-name>-<last-name>-<local-area>-<city>-<state>
    slug = models.SlugField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        unique=True,
        verbose_name='SEO Slug',
        help_text='SEO-optimized URL slug. Auto-generated if not provided. Format: <id>-<name>-<location>-<city>-<state>'
    )
    
    # Public Profile Fields (Editable by Pandit)
    display_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='Display Name',
        help_text='Public display name for the Pandit (optional, can use User name)'
    )
    about_description = models.TextField(
        blank=True,
        null=True,
        verbose_name='About / Bio',
        help_text='Detailed description about the Pandit, their experience, and services'
    )
    experience_years = models.PositiveIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Years of Experience',
        help_text='Number of years of experience as a Pandit'
    )
    languages_spoken = models.TextField(
        blank=True,
        null=True,
        verbose_name='Languages Spoken (Legacy)',
        help_text='DEPRECATED: Comma-separated list of languages. Use languages M2M field instead. Kept for backward compatibility.'
    )
    # New M2M field for controlled language selection
    languages = models.ManyToManyField(
        'masterdata.Language',
        related_name='pandit_profiles',
        blank=True,
        verbose_name='Languages',
        help_text='Languages spoken by this Pandit (controlled master data)'
    )
    
    # Contact Information (Privacy-Controlled)
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Phone Number (Legacy)',
        help_text='DEPRECATED: Legacy phone number field. Use primary_mobile_number instead. Kept for backward compatibility.'
    )
    # TASK 3.1: Normalized phone number fields (kept for backward compatibility)
    phone_country_code = models.ForeignKey(
        'masterdata.CountryCode',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='pandit_profiles',
        verbose_name='Phone Country Code (Legacy)',
        help_text='DEPRECATED: Use primary_mobile_number instead. Kept for backward compatibility.'
    )
    phone_national_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Phone National Number (Legacy)',
        help_text='DEPRECATED: Use primary_mobile_number instead. Kept for backward compatibility.'
    )
    # Primary mobile number (used for both Call and WhatsApp) - KEPT FOR BACKWARD COMPATIBILITY
    primary_mobile_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        verbose_name='Primary Mobile Number (Legacy)',
        help_text='DEPRECATED: Legacy field. Use call_mobile_number and whatsapp_mobile_number instead. Kept for backward compatibility.'
    )
    # Secondary mobile number (optional, informational only)
    secondary_mobile_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        verbose_name='Secondary Mobile Number',
        help_text='Additional mobile number (optional, informational only, not used for call/WhatsApp)'
    )
    # NEW: Separate mobile numbers for Call and WhatsApp
    call_mobile_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        verbose_name='Calling Mobile Number',
        help_text='Mobile number used for phone calls (with country code, e.g., +919876543210)'
    )
    whatsapp_mobile_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        verbose_name='WhatsApp Mobile Number',
        help_text='Mobile number used for WhatsApp (with country code, e.g., +919876543210)'
    )
    use_same_number_for_call_and_whatsapp = models.BooleanField(
        default=True,
        verbose_name='Use Same Number for Call & WhatsApp',
        help_text='If checked, WhatsApp number will mirror the calling number. If unchecked, both numbers can be set independently.'
    )
    # Enable/disable flags for primary number - KEPT FOR BACKWARD COMPATIBILITY
    enable_call = models.BooleanField(
        default=True,
        verbose_name='Enable Calls (Legacy)',
        help_text='DEPRECATED: Legacy field. Kept for backward compatibility.'
    )
    enable_whatsapp = models.BooleanField(
        default=False,
        verbose_name='Enable WhatsApp (Legacy)',
        help_text='DEPRECATED: Legacy field. Kept for backward compatibility.'
    )
    # Legacy fields (kept for backward compatibility, mapped to new fields)
    allow_call = models.BooleanField(
        default=True,
        verbose_name='Allow Calls (Legacy)',
        help_text='DEPRECATED: Use enable_call instead. Kept for backward compatibility.'
    )
    allow_whatsapp = models.BooleanField(
        default=False,
        verbose_name='Allow WhatsApp (Legacy)',
        help_text='DEPRECATED: Use enable_whatsapp instead. Kept for backward compatibility.'
    )
    
    # Profile Image (Single source of truth)
    profile_image = models.ImageField(
        upload_to='profiles/pandit_images/',
        blank=True,
        null=True,
        verbose_name='Profile Image',
        help_text='Profile picture for the Pandit (recommended: square image, max 5MB)'
    )
    
    # Cover Image (Hero section background)
    cover_image = models.ImageField(
        upload_to='profiles/cover_images/',
        blank=True,
        null=True,
        verbose_name='Cover Image',
        help_text='Cover photo for profile hero section (recommended: 1920x600px, max 5MB)'
    )
    
    # Master Data Relationships (ManyToMany - Approved Data Only)
    cities_served = models.ManyToManyField(
        'masterdata.City',
        related_name='pandits',
        blank=True,
        verbose_name='Cities Served',
        help_text='Cities where the Pandit provides services (approved master data only)'
    )
    areas_served = models.ManyToManyField(
        'masterdata.LocalArea',
        related_name='pandits',
        blank=True,
        verbose_name='Areas Served',
        help_text='Local areas where the Pandit provides services (approved master data only)'
    )
    poojas_performed = models.ManyToManyField(
        'masterdata.Pooja',
        related_name='pandits',
        blank=True,
        verbose_name='Poojas Performed',
        help_text='Types of poojas the Pandit performs (approved master data only)'
    )
    
    # Referral / Trust Ownership (CLARIFICATION)
    # PanditProfile does not define or reference referral fields.
    # Any referral linkage remains exclusively in Module 3 / User model (User.referred_by).
    # Profile is a data consumer only, not an authority for trust/referral logic.
    
    # SEO Metadata (DB-Stored, Editable, Auto-Generated)
    seo_title = models.CharField(
        max_length=60,
        blank=True,
        null=True,
        verbose_name='SEO Title',
        help_text='SEO title for search engines (max 60 characters, auto-generated from profile data)'
    )
    seo_description = models.CharField(
        max_length=160,
        blank=True,
        null=True,
        verbose_name='SEO Description',
        help_text='SEO description for search engines (max 160 characters, auto-generated from profile data)'
    )
    seo_keywords = models.TextField(
        blank=True,
        null=True,
        verbose_name='SEO Keywords',
        help_text='SEO keywords (comma-separated, unlimited length, auto-generated from profile data)'
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
    
    # Profile Approval (Admin Pandit controlled)
    is_profile_approved = models.BooleanField(
        default=False,
        verbose_name='Profile Approved',
        help_text='Whether the profile has been approved for public visibility by Admin Pandit'
    )
    profile_approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Profile Approved At',
        help_text='Timestamp when the profile was approved for public visibility'
    )
    profile_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_profiles',
        verbose_name='Approved By',
        help_text='Admin Pandit who approved this profile'
    )
    
    # Audit Fields
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_pandit_profiles',
        verbose_name='Created By',
        help_text='User who created this profile (usually the Pandit themselves)'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='updated_pandit_profiles',
        verbose_name='Updated By',
        help_text='User who last updated this profile'
    )
    
    class Meta:
        verbose_name = 'Pandit Profile'
        verbose_name_plural = 'Pandit Profiles'
        db_table = 'profiles_panditprofile'
        ordering = ['-created_at']
        # Security: Ensure unique constraint on user (one profile per user)
        constraints = [
            models.UniqueConstraint(fields=['user'], name='unique_pandit_profile_per_user')
        ]
        indexes = [
            models.Index(fields=['id'], name='profile_id_idx'),  # Fast lookup by unique ID
            models.Index(fields=['user', 'is_profile_approved'], name='profile_user_approved_idx'),  # Fast filtering
            models.Index(fields=['is_profile_approved'], name='profile_approved_idx'),  # Phase 8.1: list approved pandits
        ]
    
    def __str__(self):
        if self.display_name:
            return f"{self.display_name} ({self.user.email})"
        return f"{self.user.get_full_name()} ({self.user.email})"
    
    def get_display_name(self):
        """Return display name or fallback to user's full name or email."""
        if self.display_name:
            return self.display_name
        return self.user.get_full_name() or self.user.email
    
    def get_profile_image_url(self):
        """
        Get profile image URL with cache busting.
        
        Returns:
            - Image URL with timestamp if image exists
            - None if no image (use default avatar in templates)
        """
        if self.profile_image:
            # Add cache busting using updated_at timestamp
            timestamp = int(self.updated_at.timestamp()) if self.updated_at else ''
            return f"{self.profile_image.url}?v={timestamp}"
        return None
    
    def ensure_unique_slug(self, base_slug):
        """
        Ensure slug is unique by appending counter if needed.
        
        Args:
            base_slug: Base slug to make unique
            
        Returns:
            Unique slug string
        """
        from core.utils.slug_utils import ensure_unique_slug
        return ensure_unique_slug(self, base_slug, max_length=255)
    
    def save(self, *args, **kwargs):
        """
        Override save to auto-generate public_id, slug, and SEO metadata.
        
        Security: public_id is UUIDv7, never expose internal BIGINT id.
        
        Note: SEO metadata generation happens AFTER save because it needs to access
        ManyToMany fields (cities_served, poojas_performed, languages) which require
        the object to have a primary key.
        """
        if not self.public_id:
            self.public_id = generate_public_id()
        
        # 🔒 CRITICAL: Save first to get primary key (required for ManyToMany access)
        # This must happen BEFORE generating slug that accesses M2M fields
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Auto-generate SEO slug if not provided or empty (AFTER save so M2M fields are accessible)
        if not self.slug or self.slug.strip() == "":
            from core.utils.slug_utils import generate_pandit_slug
            base_slug = generate_pandit_slug(self)
            self.slug = self.ensure_unique_slug(base_slug)
            # Save again to persist the slug (only if it was generated)
            if is_new or not self.slug:
                super().save(update_fields=['slug'])
        
        # Auto-generate SEO metadata if enabled (after save so ManyToMany fields are accessible)
        from .seo_services import auto_generate_pandit_seo
        if auto_generate_pandit_seo(self, force=False):
            # Save again if SEO was generated
            super().save(update_fields=['seo_title', 'seo_description', 'seo_keywords', 'seo_autogenerated', 'seo_last_updated_at'])
    
    def has_profile_image(self):
        """Check if profile has an image."""
        return bool(self.profile_image)
    
    def has_cover_image(self):
        """Check if profile has a cover image."""
        return bool(self.cover_image)
    
    def get_cover_image_url(self):
        """
        Get cover image URL with cache busting.
        
        Returns:
            - Image URL with timestamp if image exists
            - None if no image (use gradient background)
        """
        if self.cover_image:
            # Add cache busting using updated_at timestamp
            timestamp = int(self.updated_at.timestamp()) if self.updated_at else ''
            return f"{self.cover_image.url}?v={timestamp}"
        return None
    
    def get_required_fields_status(self):
        """
        Get status of all required fields for profile completion.
        
        Required fields:
        - Full Name (user.first_name + user.last_name)
        - Profile Picture (profile_image)
        - City (cities_served)
        - Area (areas_served)
        - At least one Pooja (poojas_performed)
        - Description (about_description) - Optional but recommended
        
        Returns:
            dict: {
                'full_name': bool,
                'profile_image': bool,
                'city': bool,
                'area': bool,
                'poojas': bool,
                'description': bool,  # Optional
            }
        """
        return {
            'full_name': bool(self.user.first_name and self.user.last_name),
            'profile_image': self.has_profile_image(),
            'city': self.cities_served.exists(),
            'area': self.areas_served.exists(),
            'poojas': self.poojas_performed.exists(),
            'description': bool(self.about_description),  # Optional
        }
    
    def get_completion_percentage(self):
        """
        Calculate profile completion percentage.
        
        Required fields (5):
        1. Full Name
        2. Profile Picture
        3. City
        4. Area
        5. At least one Pooja
        
        Returns:
            int: Completion percentage (0-100)
        """
        status = self.get_required_fields_status()
        
        # Count required fields (excluding optional description)
        required_fields = [
            status['full_name'],
            status['profile_image'],
            status['city'],
            status['area'],
            status['poojas'],
        ]
        
        completed_count = sum(1 for field in required_fields if field)
        total_required = len(required_fields)
        
        if total_required == 0:
            return 0
        
        percentage = int((completed_count / total_required) * 100)
        return min(100, max(0, percentage))  # Clamp between 0 and 100
    
    def is_profile_complete(self):
        """
        Check if profile is complete (all required fields filled).
        
        Returns:
            bool: True if all required fields are filled
        """
        status = self.get_required_fields_status()
        return all([
            status['full_name'],
            status['profile_image'],
            status['city'],
            status['area'],
            status['poojas'],
        ])
    
    def get_missing_required_fields(self):
        """
        Get list of missing required fields.
        
        Returns:
            list: List of field names that are missing
        """
        status = self.get_required_fields_status()
        missing = []
        
        field_labels = {
            'full_name': 'Full Name',
            'profile_image': 'Profile Picture',
            'city': 'City',
            'area': 'Area',
            'poojas': 'At least one Pooja',
        }
        
        for field, is_complete in status.items():
            if field in field_labels and not is_complete:
                missing.append(field_labels[field])
        
        return missing
