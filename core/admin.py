from django.conf import settings
from django.contrib import admin
from django.contrib import messages
from django.core.mail import send_mail

from .models_follow import Follow
from .models import ExpertProfile, FeatureToggle


@admin.register(FeatureToggle)
class FeatureToggleAdmin(admin.ModelAdmin):
    list_display = ('name', 'enabled', 'description', 'created_at')
    list_editable = ('enabled',)
    list_filter = ('enabled',)
    search_fields = ('name', 'description')
    readonly_fields = ('created_at',)


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    """Admin interface for Follow model."""
    list_display = ('user', 'entity_type', 'entity_id', 'created_at')
    list_filter = ('entity_type', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('public_id', 'created_at')
    date_hierarchy = 'created_at'
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion from admin - use service layer instead."""
        return False


def _absolute_site_url(view_name):
    """Match the dashboard approval email links without importing that module."""
    from django.urls import reverse

    site_url = getattr(settings, "SITE_URL", None)
    if not site_url:
        allowed_hosts = getattr(settings, "ALLOWED_HOSTS", [])
        if allowed_hosts and allowed_hosts[0] != "*":
            host = allowed_hosts[0]
        else:
            host = "127.0.0.1:8000"
        protocol = "https" if getattr(settings, "USE_HTTPS", False) else "http"
        site_url = f"{protocol}://{host}"
    site_url = site_url.rstrip("/")
    relative_path = reverse(view_name)
    if not relative_path.startswith("/"):
        relative_path = "/" + relative_path
    return f"{site_url}{relative_path}"


def _send_main_expert_approval_email(expert):
    """One approval message using main's current dashboard send_mail path."""
    if not getattr(expert, "email", None):
        return
    send_mail(
        subject="Your Expert Profile is Approved",
        message=(
            "Congratulations! Your expert profile is now approved and live.\n\n"
            "You can now log in and manage your profile.\n\n"
            f"Login here: {_absolute_site_url('accounts:login')}\n"
            f"Expert Dashboard: {_absolute_site_url('module5_dashboards:expert_dashboard')}\n\n"
            "Thank you for joining Nitya Dharma."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[expert.email],
        fail_silently=True,
    )


@admin.register(ExpertProfile)
class ExpertProfileAdmin(admin.ModelAdmin):
    """Superuser-only Expert governance (approve / verify)."""

    list_display = (
        "name",
        "email",
        "expert_type",
        "is_active",
        "is_verified",
        "experience_years",
        "created_at",
    )
    list_filter = ("expert_type", "is_active", "is_verified")
    search_fields = ("name", "email", "phone")
    readonly_fields = tuple(
        field.name for field in ExpertProfile._meta.concrete_fields
    ) + ("services",)
    actions = ("approve_selected_experts", "verify_selected_experts")
    ordering = ("-created_at",)

    def _is_superuser(self, request) -> bool:
        return bool(getattr(request.user, "is_superuser", False))

    def has_module_permission(self, request):
        return self._is_superuser(request)

    def has_view_permission(self, request, obj=None):
        return self._is_superuser(request)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return self._is_superuser(request)

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Approve selected Experts")
    def approve_selected_experts(self, request, queryset):
        if not self._is_superuser(request):
            self.message_user(
                request,
                "Only superusers may approve Experts.",
                level=messages.ERROR,
            )
            return
        approved = 0
        skipped = 0
        for expert in queryset:
            if expert.is_active:
                skipped += 1
                continue
            expert.is_active = True
            expert.save()
            try:
                _send_main_expert_approval_email(expert)
            except Exception:
                pass
            approved += 1
        if approved:
            self.message_user(
                request,
                f"{approved} expert(s) approved successfully.",
                level=messages.SUCCESS,
            )
        if skipped:
            self.message_user(
                request,
                f"{skipped} expert(s) skipped (already approved).",
                level=messages.WARNING,
            )

    @admin.action(description="Verify selected Experts")
    def verify_selected_experts(self, request, queryset):
        if not self._is_superuser(request):
            self.message_user(
                request,
                "Only superusers may verify Experts.",
                level=messages.ERROR,
            )
            return
        verified = 0
        for expert in queryset:
            expert.is_verified = True
            expert.save()
            verified += 1
        self.message_user(
            request,
            f"{verified} expert(s) marked verified.",
            level=messages.SUCCESS,
        )
