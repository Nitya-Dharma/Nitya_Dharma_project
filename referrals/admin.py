from django.contrib import admin
from django.contrib.auth.models import User

from .models import ReferralLink, ReferralUsage, ReferralPolicy


@admin.register(ReferralPolicy)
class ReferralPolicyAdmin(admin.ModelAdmin):
    list_display = ('default_expiry_days', 'max_allowed_expiry_days', 'max_allowed_uses', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser and not ReferralPolicy.objects.filter(pk=1).exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ReferralLink)
class ReferralLinkAdmin(admin.ModelAdmin):
    list_display = ('id', 'token_preview', 'created_by', 'max_uses', 'used_count', 'expires_at', 'is_active', 'status', 'created_at')
    list_filter = ('is_active', 'status', 'created_at')
    search_fields = ('token', 'referral_code', 'created_by__email')
    readonly_fields = (
        'created_by', 'token', 'referral_code', 'code',
        'used_count',
        'created_at', 'updated_at',
        'referrer_status_at_creation', 'referrer_block_state_at_creation',
    )
    date_hierarchy = 'created_at'

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj=obj))
        if obj is not None:
            ro = list(ro) + ['max_uses', 'expires_at']
        return ro

    def token_preview(self, obj):
        if obj.token:
            return f'{obj.token[:12]}...'
        return '—'
    token_preview.short_description = 'Token'

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ReferralUsage)
class ReferralUsageAdmin(admin.ModelAdmin):
    list_display = ('referral_link', 'referred_pandit', 'used_at')
    list_filter = ('used_at',)
    search_fields = ('referred_pandit__email',)
    readonly_fields = ('referral_link', 'referred_pandit', 'used_at')
    date_hierarchy = 'used_at'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
