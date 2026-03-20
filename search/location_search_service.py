"""
STEP-3: Location-based search for Pandits.

Uses STEP-1 fields (latitude, longitude) and services.location_utils.
Bounding-box filter reduces DB load; haversine_distance for exact distance.
No schema changes; compatible with Railway and GoDaddy VPS.
"""
import math

from profiles.models import PanditProfile
from services.location_utils import haversine_distance, validate_coordinates


def find_nearby_pandits(user_lat, user_lon, radius_km=20):
    """
    Find approved Pandits within radius_km of (user_lat, user_lon).

    1. Validates coordinates (raises ValueError if invalid).
    2. Applies bounding-box filter to reduce candidates.
    3. Computes haversine distance for each; excludes null coords and distance > radius.
    4. Sorts by distance ascending.

    Returns:
        list[dict]: [{"pandit_id": int, "name": str, "city": str, "distance_km": float, "latitude": float, "longitude": float}, ...]
        distance_km rounded to 2 decimal places. latitude/longitude for debug map.
    """
    user_lat, user_lon = validate_coordinates(user_lat, user_lon)
    user_lat = float(user_lat)
    user_lon = float(user_lon)

    # Radius validation: positive, cap at 500 km
    if radius_km is None:
        radius_km = 20
    radius_km = float(radius_km)
    if radius_km <= 0:
        raise ValueError("Radius must be positive")
    if radius_km > 500:
        radius_km = 500

    # Bounding box (approx): 1° lat ≈ 111 km; 1° lon ≈ 111*cos(lat) km
    # Improvement 1: Avoid division by zero at poles (cos(±90°) = 0)
    lat_deg_per_km = 1.0 / 111.0
    cos_lat = math.cos(math.radians(float(user_lat)))
    cos_lat = max(cos_lat, 0.00001)
    lon_range = radius_km / (111.0 * cos_lat)
    lat_range = radius_km * lat_deg_per_km

    lat_min = user_lat - lat_range
    lat_max = user_lat + lat_range
    lon_min = user_lon - lon_range
    lon_max = user_lon + lon_range

    profiles = (
        PanditProfile.objects.filter(
            is_profile_approved=True,
            latitude__isnull=False,
            longitude__isnull=False,
            latitude__gte=lat_min,
            latitude__lte=lat_max,
            longitude__gte=lon_min,
            longitude__lte=lon_max,
        )
        .select_related("user")
        .prefetch_related("cities_served")
    )[:200]  # Improvement 2: Cap candidates to avoid excessive Python-side distance calc

    results = []
    for profile in profiles:
        # Improvement 3: Defensive check in case of corrupted/missing coord data
        if profile.latitude is None or profile.longitude is None:
            continue
        dist = haversine_distance(
            user_lat,
            user_lon,
            float(profile.latitude),
            float(profile.longitude),
        )
        if dist is None or dist > radius_km:
            continue
        cities = list(profile.cities_served.filter(is_active=True)[:1])
        city_name = cities[0].name if cities else ""
        name = profile.get_display_name() or (profile.user.get_full_name() or profile.user.email or "")
        results.append({
            "pandit_id": profile.user_id,
            "name": name,
            "city": city_name,
            "distance_km": round(dist, 2),
            "latitude": float(profile.latitude),
            "longitude": float(profile.longitude),
        })

    results.sort(key=lambda item: (item["distance_km"], item["pandit_id"]))
    return results if results else []
