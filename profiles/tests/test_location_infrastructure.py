"""
STEP-1: Unit tests for backend location infrastructure.

Tests:
- PanditProfile can save and load latitude/longitude.
- haversine_distance returns a valid float (km).
- validate_coordinates rejects invalid values.
"""
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model

from profiles.models import PanditProfile
from services.location_utils import haversine_distance, validate_coordinates


User = get_user_model()


class PanditProfileLocationFieldsTest(TestCase):
    """Test that PanditProfile stores and retrieves location coordinates."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="pandit-location@test.com",
            password="testpass123",
            role="pandit",
            status="active",
        )
        self.profile = self.user.pandit_profile

    def test_pandit_profile_saves_coordinates(self):
        """PanditProfile can save latitude and longitude."""
        self.profile.latitude = Decimal("17.385044")
        self.profile.longitude = Decimal("78.486671")
        self.profile.location_source = "manual"
        self.profile.save()

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.latitude, Decimal("17.385044"))
        self.assertEqual(self.profile.longitude, Decimal("78.486671"))
        self.assertEqual(self.profile.location_source, "manual")
        self.assertIsNotNone(self.profile.location_updated_at)

    def test_pandit_profile_location_optional(self):
        """Location fields are optional (null/blank)."""
        self.profile.latitude = None
        self.profile.longitude = None
        self.profile.save()
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.latitude)
        self.assertIsNone(self.profile.longitude)


class HaversineDistanceTest(TestCase):
    """Test haversine_distance utility."""

    def test_haversine_returns_float_km(self):
        """haversine_distance returns a valid float in kilometers."""
        # Hyderabad to Bangalore (approx 500 km)
        dist = haversine_distance(17.385044, 78.486671, 12.971599, 77.594563)
        self.assertIsInstance(dist, float)
        self.assertGreaterEqual(dist, 490)
        self.assertLess(dist, 650)

    def test_haversine_same_point_zero(self):
        """Same point returns 0 km."""
        dist = haversine_distance(17.385044, 78.486671, 17.385044, 78.486671)
        self.assertEqual(dist, 0.0)

    def test_haversine_none_returns_none(self):
        """Any None coordinate returns None."""
        self.assertIsNone(haversine_distance(None, 78.0, 17.0, 77.0))
        self.assertIsNone(haversine_distance(17.0, None, 12.0, 77.0))
        self.assertIsNone(haversine_distance(17.0, 78.0, None, 77.0))
        self.assertIsNone(haversine_distance(17.0, 78.0, 12.0, None))


class ValidateCoordinatesTest(TestCase):
    """Test validate_coordinates helper."""

    def test_valid_coordinates_pass(self):
        """Valid latitude/longitude do not raise and return (lat, lon) as floats."""
        lat, lon = validate_coordinates(0, 0)
        self.assertEqual((lat, lon), (0.0, 0.0))
        validate_coordinates(90, 0)
        validate_coordinates(-90, 0)
        validate_coordinates(0, 180)
        validate_coordinates(0, -180)

    def test_numeric_strings_accepted(self):
        """Numeric strings from APIs are converted and returned as floats."""
        lat, lon = validate_coordinates("17.3850", "78.4867")
        self.assertIsInstance(lat, float)
        self.assertIsInstance(lon, float)
        self.assertAlmostEqual(lat, 17.385)
        self.assertAlmostEqual(lon, 78.4867)

    def test_invalid_string_raises(self):
        """Non-numeric strings raise ValueError."""
        with self.assertRaises(ValueError) as ctx:
            validate_coordinates("abc", "78.4867")
        self.assertIn("numeric", str(ctx.exception).lower())

        with self.assertRaises(ValueError):
            validate_coordinates("17.3850", "xyz")

    def test_invalid_latitude_raises(self):
        """Out-of-range latitude raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            validate_coordinates(91, 0)
        self.assertIn("latitude", str(ctx.exception).lower())

        with self.assertRaises(ValueError) as ctx:
            validate_coordinates(-91, 0)
        self.assertIn("latitude", str(ctx.exception).lower())

    def test_invalid_longitude_raises(self):
        """Out-of-range longitude raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            validate_coordinates(0, 181)
        self.assertIn("longitude", str(ctx.exception).lower())

        with self.assertRaises(ValueError) as ctx:
            validate_coordinates(0, -181)
        self.assertIn("longitude", str(ctx.exception).lower())

    def test_none_raises(self):
        """None values raise ValueError."""
        with self.assertRaises(ValueError) as ctx:
            validate_coordinates(None, 0)
        self.assertIn("None", str(ctx.exception))
        with self.assertRaises(ValueError):
            validate_coordinates(0, None)
