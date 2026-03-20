"""
Branding Logo Management System
Allows Super Admin to upload and manage logos dynamically.
"""
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
import os

# Try to import PIL for image validation
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class BrandingLogo(models.Model):
    """
    Reusable logo system with activation toggle.
    Only one logo can be active at a time.
    """
    
    LOGO_TYPE_CHOICES = [
        ('navbar_logo', 'Navbar Logo'),
        ('footer_logo', 'Footer Logo'),
        ('email_logo', 'Email Logo'),
        ('favicon', 'Favicon'),
    ]
    
    name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Descriptive name for this logo (optional, e.g., "Main Logo 2024", "Dark Mode Logo")'
    )
    
    logo_type = models.CharField(
        max_length=20,
        choices=LOGO_TYPE_CHOICES,
        default='navbar_logo',
        help_text='Type of logo (navbar, footer, email, favicon)'
    )
    
    logo_image = models.ImageField(
        upload_to='branding/logos/',
        help_text='Logo image file (PNG, SVG, or WEBP, max 20MB, 100-800px width recommended)'
    )
    
    favicon_image = models.ImageField(
        upload_to='branding/favicons/',
        blank=True,
        null=True,
        help_text='Favicon image (optional, 16x16 or 32x32 recommended, max 20MB)'
    )
    
    is_active = models.BooleanField(
        default=False,
        help_text='Only one logo of each type can be active at a time'
    )
    
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_logos',
        help_text='Super Admin who uploaded this logo'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Branding Logo'
        verbose_name_plural = 'Branding Logos'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['logo_type', 'is_active']),
            models.Index(fields=['is_active', '-created_at']),
        ]
    
    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        name = self.name if self.name else "Unnamed Logo"
        return f"{name} ({self.get_logo_type_display()}) - {status}"
    
    def clean(self):
        """Validate logo file size, format, and dimensions."""
        from django.conf import settings
        max_image_bytes = getattr(settings, 'FILE_UPLOAD_MAX_IMAGE_BYTES', 20 * 1024 * 1024)
        errors = {}
        
        # Validate logo_image if provided
        if self.logo_image:
            if self.logo_image.size > max_image_bytes:
                errors['logo_image'] = f'Logo file size must be under {max_image_bytes // (1024*1024)} MB.'
            
            ext = os.path.splitext(self.logo_image.name)[1].lower()
            allowed_extensions = ['.png', '.svg', '.webp', '.jpg', '.jpeg']
            if ext not in allowed_extensions:
                errors['logo_image'] = f'Invalid file format. Allowed: {", ".join(allowed_extensions)}'
            
            if ext != '.svg' and PIL_AVAILABLE:
                try:
                    with Image.open(self.logo_image) as img:
                        width, height = img.size
                        if width < 100 or width > 800:
                            errors['logo_image'] = 'Logo width must be between 100px and 800px.'
                except Exception:
                    pass
        
        if self.favicon_image:
            if self.favicon_image.size > max_image_bytes:
                errors['favicon_image'] = f'Favicon file size must be under {max_image_bytes // (1024*1024)} MB.'
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Override save to ensure only one active logo per type."""
        from core.image_pipeline import optimize_image_if_new, process_derived_images_after_save
        optimize_image_if_new(self, 'logo_image')
        optimize_image_if_new(self, 'favicon_image')
        # Validate before saving
        self.full_clean()
        
        # Use atomic transaction to prevent race conditions
        with transaction.atomic():
            # If this logo is being activated, deactivate all others of the same type
            if self.is_active:
                BrandingLogo.objects.filter(
                    logo_type=self.logo_type,
                    is_active=True
                ).exclude(pk=self.pk if self.pk else None).update(is_active=False)
            
            # Save the logo
            super().save(*args, **kwargs)
            process_derived_images_after_save(self, 'logo_image')
            process_derived_images_after_save(self, 'favicon_image')
    
    def delete(self, *args, **kwargs):
        """Prevent deletion - logos should remain for history."""
        # Override delete to prevent deletion
        # Logos are kept for historical purposes and can be reactivated
        raise ValidationError({
            '__all__': ['Logos cannot be deleted. They are kept for historical purposes and can be reactivated later.']
        })
