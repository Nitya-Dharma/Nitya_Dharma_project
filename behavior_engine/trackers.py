"""
Phase 14: Helper trackers that call BehaviorEventService. All fail silently.
"""
from .models import (
    EVENT_SEARCH_QUERY,
    EVENT_SEARCH_RESULT_CLICK,
    EVENT_PANDIT_PROFILE_VIEW,
    EVENT_BOOKING_INTENT_SENT,
    EVENT_REVIEW_VIEW,
    EVENT_PAGE_VIEW,
)
from .services import track_event


def track_search_query(request, query, metadata=None):
    """Record a search query event. Does not change search results."""
    meta = metadata or {}
    if query is not None:
        meta["query"] = str(query)[:200]
    track_event(
        event_type=EVENT_SEARCH_QUERY,
        request=request,
        object_type="search",
        object_id=None,
        metadata=meta,
    )


def track_search_click(request, pandit_id, metadata=None):
    """Record a search result click (pandit profile id)."""
    meta = metadata or {}
    track_event(
        event_type=EVENT_SEARCH_RESULT_CLICK,
        request=request,
        object_type="pandit_profile",
        object_id=pandit_id,
        metadata=meta,
    )


def track_pandit_view(request, pandit_id, metadata=None):
    """Record a pandit profile page view."""
    meta = metadata or {}
    track_event(
        event_type=EVENT_PANDIT_PROFILE_VIEW,
        request=request,
        object_type="pandit_profile",
        object_id=pandit_id,
        metadata=meta,
    )


def track_booking_intent(request, pandit_id, metadata=None):
    """Record a booking intent sent (conversion signal)."""
    meta = metadata or {}
    track_event(
        event_type=EVENT_BOOKING_INTENT_SENT,
        request=request,
        object_type="pandit_profile",
        object_id=pandit_id,
        metadata=meta,
    )


def track_review_view(request, pandit_id, metadata=None):
    """Record that the reviews section was viewed for a pandit."""
    meta = metadata or {}
    track_event(
        event_type=EVENT_REVIEW_VIEW,
        request=request,
        object_type="pandit_profile",
        object_id=pandit_id,
        metadata=meta,
    )


def track_page_view(request, path=None, metadata=None):
    """Record a generic page view. Called by middleware or explicitly."""
    meta = metadata or {}
    if path is not None:
        meta["path"] = str(path)[:500]
    track_event(
        event_type=EVENT_PAGE_VIEW,
        request=request,
        object_type="page",
        object_id=None,
        metadata=meta,
    )
