"""
Django admin for BrandingLogo (read-only, Super Admin only).
Note: Primary management is done through Super Admin dashboard.
"""
from django.contrib import admin
from django.http import Http404
from .models import BrandingLogo


@admin.register(BrandingLogo)
class BrandingLogoAdmin(admin.ModelAdmin):
    """Read-only admin for BrandingLogo. Use Super Admin dashboard for management."""
    
    list_display = ('name', 'logo_type', 'is_active', 'uploaded_by', 'created_at')
    list_filter = ('logo_type', 'is_active', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at', 'uploaded_by')
    
    fieldsets = (
        ('Logo Information', {
            'fields': ('name', 'logo_type', 'logo_image', 'favicon_image')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('uploaded_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Super Admin only
    def has_module_permission(self, request):
        if not request.user.is_superuser:
            return False
        return True
    
    def has_view_permission(self, request, obj=None):
        if not request.user.is_superuser:
            raise Http404("Page not found")
        return True
    
    def has_add_permission(self, request):
        """Discourage adding via Django admin - use Super Admin dashboard."""
        if not request.user.is_superuser:
            return False
        return False  # Force use of Super Admin dashboard
    
    def has_change_permission(self, request, obj=None):
        """Discourage editing via Django admin - use Super Admin dashboard."""
        if not request.user.is_superuser:
            raise Http404("Page not found")
        return False  # Force use of Super Admin dashboard
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion."""
        return False
