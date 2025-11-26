"""Unit tests for WeatherState.

This test suite covers:
1. General ModalityState behavior (applicable to all modalities)
2. Weather-specific state management and multi-location tracking
"""

from datetime import datetime, timezone

import pytest

from models.modalities.weather_input import WeatherInput
from models.modalities.weather_state import (
    WeatherLocationState,
    WeatherReportHistoryEntry,
    WeatherState,
)
from tests.fixtures.modalities.weather import (
    CLEAR_WEATHER,
    HOT_WEATHER,
    RAINY_WEATHER,
    SNOWY_WEATHER,
    create_weather_input,
    create_weather_state,
)


class TestWeatherStateInstantiation:
    """Test WeatherState instantiation and basic properties.
    
    GENERAL PATTERN: All ModalityState subclasses should test instantiation,
    default values, and proper inheritance from ModalityState.
    """

    def test_instantiation_with_defaults(self):
        """Test creating WeatherState with default values."""
        now = datetime.now(timezone.utc)
        state = create_weather_state(last_updated=now)
        
        assert state.locations == {}
        assert state.max_history_per_location == 100
        assert state.openweather_api_key is None
        assert state.last_updated == now
        assert state.update_count == 0

    def test_instantiation_with_custom_history_limit(self):
        """Test creating WeatherState with custom history limit.
        
        WEATHER-SPECIFIC: max_history_per_location controls per-location history size.
        """
        now = datetime.now(timezone.utc)
        state = create_weather_state(last_updated=now, max_history_per_location=24)
        
        assert state.max_history_per_location == 24

    def test_instantiation_with_api_key(self):
        """Test creating WeatherState with API key.
        
        WEATHER-SPECIFIC: Supports OpenWeather API integration.
        """
        now = datetime.now(timezone.utc)
        state = create_weather_state(last_updated=now, openweather_api_key="test_key_12345")
        
        assert state.openweather_api_key == "test_key_12345"

    def test_instantiation_with_existing_locations(self):
        """Test creating WeatherState with pre-populated locations.
        
        WEATHER-SPECIFIC: Locations dict maps normalized coordinate keys to WeatherLocationState.
        """
        now = datetime.now(timezone.utc)
        location_state = WeatherLocationState(
            latitude=40.7128,
            longitude=-74.0060,
            current_report=CLEAR_WEATHER.report,
            first_seen=now,
            last_updated=now,
        )
        
        state = create_weather_state(last_updated=now, locations={"40.71,-74.01": location_state})
        
        assert len(state.locations) == 1
        assert "40.71,-74.01" in state.locations

    def test_instantiation_modality_type_is_frozen(self):
        """Test that modality_type cannot be changed after instantiation."""
        state = create_weather_state()
        
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            state.modality_type = "other"

    def test_instantiation_default_modality_type(self):
        """Test that modality_type defaults to 'weather'."""
        state = create_weather_state()
        assert state.modality_type == "weather"


class TestWeatherStateApplyInput:
    """Test WeatherState.apply_input() method.
    
    GENERAL PATTERN: All ModalityState subclasses must implement apply_input()
    to update state from input events.
    
    WEATHER-SPECIFIC: Multi-location tracking with coordinate normalization,
    per-location history management, and timestamp extraction from input.
    """

    def test_apply_input_creates_new_location(self):
        """Test that apply_input creates a new location entry.
        
        WEATHER-SPECIFIC: First input for a location creates WeatherLocationState.
        """
        state = create_weather_state()
        weather = CLEAR_WEATHER
        
        state.apply_input(weather)
        
        assert len(state.locations) == 1
        location_key = state._get_location_key(weather.latitude, weather.longitude)
        assert location_key in state.locations
        assert state.last_updated == weather.timestamp

    def test_apply_input_updates_existing_location(self):
        """Test that apply_input updates an existing location.
        
        WEATHER-SPECIFIC: Subsequent inputs to same location update current report and add to history.
        """
        state = create_weather_state()
        
        # Apply first weather update
        state.apply_input(CLEAR_WEATHER)
        
        # Apply second weather update to same location
        rainy = create_weather_input(
            latitude=CLEAR_WEATHER.latitude,
            longitude=CLEAR_WEATHER.longitude,
        )
        state.apply_input(rainy)
        
        # Should still be one location
        assert len(state.locations) == 1
        location_key = state._get_location_key(rainy.latitude, rainy.longitude)
        location = state.locations[location_key]
        assert location.update_count == 2
        assert len(location.report_history) == 1  # First report moved to history

    def test_apply_input_tracks_multiple_locations(self):
        """Test that apply_input tracks multiple distinct locations.
        
        WEATHER-SPECIFIC: Each unique location (after normalization) gets its own WeatherLocationState.
        """
        state = create_weather_state()
        
        # NYC
        state.apply_input(create_weather_input(latitude=40.7128, longitude=-74.0060))
        
        # London
        state.apply_input(create_weather_input(latitude=51.5074, longitude=-0.1278))
        
        # Tokyo
        state.apply_input(create_weather_input(latitude=35.6762, longitude=139.6503))
        
        assert len(state.locations) == 3

    def test_apply_input_normalizes_coordinates(self):
        """Test that apply_input normalizes coordinates to location keys.
        
        WEATHER-SPECIFIC: Coordinates rounded to 2 decimal places (~1km precision).
        """
        state = create_weather_state()
        
        # These coordinates should normalize to the same location key
        weather1 = create_weather_input(latitude=40.7128, longitude=-74.0060)
        weather2 = create_weather_input(latitude=40.7129, longitude=-74.0061)
        
        state.apply_input(weather1)
        state.apply_input(weather2)
        
        # Should be treated as same location (rounded to 2 decimal places)
        assert len(state.locations) == 1
        location = list(state.locations.values())[0]
        assert location.update_count == 2

    def test_apply_input_maintains_history(self):
        """Test that apply_input maintains weather history.
        
        WEATHER-SPECIFIC: Previous current_report moves to report_history on each update.
        """
        state = create_weather_state()
        
        weather = CLEAR_WEATHER
        state.apply_input(weather)
        
        # Apply multiple updates
        for _ in range(5):
            state.apply_input(
                create_weather_input(
                    latitude=weather.latitude,
                    longitude=weather.longitude,
                ),
            )
        
        location_key = state._get_location_key(weather.latitude, weather.longitude)
        location = state.locations[location_key]
        assert len(location.report_history) == 5  # All but the current report

    def test_apply_input_respects_history_limit(self):
        """Test that apply_input enforces max_history_per_location.
        
        WEATHER-SPECIFIC: History is trimmed from oldest when limit exceeded.
        """
        state = create_weather_state(max_history_per_location=3)
        
        weather = CLEAR_WEATHER
        
        # Apply 10 updates
        for _ in range(10):
            state.apply_input(
                create_weather_input(
                    latitude=weather.latitude,
                    longitude=weather.longitude,
                )
            )
        
        location_key = state._get_location_key(weather.latitude, weather.longitude)
        location = state.locations[location_key]
        
        # History should be limited to 3
        assert len(location.report_history) <= 3

    def test_apply_input_updates_timestamps(self):
        """Test that apply_input updates first_seen and last_updated.
        
        WEATHER-SPECIFIC: first_seen is set on creation, last_updated on every update.
        """
        state = create_weather_state()
        
        weather = CLEAR_WEATHER
        state.apply_input(weather)
        
        location_key = state._get_location_key(weather.latitude, weather.longitude)
        location = state.locations[location_key]
        first_seen = location.first_seen
        first_last_updated = location.last_updated
        
        # Update again
        weather2 = create_weather_input(
            latitude=weather.latitude,
            longitude=weather.longitude,
        )
        state.apply_input(weather2)
        
        location = state.locations[location_key]
        assert location.first_seen == first_seen  # Should not change
        assert location.last_updated != first_last_updated  # Should be updated
        assert location.last_updated == weather2.timestamp

    def test_apply_input_increments_update_count(self):
        """Test that apply_input increments both state and location update counts.
        
        GENERAL PATTERN: update_count tracks number of apply_input calls.
        """
        state = create_weather_state()
        initial_count = state.update_count
        
        weather = create_weather_input()
        state.apply_input(weather)
        
        assert state.update_count == initial_count + 1
        
        location_key = state._get_location_key(weather.latitude, weather.longitude)
        assert state.locations[location_key].update_count == 1


class TestWeatherStateGetSnapshot:
    """Test WeatherState.get_snapshot() method.
    
    GENERAL PATTERN: All ModalityState subclasses must implement get_snapshot()
    to provide API-friendly state representation.
    """

    def test_get_snapshot_empty_state(self):
        """Test snapshot of empty weather state."""
        state = create_weather_state()
        snapshot = state.get_snapshot()
        
        assert snapshot["modality_type"] == "weather"
        assert snapshot["locations"] == {}
        assert snapshot["location_count"] == 0
        assert "update_count" in snapshot
        assert "last_updated" in snapshot

    def test_get_snapshot_with_single_location(self):
        """Test snapshot with one location.
        
        WEATHER-SPECIFIC: Snapshot includes location_count and per-location summaries.
        """
        state = create_weather_state()
        
        state.apply_input(CLEAR_WEATHER)
        snapshot = state.get_snapshot()
        
        assert len(snapshot["locations"]) == 1
        assert snapshot["location_count"] == 1
        
        location_key = list(snapshot["locations"].keys())[0]
        location = snapshot["locations"][location_key]
        
        assert "latitude" in location
        assert "longitude" in location
        assert "current_report" in location
        assert "last_updated" in location
        assert "history_count" in location

    def test_get_snapshot_with_multiple_locations(self):
        """Test snapshot with multiple locations.
        
        WEATHER-SPECIFIC: Each location key maps to its location state summary.
        """
        state = create_weather_state()
        
        locations = [
            (40.7128, -74.0060),  # NYC
            (51.5074, -0.1278),   # London
            (35.6762, 139.6503),  # Tokyo
        ]
        
        for lat, lon in locations:
            state.apply_input(create_weather_input(latitude=lat, longitude=lon))
        
        snapshot = state.get_snapshot()
        assert len(snapshot["locations"]) == 3
        assert snapshot["location_count"] == 3

    def test_get_snapshot_includes_weather_data(self):
        """Test that snapshot includes weather report data."""
        state = create_weather_state()
        
        state.apply_input(RAINY_WEATHER)
        snapshot = state.get_snapshot()
        
        location = list(snapshot["locations"].values())[0]
        current = location["current_report"]["current"]
        
        assert "temp" in current
        assert "feels_like" in current
        assert "humidity" in current
        assert "weather" in current


class TestWeatherStateValidateState:
    """Test WeatherState.validate_state() method.
    
    GENERAL PATTERN: All ModalityState subclasses must implement validate_state()
    to ensure internal consistency.
    """

    def test_validate_state_succeeds_for_valid_state(self):
        """Test that validate_state passes for valid state."""
        state = create_weather_state()
        issues = state.validate_state()
        assert issues == []

    def test_validate_state_succeeds_for_empty_state(self):
        """Test that validate_state passes for empty state."""
        state = create_weather_state()
        issues = state.validate_state()
        assert issues == []

    def test_validate_state_with_multiple_locations(self):
        """Test validation with multiple locations."""
        state = create_weather_state()
        
        for i in range(5):
            state.apply_input(
                create_weather_input(latitude=40.0 + i, longitude=-74.0 + i),
            )
        
        issues = state.validate_state()
        assert issues == []

    def test_validate_state_detects_invalid_latitude(self):
        """Test validation detects invalid latitude.
        
        WEATHER-SPECIFIC: Validates coordinate ranges for each location.
        """
        state = create_weather_state()
        
        # Manually create invalid location state
        state.locations["invalid"] = WeatherLocationState(
            latitude=999.0,  # Invalid
            longitude=0.0,
            current_report=CLEAR_WEATHER.report,
            first_seen=datetime.now(timezone.utc),
            last_updated=datetime.now(timezone.utc),
        )
        
        issues = state.validate_state()
        assert len(issues) > 0
        assert any("latitude" in issue.lower() for issue in issues)


class TestWeatherStateQuery:
    """Test WeatherState.query() method.
    
    GENERAL PATTERN: All ModalityState subclasses should implement query()
    for flexible state interrogation.
    
    WEATHER-SPECIFIC: Query requires lat/lon parameters, supports filtering,
    unit conversion, and time range queries.
    """

    def test_query_requires_lat_lon(self):
        """Test that query requires lat and lon parameters.
        
        WEATHER-SPECIFIC: Unlike other modalities, weather queries are location-based.
        """
        state = create_weather_state()
        
        with pytest.raises(ValueError, match="lat.*lon"):
            state.query({})

    def test_query_specific_location(self):
        """Test querying a specific location."""
        state = create_weather_state()
        
        weather = CLEAR_WEATHER
        state.apply_input(weather)
        
        result = state.query({
            "lat": weather.latitude,
            "lon": weather.longitude,
        })
        
        assert result is not None
        assert "reports" in result
        assert result["count"] == 1

    def test_query_nonexistent_location(self):
        """Test querying a location that doesn't exist."""
        state = create_weather_state()
        
        result = state.query({
            "lat": 99.0,
            "lon": 99.0,
        })
        
        assert result["count"] == 0
        assert "error" in result

    def test_query_with_unit_conversion(self):
        """Test querying with unit conversion.
        
        WEATHER-SPECIFIC: Supports standard, metric, imperial units.
        """
        state = create_weather_state()
        
        weather = HOT_WEATHER
        state.apply_input(weather)
        
        # Query in metric
        result = state.query({
            "lat": weather.latitude,
            "lon": weather.longitude,
            "units": "metric",
        })
        
        assert result["count"] == 1
        # Temperature should be converted from Kelvin to Celsius
        temp_celsius = result["reports"][0]["current"]["temp"]
        assert temp_celsius < 100  # Should be in Celsius range


class TestWeatherStateSerialization:
    """Test WeatherState serialization and deserialization.
    
    GENERAL PATTERN: All ModalityState subclasses should support Pydantic
    serialization via model_dump() and model_validate() for state persistence.
    
    WEATHER-SPECIFIC: Multi-location data and helper classes
    (WeatherLocationState, WeatherReportHistoryEntry) must serialize correctly.
    """

    def test_serialization_to_dict(self):
        """Test serializing WeatherState to dictionary."""
        state = create_weather_state()
        
        data = state.model_dump()
        
        assert data["modality_type"] == "weather"
        assert "locations" in data
        assert "max_history_per_location" in data

    def test_deserialization_from_dict(self):
        """Test deserializing WeatherState from dictionary."""
        original = create_weather_state()
        data = original.model_dump()
        
        restored = WeatherState.model_validate(data)
        
        assert restored.modality_type == original.modality_type
        assert restored.max_history_per_location == original.max_history_per_location

    def test_serialization_roundtrip_empty_state(self):
        """Test serialization roundtrip for empty state."""
        original = create_weather_state()
        
        data = original.model_dump()
        restored = WeatherState.model_validate(data)
        
        assert restored.modality_type == original.modality_type
        assert restored.locations == original.locations
        assert restored.max_history_per_location == original.max_history_per_location

    def test_serialization_roundtrip_with_locations(self):
        """Test serialization roundtrip with location data.
        
        WEATHER-SPECIFIC: Ensures WeatherLocationState helper class serializes correctly.
        """
        original = create_weather_state()
        
        # Add multiple locations
        original.apply_input(create_weather_input(latitude=40.0, longitude=-74.0))
        original.apply_input(create_weather_input(latitude=51.0, longitude=-0.1))
        
        data = original.model_dump()
        restored = WeatherState.model_validate(data)
        
        assert len(restored.locations) == len(original.locations)
        for key in original.locations:
            assert key in restored.locations
            assert restored.locations[key].latitude == original.locations[key].latitude
            assert restored.locations[key].longitude == original.locations[key].longitude

    def test_serialization_preserves_history(self):
        """Test that serialization preserves weather history.
        
        WEATHER-SPECIFIC: Ensures WeatherReportHistoryEntry serializes correctly.
        """
        original = create_weather_state()
        
        weather = CLEAR_WEATHER
        
        # Add multiple reports to create history
        for _ in range(5):
            original.apply_input(
                create_weather_input(
                    latitude=weather.latitude,
                    longitude=weather.longitude,
                )
            )
        
        data = original.model_dump()
        restored = WeatherState.model_validate(data)
        
        location_key = original._get_location_key(weather.latitude, weather.longitude)
        original_history = original.locations[location_key].report_history
        restored_history = restored.locations[location_key].report_history
        
        assert len(restored_history) == len(original_history)

    def test_serialization_preserves_weather_report_history_entry(self):
        """Test that WeatherReportHistoryEntry serializes correctly.
        
        WEATHER-SPECIFIC: Tests Pydantic helper class serialization.
        """
        now = datetime.now(timezone.utc)
        entry = WeatherReportHistoryEntry(
            timestamp=now,
            report=CLEAR_WEATHER.report,
        )
        
        data = entry.model_dump()
        restored = WeatherReportHistoryEntry.model_validate(data)
        
        assert restored.timestamp == entry.timestamp
        assert restored.report.lat == entry.report.lat
        assert restored.report.lon == entry.report.lon

    def test_serialization_preserves_weather_location_state(self):
        """Test that WeatherLocationState serializes correctly.
        
        WEATHER-SPECIFIC: Tests Pydantic helper class serialization.
        """
        now = datetime.now(timezone.utc)
        location = WeatherLocationState(
            latitude=40.7128,
            longitude=-74.0060,
            current_report=CLEAR_WEATHER.report,
            first_seen=now,
            last_updated=now,
            update_count=5,
        )
        
        data = location.model_dump()
        restored = WeatherLocationState.model_validate(data)
        
        assert restored.latitude == location.latitude
        assert restored.longitude == location.longitude
        assert restored.update_count == location.update_count
        assert restored.first_seen == location.first_seen

    def test_serialization_with_api_key(self):
        """Test that API key is preserved during serialization."""
        original = create_weather_state(openweather_api_key="test_key_12345")
        
        data = original.model_dump()
        restored = WeatherState.model_validate(data)
        
        assert restored.openweather_api_key == original.openweather_api_key

    def test_serialization_handles_none_api_key(self):
        """Test serialization when API key is None."""
        original = create_weather_state()
        
        data = original.model_dump()
        restored = WeatherState.model_validate(data)
        
        assert restored.openweather_api_key is None


class TestWeatherStateEdgeCases:
    """Test edge cases and boundary conditions.
    
    WEATHER-SPECIFIC: Location key normalization, extreme history sizes,
    coordinate precision handling.
    """

    def test_location_key_normalization(self):
        """Test that location keys are normalized correctly.
        
        WEATHER-SPECIFIC: 2 decimal place precision (~1km).
        """
        state = create_weather_state()
        
        # Test normalization
        key1 = state._get_location_key(40.7128, -74.0060)
        key2 = state._get_location_key(40.71, -74.01)
        
        # Should normalize to same key
        assert key1 == key2
        assert key1 == "40.71,-74.01"

    def test_location_key_collision_prevention(self):
        """Test that sufficiently different coordinates don't collide."""
        state = create_weather_state()
        
        # Coordinates that round to different keys
        coords = [
            (40.70, -74.00),
            (40.71, -74.01),
            (40.72, -74.02),
        ]
        
        for lat, lon in coords:
            state.apply_input(create_weather_input(latitude=lat, longitude=lon))
        
        # All should be treated as separate locations
        assert len(state.locations) == 3

    def test_zero_history_limit(self):
        """Test behavior with max_history_per_location=0.
        
        WEATHER-SPECIFIC: Zero limit should prevent any history storage.
        """
        state = create_weather_state(max_history_per_location=0)
        
        weather = CLEAR_WEATHER
        
        # Apply multiple updates
        for _ in range(5):
            state.apply_input(
                create_weather_input(
                    latitude=weather.latitude,
                    longitude=weather.longitude,
                )
            )
        
        location_key = state._get_location_key(weather.latitude, weather.longitude)
        location = state.locations[location_key]
        
        # No history should be kept
        assert len(location.report_history) == 0

    def test_very_large_history_limit(self):
        """Test behavior with very large history limit."""
        state = create_weather_state(max_history_per_location=10000)
        
        weather = CLEAR_WEATHER
        
        # Apply 100 updates
        for _ in range(100):
            state.apply_input(
                create_weather_input(
                    latitude=weather.latitude,
                    longitude=weather.longitude,
                )
            )
        
        location_key = state._get_location_key(weather.latitude, weather.longitude)
        location = state.locations[location_key]
        
        # All history should be kept
        assert len(location.report_history) == 99  # First update creates location

    def test_rapid_updates_same_location(self):
        """Test rapid successive updates to the same location."""
        state = create_weather_state()
        
        weather = CLEAR_WEATHER
        
        # Apply 100 updates rapidly
        for _ in range(100):
            state.apply_input(
                create_weather_input(
                    latitude=weather.latitude,
                    longitude=weather.longitude,
                )
            )
        
        # Should still be one location
        assert len(state.locations) == 1
        location_key = state._get_location_key(weather.latitude, weather.longitude)
        location = state.locations[location_key]
        assert location.update_count == 100

    def test_extreme_coordinates_normalization(self):
        """Test coordinate normalization at extreme values.
        
        WEATHER-SPECIFIC: Poles and date line handling.
        """
        state = create_weather_state()
        
        # North Pole
        state.apply_input(create_weather_input(latitude=90.0, longitude=0.0))
        
        # South Pole
        state.apply_input(create_weather_input(latitude=-90.0, longitude=0.0))
        
        # International Date Line (180 and -180 are same longitude but stored separately)
        state.apply_input(create_weather_input(latitude=0.0, longitude=180.0))
        state.apply_input(create_weather_input(latitude=0.0, longitude=-180.0))
        
        # Should have 4 separate locations (poles and both sides of date line)
        assert len(state.locations) == 4


class TestWeatherStateIntegration:
    """Test WeatherState integration scenarios.
    
    WEATHER-SPECIFIC: Realistic multi-location weather tracking scenarios.
    """

    def test_multi_day_weather_tracking(self):
        """Test tracking weather over multiple days at one location."""
        state = create_weather_state(max_history_per_location=72)  # 3 days
        
        weather = CLEAR_WEATHER
        
        # Simulate hourly updates for 3 days
        for _ in range(72):
            state.apply_input(
                create_weather_input(
                    latitude=weather.latitude,
                    longitude=weather.longitude,
                )
            )
        
        location_key = state._get_location_key(weather.latitude, weather.longitude)
        location = state.locations[location_key]
        
        assert location.update_count == 72
        assert len(location.report_history) == 71  # All but current stored in history

    def test_world_tour_weather_tracking(self):
        """Test tracking weather across multiple cities."""
        state = create_weather_state()
        
        cities = [
            ("New York", 40.7128, -74.0060),
            ("London", 51.5074, -0.1278),
            ("Tokyo", 35.6762, 139.6503),
            ("Sydney", -33.8688, 151.2093),
            ("Paris", 48.8566, 2.3522),
        ]
        
        for name, lat, lon in cities:
            state.apply_input(create_weather_input(latitude=lat, longitude=lon))
        
        assert len(state.locations) == 5
        
        # Verify all cities are tracked
        snapshot = state.get_snapshot()
        assert len(snapshot["locations"]) == 5
        assert snapshot["location_count"] == 5

    def test_weather_condition_changes_over_time(self):
        """Test tracking changing weather conditions at one location."""
        state = create_weather_state()
        
        # Simulate weather changing from clear to rainy to snowy
        # All at same coordinates
        lat, lon = 40.0, -74.0
        
        for _ in range(3):
            weather = create_weather_input(latitude=lat, longitude=lon)
            state.apply_input(weather)
        
        location_key = state._get_location_key(lat, lon)
        location = state.locations[location_key]
        
        assert location.update_count == 3
        assert len(location.report_history) == 2
