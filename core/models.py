"""
Core models for Nitya Dharma platform.

Includes abstract base models and platform-wide models.
"""
from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

# Import Follow model to ensure it's discoverable by Django
from .models_follow import Follow
from .models_config import SystemConfig


class AuditBase(models.Model):
    """
    Abstract base model with audit fields.
    
    Provides standardized audit columns:
    - created_at, updated_at
    - created_by, updated_by
    """
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At',
        help_text='Timestamp when this record was created'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At',
        help_text='Timestamp when this record was last updated'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='%(class)s_created',
        verbose_name='Created By',
        help_text='User who created this record'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='%(class)s_updated',
        verbose_name='Updated By',
        help_text='User who last updated this record'
    )
    
    class Meta:
        abstract = True


class TimestampBase(models.Model):
    """
    Abstract base model with timestamp fields only.
    
    For read-only or system-generated records.
    """
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At',
        help_text='Timestamp when this record was created'
    )
    
    class Meta:
        abstract = True


class FeatureToggle(models.Model):
    """
    Admin-controlled feature toggle. Enable/disable features (e.g. news feed) from Django Admin.
    """
    name = models.CharField(max_length=255, unique=True, db_index=True)
    enabled = models.BooleanField(default=False)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'core_featuretoggle'
        ordering = ['name']
        verbose_name = 'Feature Toggle'
        verbose_name_plural = 'Feature Toggles'

    def __str__(self):
        return f"{self.name} ({'enabled' if self.enabled else 'disabled'})"


class FeatureFlag(AuditBase):
    """
    Feature Flag model for platform kill switches (UNIT 18).
    
    Allows Super Admin to safely disable features during incidents.
    """
    FLAG_KEY_MAX_LENGTH = 100
    
    key = models.CharField(
        max_length=FLAG_KEY_MAX_LENGTH,
        unique=True,
        db_index=True,
        verbose_name='Flag Key',
        help_text='Unique identifier for the feature flag (e.g., ENABLE_PANDIT_REGISTRATION)'
    )
    
    is_enabled = models.BooleanField(
        default=False,
        verbose_name='Is Enabled',
        help_text='Whether this feature is currently enabled'
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='Description',
        help_text='Human-readable description of what this flag controls'
    )
    
    class Meta:
        verbose_name = 'Feature Flag'
        verbose_name_plural = 'Feature Flags'
        db_table = 'core_featureflag'
        ordering = ['key']
    
    def __str__(self):
        return f"{self.key} ({'Enabled' if self.is_enabled else 'Disabled'})"


class PlatformKillSwitch(AuditBase):
    """
    Platform Kill Switch model for emergency control (UNIT 19).
    
    Allows Super Admin to disable platform-wide access during emergencies.
    """
    is_active = models.BooleanField(
        default=False,
        verbose_name='Is Active',
        help_text='If True, platform is in maintenance mode'
    )
    
    maintenance_message = models.TextField(
        blank=True,
        null=True,
        verbose_name='Maintenance Message',
        help_text='Message to display to users during maintenance'
    )
    
    disable_public_access = models.BooleanField(
        default=False,
        verbose_name='Disable Public Access',
        help_text='If True, public pages return maintenance page'
    )
    
    disable_new_writes = models.BooleanField(
        default=False,
        verbose_name='Disable New Writes',
        help_text='If True, prevent creation of new records (read-only mode)'
    )
    
    class Meta:
        verbose_name = 'Platform Kill Switch'
        verbose_name_plural = 'Platform Kill Switches'
        db_table = 'core_platformkillswitch'
    
    def __str__(self):
        return f"Kill Switch ({'ACTIVE' if self.is_active else 'INACTIVE'})"
    
    def save(self, *args, **kwargs):
        """Ensure only one kill switch record exists."""
        # If this is a new instance and one already exists, update it instead
        if not self.pk:
            existing = PlatformKillSwitch.objects.first()
            if existing:
                self.pk = existing.pk
        
        super().save(*args, **kwargs)
    
    @classmethod
    def get_active(cls):
        """Get the active kill switch configuration."""
        kill_switch = cls.objects.first()
        if not kill_switch:
            # Create default inactive kill switch
            kill_switch = cls.objects.create(
                is_active=False,
                disable_public_access=False,
                disable_new_writes=False,
            )
        return kill_switch


class ExpertService(models.Model):
    """Catalog of expert service types (Astrology, Numerology, Palmistry)."""

    slug = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("display_order", "name")

    def __str__(self):
        return self.name


class ExpertProfile(models.Model):
    EXPERT_TYPE_CHOICES = (
        ("ASTROLOGER", "Astrologer"),
        ("NUMEROLOGIST", "Numerologist"),
        ("PALMIST", "Palmist"),
    )

    name = models.CharField(max_length=100)
    expert_type = models.CharField(max_length=20, choices=EXPERT_TYPE_CHOICES)
    experience_years = models.IntegerField(default=0)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    rating = models.FloatField(default=0)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    profile_image = models.ImageField(
        upload_to="expert_profiles/", blank=True, null=True
    )
    cover_image = models.ImageField(
        upload_to="expert_covers/",
        blank=True,
        null=True
    )
    profile_views = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    services = models.ManyToManyField(
        "ExpertService",
        related_name="experts",
        blank=True,
    )

    def __str__(self):
        return f"{self.name} ({self.expert_type})"


class ExpertReview(models.Model):
    expert = models.ForeignKey(
        "ExpertProfile",
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    rating = models.IntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ExpertInquiry(models.Model):
    expert = models.ForeignKey(
        "ExpertProfile",
        on_delete=models.CASCADE,
        related_name="inquiries"
    )
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ExpertBookingIntent(models.Model):
    expert = models.ForeignKey(
        "ExpertProfile",
        on_delete=models.CASCADE,
        related_name="booking_intents"
    )
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
