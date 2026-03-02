"""
Admin configuration for pages app.

READ-ONLY view for audit logs. Pages can be managed via admin.
"""

from django.contrib import admin
from django import forms
from django.utils.html import format_html
from .models import Page, PageAuditLog, PageReview
from .models_page_review_advanced import PageReviewHelpfulVote, PageReviewReport
from .constants import PAGE_TYPE_CHOICES

# Import WordPress-style CMS admin (Super Admin only)
from . import admin_cms


class PageAdminForm(forms.ModelForm):
    """Custom form for Page admin to ensure all page types (including TEMPLE) are available."""
    
    class Meta:
        model = Page
        fields = '__all__'
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3, 'cols': 80}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Explicitly set page_type choices to ensure TEMPLE is always available
        self.fields['page_type'].choices = PAGE_TYPE_CHOICES
        # Ensure address field is visible and required
        if 'address' in self.fields:
            self.fields['address'].required = True


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    """
    Admin for Page model.
    """
    form = PageAdminForm
    list_display = ['id', 'public_id_short', 'page_type', 'title', 'slug', 'status', 'owner_role', 'created_by_email', 'created_at']
    list_filter = ['page_type', 'status', 'owner_role', 'created_at']
    search_fields = ['title', 'slug', 'description', 'address', 'public_id', 'created_by__email']
    readonly_fields = ['id', 'public_id', 'is_deleted', 'created_at', 'updated_at']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Page Identity', {
            'fields': ('id', 'public_id', 'page_type', 'title', 'slug', 'description')
        }),
        ('Location', {
            'fields': ('address', 'city', 'area'),
            'description': 'Address is required. City and Area are optional.'
        }),
        ('Ownership', {
            'fields': ('created_by', 'owner_role')
        }),
        ('Status & Lifecycle', {
            'fields': ('status', 'is_deleted')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def public_id_short(self, obj):
        """Display short version of public_id."""
        if obj.public_id:
            return obj.public_id[:8] + '...'
        return '-'
    public_id_short.short_description = 'Public ID'
    
    def created_by_email(self, obj):
        """Display creator email."""
        return obj.created_by.email
    created_by_email.short_description = 'Created By'
    
    def save_model(self, request, obj, form, change):
        """Ensure is_deleted is always False and set created_by if new."""
        if not change:  # New object
            obj.created_by = request.user
        obj.is_deleted = False  # Enforce rule
        super().save_model(request, obj, form, change)


@admin.register(PageAuditLog)
class PageAuditLogAdmin(admin.ModelAdmin):
    """
    Admin for PageAuditLog.
    
    READ-ONLY: Audit logs are immutable (append-only).
    """
    list_display = ['id', 'page_title', 'action', 'performed_by_email', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['page__title', 'page__public_id', 'performed_by__email']
    readonly_fields = ['id', 'page', 'action', 'performed_by', 'created_at']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    def page_title(self, obj):
        """Display page title."""
        return obj.page.title
    page_title.short_description = 'Page'
    
    def performed_by_email(self, obj):
        """Display performer email."""
        return obj.performed_by.email
    performed_by_email.short_description = 'Performed By'
    
    def has_add_permission(self, request):
        """Disable adding audit logs via admin (use backend services)."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing audit logs (immutable)."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Disable deleting audit logs (append-only)."""
        return False


@admin.register(PageReview)
class PageReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'page', 'user', 'rating', 'helpful_count', 'reported_count', 'is_hidden', 'is_verified', 'visibility_state', 'created_at')
    list_filter = ('visibility_state', 'is_hidden', 'is_verified', 'created_at', 'rating')
    search_fields = ('page__title', 'review_text', 'reviewer_display_name', 'user__email')
    readonly_fields = ('public_id', 'created_at', 'updated_at', 'helpful_count', 'reported_count', 'reviewer_display_name')
    fieldsets = (
        ('Basic Information', {
            'fields': ('page', 'user', 'public_id', 'reviewer_display_name')
        }),
        ('Review Content', {
            'fields': ('rating', 'review_text')
        }),
        ('Status', {
            'fields': ('visibility_state', 'is_hidden', 'is_verified')
        }),
        ('Statistics', {
            'fields': ('helpful_count', 'reported_count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(PageReviewHelpfulVote)
class PageReviewHelpfulVoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'review', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('review__id', 'user__email')
    readonly_fields = ('created_at',)


@admin.register(PageReviewReport)
class PageReviewReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'review', 'user', 'reason', 'review_action', 'created_at', 'reviewed_at')
    list_filter = ('reason', 'review_action', 'created_at', 'reviewed_at')
    search_fields = ('review__id', 'user__email', 'reason_text')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Report Information', {
            'fields': ('review', 'user', 'reason', 'reason_text')
        }),
        ('Moderation', {
            'fields': ('review_action', 'reviewed_by', 'reviewed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
