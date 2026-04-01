"""
WordPress-Style CMS Models for Super Admin-only content management.
CMSPage and CMSRevision for version-controlled content editing.
"""
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from core.validators import validate_image_file, validate_image_extension


class SocialMediaSettings(models.Model):
    """
    Singleton model for global social media links.
    Super Admin can manage from dashboard or Django admin.
    """
    
    facebook_url = models.URLField(
        blank=True,
        null=True,
        help_text='Facebook page URL'
    )
    
    instagram_url = models.URLField(
        blank=True,
        null=True,
        help_text='Instagram profile URL'
    )
    
    twitter_url = models.URLField(
        blank=True,
        null=True,
        help_text='Twitter/X profile URL'
    )
    
    linkedin_url = models.URLField(
        blank=True,
        null=True,
        help_text='LinkedIn company/profile URL'
    )
    
    youtube_url = models.URLField(
        blank=True,
        null=True,
        help_text='YouTube channel URL'
    )
    
    threads_url = models.URLField(
        blank=True,
        null=True,
        help_text='Threads profile URL'
    )
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Social Media Settings'
        verbose_name_plural = 'Social Media Settings'
    
    def save(self, *args, **kwargs):
        """Enforce singleton pattern - always use pk=1."""
        self.pk = 1
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Prevent deletion - singleton must always exist."""
        pass
    
    @classmethod
    def load(cls):
        """Get or create the singleton instance."""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
    
    def __str__(self):
        return 'Social Media Settings'


class CMSPage(models.Model):
    """
    WordPress-style CMS page model.
    One page per type (About, Terms, Privacy).
    Super Admin only.
    """
    
    PAGE_TYPES = (
        ('about', 'About Us'),
        ('terms', 'Terms and Conditions'),
        ('privacy', 'Privacy Policy'),
    )
    
    page_type = models.CharField(
        max_length=20,
        choices=PAGE_TYPES,
        unique=True,
        help_text='Type of CMS page (only one per type allowed)'
    )
    
    title = models.CharField(
        max_length=255,
        help_text='Page title (H1)'
    )
    
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text='URL slug (auto-generated from page_type)'
    )
    
    content = models.TextField(
        help_text='Main page content (HTML allowed)'
    )
    
    # SEO Fields
    seo_title = models.CharField(
        max_length=255,
        blank=True,
        help_text='SEO title (meta title, 50-60 characters recommended)'
    )
    
    seo_description = models.TextField(
        max_length=500,
        blank=True,
        help_text='SEO description (meta description, 140-160 characters recommended)'
    )
    
    seo_keywords = models.TextField(
        blank=True,
        help_text='SEO keywords (comma-separated)'
    )
    
    # Open Graph
    og_image = models.ImageField(
        upload_to='cms/og/',
        blank=True,
        null=True,
        validators=[validate_image_file, validate_image_extension],
        help_text='Open Graph image (1200x630 recommended)'
    )
    
    # Publishing
    is_published = models.BooleanField(
        default=False,
        help_text='Publish this page (visible to public)'
    )
    
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Publication date (auto-set when publishing)'
    )
    
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='cms_pages_created',
        help_text='User who created this page'
    )
    
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='cms_pages_updated',
        help_text='User who last updated this page'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'CMS Page'
        verbose_name_plural = 'CMS Pages'
        ordering = ['page_type']
    
    def __str__(self):
        return f"{self.get_page_type_display()} - {self.title}"
    
    def clean(self):
        """Validate required fields before publishing."""
        if self.is_published:
            if not self.title:
                raise ValidationError({'title': 'Title is required for published pages.'})
            if not self.content:
                raise ValidationError({'content': 'Content is required for published pages.'})
            if not self.seo_title:
                raise ValidationError({'seo_title': 'SEO title is required for published pages.'})
            if not self.seo_description:
                raise ValidationError({'seo_description': 'SEO description is required for published pages.'})
    
    def save(self, *args, **kwargs):
        """Auto-set slug and published_at, create revision."""
        from core.image_pipeline import optimize_image_if_new, process_derived_images_after_save
        optimize_image_if_new(self, 'og_image')
        # Auto-generate slug from page_type if not set
        if not self.slug:
            slug_map = {
                'about': 'about-us',
                'terms': 'terms-and-conditions',
                'privacy': 'privacy-policy',
            }
            self.slug = slug_map.get(self.page_type, self.page_type)
        
        # Auto-set published_at when publishing
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()
        elif not self.is_published:
            self.published_at = None
        
        # Create revision before saving (if updating existing page)
        if self.pk:
            try:
                old_page = CMSPage.objects.get(pk=self.pk)
                # Only create revision if content changed
                if old_page.content != self.content or old_page.title != self.title:
                    CMSRevision.objects.create(
                        page=self,
                        title=old_page.title,
                        content=old_page.content,
                        changed_by=old_page.updated_by if old_page.updated_by else self.updated_by
                    )
            except CMSPage.DoesNotExist:
                pass
        
        self.full_clean()  # Run validation
        super().save(*args, **kwargs)
        process_derived_images_after_save(self, 'og_image')


class CMSRevision(models.Model):
    """
    WordPress-style revision history for CMSPage.
    Auto-created on each save (if content changed).
    Read-only, cannot be deleted.
    """
    
    page = models.ForeignKey(
        CMSPage,
        on_delete=models.CASCADE,
        related_name='revisions'
    )
    
    title = models.CharField(max_length=255)
    content = models.TextField()
    
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='cms_revisions'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'CMS Revision'
        verbose_name_plural = 'CMS Revisions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Revision of {self.page.get_page_type_display()} - {self.created_at}"


class SiteSEOConfig(models.Model):
    """
    Global SEO configuration for the site.
    Super Admin only. Singleton pattern.
    """
    
    organization_name = models.CharField(
        max_length=255,
        default='Nitya Dharma',
        help_text='Organization name for schema markup'
    )
    
    organization_logo = models.ImageField(
        upload_to='cms/logos/',
        blank=True,
        null=True,
        validators=[validate_image_file, validate_image_extension],
        help_text='Organization logo for schema markup'
    )
    
    default_og_image = models.ImageField(
        upload_to='cms/og_images/',
        blank=True,
        null=True,
        validators=[validate_image_file, validate_image_extension],
        help_text='Default Open Graph image (1200x630 recommended)'
    )
    
    twitter_handle = models.CharField(
        max_length=100,
        blank=True,
        help_text='Twitter handle (without @)'
    )
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Site SEO Configuration'
        verbose_name_plural = 'Site SEO Configuration'
    
    def __str__(self):
        return 'Site SEO Configuration'
    
    def save(self, *args, **kwargs):
        """Ensure only one instance exists."""
        from core.image_pipeline import optimize_image_if_new, process_derived_images_after_save
        optimize_image_if_new(self, 'organization_logo')
        optimize_image_if_new(self, 'default_og_image')
        self.pk = 1
        super().save(*args, **kwargs)
        process_derived_images_after_save(self, 'organization_logo')
        process_derived_images_after_save(self, 'default_og_image')
    
    def delete(self, *args, **kwargs):
        """Prevent deletion."""
        pass


class FAQCategory(models.Model):
    """
    Optional category grouping for FAQs.
    Super Admin only.
    """
    
    name = models.CharField(
        max_length=150,
        help_text='Category name (e.g., "General", "Booking", "Pandits")'
    )
    
    order = models.PositiveIntegerField(
        default=0,
        help_text='Display order (lower numbers appear first)'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'FAQ Category'
        verbose_name_plural = 'FAQ Categories'
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class FAQItem(models.Model):
    """
    FAQ question and answer item.
    Super Admin only. Can be grouped by category.
    """
    
    category = models.ForeignKey(
        FAQCategory,
        on_delete=models.SET_NULL,
        related_name='faqs',
        null=True,
        blank=True,
        help_text='Optional category grouping'
    )
    
    question = models.CharField(
        max_length=300,
        help_text='FAQ question (displayed in accordion header)'
    )
    
    answer = models.TextField(
        help_text='FAQ answer (HTML allowed, displayed in accordion body)'
    )
    
    order = models.PositiveIntegerField(
        default=0,
        help_text='Display order within category (lower numbers appear first)'
    )
    
    is_published = models.BooleanField(
        default=False,
        help_text='Publish this FAQ (visible to public)'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'FAQ Item'
        verbose_name_plural = 'FAQ Items'
        ordering = ['order', 'question']
    
    def __str__(self):
        return self.question


class SiteBranding(models.Model):
    """
    Global site branding configuration.
    Super Admin only. Singleton pattern.
    Manages logos, favicon, and site name centrally.
    """
    
    site_name = models.CharField(
        max_length=255,
        default='Nitya Dharma',
        help_text='Site name displayed in branding'
    )
    
    primary_logo = models.ImageField(
        upload_to='branding/logos/',
        blank=True,
        null=True,
        validators=[validate_image_file, validate_image_extension],
        help_text='Primary logo (main site logo, recommended: 200x200px or larger)'
    )
    
    secondary_logo = models.ImageField(
        upload_to='branding/logos/',
        blank=True,
        null=True,
        validators=[validate_image_file, validate_image_extension],
        help_text='Secondary logo (alternative/light version, optional)'
    )
    
    favicon = models.ImageField(
        upload_to='branding/favicon/',
        blank=True,
        null=True,
        validators=[validate_image_file, validate_image_extension],
        help_text='Favicon (16x16 or 32x32 recommended)'
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='branding_created',
        help_text='User who created this branding configuration'
    )
    
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='branding_updated',
        help_text='User who last updated this branding configuration'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Site Branding'
        verbose_name_plural = 'Site Branding'
    
    def __str__(self):
        return 'Site Branding Configuration'
    
    def save(self, *args, **kwargs):
        """Ensure only one instance exists (singleton pattern)."""
        from core.image_pipeline import optimize_image_if_new, process_derived_images_after_save
        optimize_image_if_new(self, 'primary_logo')
        optimize_image_if_new(self, 'secondary_logo')
        optimize_image_if_new(self, 'favicon')
        self.pk = 1
        super().save(*args, **kwargs)
        process_derived_images_after_save(self, 'primary_logo')
        process_derived_images_after_save(self, 'secondary_logo')
        process_derived_images_after_save(self, 'favicon')
    
    def delete(self, *args, **kwargs):
        """Prevent deletion."""
        pass
