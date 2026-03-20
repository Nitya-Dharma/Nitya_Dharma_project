"""
PendingLocation service layer.

Purpose:
- Centralize admin approval/rejection logic for user-submitted "Others" locations.
- Reuse the exact same logic from both Django Admin actions and the in-app admin dashboard.

Safety:
- Additive only: does not change frontend behavior or search filters.
- Master data writes (City/LocalArea) happen only on explicit admin approval.
"""

from __future__ import annotations

from typing import Literal, Optional

from django.db import transaction
from django.utils import timezone

from masterdata.models import City, LocalArea

from .models import PendingLocation


def get_pending_locations():
    """Return pending entries for admin review."""
    return (
        PendingLocation.objects.filter(status=PendingLocation.STATUS_PENDING)
        .select_related("created_by", "related_profile", "related_profile__user")
        .order_by("-created_at")
    )


def approve_pending_location(pending_obj: PendingLocation, admin_user) -> Literal["approved", "rejected"]:
    """
    Approve a single PendingLocation.

    Returns:
        "approved" if approved, "rejected" if rejected (e.g., missing required profile data).
    """
    # Idempotency: only run master writes if still pending.
    if pending_obj.status != PendingLocation.STATUS_PENDING:
        return pending_obj.status  # type: ignore[return-value]

    now = timezone.now()

    if pending_obj.type == PendingLocation.TYPE_STATE:
        pending_obj.status = PendingLocation.STATUS_APPROVED
        pending_obj.reviewed_at = now
        pending_obj.reviewed_by = admin_user
        pending_obj.save(update_fields=["status", "reviewed_at", "reviewed_by"])
        return PendingLocation.STATUS_APPROVED

    if pending_obj.type == PendingLocation.TYPE_CITY:
        profile = pending_obj.related_profile
        state_name = (profile.custom_state_name or "").strip()
        city_name = (pending_obj.name or "").strip()

        if not state_name or not city_name:
            pending_obj.status = PendingLocation.STATUS_REJECTED
            pending_obj.reviewed_at = now
            pending_obj.reviewed_by = admin_user
            pending_obj.save(update_fields=["status", "reviewed_at", "reviewed_by"])
            return PendingLocation.STATUS_REJECTED

        existing_city = City.objects.filter(name__iexact=city_name).first()
        if not existing_city:
            City.objects.create(
                name=city_name,
                state=state_name,
                is_active=True,
                status=City.STATUS_ACTIVE,
            )

        pending_obj.status = PendingLocation.STATUS_APPROVED
        pending_obj.reviewed_at = now
        pending_obj.reviewed_by = admin_user
        pending_obj.save(update_fields=["status", "reviewed_at", "reviewed_by"])
        return PendingLocation.STATUS_APPROVED

    if pending_obj.type == PendingLocation.TYPE_AREA:
        profile = pending_obj.related_profile
        city_name = (profile.custom_city_name or "").strip()
        state_name = (profile.custom_state_name or "").strip()
        area_name = (pending_obj.name or "").strip()

        if not city_name or not state_name or not area_name:
            pending_obj.status = PendingLocation.STATUS_REJECTED
            pending_obj.reviewed_at = now
            pending_obj.reviewed_by = admin_user
            pending_obj.save(update_fields=["status", "reviewed_at", "reviewed_by"])
            return PendingLocation.STATUS_REJECTED

        city = City.objects.filter(name__iexact=city_name).first()
        if not city:
            city = City.objects.create(
                name=city_name,
                state=state_name,
                is_active=True,
                status=City.STATUS_ACTIVE,
            )

        existing_area = LocalArea.objects.filter(name__iexact=area_name, city=city).first()
        if not existing_area:
            LocalArea.objects.create(
                name=area_name,
                city=city,
                is_custom=True,
                created_by=pending_obj.created_by,
                is_active=True,
                status=LocalArea.STATUS_ACTIVE,
            )

        pending_obj.status = PendingLocation.STATUS_APPROVED
        pending_obj.reviewed_at = now
        pending_obj.reviewed_by = admin_user
        pending_obj.save(update_fields=["status", "reviewed_at", "reviewed_by"])
        return PendingLocation.STATUS_APPROVED

    # Unknown type: reject safely.
    pending_obj.status = PendingLocation.STATUS_REJECTED
    pending_obj.reviewed_at = now
    pending_obj.reviewed_by = admin_user
    pending_obj.save(update_fields=["status", "reviewed_at", "reviewed_by"])
    return PendingLocation.STATUS_REJECTED


def reject_pending_location(pending_obj: PendingLocation, admin_user) -> None:
    """Reject a single PendingLocation."""
    # Idempotency: safe to re-reject.
    pending_obj.status = PendingLocation.STATUS_REJECTED
    pending_obj.reviewed_at = timezone.now()
    pending_obj.reviewed_by = admin_user
    pending_obj.save(update_fields=["status", "reviewed_at", "reviewed_by"])

