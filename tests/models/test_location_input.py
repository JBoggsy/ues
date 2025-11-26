"""Unit tests for LocationInput.

This test suite covers:
1. General ModalityInput behavior (applicable to all modalities)
2. Location-specific validation and features
"""

from datetime import datetime, timezone

import pytest

from models.modalities.location_input import LocationInput
from tests.fixtures.modalities.location import (
    GYM_LOCATION,
    HOME_LOCATION,
    LONDON_LOCATION,
    NYC_LOCATION,
    OFFICE_LOCATION,
    create_location_input,
)


class TestLocationInputInstantiation:
    """Test LocationInput instantiation and basic properties.
    
    GENERAL PATTERN: All ModalityInput subclasses should test instantiation,
    default values, required fields, and proper inheritance from ModalityInput.
    """

    def test_instantiation_with_minimal_fields(self):
        """Test creating LocationInput with only required fields."""
        timestamp = datetime.now(timezone.utc)
        location = LocationInput(
            latitude=37.7749,
            longitude=-122.4194,
            timestamp=timestamp,
        )
        
        assert location.latitude == 37.7749
        assert location.longitude == -122.4194
        assert location.timestamp == timestamp
        assert location.modality_type == "location"
        assert location.input_id is not None
        assert location.address is None
        assert location.named_location is None

    def test_instantiation_with_all_fields(self):
        """Test creating LocationInput with all optional fields."""
        timestamp = datetime.now(timezone.utc)
        location = LocationInput(
            latitude=40.7128,
            longitude=-74.0060,
            address="123 Main St, New York, NY",
            named_location="Office",
            altitude=10.5,
            accuracy=5.0,
            speed=1.5,
            bearing=90.0,
            timestamp=timestamp,
            input_id="test-id-123",
        )
        
        assert location.latitude == 40.7128
        assert location.longitude == -74.0060
        assert location.address == "123 Main St, New York, NY"
        assert location.named_location == "Office"
        assert location.altitude == 10.5
        assert location.accuracy == 5.0
        assert location.speed == 1.5
        assert location.bearing == 90.0
        assert location.input_id == "test-id-123"

    def test_instantiation_modality_type_is_frozen(self):
        """Test that modality_type cannot be changed after instantiation."""
        location = create_location_input()
        
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            location.modality_type = "other"

    def test_instantiation_auto_generates_input_id(self):
        """Test that input_id is auto-generated if not provided."""
        location1 = create_location_input()
        location2 = create_location_input()
        
        assert location1.input_id is not None
        assert location2.input_id is not None
        assert location1.input_id != location2.input_id


class TestLocationInputValidation:
    """Test LocationInput field validation.
    
    LOCATION-SPECIFIC: These tests verify lat/lon ranges, accuracy, speed, and bearing
    validation which are unique to LocationInput.
    """

    def test_validate_latitude_within_range(self):
        """Test that valid latitude values are accepted."""
        for lat in [-90, -45, 0, 45, 90]:
            location = create_location_input(latitude=lat)
            assert location.latitude == lat

    def test_validate_latitude_below_minimum(self):
        """Test that latitude below -90 is rejected."""
        with pytest.raises(ValueError, match="Latitude must be between -90 and 90"):
            create_location_input(latitude=-91)

    def test_validate_latitude_above_maximum(self):
        """Test that latitude above 90 is rejected."""
        with pytest.raises(ValueError, match="Latitude must be between -90 and 90"):
            create_location_input(latitude=91)

    def test_validate_longitude_within_range(self):
        """Test that valid longitude values are accepted."""
        for lon in [-180, -90, 0, 90, 180]:
            location = create_location_input(longitude=lon)
            assert location.longitude == lon

    def test_validate_longitude_below_minimum(self):
        """Test that longitude below -180 is rejected."""
        with pytest.raises(ValueError, match="Longitude must be between -180 and 180"):
            create_location_input(longitude=-181)

    def test_validate_longitude_above_maximum(self):
        """Test that longitude above 180 is rejected."""
        with pytest.raises(ValueError, match="Longitude must be between -180 and 180"):
            create_location_input(longitude=181)

    def test_validate_accuracy_non_negative(self):
        """Test that accuracy must be non-negative if provided."""
        location = create_location_input(accuracy=10.5)
        assert location.accuracy == 10.5
        
        location_zero = create_location_input(accuracy=0.0)
        assert location_zero.accuracy == 0.0

    def test_validate_accuracy_negative_rejected(self):
        """Test that negative accuracy is rejected."""
        with pytest.raises(ValueError, match="Accuracy must be non-negative"):
            create_location_input(accuracy=-1.0)

    def test_validate_speed_non_negative(self):
        """Test that speed must be non-negative if provided."""
        location = create_location_input(speed=5.5)
        assert location.speed == 5.5
        
        location_zero = create_location_input(speed=0.0)
        assert location_zero.speed == 0.0

    def test_validate_speed_negative_rejected(self):
        """Test that negative speed is rejected."""
        with pytest.raises(ValueError, match="Speed must be non-negative"):
            create_location_input(speed=-1.0)

    def test_validate_bearing_within_range(self):
        """Test that valid bearing values are accepted."""
        for bearing in [0, 90, 180, 270, 360]:
            location = create_location_input(bearing=bearing)
            assert location.bearing == bearing

    def test_validate_bearing_below_minimum(self):
        """Test that bearing below 0 is rejected."""
        with pytest.raises(ValueError, match="Bearing must be between 0 and 360"):
            create_location_input(bearing=-1)

    def test_validate_bearing_above_maximum(self):
        """Test that bearing above 360 is rejected."""
        with pytest.raises(ValueError, match="Bearing must be between 0 and 360"):
            create_location_input(bearing=361)


class TestLocationInputAbstractMethods:
    """Test implementation of ModalityInput abstract methods.
    
    GENERAL PATTERN: All ModalityInput subclasses must implement validate_input(),
    get_affected_entities(), get_summary(), and should_merge_with().
    """

    def test_validate_input_succeeds(self):
        """Test that validate_input() does not raise errors for valid input."""
        location = create_location_input()
        location.validate_input()  # Should not raise

    def test_get_affected_entities_basic(self):
        """Test get_affected_entities() for basic location update."""
        location = create_location_input()
        entities = location.get_affected_entities()
        
        assert "user_location" in entities
        assert len(entities) == 1

    def test_get_affected_entities_with_named_location(self):
        """Test get_affected_entities() includes named location."""
        location = create_location_input(named_location="Office")
        entities = location.get_affected_entities()
        
        assert "user_location" in entities
        assert "location:Office" in entities
        assert len(entities) == 2

    def test_get_summary_with_named_location_and_address(self):
        """Test get_summary() with both named location and address."""
        location = create_location_input(
            latitude=40.7128,
            longitude=-74.0060,
            named_location="Office",
            address="123 Main St, NYC",
        )
        summary = location.get_summary()
        
        assert "Office" in summary
        assert "123 Main St, NYC" in summary
        assert "40.7128" in summary
        assert "-74.006" in summary  # Python drops trailing zeros

    def test_get_summary_with_address_only(self):
        """Test get_summary() with address but no named location."""
        location = create_location_input(
            latitude=40.7128,
            longitude=-74.0060,
            address="123 Main St, NYC",
        )
        summary = location.get_summary()
        
        assert "Moved to" in summary
        assert "123 Main St, NYC" in summary
        assert "40.7128" in summary

    def test_get_summary_with_named_location_only(self):
        """Test get_summary() with named location but no address."""
        location = create_location_input(
            latitude=40.7128,
            longitude=-74.0060,
            named_location="Office",
        )
        summary = location.get_summary()
        
        assert "Office" in summary
        assert "40.7128" in summary

    def test_get_summary_with_coordinates_only(self):
        """Test get_summary() with only coordinates."""
        location = create_location_input(
            latitude=40.7128,
            longitude=-74.0060,
        )
        summary = location.get_summary()
        
        assert "Location update" in summary
        assert "40.7128" in summary
        assert "-74.006" in summary  # Python drops trailing zeros

    def test_should_merge_with_same_type_within_time_threshold(self):
        """Test that locations within 1 second should merge."""
        timestamp = datetime.now(timezone.utc)
        location1 = create_location_input(
            latitude=40.7128,
            longitude=-74.0060,
            timestamp=timestamp,
        )
        location2 = create_location_input(
            latitude=40.7129,
            longitude=-74.0061,
            timestamp=timestamp,
        )
        
        assert location1.should_merge_with(location2)

    def test_should_merge_with_same_type_outside_time_threshold(self):
        """Test that locations more than 1 second apart should not merge."""
        from datetime import timedelta
        
        timestamp1 = datetime.now(timezone.utc)
        timestamp2 = timestamp1 + timedelta(seconds=2)
        
        location1 = create_location_input(timestamp=timestamp1)
        location2 = create_location_input(timestamp=timestamp2)
        
        assert not location1.should_merge_with(location2)

    def test_should_merge_with_different_named_locations(self):
        """Test that locations with different named locations should not merge."""
        timestamp = datetime.now(timezone.utc)
        location1 = create_location_input(
            named_location="Home",
            timestamp=timestamp,
        )
        location2 = create_location_input(
            named_location="Office",
            timestamp=timestamp,
        )
        
        assert not location1.should_merge_with(location2)

    def test_should_merge_with_different_type(self):
        """Test that locations should not merge with other modality types."""
        from models.modalities.time_input import TimeInput
        
        location = create_location_input()
        time_input = TimeInput(
            timezone="UTC",
            format_preference="12h",
            timestamp=location.timestamp,
        )
        
        assert not location.should_merge_with(time_input)


class TestLocationInputSerialization:
    """Test LocationInput serialization and deserialization.
    
    GENERAL PATTERN: All ModalityInput subclasses should be serializable to/from
    JSON via Pydantic's model_dump() and model_validate().
    """

    def test_serialization_to_dict(self):
        """Test serializing LocationInput to dictionary."""
        location = create_location_input(
            latitude=40.7128,
            longitude=-74.0060,
            address="NYC",
            named_location="Office",
        )
        data = location.model_dump()
        
        assert data["latitude"] == 40.7128
        assert data["longitude"] == -74.0060
        assert data["address"] == "NYC"
        assert data["named_location"] == "Office"
        assert data["modality_type"] == "location"

    def test_deserialization_from_dict(self):
        """Test deserializing LocationInput from dictionary."""
        timestamp = datetime.now(timezone.utc)
        data = {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "address": "NYC",
            "timestamp": timestamp,
            "modality_type": "location",
        }
        
        location = LocationInput.model_validate(data)
        
        assert location.latitude == 40.7128
        assert location.longitude == -74.0060
        assert location.address == "NYC"

    def test_serialization_roundtrip(self):
        """Test that serialization and deserialization preserves data."""
        original = create_location_input(
            latitude=51.5074,
            longitude=-0.1278,
            address="London, UK",
            named_location="London Office",
            altitude=15.5,
            accuracy=10.0,
            speed=0.0,
            bearing=180.0,
        )
        
        data = original.model_dump()
        restored = LocationInput.model_validate(data)
        
        assert restored.latitude == original.latitude
        assert restored.longitude == original.longitude
        assert restored.address == original.address
        assert restored.named_location == original.named_location
        assert restored.altitude == original.altitude
        assert restored.accuracy == original.accuracy
        assert restored.speed == original.speed
        assert restored.bearing == original.bearing


class TestLocationInputFixtures:
    """Test the pre-built fixture location inputs.
    
    LOCATION-SPECIFIC: Verify that fixture data is correctly structured.
    """

    def test_home_location_fixture(self):
        """Test HOME_LOCATION fixture has expected values."""
        assert HOME_LOCATION.named_location == "Home"
        assert "San Francisco" in HOME_LOCATION.address
        assert HOME_LOCATION.latitude == 37.7749

    def test_office_location_fixture(self):
        """Test OFFICE_LOCATION fixture has expected values."""
        assert OFFICE_LOCATION.named_location == "Office"
        assert "San Francisco" in OFFICE_LOCATION.address

    def test_gym_location_fixture(self):
        """Test GYM_LOCATION fixture has expected values."""
        assert GYM_LOCATION.named_location == "Gym"
        assert "San Francisco" in GYM_LOCATION.address

    def test_city_location_fixtures(self):
        """Test city location fixtures have correct coordinates."""
        assert NYC_LOCATION.latitude == 40.7128
        assert NYC_LOCATION.longitude == -74.0060
        assert "New York" in NYC_LOCATION.address
        
        assert LONDON_LOCATION.latitude == 51.5074
        assert LONDON_LOCATION.longitude == -0.1278
        assert "London" in LONDON_LOCATION.address
