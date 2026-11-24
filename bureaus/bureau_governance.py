"""Shared Bureau approval/activation helpers for dashboard and Django Admin.

Lifecycle flags remain independent:
- is_approved
- is_active
- is_email_verified

Mutations use Model.save() so bureaus.signals pre_save/post_save still run.
Do not use QuerySet.update() for lifecycle changes.
"""

from __future__ import annotations


def approve_bureau_profile(bureau) -> bool:
    """Set is_approved=True only. Does not activate or change email verification.

    Returns True when approval was applied; False if already approved.
    """
    if getattr(bureau, "is_approved", False):
        return False
    bureau.is_approved = True
    bureau.save(update_fields=["is_approved"])
    return True


def activate_bureau_profile(bureau) -> bool:
    """Set is_active=True only when already approved. Never imply-approve.

    Returns True when activation was applied.
    Returns False if not approved, or already active.
    """
    if not getattr(bureau, "is_approved", False):
        return False
    if getattr(bureau, "is_active", False):
        return False
    bureau.is_active = True
    bureau.save(update_fields=["is_active"])
    return True
