"""Unit tests for LocationState.

This test suite covers:
1. General ModalityState behavior (applicable to all modalities)
2. Location-specific state management and features
"""

from datetime import datetime, timedelta, timezone

import pytest

from models.modalities.location_input import LocationInput
from models.modalities.location_state import LocationHistoryEntry, LocationState
from tests.fixtures.modalities.location import (
    GYM_LOCATION,
    HOME_LOCATION,
    OFFICE_LOCATION,
    create_location_input,
    create_location_state,
)


class TestLocationStateInstantiation:
    """Test LocationState instantiation and basic properties.
    
    GENERAL PATTERN: All ModalityState subclasses should test instantiation,
    default values, and proper inheritance from ModalityState.
    """

    def test_instantiation_with_minimal_fields(self):
        """Test creating LocationState with minimal configuration."""
        timestamp = datetime.now(timezone.utc)
        state = LocationState(
            last_updated=timestamp,
        )
        
        assert state.modality_type == "location"
        assert state.last_updated == timestamp
        assert state.update_count == 0
        assert state.current_latitude is None
        assert state.current_longitude is None
        assert state.location_history == []

    def test_instantiation_with_current_location(self):
        """Test creating LocationState with initial location."""
        timestamp = datetime.now(timezone.utc)
        state = LocationState(
            current_latitude=37.7749,
            current_longitude=-122.4194,
            current_address="San Francisco, CA",
            current_named_location="Home",
            last_updated=timestamp,
        )
        
        assert state.current_latitude == 37.7749
        assert state.current_longitude == -122.4194
        assert state.current_address == "San Francisco, CA"
        assert state.current_named_location == "Home"

    def test_instantiation_modality_type_is_frozen(self):
        """Test that modality_type cannot be changed after instantiation."""
        state = create_location_state()
        
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            state.modality_type = "other"

    def test_instantiation_default_history_size(self):
        """Test that default max_history_size is set correctly."""
        state = create_location_state()
        
        assert state.max_history_size == 100


class TestLocationStateApplyInput:
    """Test LocationState.apply_input() method.
    
    GENERAL PATTERN: All ModalityState subclasses must implement apply_input()
    to modify state based on ModalityInput instances.
    """

    def test_apply_input_updates_current_location(self):
        """Test that applying LocationInput updates current location."""
        state = create_location_state()
        location_input = create_location_input(
            latitude=40.7128,
            longitude=-74.0060,
            address="New York, NY",
            named_location="NYC Office",
        )
        
        state.apply_input(location_input)
        
        assert state.current_latitude == 40.7128
        assert state.current_longitude == -74.0060
        assert state.current_address == "New York, NY"
        assert state.current_named_location == "NYC Office"

    def test_apply_input_increments_update_count(self):
        """Test that applying input increments update_count."""
        state = create_location_state()
        assert state.update_count == 0
        
        state.apply_input(create_location_input())
        assert state.update_count == 1
        
        state.apply_input(create_location_input())
        assert state.update_count == 2

    def test_apply_input_updates_last_updated_timestamp(self):
        """Test that applying input updates last_updated to input timestamp."""
        initial_time = datetime.now(timezone.utc)
        state = LocationState(last_updated=initial_time)
        
        input_time = initial_time + timedelta(hours=1)
        location_input = create_location_input(timestamp=input_time)
        
        state.apply_input(location_input)
        
        assert state.last_updated == input_time

    def test_apply_input_adds_previous_location_to_history(self):
        """Test that applying input preserves previous location in history."""
        initial_time = datetime.now(timezone.utc)
        state = LocationState(
            current_latitude=37.7749,
            current_longitude=-122.4194,
            current_address="San Francisco, CA",
            last_updated=initial_time,
        )
        
        new_input = create_location_input(
            latitude=40.7128,
            longitude=-74.0060,
            address="New York, NY",
        )
        
        state.apply_input(new_input)
        
        assert len(state.location_history) == 1
        assert state.location_history[0].latitude == 37.7749
        assert state.location_history[0].longitude == -122.4194
        assert state.location_history[0].address == "San Francisco, CA"

    def test_apply_input_manages_history_size(self):
        """Test that history is trimmed when it exceeds max_history_size."""
        state = LocationState(
            current_latitude=37.7749,
            current_longitude=-122.4194,
            last_updated=datetime.now(timezone.utc),
            max_history_size=5,
        )
        
        # Apply 10 location updates
        for i in range(10):
            location_input = create_location_input(
                latitude=37.0 + i * 0.1,
                longitude=-122.0 - i * 0.1,
            )
            state.apply_input(location_input)
        
        # History should be capped at max_history_size
        assert len(state.location_history) == 5

    def test_apply_input_preserves_all_location_fields(self):
        """Test that all optional location fields are preserved in history."""
        state = LocationState(
            current_latitude=37.7749,
            current_longitude=-122.4194,
            current_altitude=10.0,
            current_accuracy=5.0,
            current_speed=1.5,
            current_bearing=90.0,
            last_updated=datetime.now(timezone.utc),
        )
        
        new_input = create_location_input(
            latitude=40.0,
            longitude=-74.0,
        )
        
        state.apply_input(new_input)
        
        history_entry = state.location_history[0]
        assert history_entry.altitude == 10.0
        assert history_entry.accuracy == 5.0
        assert history_entry.speed == 1.5
        assert history_entry.bearing == 90.0

    def test_apply_input_rejects_wrong_input_type(self):
        """Test that applying wrong input type raises ValueError."""
        from models.modalities.time_input import TimeInput
        
        state = create_location_state()
        time_input = TimeInput(
            timezone="UTC",
            format_preference="12h",
            timestamp=datetime.now(timezone.utc),
        )
        
        with pytest.raises(ValueError, match="LocationState can only apply LocationInput"):
            state.apply_input(time_input)

    def test_apply_input_first_location_no_history(self):
        """Test that first location update doesn't create history entry."""
        state = LocationState(last_updated=datetime.now(timezone.utc))
        location_input = create_location_input()
        
        state.apply_input(location_input)
        
        assert len(state.location_history) == 0
        assert state.current_latitude is not None


class TestLocationStateGetSnapshot:
    """Test LocationState.get_snapshot() method.
    
    GENERAL PATTERN: All ModalityState subclasses must implement get_snapshot()
    to return JSON-serializable state for API responses.
    """

    def test_get_snapshot_includes_metadata(self):
        """Test that snapshot includes modality_type, last_updated, update_count."""
        state = create_location_state()
        snapshot = state.get_snapshot()
        
        assert snapshot["modality_type"] == "location"
        assert "last_updated" in snapshot
        assert snapshot["update_count"] == 0

    def test_get_snapshot_with_current_location(self):
        """Test snapshot includes current location when set."""
        state = create_location_state(
            current_latitude=37.7749,
            current_longitude=-122.4194,
            current_address="San Francisco, CA",
        )
        snapshot = state.get_snapshot()
        
        assert "current" in snapshot
        assert snapshot["current"]["latitude"] == 37.7749
        assert snapshot["current"]["longitude"] == -122.4194
        assert snapshot["current"]["address"] == "San Francisco, CA"

    def test_get_snapshot_without_current_location(self):
        """Test snapshot when no current location is set."""
        state = LocationState(last_updated=datetime.now(timezone.utc))
        snapshot = state.get_snapshot()
        
        assert "current" in snapshot
        assert snapshot["current"] == {}

    def test_get_snapshot_includes_history(self):
        """Test that snapshot includes location history."""
        state = create_location_state()
        state.apply_input(HOME_LOCATION)
        state.apply_input(OFFICE_LOCATION)
        
        snapshot = state.get_snapshot()
        
        assert "history" in snapshot
        assert len(snapshot["history"]) >= 1  # At least one previous location

    def test_get_snapshot_is_json_serializable(self):
        """Test that snapshot can be JSON serialized."""
        import json
        
        state = create_location_state()
        state.apply_input(create_location_input())
        
        snapshot = state.get_snapshot()
        json_str = json.dumps(snapshot)
        
        assert json_str is not None
        assert isinstance(json_str, str)


class TestLocationStateValidateState:
    """Test LocationState.validate_state() method.
    
    GENERAL PATTERN: All ModalityState subclasses must implement validate_state()
    to check internal consistency and return error messages.
    """

    def test_validate_state_valid_state_returns_empty_list(self):
        """Test that valid state returns no issues."""
        state = create_location_state()
        issues = state.validate_state()
        
        assert issues == []

    def test_validate_state_detects_mismatched_coordinates(self):
        """Test detection of latitude set without longitude."""
        state = LocationState(
            current_latitude=37.7749,
            current_longitude=None,
            last_updated=datetime.now(timezone.utc),
        )
        issues = state.validate_state()
        
        assert len(issues) > 0
        assert any("latitude and longitude" in issue.lower() for issue in issues)

    def test_validate_state_detects_invalid_latitude_range(self):
        """Test detection of out-of-range latitude."""
        state = create_location_state()
        # Manually set invalid value to bypass field validation
        state.current_latitude = 100.0
        
        issues = state.validate_state()
        
        assert any("latitude" in issue.lower() and "valid range" in issue.lower() 
                   for issue in issues)

    def test_validate_state_detects_invalid_longitude_range(self):
        """Test detection of out-of-range longitude."""
        state = create_location_state()
        state.current_longitude = 200.0
        
        issues = state.validate_state()
        
        assert any("longitude" in issue.lower() and "valid range" in issue.lower() 
                   for issue in issues)

    def test_validate_state_detects_history_not_chronological(self):
        """Test detection of non-chronological history entries."""
        state = create_location_state()
        
        # Manually create out-of-order history
        now = datetime.now(timezone.utc)
        state.location_history = [
            LocationHistoryEntry(
                timestamp=now,
                latitude=37.0,
                longitude=-122.0,
            ),
            LocationHistoryEntry(
                timestamp=now - timedelta(hours=1),  # Earlier time, wrong order
                latitude=37.1,
                longitude=-122.1,
            ),
        ]
        
        issues = state.validate_state()
        
        assert any("chronological" in issue.lower() for issue in issues)

    def test_validate_state_detects_history_exceeds_maximum(self):
        """Test detection of history exceeding max_history_size."""
        state = create_location_state(max_history_size=5)
        
        # Manually create oversized history
        now = datetime.now(timezone.utc)
        for i in range(10):
            state.location_history.append(
                LocationHistoryEntry(
                    timestamp=now + timedelta(minutes=i),
                    latitude=37.0 + i * 0.1,
                    longitude=-122.0,
                )
            )
        
        issues = state.validate_state()
        
        assert any("exceeds maximum" in issue.lower() for issue in issues)


class TestLocationStateQuery:
    """Test LocationState.query() method.
    
    LOCATION-SPECIFIC: Test location-specific query capabilities like filtering
    by time range, named location, and limit parameters.
    """

    def test_query_returns_current_location_by_default(self):
        """Test that query includes current location by default."""
        state = create_location_state()
        state.apply_input(HOME_LOCATION)
        
        result = state.query({})
        
        assert result["count"] >= 1
        assert any(loc.get("is_current") for loc in result["locations"])

    def test_query_excludes_current_when_requested(self):
        """Test that query can exclude current location."""
        state = create_location_state()
        state.apply_input(HOME_LOCATION)
        
        result = state.query({"include_current": False})
        
        assert not any(loc.get("is_current") for loc in result["locations"])

    def test_query_filters_by_time_range(self):
        """Test filtering locations by time range."""
        now = datetime.now(timezone.utc)
        state = create_location_state(last_updated=now)
        
        # Add locations at different times
        for i in range(5):
            location_input = create_location_input(
                latitude=37.0 + i * 0.1,
                longitude=-122.0,
                timestamp=now + timedelta(hours=i),
            )
            state.apply_input(location_input)
        
        # Query for locations after 2 hours
        result = state.query({"since": now + timedelta(hours=2)})
        
        assert result["count"] <= 3  # Should exclude first 2 locations

    def test_query_filters_by_named_location(self):
        """Test filtering locations by named location."""
        state = create_location_state()
        
        home_input = create_location_input(named_location="Home")
        state.apply_input(home_input)
        
        office_input = create_location_input(named_location="Office")
        state.apply_input(office_input)
        
        result = state.query({"named_location": "Home"})
        
        # Should only return Home location from history
        assert result["count"] >= 1
        for loc in result["locations"]:
            if "named_location" in loc:
                assert loc["named_location"] == "Home"

    def test_query_respects_limit(self):
        """Test that query respects limit parameter."""
        state = create_location_state()
        
        # Add multiple locations
        for i in range(10):
            state.apply_input(create_location_input(latitude=37.0 + i * 0.1))
        
        result = state.query({"limit": 3})
        
        assert result["count"] <= 3
        assert len(result["locations"]) <= 3

    def test_query_empty_state(self):
        """Test querying empty state returns empty results."""
        state = LocationState(last_updated=datetime.now(timezone.utc))
        
        result = state.query({"include_current": False})
        
        assert result["count"] == 0
        assert result["locations"] == []


class TestLocationHistoryEntry:
    """Test LocationHistoryEntry helper class.
    
    LOCATION-SPECIFIC: Test the history entry data structure.
    """

    def test_history_entry_creation(self):
        """Test creating a LocationHistoryEntry."""
        now = datetime.now(timezone.utc)
        entry = LocationHistoryEntry(
            timestamp=now,
            latitude=37.7749,
            longitude=-122.4194,
            address="San Francisco, CA",
            named_location="Home",
        )
        
        assert entry.timestamp == now
        assert entry.latitude == 37.7749
        assert entry.longitude == -122.4194
        assert entry.address == "San Francisco, CA"
        assert entry.named_location == "Home"

    def test_history_entry_to_dict(self):
        """Test converting history entry to dictionary."""
        now = datetime.now(timezone.utc)
        entry = LocationHistoryEntry(
            timestamp=now,
            latitude=40.7128,
            longitude=-74.0060,
            address="NYC",
            altitude=10.5,
            accuracy=5.0,
        )
        
        entry_dict = entry.to_dict()
        
        assert entry_dict["latitude"] == 40.7128
        assert entry_dict["longitude"] == -74.0060
        assert entry_dict["address"] == "NYC"
        assert entry_dict["altitude"] == 10.5
        assert entry_dict["accuracy"] == 5.0
        assert "timestamp" in entry_dict

    def test_history_entry_to_dict_omits_none_values(self):
        """Test that to_dict omits None optional fields."""
        entry = LocationHistoryEntry(
            timestamp=datetime.now(timezone.utc),
            latitude=37.0,
            longitude=-122.0,
        )
        
        entry_dict = entry.to_dict()
        
        assert "address" not in entry_dict
        assert "named_location" not in entry_dict
        assert "altitude" not in entry_dict


class TestLocationStateIntegration:
    """Integration tests for LocationState with multiple operations.
    
    LOCATION-SPECIFIC: Test realistic usage patterns.
    """

    def test_tracking_daily_locations(self):
        """Test tracking a day's worth of location changes."""
        start_time = datetime.now(timezone.utc).replace(hour=8, minute=0, second=0)
        state = LocationState(last_updated=start_time)
        
        # Morning at home
        state.apply_input(create_location_input(
            latitude=37.7749,
            longitude=-122.4194,
            named_location="Home",
            timestamp=start_time,
        ))
        
        # Commute to office
        state.apply_input(create_location_input(
            latitude=37.7849,
            longitude=-122.4094,
            named_location="Office",
            timestamp=start_time + timedelta(hours=1),
        ))
        
        # Lunch at restaurant
        state.apply_input(create_location_input(
            latitude=37.7750,
            longitude=-122.4150,
            named_location="Lunch Spot",
            timestamp=start_time + timedelta(hours=5),
        ))
        
        # Back to office
        state.apply_input(create_location_input(
            latitude=37.7849,
            longitude=-122.4094,
            named_location="Office",
            timestamp=start_time + timedelta(hours=6),
        ))
        
        # Home in evening
        state.apply_input(create_location_input(
            latitude=37.7749,
            longitude=-122.4194,
            named_location="Home",
            timestamp=start_time + timedelta(hours=10),
        ))
        
        assert state.update_count == 5
        assert len(state.location_history) == 4
        assert state.current_named_location == "Home"
        
        # Query all office visits
        office_visits = state.query({"named_location": "Office"})
        assert office_visits["count"] == 2

    def test_state_consistency_after_many_updates(self):
        """Test that state remains consistent after many updates."""
        state = create_location_state(max_history_size=20)
        
        # Apply 50 location updates
        now = datetime.now(timezone.utc)
        for i in range(50):
            location_input = create_location_input(
                latitude=37.0 + (i % 90) * 0.01,
                longitude=-122.0 - (i % 180) * 0.01,
                timestamp=now + timedelta(minutes=i),
            )
            state.apply_input(location_input)
        
        # Validate state consistency
        issues = state.validate_state()
        assert issues == []
        
        # Check history is properly managed
        assert len(state.location_history) == 20
        assert state.update_count == 50


class TestLocationStateSerialization:
    """Test LocationState serialization and deserialization.
    
    GENERAL PATTERN: All ModalityState subclasses should support Pydantic
    serialization via model_dump() and model_validate() for state persistence.
    """

    def test_serialization_to_dict(self):
        """Test serializing LocationState to dictionary."""
        state = create_location_state(
            current_latitude=40.7128,
            current_longitude=-74.0060,
            current_address="New York, NY",
        )
        state.apply_input(HOME_LOCATION)
        
        data = state.model_dump()
        
        assert data["modality_type"] == "location"
        # apply_input replaces current location, so check for HOME_LOCATION values
        assert data["current_latitude"] == 37.7749
        assert data["current_longitude"] == -122.4194
        assert "location_history" in data
        assert len(data["location_history"]) >= 1

    def test_deserialization_from_dict(self):
        """Test deserializing LocationState from dictionary."""
        state = create_location_state(
            current_latitude=37.7749,
            current_longitude=-122.4194,
        )
        state.apply_input(OFFICE_LOCATION)
        
        data = state.model_dump()
        restored = LocationState.model_validate(data)
        
        assert restored.modality_type == state.modality_type
        assert restored.current_latitude == state.current_latitude
        assert restored.current_longitude == state.current_longitude
        assert restored.update_count == state.update_count
        assert len(restored.location_history) == len(state.location_history)

    def test_serialization_roundtrip(self):
        """Test complete serialization/deserialization roundtrip."""
        original = create_location_state(
            current_latitude=51.5074,
            current_longitude=-0.1278,
            current_address="London, UK",
        )
        original.apply_input(HOME_LOCATION)
        original.apply_input(OFFICE_LOCATION)
        
        data = original.model_dump()
        restored = LocationState.model_validate(data)
        
        assert restored.current_latitude == original.current_latitude
        assert restored.current_longitude == original.current_longitude
        assert restored.current_address == original.current_address
        assert len(restored.location_history) == len(original.location_history)
        assert restored.location_history[0].latitude == original.location_history[0].latitude

    def test_serialization_with_full_location_data(self):
        """Test serialization preserves all optional location fields."""
        state = create_location_state(
            current_latitude=48.8566,
            current_longitude=2.3522,
            current_address="Paris, France",
        )
        state.apply_input(create_location_input(
            latitude=48.8584,
            longitude=2.2945,
            altitude=35.0,
            accuracy=5.0,
            speed=1.5,
            bearing=90.0,
            named_location="Eiffel Tower",
        ))
        
        data = state.model_dump()
        restored = LocationState.model_validate(data)
        
        assert restored.current_altitude == 35.0
        assert restored.current_accuracy == 5.0
        assert restored.current_speed == 1.5
        assert restored.current_bearing == 90.0
        assert restored.current_named_location == "Eiffel Tower"

    def test_serialization_preserves_history(self):
        """Test that location history is properly serialized."""
        state = create_location_state()
        now = datetime.now(timezone.utc)
        
        for i in range(3):
            state.apply_input(create_location_input(
                latitude=40.0 + i,
                longitude=-74.0 + i,
                timestamp=now + timedelta(hours=i),
            ))
        
        data = state.model_dump()
        restored = LocationState.model_validate(data)
        
        assert len(restored.location_history) == len(state.location_history)
        for i in range(len(state.location_history)):
            assert restored.location_history[i].latitude == state.location_history[i].latitude
            assert restored.location_history[i].longitude == state.location_history[i].longitude


class TestLocationStateCreateUndoData:
    """Test LocationState.create_undo_data() method.
    
    GENERAL PATTERN: All ModalityState subclasses must implement create_undo_data()
    to capture minimal data needed to reverse an apply_input() operation.
    """

    def test_create_undo_data_for_first_location_update(self):
        """Test create_undo_data when no current location exists.
        
        LOCATION-SPECIFIC: First update should capture 'clear_current' action.
        """
        state = LocationState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        location_input = create_location_input(
            latitude=40.7128,
            longitude=-74.0060,
            address="New York, NY",
        )
        
        undo_data = state.create_undo_data(location_input)
        
        assert undo_data["action"] == "clear_current"
        assert "state_previous_update_count" in undo_data
        assert "state_previous_last_updated" in undo_data

    def test_create_undo_data_for_location_update(self):
        """Test create_undo_data captures previous location state."""
        state = create_location_state(
            current_latitude=37.7749,
            current_longitude=-122.4194,
            current_address="San Francisco, CA",
        )
        state.current_named_location = "Home"
        
        new_location = create_location_input(
            latitude=40.7128,
            longitude=-74.0060,
            address="New York, NY",
        )
        
        undo_data = state.create_undo_data(new_location)
        
        assert undo_data["action"] == "restore_previous"
        assert undo_data["previous_latitude"] == 37.7749
        assert undo_data["previous_longitude"] == -122.4194
        assert undo_data["previous_address"] == "San Francisco, CA"
        assert undo_data["previous_named_location"] == "Home"

    def test_create_undo_data_captures_all_optional_fields(self):
        """Test create_undo_data captures all optional location fields."""
        state = create_location_state()
        state.current_altitude = 100.0
        state.current_accuracy = 10.0
        state.current_speed = 5.0
        state.current_bearing = 90.0
        
        new_location = create_location_input(
            latitude=40.7128,
            longitude=-74.0060,
        )
        
        undo_data = state.create_undo_data(new_location)
        
        assert undo_data["previous_altitude"] == 100.0
        assert undo_data["previous_accuracy"] == 10.0
        assert undo_data["previous_speed"] == 5.0
        assert undo_data["previous_bearing"] == 90.0

    def test_create_undo_data_at_capacity(self):
        """Test create_undo_data captures removed history entry at capacity.
        
        GENERAL PATTERN: When capacity limits cause entries to be removed,
        capture them for potential restoration.
        """
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        state = LocationState(
            last_updated=now,
            max_history_size=3,
        )
        
        # Fill to capacity: 3 history entries + 1 current
        for i in range(4):
            state.apply_input(create_location_input(
                latitude=40.0 + i * 0.1,
                longitude=-74.0 + i * 0.1,
                timestamp=now + timedelta(hours=i),
            ))
        
        assert len(state.location_history) == 3
        oldest_lat = state.location_history[0].latitude
        
        # Next update will trim oldest
        new_location = create_location_input(
            latitude=45.0,
            longitude=-75.0,
            timestamp=now + timedelta(hours=5),
        )
        
        undo_data = state.create_undo_data(new_location)
        
        assert "removed_history_entry" in undo_data
        assert undo_data["removed_history_entry"]["latitude"] == oldest_lat

    def test_create_undo_data_captures_state_metadata(self):
        """Test create_undo_data captures state-level metadata.
        
        GENERAL PATTERN: All undo data must include update_count and last_updated.
        """
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        state = LocationState(
            last_updated=now,
            update_count=5,
        )
        
        location_input = create_location_input()
        
        undo_data = state.create_undo_data(location_input)
        
        assert undo_data["state_previous_update_count"] == 5
        assert undo_data["state_previous_last_updated"] == now.isoformat()

    def test_create_undo_data_raises_for_invalid_input_type(self):
        """Test create_undo_data raises for non-LocationInput.
        
        GENERAL PATTERN: Validate input type and fail fast.
        """
        from models.modalities.chat_input import ChatInput
        
        state = create_location_state()
        chat_input = ChatInput(
            timestamp=datetime.now(timezone.utc),
            operation="send_message",
            conversation_id="test",
            role="user",
            content="Hello",
        )
        
        with pytest.raises(ValueError, match="LocationInput"):
            state.create_undo_data(chat_input)

    def test_create_undo_data_does_not_modify_state(self):
        """Test create_undo_data is read-only.
        
        GENERAL PATTERN: create_undo_data should not modify state.
        """
        state = create_location_state()
        original_lat = state.current_latitude
        original_lon = state.current_longitude
        original_count = state.update_count
        
        location_input = create_location_input(latitude=40.0, longitude=-74.0)
        state.create_undo_data(location_input)
        
        assert state.current_latitude == original_lat
        assert state.current_longitude == original_lon
        assert state.update_count == original_count


class TestLocationStateApplyUndo:
    """Test LocationState.apply_undo() method.
    
    GENERAL PATTERN: All ModalityState subclasses must implement apply_undo()
    to reverse apply_input() operations using data from create_undo_data().
    """

    def test_apply_undo_clears_first_location(self):
        """Test apply_undo clears current location for first update."""
        state = LocationState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        location_input = create_location_input(
            latitude=40.7128,
            longitude=-74.0060,
        )
        
        undo_data = state.create_undo_data(location_input)
        state.apply_input(location_input)
        
        assert state.current_latitude == 40.7128
        
        state.apply_undo(undo_data)
        
        assert state.current_latitude is None
        assert state.current_longitude is None
        assert state.current_address is None

    def test_apply_undo_restores_previous_location(self):
        """Test apply_undo restores previous location state."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        state = create_location_state(
            current_latitude=37.7749,
            current_longitude=-122.4194,
            current_address="San Francisco, CA",
            last_updated=now,
        )
        
        new_location = create_location_input(
            latitude=40.7128,
            longitude=-74.0060,
            address="New York, NY",
            timestamp=now + timedelta(hours=1),
        )
        
        undo_data = state.create_undo_data(new_location)
        state.apply_input(new_location)
        
        assert state.current_latitude == 40.7128
        assert len(state.location_history) == 1
        
        state.apply_undo(undo_data)
        
        assert state.current_latitude == 37.7749
        assert state.current_longitude == -122.4194
        assert state.current_address == "San Francisco, CA"
        assert len(state.location_history) == 0

    def test_apply_undo_restores_all_optional_fields(self):
        """Test apply_undo restores all optional location fields."""
        state = create_location_state()
        state.current_altitude = 100.0
        state.current_accuracy = 10.0
        state.current_speed = 5.0
        state.current_bearing = 90.0
        state.current_named_location = "Home"
        
        new_location = create_location_input(
            latitude=40.7128,
            longitude=-74.0060,
            altitude=50.0,
            accuracy=5.0,
        )
        
        undo_data = state.create_undo_data(new_location)
        state.apply_input(new_location)
        
        state.apply_undo(undo_data)
        
        assert state.current_altitude == 100.0
        assert state.current_accuracy == 10.0
        assert state.current_speed == 5.0
        assert state.current_bearing == 90.0
        assert state.current_named_location == "Home"

    def test_apply_undo_restores_trimmed_history_entry(self):
        """Test apply_undo restores history entry trimmed at capacity.
        
        GENERAL PATTERN: When capacity limits cause entries to be removed,
        restore them on undo.
        """
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        state = LocationState(
            last_updated=now,
            max_history_size=3,
        )
        
        # Fill to capacity
        for i in range(4):
            state.apply_input(create_location_input(
                latitude=40.0 + i * 0.1,
                longitude=-74.0 + i * 0.1,
                address=f"Location {i}",
                timestamp=now + timedelta(hours=i),
            ))
        
        assert len(state.location_history) == 3
        oldest_before = state.location_history[0].latitude
        
        # Another update will trim
        new_location = create_location_input(
            latitude=45.0,
            longitude=-75.0,
            timestamp=now + timedelta(hours=5),
        )
        
        undo_data = state.create_undo_data(new_location)
        state.apply_input(new_location)
        
        # Oldest entry was trimmed
        assert state.location_history[0].latitude != oldest_before
        
        state.apply_undo(undo_data)
        
        # Oldest entry should be restored
        assert len(state.location_history) == 3
        assert state.location_history[0].latitude == oldest_before

    def test_apply_undo_restores_state_metadata(self):
        """Test apply_undo restores state-level metadata.
        
        GENERAL PATTERN: Always restore update_count and last_updated.
        """
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        state = LocationState(
            last_updated=now,
            update_count=5,
        )
        
        location_input = create_location_input(
            timestamp=now + timedelta(hours=1),
        )
        
        undo_data = state.create_undo_data(location_input)
        state.apply_input(location_input)
        
        assert state.update_count == 6
        assert state.last_updated != now
        
        state.apply_undo(undo_data)
        
        assert state.update_count == 5
        assert state.last_updated == now

    def test_apply_undo_raises_for_missing_action(self):
        """Test apply_undo raises for missing action field.
        
        GENERAL PATTERN: Validate required fields.
        """
        state = create_location_state()
        
        with pytest.raises(ValueError, match="action"):
            state.apply_undo({})

    def test_apply_undo_raises_for_unknown_action(self):
        """Test apply_undo raises for unknown action.
        
        GENERAL PATTERN: Handle unknown actions gracefully with clear error.
        """
        state = create_location_state()
        
        with pytest.raises(ValueError, match="Unknown undo action"):
            state.apply_undo({"action": "invalid_action"})

    def test_undo_full_cycle_first_update(self):
        """Test complete undo cycle for first location update.
        
        GENERAL PATTERN: create_undo → apply → undo = original state
        """
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        state = LocationState(last_updated=now)
        
        original_snapshot = state.get_snapshot()
        
        location_input = create_location_input(
            latitude=40.7128,
            longitude=-74.0060,
            timestamp=now + timedelta(hours=1),
        )
        
        undo_data = state.create_undo_data(location_input)
        state.apply_input(location_input)
        state.apply_undo(undo_data)
        
        restored_snapshot = state.get_snapshot()
        
        assert restored_snapshot["current"] == original_snapshot["current"]
        assert restored_snapshot["update_count"] == original_snapshot["update_count"]

    def test_undo_full_cycle_with_history(self):
        """Test complete undo cycle with existing history."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        state = create_location_state(last_updated=now)
        
        # Build some history
        state.apply_input(create_location_input(
            latitude=40.0,
            longitude=-74.0,
            timestamp=now + timedelta(hours=1),
        ))
        
        original_history_len = len(state.location_history)
        original_lat = state.current_latitude
        
        # New update to undo
        new_location = create_location_input(
            latitude=45.0,
            longitude=-75.0,
            timestamp=now + timedelta(hours=2),
        )
        
        undo_data = state.create_undo_data(new_location)
        state.apply_input(new_location)
        state.apply_undo(undo_data)
        
        assert len(state.location_history) == original_history_len
        assert state.current_latitude == original_lat

    def test_undo_full_cycle_at_capacity(self):
        """Test complete undo cycle when at capacity.
        
        GENERAL PATTERN: Verify capacity edge case is handled correctly.
        """
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        state = LocationState(
            last_updated=now,
            max_history_size=3,
        )
        
        # Fill to capacity
        for i in range(4):
            state.apply_input(create_location_input(
                latitude=40.0 + i * 0.1,
                longitude=-74.0 + i * 0.1,
                timestamp=now + timedelta(hours=i),
            ))
        
        # Capture state at capacity
        original_history = [
            (e.latitude, e.longitude) for e in state.location_history
        ]
        original_current = (state.current_latitude, state.current_longitude)
        
        # Another update
        new_location = create_location_input(
            latitude=50.0,
            longitude=-80.0,
            timestamp=now + timedelta(hours=5),
        )
        
        undo_data = state.create_undo_data(new_location)
        state.apply_input(new_location)
        state.apply_undo(undo_data)
        
        restored_history = [
            (e.latitude, e.longitude) for e in state.location_history
        ]
        restored_current = (state.current_latitude, state.current_longitude)
        
        assert restored_history == original_history
        assert restored_current == original_current

    def test_multiple_sequential_undos(self):
        """Test multiple sequential undo operations.
        
        GENERAL PATTERN: Each undo should be independent and work correctly.
        """
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        state = LocationState(last_updated=now)
        
        undo_data_list = []
        
        # Apply 3 locations, capturing undo data each time
        for i in range(3):
            location = create_location_input(
                latitude=40.0 + i,
                longitude=-74.0 + i,
                address=f"Location {i}",
                timestamp=now + timedelta(hours=i + 1),
            )
            undo_data_list.append(state.create_undo_data(location))
            state.apply_input(location)
        
        assert state.current_latitude == 42.0
        assert len(state.location_history) == 2
        
        # Undo in reverse order
        state.apply_undo(undo_data_list[2])
        assert state.current_latitude == 41.0
        assert len(state.location_history) == 1
        
        state.apply_undo(undo_data_list[1])
        assert state.current_latitude == 40.0
        assert len(state.location_history) == 0
        
        state.apply_undo(undo_data_list[0])
        assert state.current_latitude is None
        assert len(state.location_history) == 0

    def test_undo_preserves_history_entry_details(self):
        """Test that undo preserves all history entry details."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        state = LocationState(
            last_updated=now,
            max_history_size=2,
        )
        
        # Add locations with full details
        for i in range(3):
            state.apply_input(create_location_input(
                latitude=40.0 + i,
                longitude=-74.0 + i,
                address=f"Address {i}",
                named_location=f"Location {i}",
                altitude=100.0 + i * 10,
                accuracy=5.0 + i,
                speed=10.0 + i,
                bearing=90.0 + i * 10,
                timestamp=now + timedelta(hours=i),
            ))
        
        # Capture first entry before it gets trimmed
        first_entry = state.location_history[0]
        
        # New update will trim first entry
        new_location = create_location_input(
            latitude=50.0,
            longitude=-80.0,
            timestamp=now + timedelta(hours=4),
        )
        
        undo_data = state.create_undo_data(new_location)
        state.apply_input(new_location)
        state.apply_undo(undo_data)
        
        # Verify first entry is restored with all details
        restored_first = state.location_history[0]
        assert restored_first.latitude == first_entry.latitude
        assert restored_first.altitude == first_entry.altitude
        assert restored_first.accuracy == first_entry.accuracy
        assert restored_first.speed == first_entry.speed
        assert restored_first.bearing == first_entry.bearing
        assert restored_first.named_location == first_entry.named_location
