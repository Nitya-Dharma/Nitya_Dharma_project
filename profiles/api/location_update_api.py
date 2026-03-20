"""
STEP-2: Pandit location update API.

Secure POST endpoint for authenticated Pandits to update their GPS location.
Uses STEP-1 fields and services/location_utils.validate_coordinates.
"""
import json
import logging
from datetime import timedelta

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from profiles.models import PanditProfile
from services.location_utils import validate_coordinates

logger = logging.getLogger(__name__)


@require_POST
def update_pandit_location(request):
    """
    POST /api/pandit/update-location/

    Body: {"latitude": 17.3850, "longitude": 78.4867} (numbers or numeric strings).

    - 401 if not authenticated.
    - 403 if user is not a Pandit.
    - 400 if wrong Content-Type, malformed JSON, missing/invalid coordinates.
    - 404 if PanditProfile does not exist.
    - 429 if location updated too frequently (rate limit).
    - 200 and updated location on success (or "Location unchanged" if same coords).
    """
    now = timezone.now()

    # A: API-safe auth — return 401 JSON (no redirect)
    if not request.user.is_authenticated:
        return JsonResponse(
            {"status": "error", "message": "Authentication required"},
            status=401,
        )

    # E: Use existing User.role (accounts.models) — do not invent role system
    if request.user.role != "pandit":
        return JsonResponse(
            {"status": "error", "message": "Only Pandits can update location"},
            status=403,
        )

    # D: Require application/json
    content_type = request.content_type or ""
    if "application/json" not in content_type:
        return JsonResponse(
            {"status": "error", "message": "Content-Type must be application/json"},
            status=400,
        )

    # B: Robust JSON parsing — prevent malformed JSON crashes
    if not request.body:
        return JsonResponse(
            {"status": "error", "message": "Invalid JSON"},
            status=400,
        )
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"status": "error", "message": "Invalid JSON"},
            status=400,
        )

    # Improvement 3: Strong JSON structure validation
    if "latitude" not in data or "longitude" not in data:
        return JsonResponse(
            {"status": "error", "message": "Missing latitude or longitude"},
            status=400,
        )

    latitude = data.get("latitude")
    longitude = data.get("longitude")

    # Validate and normalize coordinates (handles numeric strings)
    try:
        latitude, longitude = validate_coordinates(latitude, longitude)
    except ValueError:
        return JsonResponse(
            {"status": "error", "message": "Invalid coordinates"},
            status=400,
        )

    # C: Safe PanditProfile lookup — 404 if missing (do not auto-create)
    try:
        pandit_profile = request.user.pandit_profile
    except PanditProfile.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Pandit profile not found"},
            status=404,
        )

    # Idempotent update first: same coordinates → 200 "Location unchanged" (no rate limit)
    # Compare as floats (profile stores Decimal) to avoid type/precision mismatch
    def _coords_equal(profile_val, request_val):
        if profile_val is None and request_val is None:
            return True
        if profile_val is None or request_val is None:
            return False
        return round(float(profile_val), 6) == round(float(request_val), 6)

    if _coords_equal(pandit_profile.latitude, latitude) and _coords_equal(pandit_profile.longitude, longitude):
        return JsonResponse(
            {
                "status": "success",
                "message": "Location unchanged",
                "data": {"latitude": latitude, "longitude": longitude},
            },
            status=200,
        )

    # Rate limiting: only when profile already has location (first-time update always allowed)
    last_updated = pandit_profile.location_updated_at
    has_existing_location = (
        pandit_profile.latitude is not None or pandit_profile.longitude is not None
    )
    if (
        has_existing_location
        and last_updated
        and now - last_updated < timedelta(seconds=5)
    ):
        return JsonResponse(
            {
                "status": "error",
                "message": "Location updated too frequently. Please wait a few seconds.",
            },
            status=429,
        )

    pandit_profile.latitude = latitude
    pandit_profile.longitude = longitude
    pandit_profile.location_source = "gps"
    pandit_profile.is_location_verified = False
    pandit_profile.save()

    logger.info(
        "Pandit location updated",
        extra={
            "user_id": request.user.id,
            "latitude": latitude,
            "longitude": longitude,
        },
    )

    return JsonResponse(
        {
            "status": "success",
            "message": "Location updated successfully",
            "data": {
                "latitude": latitude,
                "longitude": longitude,
            },
        },
        status=200,
    )
