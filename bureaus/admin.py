from django.contrib import admin
from django.contrib import messages

from .bureau_governance import activate_bureau_profile, approve_bureau_profile
from .models import BureauProfile


@admin.register(BureauProfile)
class BureauProfileAdmin(admin.ModelAdmin):
    """Superuser-only Bureau governance (approve / activate)."""

    list_display = (
        "bureau_name",
        "user_email",
        "phone_number",
        "city",
        "is_active",
        "is_approved",
        "is_email_verified",
        "created_at",
    )
    list_filter = ("is_active", "is_approved", "is_email_verified", "city")
    search_fields = ("bureau_name", "user__email", "phone_number", "city")
    readonly_fields = tuple(
        field.name for field in BureauProfile._meta.concrete_fields
    )
    ordering = ("-created_at",)
    actions = ("approve_selected_bureaus", "activate_selected_bureaus")

    @admin.display(description="Email")
    def user_email(self, obj):
        return getattr(getattr(obj, "user", None), "email", "") or ""

    def _is_superuser(self, request) -> bool:
        return bool(getattr(request.user, "is_superuser", False))

    def has_module_permission(self, request):
        return self._is_superuser(request)

    def has_view_permission(self, request, obj=None):
        return self._is_superuser(request)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # Allow change so actions/changelist work; lifecycle fields are readonly.
        return self._is_superuser(request)

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Approve selected Bureaus")
    def approve_selected_bureaus(self, request, queryset):
        if not self._is_superuser(request):
            self.message_user(
                request,
                "Only superusers may approve Bureaus.",
                level=messages.ERROR,
            )
            return
        approved = 0
        skipped = 0
        for bureau in queryset:
            if approve_bureau_profile(bureau):
                approved += 1
            else:
                skipped += 1
        if approved:
            self.message_user(
                request,
                f"{approved} bureau(s) approved successfully.",
                level=messages.SUCCESS,
            )
        if skipped:
            self.message_user(
                request,
                f"{skipped} bureau(s) skipped (already approved).",
                level=messages.WARNING,
            )

    @admin.action(description="Activate selected Bureaus")
    def activate_selected_bureaus(self, request, queryset):
        if not self._is_superuser(request):
            self.message_user(
                request,
                "Only superusers may activate Bureaus.",
                level=messages.ERROR,
            )
            return
        activated = 0
        skipped = 0
        for bureau in queryset:
            if activate_bureau_profile(bureau):
                activated += 1
            else:
                skipped += 1
        if activated:
            self.message_user(
                request,
                f"{activated} bureau(s) activated successfully.",
                level=messages.SUCCESS,
            )
        if skipped:
            self.message_user(
                request,
                f"{skipped} bureau(s) skipped (not approved or already active).",
                level=messages.WARNING,
            )
