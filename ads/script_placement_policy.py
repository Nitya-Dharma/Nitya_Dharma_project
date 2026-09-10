"""Script advertisement placement-fit policy (create/edit validation only).

Approved numeric fixed-width budgets (px):
- sidebar: 300
- in_content: 336

Responsive-only (fixed rejected):
- dashboard_sidebar
- floating

Fluid placements (top, footer, dashboard_top): fixed scripts allowed without an
invented pixel maximum; no width budget is applied for those slots.

Does not change serving, CSS, tracking, or image advertisement validation.
"""

from __future__ import annotations

from ads.constants import AD_POSITION_LABELS

# Fixed scripts rejected outright (responsive-only placements).
SCRIPT_FIXED_RESPONSIVE_ONLY_SLOTS = frozenset(
    {
        "dashboard_sidebar",
        "floating",
    }
)

# Approved maximum declared banner_width (px) for fixed scripts.
# Fluid placements are intentionally omitted (no invented budgets).
SCRIPT_FIXED_MAX_WIDTH_PX = {
    "sidebar": 300,
    "in_content": 336,
}


def _slot_label(slot: str) -> str:
    return AD_POSITION_LABELS.get(slot, slot.replace("_", " "))


def validate_fixed_script_placement_fit(slots, banner_width, banner_height):
    """Return a list of human-readable validation error strings (empty if OK).

    ``slots``: iterable of placement keys.
    ``banner_width`` / ``banner_height``: cleaned form values (int or None).
    """
    errors = []
    slot_list = [s for s in (slots or []) if s]

    if banner_width is None or banner_width <= 0:
        errors.append(
            "Fixed script advertisements require a positive banner width in pixels."
        )
    if banner_height is None or banner_height <= 0:
        errors.append(
            "Fixed script advertisements require a positive banner height in pixels."
        )

    # Placement rules still run so admins see incompatible slots even when dims missing.
    for slot in slot_list:
        label = _slot_label(slot)
        if slot in SCRIPT_FIXED_RESPONSIVE_ONLY_SLOTS:
            errors.append(
                f"Fixed script advertisements cannot be used in {label}. "
                "Use a responsive script instead."
            )
            continue
        max_w = SCRIPT_FIXED_MAX_WIDTH_PX.get(slot)
        if max_w is None:
            # Fluid placement: no invented numeric budget.
            continue
        if banner_width is not None and banner_width > 0 and banner_width > max_w:
            errors.append(
                f"Fixed script width cannot exceed {max_w}px for {label}."
            )

    if len(slot_list) > 1 and errors:
        # Clarify multi-placement contract without duplicating every detail.
        errors.append(
            "If multiple placements are selected, the fixed script must fit "
            "every selected placement."
        )

    # De-duplicate while preserving order
    seen = set()
    unique = []
    for msg in errors:
        if msg not in seen:
            seen.add(msg)
            unique.append(msg)
    return unique
