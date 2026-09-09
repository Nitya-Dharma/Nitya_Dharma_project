"""
Ad position configuration: recommended image sizes per placement.
Used by forms, validation, and templates. Do not hardcode sizes in templates.
"""

# Recommended (width, height) per slot for validation and UI display
AD_POSITION_IMAGE_SIZES = {
    "top": {"width": 970, "height": 90},
    "sidebar": {"width": 300, "height": 250},
    "footer": {"width": 728, "height": 90},
    "in_content": {"width": 336, "height": 280},
    "dashboard_top": {"width": 728, "height": 90},
    "dashboard_sidebar": {"width": 250, "height": 250},
    "floating": {"width": 300, "height": 250},
}

# Human-readable labels for each slot (match Advertisement.PLACEMENT_CHOICES)
AD_POSITION_LABELS = {
    "top": "Top Banner",
    "sidebar": "Sidebar",
    "footer": "Footer",
    "in_content": "In Content",
    "dashboard_top": "Dashboard Top",
    "dashboard_sidebar": "Dashboard Sidebar",
    "floating": "Floating",
}

def get_recommended_size_text(slot):
    """Return e.g. '970 × 90' for display in UI."""
    s = AD_POSITION_IMAGE_SIZES.get(slot)
    if not s:
        return ""
    return f"{s['width']} × {s['height']}"
