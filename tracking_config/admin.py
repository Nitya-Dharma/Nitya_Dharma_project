"""
Django Admin configuration for tracking configuration.

CRITICAL: This admin is visible ONLY to Super Admin.
Admin Pandit must not know tracking configuration exists.
"""
from django.contrib import admin
from django.http import Http404
from django.contrib.auth import get_user_model
from django import forms
from .models import TrackingConfiguration, TrackingConfigurationAudit

User = get_user_model()


class TrackingConfigurationAdminForm(forms.ModelForm):
    """Explicit form with separate field definitions for each snippet."""
    
    head_snippet = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 18,
            'cols': 100,
            'style': 'font-family: monospace;',
        }),
        required=False,
        label="Head Snippet",
        help_text="Paste your GTM/analytics script that goes in the <head> section",
        initial='<!-- ✅ HEAD SNIPPET FIELD IS WORKING -->\n<!-- Paste GTM <head> script here -->\n<!-- Example: <script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({\'gtm.start\':\nnew Date().getTime(),event:\'gtm.js\'});var f=d.getElementsByTagName(s)[0],\nj=d.createElement(s),dl=l!=\'dataLayer\'?\'&l=\'+l:\'\';j.async=true;j.src=\n\'https://www.googletagmanager.com/gtm.js?id=\'+i+dl;f.parentNode.insertBefore(j,f);\n})(window,document,\'script\',\'dataLayer\',\'GTM-XXXXXXX\');</script> -->'
    )

    body_snippet = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 18,
            'cols': 100,
            'style': 'font-family: monospace;',
        }),
        required=False,
        label="Body Snippet",
        help_text="Paste your GTM/analytics noscript or iframe that goes immediately after <body>",
        initial='<!-- ✅ BODY SNIPPET FIELD IS WORKING -->\n<!-- Paste GTM <body> noscript/iframe here -->\n<!-- Example: <noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-XXXXXXX"\nheight="0" width="0" style="display:none;visibility:hidden"></iframe></noscript> -->'
    )

    footer_snippet = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 18,
            'cols': 100,
            'style': 'font-family: monospace;',
        }),
        required=False,
        label="Footer Snippet",
        help_text="Optional: Additional scripts to inject before </body> (usually empty for GTM)",
        initial='<!-- ✅ FOOTER SNIPPET FIELD IS WORKING -->\n<!-- Optional: Paste additional tracking scripts here -->\n<!-- This goes before </body> -->\n<!-- Usually left empty for standard GTM setup -->'
    )

    class Meta:
        model = TrackingConfiguration
        fields = '__all__'


class TrackingConfigurationAuditInline(admin.TabularInline):
    """Inline admin for audit logs (read-only)."""
    model = TrackingConfigurationAudit
    extra = 0
    can_delete = False
    readonly_fields = ('changed_by', 'action', 'old_value', 'new_value', 'changed_at')
    
    def has_add_permission(self, request, obj=None):
        """Audit logs are created automatically, not manually."""
        return False


@admin.register(TrackingConfiguration)
class TrackingConfigurationAdmin(admin.ModelAdmin):
    """
    Admin interface for Tracking Configuration.
    
    SECURITY: Only Super Admin can see this.
    Admin Pandit gets 404 if they try to access.
    """
    
    form = TrackingConfigurationAdminForm
    
    list_display = ('provider_type', 'is_active', 'created_by', 'created_at', 'updated_at')
    list_filter = ('provider_type', 'is_active', 'created_at')
    search_fields = ('provider_type',)
    readonly_fields = ('created_by', 'updated_by', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Configuration', {
            'fields': ('provider_type', 'is_active', 'excluded_route_patterns')
        }),
        ('Tracking Snippets', {
            'fields': (
                'head_snippet',
                'body_snippet',
                'footer_snippet',
            ),
            'description': 'Paste GTM / analytics snippets. Head, Body, and Footer are injected separately.'
        }),
        ('Audit Information', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [TrackingConfigurationAuditInline]
    
    def get_queryset(self, request):
        """Only Super Admin can see tracking configurations."""
        if not request.user.is_superuser:
            # Return empty queryset to hide from non-Super-Admin
            return TrackingConfiguration.objects.none()
        return super().get_queryset(request)
    
    def has_module_permission(self, request):
        """Only Super Admin can see the tracking_config app."""
        if not request.user.is_superuser:
            return False
        return super().has_module_permission(request)
    
    def has_view_permission(self, request, obj=None):
        """Only Super Admin can view."""
        if not request.user.is_superuser:
            return False
        return super().has_view_permission(request, obj)
    
    def has_add_permission(self, request):
        """Only Super Admin can add."""
        if not request.user.is_superuser:
            return False
        return super().has_add_permission(request)
    
    def has_change_permission(self, request, obj=None):
        """Only Super Admin can change."""
        if not request.user.is_superuser:
            return False
        return super().has_change_permission(request, obj)
    
    def has_delete_permission(self, request, obj=None):
        """Disable delete - use soft-disable instead."""
        return False
    
    def save_model(self, request, obj, form, change):
        """Set created_by and updated_by to current user."""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
    
    def changelist_view(self, request, extra_context=None):
        """Return 404 for non-Super-Admin users (security by invisibility)."""
        if not request.user.is_superuser:
            raise Http404("Page not found")
        return super().changelist_view(request, extra_context)
    
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """Return 404 for non-Super-Admin users (security by invisibility)."""
        if not request.user.is_superuser:
            raise Http404("Page not found")
        return super().changeform_view(request, object_id, form_url, extra_context)


@admin.register(TrackingConfigurationAudit)
class TrackingConfigurationAuditAdmin(admin.ModelAdmin):
    """
    Admin interface for Tracking Configuration Audit logs.
    
    SECURITY: Only Super Admin can see this.
    Read-only interface.
    """
    
    list_display = ('tracking_configuration', 'action', 'changed_by', 'changed_at')
    list_filter = ('action', 'changed_at')
    search_fields = ('tracking_configuration__provider_type', 'changed_by__email', 'action')
    readonly_fields = ('tracking_configuration', 'changed_by', 'action', 'old_value', 'new_value', 'changed_at')
    
    fieldsets = (
        ('Audit Information', {
            'fields': ('tracking_configuration', 'changed_by', 'action', 'changed_at')
        }),
        ('Change Details', {
            'fields': ('old_value', 'new_value'),
            'classes': ('collapse',)
        }),
    )
    
    def has_module_permission(self, request):
        """Only Super Admin can see audit logs."""
        if not request.user.is_superuser:
            return False
        return super().has_module_permission(request)
    
    def has_add_permission(self, request):
        """Audit logs are created automatically."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Audit logs are immutable."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Audit logs cannot be deleted."""
        return False
    
    def changelist_view(self, request, extra_context=None):
        """Return 404 for non-Super-Admin users (security by invisibility)."""
        if not request.user.is_superuser:
            raise Http404("Page not found")
        return super().changelist_view(request, extra_context)
    
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """Return 404 for non-Super-Admin users (security by invisibility)."""
        if not request.user.is_superuser:
            raise Http404("Page not found")
        return super().changeform_view(request, object_id, form_url, extra_context)
