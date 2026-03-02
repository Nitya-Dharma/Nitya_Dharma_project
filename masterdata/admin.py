"""
Admin configuration for Master Data models.

SECURITY RULES:
- Only Super Admin can manage master data
- Pandits and Admin Pandits CANNOT create/edit/delete master data
- Master data is authoritative and locked
"""
from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import (
    City, LocalArea, Pooja, Language, PoojaCategory,
    CountryCode, ProfileCompletionRule, UploadConfig
)


class MasterDataAdminMixin:
    """
    Mixin to restrict master data management to Super Admin only.
    """
    def has_add_permission(self, request):
        """Only Super Admin can add master data."""
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        """Only Super Admin can change master data."""
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        """Only Super Admin can delete master data."""
        return request.user.is_superuser
    
    def save_model(self, request, obj, form, change):
        """Override to enforce Super Admin requirement."""
        if not request.user.is_superuser:
            messages.error(request, 'Only Super Admin can manage master data.')
            return
        super().save_model(request, obj, form, change)


@admin.register(City)
class CityAdmin(MasterDataAdminMixin, admin.ModelAdmin):
    """
    Admin interface for City master data.
    
    RESTRICTED: Only Super Admin can manage cities.
    """
    list_display = ('name', 'state', 'is_active', 'created_at')
    list_filter = ('is_active', 'state', 'created_at')
    search_fields = ('name', 'state')
    readonly_fields = ('created_at', 'updated_at')
    
    def get_readonly_fields(self, request, obj=None):
        """Make all fields readonly for non-superusers."""
        if not request.user.is_superuser:
            return self.readonly_fields + ('name', 'state', 'is_active')
        return self.readonly_fields


@admin.register(LocalArea)
class LocalAreaAdmin(MasterDataAdminMixin, admin.ModelAdmin):
    """
    Admin interface for Local Area master data.
    
    RESTRICTED: Only Super Admin can manage local areas.
    """
    list_display = ('name', 'city', 'is_active', 'is_custom', 'created_by', 'created_at')
    list_filter = ('is_active', 'is_custom', 'city', 'created_at')
    search_fields = ('name', 'city__name', 'created_by__email')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'is_custom')
    autocomplete_fields = ['city']
    
    def get_readonly_fields(self, request, obj=None):
        """Make all fields readonly for non-superusers."""
        if not request.user.is_superuser:
            return self.readonly_fields + ('name', 'city', 'is_active')
        return self.readonly_fields


@admin.register(Pooja)
class PoojaAdmin(MasterDataAdminMixin, admin.ModelAdmin):
    """
    Admin interface for Pooja master data.
    
    TASK 23: Pooja Types Removed After Being Used
    
    RESTRICTED: Only Super Admin can manage poojas.
    AUTHORITATIVE LIST: Poojas are locked and cannot be edited by Pandits or Admin Pandits.
    """
    list_display = ('name', 'category', 'status', 'is_active', 'created_at')
    list_filter = ('category', 'status', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['deactivate_pooja']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category', 'description')
        }),
        ('Status', {
            'fields': ('status', 'is_active',),
            'description': 'TASK 23: Use "Deactivate" action instead of "Delete" for poojas in use.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Make all fields readonly for non-superusers."""
        if not request.user.is_superuser:
            return self.readonly_fields + ('name', 'category', 'description', 'is_active', 'status')
        return self.readonly_fields
    
    def get_queryset(self, request):
        """Order by category and name."""
        qs = super().get_queryset(request)
        return qs.select_related().order_by('category', 'name')
    
    def delete_model(self, request, obj):
        """
        TASK 23: Override delete to show deactivation message.
        """
        from profiles.models import PanditProfile
        profile_count = PanditProfile.objects.filter(poojas_performed__id=obj.id).count()
        
        if profile_count > 0:
            messages.warning(
                request,
                f'This pooja is already in use by {profile_count} profile(s) and cannot be deleted. '
                f'Use the "Deactivate" action instead.'
            )
            # Try to call the model's delete method (which will raise ValidationError)
            try:
                obj.delete()
            except ValidationError as e:
                messages.error(request, str(e))
        else:
            try:
                obj.delete()
            except ValidationError as e:
                messages.error(request, str(e))
    
    def delete_queryset(self, request, queryset):
        """
        TASK 23: Override bulk delete to prevent deletion.
        """
        messages.error(
            request,
            'Bulk deletion is not allowed for Pooja types. '
            'Use the "Deactivate" action instead, or deactivate individual poojas.'
        )
    
    def deactivate_pooja(self, request, queryset):
        """
        TASK 23: Admin action to deactivate pooja types.
        """
        deactivated_count = 0
        for pooja in queryset:
            try:
                pooja.deactivate(reason="Deactivated via admin action", actor=request.user)
                deactivated_count += 1
            except Exception as e:
                messages.error(request, f"Error deactivating {pooja.name}: {str(e)}")
        
        if deactivated_count > 0:
            messages.success(
                request,
                f'{deactivated_count} pooja(s) deactivated successfully. '
                f'They are now INACTIVE and will not appear in selection forms, but remain visible in historical displays.'
            )
    deactivate_pooja.short_description = "Deactivate selected poojas (TASK 23)"


@admin.register(Language)
class LanguageAdmin(MasterDataAdminMixin, admin.ModelAdmin):
    """
    Admin interface for Language master data.
    
    RESTRICTED: Only Super Admin can manage languages.
    """
    list_display = ('name', 'native_name', 'code', 'is_active', 'status', 'created_at')
    list_filter = ('is_active', 'status', 'created_at')
    search_fields = ('name', 'native_name', 'code')
    readonly_fields = ('created_at', 'updated_at', 'public_id')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'native_name')
        }),
        ('Status', {
            'fields': ('status', 'is_active'),
            'description': 'Use "Deactivate" action instead of "Delete" for languages in use.'
        }),
        ('System', {
            'fields': ('public_id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Make all fields readonly for non-superusers."""
        if not request.user.is_superuser:
            return self.readonly_fields + ('code', 'name', 'native_name', 'is_active', 'status')
        return self.readonly_fields
    
    def delete_model(self, request, obj):
        """Override delete to show deactivation message."""
        from profiles.models import PanditProfile
        profile_count = PanditProfile.objects.filter(languages__id=obj.id).count()
        
        if profile_count > 0:
            messages.warning(
                request,
                f'This language is already in use by {profile_count} profile(s) and cannot be deleted. '
                f'Use the "Deactivate" action instead.'
            )
            try:
                obj.delete()
            except ValidationError as e:
                messages.error(request, str(e))
        else:
            try:
                obj.delete()
            except ValidationError as e:
                messages.error(request, str(e))
    
    def delete_queryset(self, request, queryset):
        """Override bulk delete to prevent deletion."""
        messages.error(
            request,
            'Bulk deletion is not allowed for Languages. '
            'Use the "Deactivate" action instead, or deactivate individual languages.'
        )
    
    def deactivate_language(self, request, queryset):
        """Admin action to deactivate languages."""
        deactivated_count = 0
        for language in queryset:
            try:
                language.deactivate(reason="Deactivated via admin action", actor=request.user)
                deactivated_count += 1
            except Exception as e:
                messages.error(request, f"Error deactivating {language.name}: {str(e)}")
        
        if deactivated_count > 0:
            messages.success(
                request,
                f'{deactivated_count} language(s) deactivated successfully. '
                f'They are now INACTIVE and will not appear in selection forms, but remain visible in historical displays.'
            )
    deactivate_language.short_description = "Deactivate selected languages"
    
    actions = ['deactivate_language']


@admin.register(PoojaCategory)
class PoojaCategoryAdmin(MasterDataAdminMixin, admin.ModelAdmin):
    """
    Admin interface for Pooja Category master data.
    
    RESTRICTED: Only Super Admin can manage pooja categories.
    """
    list_display = ('name', 'display_order', 'is_active', 'status', 'created_at')
    list_filter = ('is_active', 'status', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at', 'public_id')
    list_editable = ('display_order',)  # Allow quick reordering
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'display_order')
        }),
        ('Status', {
            'fields': ('status', 'is_active'),
            'description': 'Use "Deactivate" action instead of "Delete" for categories in use.'
        }),
        ('System', {
            'fields': ('public_id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Make all fields readonly for non-superusers."""
        if not request.user.is_superuser:
            return self.readonly_fields + ('name', 'description', 'display_order', 'is_active', 'status')
        return self.readonly_fields
    
    def delete_model(self, request, obj):
        """Override delete to show deactivation message."""
        from masterdata.models import Pooja
        pooja_count = Pooja.objects.filter(pooja_category=obj).count()
        
        if pooja_count > 0:
            messages.warning(
                request,
                f'This category is already in use by {pooja_count} pooja(s) and cannot be deleted. '
                f'Use the "Deactivate" action instead.'
            )
            try:
                obj.delete()
            except ValidationError as e:
                messages.error(request, str(e))
        else:
            try:
                obj.delete()
            except ValidationError as e:
                messages.error(request, str(e))
    
    actions = ['deactivate_category']
    
    def deactivate_category(self, request, queryset):
        """Admin action to deactivate categories."""
        deactivated_count = 0
        for category in queryset:
            try:
                category.deactivate(reason="Deactivated via admin action", actor=request.user)
                deactivated_count += 1
            except Exception as e:
                messages.error(request, f"Error deactivating {category.name}: {str(e)}")
        
        if deactivated_count > 0:
            messages.success(
                request,
                f'{deactivated_count} category(ies) deactivated successfully.'
            )
    deactivate_category.short_description = "Deactivate selected categories"


@admin.register(CountryCode)
class CountryCodeAdmin(MasterDataAdminMixin, admin.ModelAdmin):
    """
    Admin interface for Country Code master data.
    
    RESTRICTED: Only Super Admin can manage country codes.
    """
    list_display = ('country_name', 'iso_code', 'dial_code', 'is_active', 'status', 'created_at')
    list_filter = ('is_active', 'status', 'created_at')
    search_fields = ('country_name', 'iso_code', 'dial_code')
    readonly_fields = ('created_at', 'updated_at', 'public_id')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('country_name', 'iso_code', 'dial_code')
        }),
        ('Status', {
            'fields': ('status', 'is_active'),
            'description': 'Use "Deactivate" action instead of "Delete" for country codes in use.'
        }),
        ('System', {
            'fields': ('public_id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Make all fields readonly for non-superusers."""
        if not request.user.is_superuser:
            return self.readonly_fields + ('country_name', 'iso_code', 'dial_code', 'is_active', 'status')
        return self.readonly_fields
    
    actions = ['deactivate_country_code']
    
    def deactivate_country_code(self, request, queryset):
        """Admin action to deactivate country codes."""
        deactivated_count = 0
        for country_code in queryset:
            try:
                country_code.deactivate(reason="Deactivated via admin action", actor=request.user)
                deactivated_count += 1
            except Exception as e:
                messages.error(request, f"Error deactivating {country_code.country_name}: {str(e)}")
        
        if deactivated_count > 0:
            messages.success(
                request,
                f'{deactivated_count} country code(s) deactivated successfully.'
            )
    deactivate_country_code.short_description = "Deactivate selected country codes"


@admin.register(ProfileCompletionRule)
class ProfileCompletionRuleAdmin(MasterDataAdminMixin, admin.ModelAdmin):
    """
    Admin interface for Profile Completion Rule master data.
    
    RESTRICTED: Only Super Admin can manage profile completion rules.
    """
    list_display = ('display_label', 'field_name', 'is_required', 'weight', 'is_active', 'status', 'created_at')
    list_filter = ('is_required', 'is_active', 'status', 'created_at')
    search_fields = ('field_name', 'display_label')
    readonly_fields = ('created_at', 'updated_at', 'public_id')
    list_editable = ('weight', 'is_required', 'is_active')  # Allow quick editing
    
    fieldsets = (
        ('Rule Definition', {
            'fields': ('field_name', 'display_label', 'is_required', 'weight')
        }),
        ('Status', {
            'fields': ('status', 'is_active'),
            'description': 'Deactivated rules are not used in completion calculations.'
        }),
        ('System', {
            'fields': ('public_id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Make all fields readonly for non-superusers."""
        if not request.user.is_superuser:
            return self.readonly_fields + ('field_name', 'display_label', 'is_required', 'weight', 'is_active', 'status')
        return self.readonly_fields
    
    actions = ['deactivate_rule']
    
    def deactivate_rule(self, request, queryset):
        """Admin action to deactivate rules."""
        deactivated_count = 0
        for rule in queryset:
            try:
                rule.deactivate(reason="Deactivated via admin action", actor=request.user)
                deactivated_count += 1
            except Exception as e:
                messages.error(request, f"Error deactivating {rule.field_name}: {str(e)}")
        
        if deactivated_count > 0:
            messages.success(
                request,
                f'{deactivated_count} rule(s) deactivated successfully.'
            )
    deactivate_rule.short_description = "Deactivate selected rules"


@admin.register(UploadConfig)
class UploadConfigAdmin(MasterDataAdminMixin, admin.ModelAdmin):
    """
    Admin interface for Upload Config master data.
    
    RESTRICTED: Only Super Admin can manage upload configs.
    """
    list_display = ('key', 'max_size_mb', 'recommended_dimensions', 'is_active', 'status', 'created_at')
    list_filter = ('is_active', 'status', 'created_at')
    search_fields = ('key', 'recommended_dimensions')
    readonly_fields = ('created_at', 'updated_at', 'public_id')
    
    fieldsets = (
        ('Configuration', {
            'fields': ('key', 'max_size_mb', 'allowed_mime_types', 'recommended_dimensions')
        }),
        ('Status', {
            'fields': ('status', 'is_active'),
            'description': 'Deactivated configs are not used by upload handlers.'
        }),
        ('System', {
            'fields': ('public_id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Make all fields readonly for non-superusers."""
        if not request.user.is_superuser:
            return self.readonly_fields + ('key', 'max_size_mb', 'allowed_mime_types', 'recommended_dimensions', 'is_active', 'status')
        return self.readonly_fields
    
    actions = ['deactivate_config']
    
    def deactivate_config(self, request, queryset):
        """Admin action to deactivate configs."""
        deactivated_count = 0
        for config in queryset:
            try:
                config.deactivate(reason="Deactivated via admin action", actor=request.user)
                deactivated_count += 1
            except Exception as e:
                messages.error(request, f"Error deactivating {config.key}: {str(e)}")
        
        if deactivated_count > 0:
            messages.success(
                request,
                f'{deactivated_count} config(s) deactivated successfully.'
            )
    deactivate_config.short_description = "Deactivate selected configs"
