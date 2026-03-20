"""
STEP-1: Location utilities for Nitya Dharma.

Pure Python (stdlib only). Used for distance calculation and coordinate
validation in location-based search. No paid APIs or external services.
"""
import math


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two GPS points using the Haversine formula.
    Returns distance in kilometers.

    Args:
        lat1, lon1: First point (degrees).
        lat2, lon2: Second point (degrees).

    Returns:
        Distance in km, or None if any coordinate is None.
    """
    if None in [lat1, lon1, lat2, lon2]:
        return None

    R = 6371  # Earth radius in km

    dlat = math.radians(float(lat2) - float(lat1))
    dlon = math.radians(float(lon2) - float(lon1))

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(float(lat1)))
        * math.cos(math.radians(float(lat2)))
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def validate_coordinates(latitude, longitude):
    """
    Validate latitude and longitude; safely accept numeric strings from APIs.
    Converts to float, rejects None and non-numeric inputs, validates ranges.
    Returns normalized (latitude, longitude) as floats.

    Args:
        latitude: -90 to 90 (number or numeric string).
        longitude: -180 to 180 (number or numeric string).

    Returns:
        (latitude, longitude) as floats.

    Raises:
        ValueError: If None, non-numeric, or out of range.
    """
    if latitude is None or longitude is None:
        raise ValueError("Coordinates cannot be None")

    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        raise ValueError("Coordinates must be numeric")

    if latitude < -90 or latitude > 90:
        raise ValueError("Invalid latitude")

    if longitude < -180 or longitude > 180:
        raise ValueError("Invalid longitude")

    return latitude, longitude
