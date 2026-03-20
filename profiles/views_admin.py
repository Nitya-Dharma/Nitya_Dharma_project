"""
In-app Admin dashboard views.

Additive governance UI:
- Shows PendingLocation entries.
- Allows Admin/Super Admin to approve/reject.

Safety:
- Uses the shared service layer (profiles/services_pending_location.py).
- Does not modify profile edit flow or search behavior.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.utils import is_admin

from .models import PendingLocation
from .services_pending_location import (
    approve_pending_location,
    get_pending_locations,
    reject_pending_location,
)


@login_required
def pending_locations_dashboard(request):
    """
    Admin dashboard for reviewing user-submitted "Others" location entries.
    """
    if not (request.user.is_superuser or is_admin(request.user)):
        messages.error(request, "You do not have permission to access this page.")
        return redirect("core:home")

    if request.method == "POST":
        action = request.POST.get("action", "").strip().lower()

        # Bulk actions
        if action in ("bulk_approve", "bulk_reject"):
            selected_ids = request.POST.getlist("selected_ids")
            # Convert to unique strings defensively.
            selected_ids = [str(i).strip() for i in selected_ids if str(i).strip()]
            if not selected_ids:
                messages.error(request, "Please select at least one pending location.")
                return redirect("profiles:pending_locations_dashboard")

            pending_qs = PendingLocation.objects.filter(
                id__in=selected_ids,
                status=PendingLocation.STATUS_PENDING,
            ).select_related("created_by", "related_profile", "related_profile__user")

            processed = 0
            approved_count = 0
            rejected_count = 0

            # Safety: process remaining items even if one fails.
            for pending_obj in pending_qs:
                processed += 1
                if action == "bulk_approve":
                    result = approve_pending_location(pending_obj, request.user)
                    if result == PendingLocation.STATUS_APPROVED:
                        approved_count += 1
                    else:
                        rejected_count += 1
                else:
                    reject_pending_location(pending_obj, request.user)
                    rejected_count += 1

            if processed == 0:
                messages.error(request, "Selected locations are either invalid or no longer pending.")
            else:
                if action == "bulk_approve":
                    messages.success(
                        request,
                        f"{approved_count} location(s) approved successfully.",
                    )
                    if rejected_count:
                        messages.warning(
                            request,
                            f"{rejected_count} location(s) could not be approved and were rejected due to missing data.",
                        )
                else:
                    messages.success(
                        request,
                        f"{rejected_count} location(s) rejected successfully.",
                    )

            return redirect("profiles:pending_locations_dashboard")

        # Single actions
        pending_id = request.POST.get("pending_id", "").strip()
        if not pending_id:
            messages.error(request, "Invalid request: missing pending location id.")
            return redirect("profiles:pending_locations_dashboard")

        pending_obj = get_object_or_404(PendingLocation, id=pending_id)

        # Only allow changes on pending entries.
        if pending_obj.status != PendingLocation.STATUS_PENDING:
            messages.error(request, "This location is no longer pending.")
            return redirect("profiles:pending_locations_dashboard")

        if action == "approve":
            # Service layer handles validation and master-data writes.
            result = approve_pending_location(pending_obj, request.user)
            if result == PendingLocation.STATUS_APPROVED:
                messages.success(request, "Location approved.")
            else:
                messages.warning(request, "Location could not be approved. It was rejected due to missing data.")
        elif action == "reject":
            reject_pending_location(pending_obj, request.user)
            messages.success(request, "Location rejected.")
        else:
            messages.error(request, "Invalid action.")

        return redirect("profiles:pending_locations_dashboard")

    pending_locations = get_pending_locations()

    context = {
        "dashboard_has_data": pending_locations.exists(),
        "dashboard_loading": False,
        "dashboard_error": None,
        "pending_locations": pending_locations,
    }
    return render(request, "module5_dashboards/pending_locations.html", context)

