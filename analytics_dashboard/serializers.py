"""
Phase 13: Serializers for admin analytics responses. Read-only formatting.
"""
# All serializers are simple dicts; we format in views. These are logical names for consistency.


def format_trending_searches(data):
    """Format trending searches list."""
    return {"trending_searches": data}


def format_top_clicked_pandits(data):
    """Format top clicked pandits list."""
    return {"top_clicked_pandits": data}


def format_top_reviewed_pandits(data):
    """Format top reviewed pandits list."""
    return {"top_reviewed_pandits": data}


def format_city_activity(data):
    """Format city activity list."""
    return {"city_activity": data}


def format_booking_stats(data):
    """Format booking intent stats."""
    return {"booking_stats": data}


def format_user_engagement(data):
    """Format user engagement stats."""
    return {"user_engagement": data}
