"""Resolve Account Settings display values from User + related role profiles.

Account Settings edits User account fields only. Role-specific names/images
(ExpertProfile, BureauProfile, PanditProfile) are loaded for display/prefill
when User fields are empty — they are not saved from this page.
"""

from __future__ import annotations

from typing import Any


def _split_person_name(full: str) -> tuple[str, str]:
    """Split a single display name into first / remaining last tokens."""
    parts = (full or "").strip().split(None, 1)
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


def _safe_image_url(field) -> str | None:
    try:
        if field and getattr(field, "name", None):
            return field.url
    except Exception:
        return None
    return None


def build_account_profile_prefill(user) -> dict[str, Any]:
    """
    Build template context for Account Settings profile prefill.

    - form_first_name / form_last_name: User values when set; otherwise derived
      from ExpertProfile.name only (person-style name). Bureau/Pandit professional
      names are not forced into first/last.
    - account_picture_url: User.profile_picture, else related profile image (display).
    - related_profile: read-only professional identity + edit link (if any).
    """
    first = (getattr(user, "first_name", None) or "").strip()
    last = (getattr(user, "last_name", None) or "").strip()
    picture_url = _safe_image_url(getattr(user, "profile_picture", None))
    picture_owned = bool(picture_url)
    picture_source = "account" if picture_owned else None
    related: dict[str, Any] | None = None

    # Expert (Astrologer / Numerologist / Palmist) — shared ExpertProfile
    expert = None
    try:
        from services.views_expert_ui import get_expert_by_user

        expert = get_expert_by_user(user)
    except Exception:
        expert = None

    if expert:
        expert_name = (getattr(expert, "name", None) or "").strip()
        related = {
            "kind": "expert",
            "label": "Expert profile",
            "type_label": (getattr(expert, "expert_type", None) or "Expert").replace("_", " ").title(),
            "name": expert_name,
            "edit_url": "/dashboard/expert/?tab=profile",
            "edit_label": "Edit Expert Profile",
        }
        if not picture_url:
            picture_url = _safe_image_url(getattr(expert, "profile_image", None))
            if picture_url:
                picture_source = "expert"
        if not first and not last and expert_name:
            first, last = _split_person_name(expert_name)
            related["name_prefilled_into_account_fields"] = True

    # Bureau — only when not already an expert profile owner
    if related is None:
        bureau = None
        try:
            from bureaus.utils import get_bureau_for_user, get_owned_email_verified_bureau

            bureau = get_bureau_for_user(user) or get_owned_email_verified_bureau(user)
        except Exception:
            bureau = None
        if bureau:
            bureau_name = (getattr(bureau, "bureau_name", None) or "").strip()
            related = {
                "kind": "bureau",
                "label": "Hindu Marriage Bureau profile",
                "type_label": "Hindu Marriage Bureau",
                "name": bureau_name,
                "edit_url": "/bureaus/profile/edit/",
                "edit_label": "Edit Bureau Profile",
                # Bureau name is organizational — do not map into personal first/last.
                "name_prefilled_into_account_fields": False,
            }
            if not picture_url:
                picture_url = _safe_image_url(getattr(bureau, "profile_image", None))
                if picture_url:
                    picture_source = "bureau"

    # Pandit profile image fallback / display name context
    if related is None and getattr(user, "role", None) == "pandit":
        pandit = getattr(user, "pandit_profile", None)
        if pandit is not None:
            display = (getattr(pandit, "display_name", None) or "").strip()
            related = {
                "kind": "pandit",
                "label": "Pandit profile",
                "type_label": "Pandit",
                "name": display or (user.get_full_name() or "").strip(),
                "edit_url": "/profiles/edit/",
                "edit_label": "Edit Pandit Profile",
                "name_prefilled_into_account_fields": False,
            }
            if not picture_url:
                picture_url = _safe_image_url(getattr(pandit, "profile_image", None))
                if picture_url:
                    picture_source = "pandit"

    summary_name = f"{first} {last}".strip() or (
        (related or {}).get("name") or ""
    ).strip() or (getattr(user, "email", None) or "")

    return {
        "form_first_name": first,
        "form_last_name": last,
        "account_picture_url": picture_url,
        "account_picture_owned": picture_owned,
        "account_picture_source": picture_source,
        "related_profile": related,
        "account_summary_name": summary_name,
    }
