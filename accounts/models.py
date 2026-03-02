from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.core.exceptions import ValidationError
from datetime import timedelta
from core.public_id import generate_public_id
from core.deletion_guard import DeletionGuardMixin


class UserManager(BaseUserManager):
    """
    Custom manager for User model that uses email instead of username.
    """
    
    def create_user(self, email, password=None, **extra_fields):
        """
        Create and return a regular user with the given email and password.
        """
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        # Username is optional, so we don't require it
        # If not provided, it will be None (nullable field)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and return a superuser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('status', 'active')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class User(DeletionGuardMixin, AbstractUser):
    """
    Custom User model for Nitya Dharma platform.
    
    Uses email as the unique identifier for authentication.
    Username is kept for display purposes only.
    """
    
    # Role choices
    ROLE_CHOICES = [
        ('user', 'User'),
        ('pandit', 'Pandit'),
        ('admin', 'Admin'),
    ]
    
    # Status choices
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('rejected', 'Rejected'),
        ('deactivated', 'Deactivated'),  # Soft-deleted, preserves referral history
    ]
    
    # Email is the primary identifier
    email = models.EmailField(unique=True, verbose_name='Email Address')
    
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
    
    # Username is optional and for display only
    # 🔒 RULE: Never use username for authentication (use email)
    # 🔒 RULE: Never use username as foreign key (use user FK)
    # 🔒 RULE: Username is for public identity only (URLs, display, SEO)
    username = models.CharField(
        max_length=150,
        unique=True,
        null=True,
        blank=True,
        verbose_name='Username (Display)',
        help_text='Optional display name for public URLs/profiles. Email is used for login. Never use for authentication or foreign keys.'
    )
    
    # Role field: user, pandit, or admin
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='user',
        verbose_name='Role',
        help_text='User role: user, pandit, or admin'
    )
    
    # Status field: pending, active, or rejected
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Status',
        help_text='Account status: pending, active, or rejected'
    )
    
    # Theme preference (Light/Dark mode)
    theme_preference = models.CharField(
        max_length=10,
        choices=[('light', 'Light'), ('dark', 'Dark')],
        default='light',
        verbose_name='Theme Preference',
        help_text='User preference for light or dark theme'
    )
    
    # Email verification (TASK 4: Email verification field)
    email_verified = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name='Email Verified',
        help_text='Whether the user has verified their email address. Email verification is mandatory before activation.'
    )
    
    # Email verification resend tracking (TASK 1: Resend capability)
    email_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Email Verified At',
        help_text='Timestamp when email was verified. NULL if not verified.'
    )
    last_verification_email_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Last Verification Email Sent At',
        help_text='Timestamp of last verification email sent. Used for cooldown enforcement.'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    # Trust Chain: referred_by relationship (for Pandits only)
    # This creates the trust chain: Pandit A → Pandit B → Pandit C
    # ⚠️ This is NOT recursive permission inheritance
    # ⚠️ Used ONLY for transparency & display (Module 10)
    # ⚠️ Set only once at registration, immutable after that
    referred_by = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,  # Never delete referral relationship (audit requirement)
        null=True,
        blank=True,
        related_name='referred_pandits',
        verbose_name='Referred By',
        help_text='The Pandit who referred this Pandit. Used for trust chain display only, not for permissions.'
    )
    
    # Contact Information (for Call/WhatsApp buttons)
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Phone Number',
        help_text='Phone number for contact (used for Call button)'
    )
    whatsapp_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='WhatsApp Number',
        help_text='WhatsApp number for contact (used for WhatsApp button)'
    )
    
    # Profile Picture
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        blank=True,
        null=True,
        verbose_name='Profile Picture',
        help_text='User profile picture (optional)'
    )
    
    # Use email as the username field for authentication
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Email and password are required by default
    
    # Use custom manager
    objects = UserManager()
    
    def save(self, *args, **kwargs):
        """Auto-generate public_id if not set."""
        if not self.public_id:
            self.public_id = generate_public_id()
        super().save(*args, **kwargs)
    
    def delete(self, using=None, keep_parents=False):
        """
        Override delete() to prevent hard deletion.
        
        For Pandits with referrals, use soft deactivation instead.
        For all users, prefer soft deactivation to preserve audit history.
        """
        from core.audit import log_blocked_deletion
        from accounts.services_deactivation import has_referral_descendants, deactivate_pandit_with_custodianship
        
        # Log the blocked deletion attempt
        log_blocked_deletion(self, actor=None, reason="Hard deletion blocked - use deactivation instead")
        
        # For Pandits, use existing deactivation service
        if self.role == 'pandit':
            if has_referral_descendants(self):
                raise ValidationError(
                    f"Pandit {self.email} has active referral relationships and cannot be hard-deleted. "
                    f"Use deactivation instead."
                )
            else:
                raise ValidationError(
                    f"Pandit {self.email} cannot be hard-deleted. Use deactivation to preserve audit history."
                )
        
        # For all users, block hard deletion
        raise ValidationError(
            f"User {self.email} cannot be hard-deleted. Use deactivation to preserve audit history."
        )
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        db_table = 'accounts_user'
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        """Return the full name or email if name is not available."""
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        return self.email
    
    def get_short_name(self):
        """Return the short name or email if name is not available."""
        return self.first_name or self.email


# TASK 2: Email Verification Token Model
class EmailVerificationToken(models.Model):
    """
    Email verification token for user email verification.
    
    TASK 2: Email Verification Model
    
    Rules:
    - One active token per user
    - Tokens expire in 24 hours
    - Immutable after use
    - Token is secure random string (unique)
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
    
    # User who this token belongs to
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='email_verification_tokens',
        verbose_name='User',
        help_text='User who this verification token belongs to'
    )
    
    # TASK 11: Who sent/resent this verification email (preserved even if Admin Pandit is deactivated)
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_email_verifications',
        verbose_name='Sent By',
        help_text='User who sent/resent this verification email (preserved for audit)'
    )
    
    # TASK 11: Last sent timestamp
    last_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Last Sent At',
        help_text='Timestamp when verification email was last sent'
    )
    
    # Secure random token (unique)
    token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        editable=False,
        verbose_name='Verification Token',
        help_text='Secure random string used for email verification (auto-generated)'
    )
    
    # Expiry timestamp
    expires_at = models.DateTimeField(
        db_index=True,
        verbose_name='Expires At',
        help_text='Token expiry timestamp (24 hours from creation)'
    )
    
    # Usage tracking
    is_used = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name='Is Used',
        help_text='Whether this token has been used for verification (immutable after use)'
    )
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Used At',
        help_text='Timestamp when token was used for verification'
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Created At',
        help_text='When this verification token was created'
    )
    
    class Meta:
        db_table = 'accounts_email_verification_token'
        verbose_name = 'Email Verification Token'
        verbose_name_plural = 'Email Verification Tokens'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_used', 'expires_at']),
            models.Index(fields=['token']),
            models.Index(fields=['expires_at']),
        ]
    
    def save(self, *args, **kwargs):
        """Auto-generate public_id and token if not set."""
        if not self.public_id:
            self.public_id = generate_public_id()
        
        # Generate secure random token if not set
        if not self.token:
            self.token = get_random_string(64)
            # Ensure uniqueness
            while EmailVerificationToken.objects.filter(token=self.token).exists():
                self.token = get_random_string(64)
        
        # Set expiry to 24 hours from now if not set
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        
        super().save(*args, **kwargs)
    
    def is_valid(self):
        """
        Check if token is valid (not used and not expired).
        
        Returns:
            bool: True if token is valid, False otherwise
        """
        from django.utils import timezone
        if self.is_used:
            return False
        if self.expires_at < timezone.now():
            return False
        return True
    
    def __str__(self):
        email = self.user.email if hasattr(self.user, 'email') else str(self.user_id)
        return f"EmailVerificationToken for {email} (expires: {self.expires_at})"
