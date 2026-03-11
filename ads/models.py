"""
Super Admin–controlled Advertisement Banner System.

Isolated from other apps; no foreign keys to user or other models.
Supports responsive image validation (size, dimensions, format); no auto-resize.
"""

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError


# Recommended min dimensions per placement (width, height) for validation guidance only.
# Not used for resizing; images smaller than these are rejected.
RECOMMENDED_SIZES = {
    "top": (970, 90),
    "sidebar": (300, 250),
    "sidebar_top": (300, 250),
    "sidebar_bottom": (300, 250),
    "content_middle": (336, 280),
    "in_content": (336, 280),
    "footer": (728, 90),
    "dashboard_top": (728, 90),
    "dashboard_sidebar": (250, 250),
}

# Mobile-optimized banner sizes (shown on viewports ≤768px when mobile_image is set).
# Use these for Mobile image upload to get crisp display on phones.
RECOMMENDED_MOBILE_SIZES = {
    "top": (320, 50),           # Mobile leaderboard
    "sidebar": (300, 250),      # Same or use 320×50
    "footer": (320, 50),
    "in_content": (320, 50),
    "dashboard_top": (320, 50),
    "dashboard_sidebar": (250, 250),
}

ALLOWED_IMAGE_FORMATS = ("JPEG", "JPG", "PNG", "WEBP", "JFIF")
MAX_IMAGE_SIZE_BYTES = 1 * 1024 * 1024  # 1MB


class Advertisement(models.Model):
    PLACEMENT_CHOICES = [
        ('top', 'Top Banner'),
        ('sidebar', 'Sidebar'),
        ('footer', 'Footer'),
        ('in_content', 'In Content'),
        ('dashboard_top', 'Dashboard Top'),
        ('dashboard_sidebar', 'Dashboard Sidebar'),
    ]
    AD_TYPE_SCRIPT = 'script'
    AD_TYPE_IMAGE = 'image'
    AD_TYPE_CHOICES = [
        (AD_TYPE_SCRIPT, 'Script (AdSense / HTML)'),
        (AD_TYPE_IMAGE, 'Image Banner'),
    ]

    name = models.CharField(max_length=100)
    placement = models.CharField(max_length=50, choices=PLACEMENT_CHOICES)
    slots = models.JSONField(
        default=list,
        blank=True,
        help_text="Select one or more positions where this ad should appear.",
    )
    ad_type = models.CharField(
        max_length=20,
        choices=AD_TYPE_CHOICES,
        default=AD_TYPE_SCRIPT,
    )
    script_code = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)

    # Image banner fields (used when ad_type == 'image')
    image = models.ImageField(
        upload_to='ads/banners/',
        null=True,
        blank=True,
        help_text="Desktop banner. Sizes: Top 970×90, Sidebar 300×250, Footer 728×90, In Content 336×280, Dashboard Top 728×90, Dashboard Sidebar 250×250. JPG/PNG/WEBP, max 1MB.",
    )
    redirect_url = models.URLField(max_length=500, blank=True)
    # Optional fixed dimensions; used when is_responsive=False
    banner_width = models.PositiveIntegerField(null=True, blank=True)
    banner_height = models.PositiveIntegerField(null=True, blank=True)
    is_responsive = models.BooleanField(default=True)
    mobile_image = models.ImageField(
        upload_to='ads/mobile/',
        null=True,
        blank=True,
        help_text="Optional. Shown on screens ≤768px for better mobile display. Recommended: 320×50 (leaderboard) or 320×100. JPG/PNG/WEBP, max 1MB.",
    )

    exclude_urls = models.TextField(
        blank=True,
        null=True,
        help_text="Enter URL prefixes (one per line) where this ad should NOT appear. Example: /login/ , /register/",
    )
    show_on_dashboard = models.BooleanField(
        default=False,
        help_text="Enable if this ad should appear inside dashboard pages.",
    )
    target_roles = models.JSONField(
        default=list,
        blank=True,
        help_text="Optional. Limit ad visibility to specific roles. Example: ['user', 'pandit']",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def is_currently_active(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True

    def is_allowed_on_url(self, request_path):
        if not self.exclude_urls:
            return True
        patterns = self.exclude_urls.splitlines()
        for pattern in patterns:
            pattern = pattern.strip()
            if pattern and request_path.startswith(pattern):
                return False
        return True

    def is_allowed_for_user(self, user):
        if not self.target_roles:
            return True
        if not user.is_authenticated:
            return False
        if hasattr(user, "role"):
            return user.role in self.target_roles
        return False

    def save(self, *args, **kwargs):
        # Backward compat: if slots empty but placement exists, copy to slots
        if not self.slots and self.placement:
            self.slots = [self.placement]
        # Keep placement in sync with first slot (required field)
        if self.slots:
            self.placement = self.slots[0]
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.ad_type != self.AD_TYPE_IMAGE or not self.image:
            return

        # File size limit (max 1MB)
        try:
            size = getattr(self.image, "size", 0) or 0
            if size > MAX_IMAGE_SIZE_BYTES:
                raise ValidationError(
                    {"image": "Ad image must be under 1MB."}
                )
        except (TypeError, AttributeError):
            pass

        try:
            from PIL import Image as PILImage
        except ImportError:
            return

        img = None
        try:
            if hasattr(self.image, "path") and getattr(self.image, "path", None):
                import os
                if os.path.exists(self.image.path):
                    img = PILImage.open(self.image.path)
            else:
                if hasattr(self.image, "seek"):
                    self.image.seek(0)
                img = PILImage.open(self.image)
        except (OSError, TypeError, AttributeError):
            return

        if img is None:
            return

        try:
            width, height = img.size
        except AttributeError:
            return

        # Allowed formats (PIL may return JPEG or JFIF for jpg files)
        fmt = (getattr(img, "format") or "").upper()
        if fmt and fmt not in ALLOWED_IMAGE_FORMATS:
            raise ValidationError(
                {"image": "Only JPG, PNG, or WEBP images allowed."}
            )

        effective_placement = (self.slots[0] if self.slots else self.placement)
        recommended = RECOMMENDED_SIZES.get(effective_placement)
        if recommended:
            rec_w, rec_h = recommended
            if width < rec_w or height < rec_h:
                raise ValidationError(
                    {"image": f"Image too small for this placement. Minimum recommended size is {rec_w}×{rec_h}px."}
                )
        img.close()

    def get_slots_display(self):
        """Return list of display labels for selected slots (for list/display)."""
        choices_dict = dict(self.PLACEMENT_CHOICES)
        effective = self.slots if (self.slots) else ([self.placement] if self.placement else [])
        return [choices_dict.get(s, s) for s in effective]

    def __str__(self):
        if self.slots:
            return f"{self.name} ({', '.join(self.slots)})"
        return f"{self.name} ({self.placement})"
