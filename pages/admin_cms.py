"""
WordPress-Style CMS Admin - Super Admin Only
Content Management System with version control.
"""
from django.contrib import admin
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.utils.html import format_html
from django.urls import reverse
from .models_cms import CMSPage, CMSRevision, SiteSEOConfig, SiteBranding, SocialMediaSettings, FAQCategory, FAQItem


class CMSRevisionInline(admin.TabularInline):
    """Inline for viewing page revisions (read-only)."""
    model = CMSRevision
    extra = 0
    readonly_fields = ['title', 'content', 'changed_by', 'created_at']
    can_delete = False
    can_add = False
    max_num = 0
    show_change_link = False
    
    def has_add_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(CMSPage)
class CMSPageAdmin(admin.ModelAdmin):
    """
    WordPress-style CMS Admin for CMSPage.
    Super Admin only - all permissions restricted.
    """
    
    list_display = ['page_type_display', 'title', 'is_published', 'published_at', 'updated_at', 'view_link', 'revision_count']
    list_filter = ['is_published', 'page_type', 'created_at', 'updated_at']
    search_fields = ['title', 'content', 'seo_title', 'seo_description']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by', 'slug']
    ordering = ['page_type']
    inlines = [CMSRevisionInline]
    
    fieldsets = (
        ('Page Content', {
            'fields': ('page_type', 'title', 'content'),
            'description': 'Main page content. Use HTML for formatting. Large textarea for WordPress-style editing.'
        }),
        ('SEO Settings', {
            'fields': ('seo_title', 'seo_description', 'seo_keywords'),
            'classes': ('collapse',),
            'description': 'SEO meta tags for search engines.'
        }),
        ('Open Graph', {
            'fields': ('og_image',),
            'classes': ('collapse',),
            'description': 'Social media preview image (1200x630 recommended).'
        }),
        ('Publishing', {
            'fields': ('is_published', 'published_at', 'slug'),
            'description': 'Control page visibility. Slug is auto-generated from page type.'
        }),
        ('Metadata', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def page_type_display(self, obj):
        """Display page type with badge."""
        return obj.get_page_type_display()
    page_type_display.short_description = 'Page Type'
    
    def revision_count(self, obj):
        """Show number of revisions."""
        count = obj.revisions.count()
        return format_html('<span style="color: #64748B;">{} revisions</span>', count)
    revision_count.short_description = 'Revisions'
    
    def view_link(self, obj):
        """Link to view the page."""
        if obj.is_published:
            # Map page_type to URL
            url_map = {
                'about': '/about-us/',
                'terms': '/terms-and-conditions/',
                'privacy': '/privacy-policy/',
            }
            url = url_map.get(obj.page_type, '/')
            return format_html('<a href="{}" target="_blank" style="color: #E11D48;">View Page</a>', url)
        return format_html('<span style="color: #64748B;">Draft</span>')
    view_link.short_description = 'Preview'
    
    # Super Admin Only Permissions
    def has_module_permission(self, request):
        """Only Super Admin can see this module."""
        if not request.user.is_superuser:
            return False
        return True
    
    def has_view_permission(self, request, obj=None):
        """Only Super Admin can view."""
        if not request.user.is_superuser:
            raise Http404("Page not found")
        return True
    
    def has_add_permission(self, request):
        """Only Super Admin can add."""
        if not request.user.is_superuser:
            return False
        return True
    
    def has_change_permission(self, request, obj=None):
        """Only Super Admin can change."""
        if not request.user.is_superuser:
            raise Http404("Page not found")
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Only Super Admin can delete."""
        if not request.user.is_superuser:
            return False
        return True
    
    def save_model(self, request, obj, form, change):
        """Set created_by/updated_by and validate."""
        if not change:  # New object
            obj.created_by = request.user
        obj.updated_by = request.user
        
        # Validate before saving
        try:
            obj.full_clean()
        except ValidationError as e:
            messages.error(request, f"Validation error: {e}")
            raise
        
        super().save_model(request, obj, form, change)
        messages.success(request, f"CMS page '{obj.title}' saved successfully.")


@admin.register(CMSRevision)
class CMSRevisionAdmin(admin.ModelAdmin):
    """
    Admin for CMSRevision (read-only).
    Super Admin only.
    """
    
    list_display = ['page', 'changed_by', 'created_at', 'content_preview']
    list_filter = ['created_at', 'page']
    search_fields = ['page__title', 'content']
    readonly_fields = ['page', 'title', 'content', 'changed_by', 'created_at']
    
    def content_preview(self, obj):
        """Show content preview."""
        preview = obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
        return format_html('<div style="max-width: 300px;">{}</div>', preview)
    content_preview.short_description = 'Content Preview'
    
    # Super Admin Only
    def has_module_permission(self, request):
        """Only Super Admin can see CMS revisions."""
        if not request.user.is_superuser:
            return False
        return True
    
    def has_add_permission(self, request):
        return False  # Revisions are auto-created
    
    def has_change_permission(self, request, obj=None):
        return False  # Revisions are immutable
    
    def has_delete_permission(self, request, obj=None):
        return False  # Revisions cannot be deleted


@admin.register(SiteSEOConfig)
class SiteSEOConfigAdmin(admin.ModelAdmin):
    """
    Admin for SiteSEOConfig.
    Super Admin only. Singleton pattern.
    """
    
    fieldsets = (
        ('Organization', {
            'fields': ('organization_name', 'organization_logo')
        }),
        ('Default Images', {
            'fields': ('default_og_image',)
        }),
        ('Social Media', {
            'fields': ('twitter_handle',)
        }),
        ('Metadata', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['updated_at']
    
    def has_add_permission(self, request):
        """Only one instance allowed."""
        if not SiteSEOConfig.objects.exists():
            return request.user.is_superuser
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion."""
        return False
    
    # Super Admin Only
    def has_module_permission(self, request):
        """Only Super Admin can see SiteSEOConfig."""
        if not request.user.is_superuser:
            return False
        return True
    
    def has_view_permission(self, request, obj=None):
        """Only Super Admin can view SiteSEOConfig."""
        if not request.user.is_superuser:
            raise Http404("Page not found")
        return True
    
    def has_change_permission(self, request, obj=None):
        """Only Super Admin can change SiteSEOConfig."""
        if not request.user.is_superuser:
            raise Http404("Page not found")
        return True


@admin.register(SiteBranding)
class SiteBrandingAdmin(admin.ModelAdmin):
    """
    Admin for SiteBranding.
    Super Admin only. Singleton pattern.
    """
    
    fieldsets = (
        ('Site Identity', {
            'fields': ('site_name',)
        }),
        ('Logos', {
            'fields': ('primary_logo', 'secondary_logo'),
            'description': 'Upload logos for site branding. Primary logo is used by default. Secondary logo can be used for light/dark mode variations.'
        }),
        ('Favicon', {
            'fields': ('favicon',),
            'description': 'Upload favicon (16x16 or 32x32 recommended).'
        }),
        ('Metadata', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    def has_add_permission(self, request):
        """Only allow creation if no instance exists."""
        if not request.user.is_superuser:
            return False
        if SiteBranding.objects.exists():
            return False
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion."""
        return False
    
    # Super Admin Only
    def has_module_permission(self, request):
        """Hide CMS revisions from Django admin - use dashboard instead."""
        return False  # Completely hidden from admin index
    
    def has_view_permission(self, request, obj=None):
        if not request.user.is_superuser:
            raise Http404("Page not found")
        return True
    
    def has_change_permission(self, request, obj=None):
        if not request.user.is_superuser:
            raise Http404("Page not found")
        return True
    
    def save_model(self, request, obj, form, change):
        """Set created_by/updated_by."""
        if not change:  # New object
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(SocialMediaSettings)
class SocialMediaSettingsAdmin(admin.ModelAdmin):
    """
    Admin for SocialMediaSettings.
    Super Admin only. Singleton pattern.
    """
    
    fieldsets = (
        ('Social Media Links', {
            'fields': (
                'facebook_url',
                'instagram_url',
                'twitter_url',
                'linkedin_url',
                'youtube_url',
                'threads_url',
            ),
            'description': 'Enter full URLs for each social media platform. Leave blank to hide from footer.'
        }),
        ('Metadata', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['updated_at']
    
    def has_add_permission(self, request):
        """Only allow creation if no instance exists."""
        if not request.user.is_superuser:
            return False
        return not SocialMediaSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion - singleton must always exist."""
        return False
    
    # Super Admin Only
    def has_module_permission(self, request):
        """Only Super Admin can see SocialMediaSettings."""
        if not request.user.is_superuser:
            return False
        return True
    
    def has_view_permission(self, request, obj=None):
        """Only Super Admin can view."""
        if not request.user.is_superuser:
            raise Http404("Page not found")
        return True
    
    def has_change_permission(self, request, obj=None):
        """Only Super Admin can change."""
        if not request.user.is_superuser:
            raise Http404("Page not found")
        return True
