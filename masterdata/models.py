from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
from core.public_id import generate_public_id


class City(models.Model):
    """
    Master data model for Cities.
    
    TASK 24: Location / Area Renamed or Merged
    
    Created and approved by Super Admin only.
    Pandits can select from approved cities only.
    
    Locations are immutable - IDs never change, display_name can change.
    """
    # Public ID (UUIDv7 for external-facing URLs)
    public_id = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        editable=False,
        verbose_name='Public ID',
        help_text='Public-facing UUIDv7 identifier for this city'
    )
    
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='City Name',
        help_text='Name of the city (e.g., Mumbai, Delhi). This is the display name and can be changed.'
    )
    # TASK 24: Canonical code (immutable identifier)
    canonical_code = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Canonical Code',
        help_text='Immutable canonical code for this city (e.g., MUMBAI, DELHI). Never changes.'
    )
    state = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='State',
        help_text='State or province name (optional)'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Is Active',
        help_text='Whether this city is available for selection'
    )
    # TASK 24: Status field. Pending = user-requested (Pandit "Others"), awaiting admin approval.
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    STATUS_PENDING = 'pending'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_INACTIVE, 'Inactive'),
        (STATUS_PENDING, 'Pending'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        db_index=True,
        verbose_name='Status',
        help_text='City status: ACTIVE, INACTIVE, or PENDING (user-requested)'
    )
    # TASK 24: Merged into (for merge scenarios)
    merged_into = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='merged_cities',
        verbose_name='Merged Into',
        help_text='If this city was merged, points to the primary city it was merged into'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    class Meta:
        verbose_name = 'City'
        verbose_name_plural = 'Cities'
        db_table = 'masterdata_city'
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        """TASK 24: Auto-generate canonical_code if not set. Also generate public_id."""
        if not self.public_id:
            self.public_id = generate_public_id()
        if not self.canonical_code and self.name:
            # Generate canonical code from name (uppercase, no spaces)
            self.canonical_code = self.name.upper().replace(' ', '_').replace('-', '_')
        super().save(*args, **kwargs)
    
    def __str__(self):
        if self.state:
            return f"{self.name}, {self.state}"
        return self.name
    
    def delete(self, using=None, keep_parents=False):
        """
        TASK 24: Override delete() to prevent hard deletion.
        
        Cities must never be hard-deleted. Use deactivate() or merge() instead.
        """
        from core.audit import log_blocked_deletion
        log_blocked_deletion(
            self,
            actor=None,
            reason="City deletion blocked - use deactivate() or merge() instead"
        )
        raise ValidationError(
            f"Hard deletion is not allowed for City '{self.name}'. "
            f"Use the 'Deactivate' action or merge with another city instead."
        )


class Mandal(models.Model):
    """
    Master data model for Mandals (intermediate level between City and LocalArea).
    
    Hierarchy: City -> Mandal -> LocalArea
    
    Created and approved by Super Admin only.
    """
    # Public ID (UUIDv7 for external-facing URLs)
    public_id = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        editable=False,
        verbose_name='Public ID',
        help_text='Public-facing UUIDv7 identifier for this mandal'
    )
    
    name = models.CharField(
        max_length=100,
        verbose_name='Mandal Name',
        help_text='Name of the mandal'
    )
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,  # Never delete if referenced
        related_name='mandals',
        verbose_name='City',
        help_text='City this mandal belongs to'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Is Active',
        help_text='Whether this mandal is available for selection'
    )
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_INACTIVE, 'Inactive'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        db_index=True,
        verbose_name='Status',
        help_text='Mandal status: ACTIVE or INACTIVE'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    class Meta:
        verbose_name = 'Mandal'
        verbose_name_plural = 'Mandals'
        db_table = 'masterdata_mandal'
        ordering = ['city', 'name']
        unique_together = [['name', 'city']]  # Same mandal name can exist in different cities
    
    def save(self, *args, **kwargs):
        """Auto-generate public_id if not set."""
        if not self.public_id:
            self.public_id = generate_public_id()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name}, {self.city.name}"
    
    def delete(self, using=None, keep_parents=False):
        """Override delete() to prevent hard deletion."""
        from core.audit import log_blocked_deletion
        log_blocked_deletion(
            self,
            actor=None,
            reason="Mandal deletion blocked - use deactivate() instead"
        )
        raise ValidationError(
            f"Hard deletion is not allowed for Mandal '{self.name}'. "
            f"Use the 'Deactivate' action instead."
        )


class LocalArea(models.Model):
    """
    Master data model for Local Areas.
    
    TASK 24: Location / Area Renamed or Merged
    
    Local areas are linked to cities.
    Created and approved by Super Admin only.
    Pandits can select from approved areas only.
    
    Locations are immutable - IDs never change, display_name can change.
    """
    # Public ID (UUIDv7 for external-facing URLs)
    public_id = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        editable=False,
        verbose_name='Public ID',
        help_text='Public-facing UUIDv7 identifier for this local area'
    )
    
    name = models.CharField(
        max_length=100,
        verbose_name='Area Name',
        help_text='Name of the local area (e.g., Andheri, Connaught Place). This is the display name and can be changed.'
    )
    # TASK 24: Canonical code (immutable identifier)
    canonical_code = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Canonical Code',
        help_text='Immutable canonical code for this area (e.g., ANDHERI, CP). Never changes.'
    )
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,  # Never delete if referenced
        related_name='local_areas',
        verbose_name='City',
        help_text='City this area belongs to'
    )
    mandal = models.ForeignKey(
        'Mandal',
        on_delete=models.PROTECT,  # Never delete if referenced
        related_name='local_areas',
        null=True,
        blank=True,
        verbose_name='Mandal',
        help_text='Mandal this area belongs to (optional, for hierarchical organization)'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Is Active',
        help_text='Whether this area is available for selection'
    )
    # TASK 24: Status field
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_INACTIVE, 'Inactive'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        db_index=True,
        verbose_name='Status',
        help_text='Area status: ACTIVE or INACTIVE'
    )
    # TASK 24: Merged into (for merge scenarios)
    merged_into = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='merged_areas',
        verbose_name='Merged Into',
        help_text='If this area was merged, points to the primary area it was merged into'
    )
    # Custom Area Fields (for Pandit-submitted areas)
    is_custom = models.BooleanField(
        default=False,
        verbose_name='Is Custom',
        help_text='Whether this area was created by a Pandit (custom entry)'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_local_areas',
        verbose_name='Created By',
        help_text='User (Pandit) who created this custom area'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    class Meta:
        verbose_name = 'Local Area'
        verbose_name_plural = 'Local Areas'
        db_table = 'masterdata_localarea'
        ordering = ['city', 'name']
        unique_together = [['name', 'city']]  # Same area name can exist in different cities
    
    def save(self, *args, **kwargs):
        """TASK 24: Auto-generate canonical_code if not set. Also generate public_id."""
        if not self.public_id:
            self.public_id = generate_public_id()
        if not self.canonical_code and self.name:
            # Generate canonical code from name (uppercase, no spaces)
            self.canonical_code = self.name.upper().replace(' ', '_').replace('-', '_')
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name}, {self.city.name}"
    
    def delete(self, using=None, keep_parents=False):
        """
        TASK 24: Override delete() to prevent hard deletion.
        
        Local areas must never be hard-deleted. Use deactivate() or merge() instead.
        """
        from core.audit import log_blocked_deletion
        log_blocked_deletion(
            self,
            actor=None,
            reason="LocalArea deletion blocked - use deactivate() or merge() instead"
        )
        raise ValidationError(
            f"Hard deletion is not allowed for Local Area '{self.name}'. "
            f"Use the 'Deactivate' action or merge with another area instead."
        )


class PoojaCategory(models.Model):
    """
    Master data model for Pooja Categories.
    
    Categories organize poojas hierarchically.
    Created and approved by Super Admin only.
    """
    # Public ID (UUIDv7 for external-facing URLs)
    public_id = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        editable=False,
        verbose_name='Public ID',
        help_text='Public-facing UUIDv7 identifier for this category'
    )
    
    name = models.CharField(
        max_length=200,
        unique=True,
        verbose_name='Category Name',
        help_text='Name of the pooja category (e.g., Daily & Common Household Poojas)'
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='Description',
        help_text='Optional description of this pooja category'
    )
    display_order = models.PositiveIntegerField(
        default=0,
        verbose_name='Display Order',
        help_text='Order in which this category appears in UI (lower numbers first)'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Is Active',
        help_text='Whether this category is available for selection'
    )
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_INACTIVE, 'Inactive'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        db_index=True,
        verbose_name='Status',
        help_text='Category status: ACTIVE or INACTIVE'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    class Meta:
        verbose_name = 'Pooja Category'
        verbose_name_plural = 'Pooja Categories'
        db_table = 'masterdata_poojacategory'
        ordering = ['display_order', 'name']
    
    def save(self, *args, **kwargs):
        """Auto-generate public_id if not set."""
        if not self.public_id:
            self.public_id = generate_public_id()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name
    
    def delete(self, using=None, keep_parents=False):
        """Override delete() to prevent hard deletion."""
        from core.audit import log_blocked_deletion
        log_blocked_deletion(
            self,
            actor=None,
            reason="PoojaCategory deletion blocked - use deactivate() instead"
        )
        raise ValidationError(
            f"Hard deletion is not allowed for Pooja Category '{self.name}'. "
            f"Use the 'Deactivate' action instead."
        )
    
    def deactivate(self, reason=None, actor=None):
        """
        Deactivate category (soft delete).
        
        Sets status to INACTIVE and is_active to False.
        Category remains in database but hidden from selection.
        """
        self.status = self.STATUS_INACTIVE
        self.is_active = False
        self.save(update_fields=['status', 'is_active', 'updated_at'])
        
        # Log audit event
        from core.audit import log_deactivation
        log_deactivation(
            self,
            actor=actor,
            reason=reason or "PoojaCategory deactivated"
        )
        
        return self


class Pooja(models.Model):
    """
    Master data model for Pooja Types.
    
    TASK 23: Pooja Types Removed After Being Used
    
    AUTHORITATIVE LIST - Cannot be edited by Pandits or Admin Pandits.
    Only Super Admin can manage this master data.
    
    Categories:
    - A. Daily & Common Household Poojas
    - B. House, Property & Vehicle Poojas
    - C. Important Life Samskaras
    - D. Festival & Temple Poojas
    - E. Homams / Fire Rituals
    - F. Yagnas
    """
    
    # Category choices (authoritative list)
    CATEGORY_CHOICES = [
        ('daily_household', 'A. Daily & Common Household Poojas'),
        ('house_property_vehicle', 'B. House, Property & Vehicle Poojas'),
        ('life_samskaras', 'C. Important Life Samskaras'),
        ('festival_temple', 'D. Festival & Temple Poojas'),
        ('homams', 'E. Homams / Fire Rituals'),
        ('yagnas', 'F. Yagnas'),
    ]
    
    # TASK 23: Status choices (ACTIVE/INACTIVE)
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_INACTIVE, 'Inactive'),
    ]
    
    # Public ID (UUIDv7 for external-facing URLs)
    public_id = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        editable=False,
        verbose_name='Public ID',
        help_text='Public-facing UUIDv7 identifier for this pooja'
    )
    
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Pooja Name',
        help_text='Name of the pooja type (e.g., Ganapati Puja, Satyanarayana Vratam)'
    )
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        blank=True,
        null=True,
        verbose_name='Category',
        help_text='Category this pooja belongs to (authoritative list) - DEPRECATED, use pooja_category FK'
    )
    pooja_category = models.ForeignKey(
        'PoojaCategory',
        on_delete=models.PROTECT,  # Never delete if referenced
        related_name='poojas',
        null=True,
        blank=True,
        verbose_name='Pooja Category',
        help_text='Category this pooja belongs to (FK to PoojaCategory)'
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='Description',
        help_text='Optional description of the pooja'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Is Active',
        help_text='Whether this pooja is available for selection'
    )
    # TASK 23: Status field (ACTIVE/INACTIVE) - replaces hard deletion
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        db_index=True,
        verbose_name='Status',
        help_text='Pooja status: ACTIVE (selectable) or INACTIVE (historical display only)'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    class Meta:
        verbose_name = 'Pooja'
        verbose_name_plural = 'Poojas'
        db_table = 'masterdata_pooja'
        ordering = ['pooja_category', 'category', 'name']
        # Security: Ensure unique constraint on name
        constraints = [
            models.UniqueConstraint(fields=['name'], name='unique_pooja_name')
        ]
    
    def save(self, *args, **kwargs):
        """Auto-generate public_id if not set."""
        if not self.public_id:
            self.public_id = generate_public_id()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name
    
    def delete(self, using=None, keep_parents=False):
        """
        TASK 23: Override delete() to prevent hard deletion.
        
        Pooja types must never be hard-deleted if they are referenced.
        Use deactivate() method to mark as INACTIVE instead.
        """
        # Check if pooja is referenced
        from profiles.models import PanditProfile
        from pages.models import PagePost
        
        # Check references in Pandit profiles
        profile_count = PanditProfile.objects.filter(poojas_performed__id=self.id).count()
        
        # Check references in pages/posts (if applicable)
        # Note: Adjust based on actual model relationships
        
        if profile_count > 0:
            from core.audit import log_blocked_deletion
            log_blocked_deletion(
                self,
                actor=None,
                reason=f"Pooja type deletion blocked - referenced by {profile_count} profile(s). Use deactivate() instead."
            )
            raise ValidationError(
                f"Hard deletion is not allowed for Pooja '{self.name}'. "
                f"This pooja is already in use by {profile_count} profile(s) and will be marked inactive. "
                f"Use the 'Deactivate' action instead of 'Delete'."
            )
        
        # If not referenced, allow deletion (though deactivation is still preferred)
        from core.audit import log_blocked_deletion
        log_blocked_deletion(
            self,
            actor=None,
            reason="Pooja type deletion blocked - use deactivate() instead"
        )
        raise ValidationError(
            f"Hard deletion is not allowed for Pooja '{self.name}'. "
            f"Use the 'Deactivate' action instead of 'Delete'."
        )
    
    def deactivate(self, reason=None, actor=None):
        """
        TASK 23: Deactivate pooja type (mark as INACTIVE).
        
        Args:
            reason: Optional reason for deactivation
            actor: User performing the deactivation
        """
        from django.utils import timezone
        from core.audit import log_deactivation
        
        self.status = self.STATUS_INACTIVE
        self.is_active = False
        self.save(update_fields=['status', 'is_active', 'updated_at'])
        
        # Log audit event
        log_deactivation(
            self,
            actor=actor,
            reason=reason or "Pooja type deactivated"
        )
        
        return self


class Language(models.Model):
    """
    Master data model for Languages.
    
    Used for Pandit Profile languages_spoken field.
    Replaces free-text comma-separated list with controlled master data.
    
    Created and approved by Super Admin only.
    """
    # Public ID (UUIDv7 for external-facing URLs)
    public_id = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        editable=False,
        verbose_name='Public ID',
        help_text='Public-facing UUIDv7 identifier for this language'
    )
    
    # ISO 639-1 language code (e.g., 'en', 'hi', 'te', 'mr')
    code = models.CharField(
        max_length=10,
        unique=True,
        verbose_name='Language Code',
        help_text='ISO 639-1 language code (e.g., en, hi, te, mr)'
    )
    
    # English name
    name = models.CharField(
        max_length=100,
        verbose_name='Language Name',
        help_text='English name of the language (e.g., English, Hindi, Telugu)'
    )
    
    # Native name (optional, for display in native script)
    native_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Native Name',
        help_text='Native name of the language in its own script (e.g., हिन्दी, తెలుగు)'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Is Active',
        help_text='Whether this language is available for selection'
    )
    
    # Status field (for soft deletion)
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_INACTIVE, 'Inactive'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        db_index=True,
        verbose_name='Status',
        help_text='Language status: ACTIVE or INACTIVE'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    class Meta:
        verbose_name = 'Language'
        verbose_name_plural = 'Languages'
        db_table = 'masterdata_language'
        ordering = ['name']
        indexes = [
            models.Index(fields=['code'], name='language_code_idx'),
            models.Index(fields=['status', 'is_active'], name='language_status_idx'),
        ]
    
    def save(self, *args, **kwargs):
        """Auto-generate public_id if not set."""
        if not self.public_id:
            self.public_id = generate_public_id()
        super().save(*args, **kwargs)
    
    def __str__(self):
        if self.native_name:
            return f"{self.name} ({self.native_name})"
        return self.name
    
    def delete(self, using=None, keep_parents=False):
        """
        Override delete() to prevent hard deletion.
        
        Languages must never be hard-deleted. Use deactivate() instead.
        """
        from core.audit import log_blocked_deletion
        log_blocked_deletion(
            self,
            actor=None,
            reason="Language deletion blocked - use deactivate() instead"
        )
        raise ValidationError(
            f"Hard deletion is not allowed for Language '{self.name}'. "
            f"Use the 'Deactivate' action instead."
        )
    
    def deactivate(self, reason=None, actor=None):
        """
        Deactivate language (soft delete).
        
        Sets status to INACTIVE and is_active to False.
        Language remains in database but hidden from selection.
        """
        self.status = self.STATUS_INACTIVE
        self.is_active = False
        self.save(update_fields=['status', 'is_active', 'updated_at'])
        
        # Log audit event
        from core.audit import log_deactivation
        log_deactivation(
            self,
            actor=actor,
            reason=reason or "Language deactivated"
        )
        
        return self


class CountryCode(models.Model):
    """
    Master data model for Country Codes.
    
    Used for Pandit Profile phone number normalization.
    Replaces hardcoded +91 assumption with international support.
    
    Created and approved by Super Admin only.
    """
    # Public ID (UUIDv7 for external-facing URLs)
    public_id = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        editable=False,
        verbose_name='Public ID',
        help_text='Public-facing UUIDv7 identifier for this country code'
    )
    
    country_name = models.CharField(
        max_length=100,
        verbose_name='Country Name',
        help_text='Full name of the country (e.g., India, United States)'
    )
    iso_code = models.CharField(
        max_length=2,
        unique=True,
        verbose_name='ISO Code',
        help_text='ISO 3166-1 alpha-2 country code (e.g., IN, US)'
    )
    dial_code = models.CharField(
        max_length=10,
        verbose_name='Dial Code',
        help_text='International dialing code (e.g., +91, +1)'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Is Active',
        help_text='Whether this country code is available for selection'
    )
    
    # Status field (for soft deletion)
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_INACTIVE, 'Inactive'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        db_index=True,
        verbose_name='Status',
        help_text='Country code status: ACTIVE or INACTIVE'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    class Meta:
        verbose_name = 'Country Code'
        verbose_name_plural = 'Country Codes'
        db_table = 'masterdata_countrycode'
        ordering = ['country_name']
        indexes = [
            models.Index(fields=['iso_code'], name='countrycode_iso_idx'),
            models.Index(fields=['dial_code'], name='countrycode_dial_idx'),
            models.Index(fields=['status', 'is_active'], name='countrycode_status_idx'),
        ]
    
    def save(self, *args, **kwargs):
        """Auto-generate public_id if not set."""
        if not self.public_id:
            self.public_id = generate_public_id()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.country_name} ({self.dial_code})"
    
    def delete(self, using=None, keep_parents=False):
        """
        Override delete() to prevent hard deletion.
        
        Country codes must never be hard-deleted. Use deactivate() instead.
        """
        from core.audit import log_blocked_deletion
        log_blocked_deletion(
            self,
            actor=None,
            reason="CountryCode deletion blocked - use deactivate() instead"
        )
        raise ValidationError(
            f"Hard deletion is not allowed for Country Code '{self.country_name}'. "
            f"Use the 'Deactivate' action instead."
        )
    
    def deactivate(self, reason=None, actor=None):
        """
        Deactivate country code (soft delete).
        
        Sets status to INACTIVE and is_active to False.
        Country code remains in database but hidden from selection.
        """
        self.status = self.STATUS_INACTIVE
        self.is_active = False
        self.save(update_fields=['status', 'is_active', 'updated_at'])
        
        # Log audit event
        from core.audit import log_deactivation
        log_deactivation(
            self,
            actor=actor,
            reason=reason or "CountryCode deactivated"
        )
        
        return self


class ProfileCompletionRule(models.Model):
    """
    Master data model for Profile Completion Rules.
    
    Replaces hardcoded required fields list in PanditProfile model.
    Allows dynamic configuration of profile completion requirements.
    
    Created and approved by Super Admin only.
    """
    # Public ID (UUIDv7 for external-facing URLs)
    public_id = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        editable=False,
        verbose_name='Public ID',
        help_text='Public-facing UUIDv7 identifier for this rule'
    )
    
    field_name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Field Name',
        help_text='Internal field name (e.g., full_name, profile_image, city)'
    )
    display_label = models.CharField(
        max_length=200,
        verbose_name='Display Label',
        help_text='User-friendly label (e.g., Full Name, Profile Picture, City)'
    )
    is_required = models.BooleanField(
        default=True,
        verbose_name='Is Required',
        help_text='Whether this field is required for profile completion'
    )
    weight = models.PositiveIntegerField(
        default=10,
        verbose_name='Weight',
        help_text='Weight for completion percentage calculation (default: 10)'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Is Active',
        help_text='Whether this rule is currently active'
    )
    
    # Status field (for soft deletion)
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_INACTIVE, 'Inactive'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        db_index=True,
        verbose_name='Status',
        help_text='Rule status: ACTIVE or INACTIVE'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    class Meta:
        verbose_name = 'Profile Completion Rule'
        verbose_name_plural = 'Profile Completion Rules'
        db_table = 'masterdata_profilecompletionrule'
        ordering = ['weight', 'field_name']
        indexes = [
            models.Index(fields=['field_name'], name='profile_rule_field_idx'),
            models.Index(fields=['status', 'is_active'], name='profile_rule_status_idx'),
        ]
    
    def save(self, *args, **kwargs):
        """Auto-generate public_id if not set."""
        if not self.public_id:
            self.public_id = generate_public_id()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.display_label} ({self.field_name})"
    
    def delete(self, using=None, keep_parents=False):
        """
        Override delete() to prevent hard deletion.
        
        Profile completion rules must never be hard-deleted. Use deactivate() instead.
        """
        from core.audit import log_blocked_deletion
        log_blocked_deletion(
            self,
            actor=None,
            reason="ProfileCompletionRule deletion blocked - use deactivate() instead"
        )
        raise ValidationError(
            f"Hard deletion is not allowed for Profile Completion Rule '{self.field_name}'. "
            f"Use the 'Deactivate' action instead."
        )
    
    def deactivate(self, reason=None, actor=None):
        """
        Deactivate rule (soft delete).
        
        Sets status to INACTIVE and is_active to False.
        Rule remains in database but is not used in calculations.
        """
        self.status = self.STATUS_INACTIVE
        self.is_active = False
        self.save(update_fields=['status', 'is_active', 'updated_at'])
        
        # Log audit event
        from core.audit import log_deactivation
        log_deactivation(
            self,
            actor=actor,
            reason=reason or "ProfileCompletionRule deactivated"
        )
        
        return self


class UploadConfig(models.Model):
    """
    Master data model for Upload Configuration.
    
    Replaces hardcoded file size limits and MIME types in JavaScript.
    Allows dynamic configuration of upload constraints.
    
    Created and approved by Super Admin only.
    """
    # Public ID (UUIDv7 for external-facing URLs)
    public_id = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        editable=False,
        verbose_name='Public ID',
        help_text='Public-facing UUIDv7 identifier for this config'
    )
    
    key = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Config Key',
        help_text='Unique identifier for this config (e.g., profile_image, cover_image)'
    )
    max_size_mb = models.PositiveIntegerField(
        default=5,
        verbose_name='Max Size (MB)',
        help_text='Maximum file size in megabytes'
    )
    allowed_mime_types = models.JSONField(
        default=list,
        verbose_name='Allowed MIME Types',
        help_text='List of allowed MIME types (e.g., ["image/jpeg", "image/png"])'
    )
    recommended_dimensions = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Recommended Dimensions',
        help_text='Recommended image dimensions (e.g., 1920x600px, 500x500px)'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Is Active',
        help_text='Whether this configuration is currently active'
    )
    
    # Status field (for soft deletion)
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_INACTIVE, 'Inactive'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        db_index=True,
        verbose_name='Status',
        help_text='Config status: ACTIVE or INACTIVE'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    class Meta:
        verbose_name = 'Upload Config'
        verbose_name_plural = 'Upload Configs'
        db_table = 'masterdata_uploadconfig'
        ordering = ['key']
        indexes = [
            models.Index(fields=['key'], name='uploadconfig_key_idx'),
            models.Index(fields=['status', 'is_active'], name='uploadconfig_status_idx'),
        ]
    
    def save(self, *args, **kwargs):
        """Auto-generate public_id if not set."""
        if not self.public_id:
            self.public_id = generate_public_id()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.key} ({self.max_size_mb}MB)"
    
    def delete(self, using=None, keep_parents=False):
        """
        Override delete() to prevent hard deletion.
        
        Upload configs must never be hard-deleted. Use deactivate() instead.
        """
        from core.audit import log_blocked_deletion
        log_blocked_deletion(
            self,
            actor=None,
            reason="UploadConfig deletion blocked - use deactivate() instead"
        )
        raise ValidationError(
            f"Hard deletion is not allowed for Upload Config '{self.key}'. "
            f"Use the 'Deactivate' action instead."
        )
    
    def deactivate(self, reason=None, actor=None):
        """
        Deactivate config (soft delete).
        
        Sets status to INACTIVE and is_active to False.
        Config remains in database but is not used.
        """
        self.status = self.STATUS_INACTIVE
        self.is_active = False
        self.save(update_fields=['status', 'is_active', 'updated_at'])
        
        # Log audit event
        from core.audit import log_deactivation
        log_deactivation(
            self,
            actor=actor,
            reason=reason or "UploadConfig deactivated"
        )
        
        return self
