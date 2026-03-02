from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.core.exceptions import ValidationError
from .models import User

# Import referral models to handle PROTECT constraints
try:
    from referrals.models import ReferralUsage, ReferralLink
except ImportError:
    ReferralUsage = None
    ReferralLink = None

# Import deactivation service
try:
    from .services_deactivation import (
        can_delete_pandit,
        deactivate_pandit_with_custodianship,
        has_referral_descendants,
        get_referral_descendants_count,
    )
except ImportError:
    can_delete_pandit = None
    deactivate_pandit_with_custodianship = None
    has_referral_descendants = None
    get_referral_descendants_count = None


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom admin configuration for User model.
    
    Follows architectural rules:
    - Rule 1: Email is used for authentication/search (not username)
    - Rule 3: Username is for display only (can be shown in admin)
    """
    
    # List display - email is primary identifier (Rule 1)
    list_display = (
        'email',
        'first_name',
        'last_name',
        'role',
        'status',
        'is_active',
        'is_staff',
        'date_joined',
    )
    
    # List filter - filter by role, status, and active status
    list_filter = (
        'role',
        'status',
        'is_active',
        'is_staff',
        'is_superuser',
        'date_joined',
    )
    
    # Search fields - use email (Rule 1: email for authentication/search)
    search_fields = ('email', 'first_name', 'last_name')
    
    # Ordering - by email (primary identifier)
    ordering = ('email',)
    
    # Fieldsets for detail/edit view
    fieldsets = (
        # Authentication section - email is primary (Rule 1)
        (_('Authentication'), {
            'fields': ('email', 'password')
        }),
        
        # Personal information - username is for display (Rule 3)
        (_('Personal Information'), {
            'fields': ('first_name', 'last_name', 'username')
        }),
        
        # Role and Status - core business fields
        (_('Role & Status'), {
            'fields': ('role', 'status')
        }),
        
        # Permissions
        (_('Permissions'), {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions',
            ),
        }),
        
        # Important dates
        (_('Important Dates'), {
            'fields': ('date_joined', 'last_login', 'created_at', 'updated_at')
        }),
    )
    
    # Fieldsets for add user form - email is required (Rule 1)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    
    # Read-only fields
    readonly_fields = ('date_joined', 'last_login', 'created_at', 'updated_at')
    
    # Filter horizontal for many-to-many fields
    filter_horizontal = ('groups', 'user_permissions',)
    
    def delete_model(self, request, obj):
        """
        Override delete to enforce soft deactivation for Pandits with referrals.
        
        Rules:
        - Pandits with referral descendants CANNOT be hard-deleted
        - All Pandits should be soft-deactivated instead
        - If Pandit has referrals, Super Admin becomes custodian
        """
        # Check if this is a Pandit
        if obj.role == 'pandit':
            # Check if deletion is allowed
            if can_delete_pandit:
                can_delete, reason = can_delete_pandit(obj)
                if not can_delete:
                    # Attempt soft deactivation instead
                    if deactivate_pandit_with_custodianship and request.user.is_superuser:
                        try:
                            success, message, custodianship = deactivate_pandit_with_custodianship(
                                pandit=obj,
                                deactivated_by=request.user,
                                reason=f"Deletion attempted via admin by {request.user.email}"
                            )
                            messages.warning(request, reason)
                            messages.success(request, message)
                            return  # Exit - user is deactivated, not deleted
                        except ValidationError as e:
                            messages.error(request, str(e))
                            return
                    else:
                        messages.error(request, reason)
                        return
        
        # For non-Pandits or Pandits without referrals, allow deletion
        # But still prefer soft deactivation for audit trails
        if obj.role == 'pandit' and not request.user.is_superuser:
            messages.error(
                request,
                "Only Super Admin can delete Pandits. Please use deactivation instead."
            )
            return
        
        # Proceed with deletion (for non-Pandits or when explicitly allowed)
        super().delete_model(request, obj)
        messages.success(request, f"User {obj.email} has been deleted successfully.")
    
    def delete_queryset(self, request, queryset):
        """
        Override bulk delete to enforce soft deactivation for Pandits with referrals.
        """
        pandits_with_referrals = []
        pandits_to_deactivate = []
        other_users = []
        
        for user in queryset:
            if user.role == 'pandit':
                if can_delete_pandit:
                    can_delete, reason = can_delete_pandit(user)
                    if not can_delete:
                        pandits_with_referrals.append((user, reason))
                        if request.user.is_superuser:
                            pandits_to_deactivate.append(user)
                        continue
                # Pandit without referrals - still prefer deactivation
                if request.user.is_superuser:
                    pandits_to_deactivate.append(user)
                else:
                    pandits_with_referrals.append((user, "Only Super Admin can delete Pandits."))
            else:
                other_users.append(user)
        
        # Handle Pandits with referrals - deactivate instead
        if pandits_with_referrals:
            for user, reason in pandits_with_referrals:
                if user in pandits_to_deactivate and deactivate_pandit_with_custodianship:
                    try:
                        success, message, custodianship = deactivate_pandit_with_custodianship(
                            pandit=user,
                            deactivated_by=request.user,
                            reason=f"Bulk deletion attempted via admin by {request.user.email}"
                        )
                        messages.success(request, f"{user.email}: {message}")
                    except ValidationError as e:
                        messages.error(request, f"{user.email}: {str(e)}")
                else:
                    messages.warning(request, f"{user.email}: {reason}")
        
        # Delete non-Pandits or explicitly allowed users
        if other_users:
            count = len(other_users)
            User.objects.filter(id__in=[u.id for u in other_users]).delete()
            messages.success(request, f"{count} non-Pandit user(s) deleted successfully.")
