"""Unit tests for TimeState.

This test suite covers:
1. General ModalityState behavior (applicable to all modalities)
2. Time-specific state management and features
"""

from datetime import datetime, timedelta, timezone

import pytest

from models.modalities.time_input import TimeInput
from models.modalities.time_state import TimeSettingsHistoryEntry, TimeState
from tests.fixtures.modalities.time import (
    PARIS_INPUT,
    TOKYO_INPUT,
    UK_INPUT,
    US_EASTERN_INPUT,
    create_time_input,
    create_time_state,
)


class TestTimeStateInstantiation:
    """Test TimeState instantiation and basic properties.
    
    GENERAL PATTERN: All ModalityState subclasses should test instantiation,
    default values, and proper inheritance from ModalityState.
    """

    def test_instantiation_with_minimal_fields(self):
        """Test creating TimeState with minimal configuration."""
        timestamp = datetime.now(timezone.utc)
        state = TimeState(
            last_updated=timestamp,
        )
        
        assert state.modality_type == "time"
        assert state.last_updated == timestamp
        assert state.update_count == 0
        assert state.timezone == "UTC"
        assert state.format_preference == "12h"
        assert state.settings_history == []

    def test_instantiation_with_custom_settings(self):
        """Test creating TimeState with custom initial settings."""
        timestamp = datetime.now(timezone.utc)
        state = TimeState(
            timezone="America/New_York",
            format_preference="24h",
            date_format="MM/DD/YYYY",
            locale="en_US",
            week_start="sunday",
            last_updated=timestamp,
        )
        
        assert state.timezone == "America/New_York"
        assert state.format_preference == "24h"
        assert state.date_format == "MM/DD/YYYY"
        assert state.locale == "en_US"
        assert state.week_start == "sunday"

    def test_instantiation_modality_type_is_frozen(self):
        """Test that modality_type cannot be changed after instantiation."""
        state = create_time_state()
        
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            state.modality_type = "other"

    def test_instantiation_default_history_size(self):
        """Test that default max_history_size is set correctly."""
        state = create_time_state()
        
        assert state.max_history_size == 50


class TestTimeStateApplyInput:
    """Test TimeState.apply_input() method.
    
    GENERAL PATTERN: All ModalityState subclasses must implement apply_input()
    to modify state based on ModalityInput instances.
    """

    def test_apply_input_updates_current_settings(self):
        """Test that applying TimeInput updates current settings."""
        state = create_time_state()
        time_input = create_time_input(
            timezone="America/New_York",
            format_preference="24h",
            date_format="MM/DD/YYYY",
            locale="en_US",
        )
        
        state.apply_input(time_input)
        
        assert state.timezone == "America/New_York"
        assert state.format_preference == "24h"
        assert state.date_format == "MM/DD/YYYY"
        assert state.locale == "en_US"

    def test_apply_input_increments_update_count(self):
        """Test that applying input increments update_count."""
        state = create_time_state()
        assert state.update_count == 0
        
        state.apply_input(create_time_input())
        assert state.update_count == 1
        
        state.apply_input(create_time_input())
        assert state.update_count == 2

    def test_apply_input_updates_last_updated_timestamp(self):
        """Test that applying input updates last_updated to input timestamp."""
        initial_time = datetime.now(timezone.utc)
        state = TimeState(last_updated=initial_time)
        
        input_time = initial_time + timedelta(hours=1)
        time_input = create_time_input(timestamp=input_time)
        
        state.apply_input(time_input)
        
        assert state.last_updated == input_time

    def test_apply_input_adds_previous_settings_to_history(self):
        """Test that applying input preserves previous settings in history."""
        initial_time = datetime.now(timezone.utc)
        state = TimeState(
            timezone="UTC",
            format_preference="12h",
            last_updated=initial_time,
        )
        
        new_input = create_time_input(
            timezone="America/New_York",
            format_preference="24h",
        )
        
        state.apply_input(new_input)
        
        assert len(state.settings_history) == 1
        assert state.settings_history[0].timezone == "UTC"
        assert state.settings_history[0].format_preference == "12h"

    def test_apply_input_manages_history_size(self):
        """Test that history is trimmed when it exceeds max_history_size."""
        state = TimeState(
            timezone="UTC",
            format_preference="12h",
            last_updated=datetime.now(timezone.utc),
            max_history_size=5,
        )
        
        # Apply 10 settings updates
        timezones = ["America/New_York", "America/Chicago", "America/Denver",
                     "America/Los_Angeles", "America/Phoenix", "America/Anchorage",
                     "Pacific/Honolulu", "America/Halifax", "America/Toronto",
                     "America/Vancouver"]
        
        for tz in timezones:
            time_input = create_time_input(timezone=tz)
            state.apply_input(time_input)
        
        # History should be capped at max_history_size
        assert len(state.settings_history) == 5

    def test_apply_input_preserves_all_settings_fields(self):
        """Test that all optional settings fields are preserved in history."""
        state = TimeState(
            timezone="UTC",
            format_preference="12h",
            date_format="YYYY-MM-DD",
            locale="en_US",
            week_start="sunday",
            last_updated=datetime.now(timezone.utc),
        )
        
        new_input = create_time_input(
            timezone="Europe/London",
            format_preference="24h",
        )
        
        state.apply_input(new_input)
        
        history_entry = state.settings_history[0]
        assert history_entry.date_format == "YYYY-MM-DD"
        assert history_entry.locale == "en_US"
        assert history_entry.week_start == "sunday"

    def test_apply_input_rejects_wrong_input_type(self):
        """Test that applying wrong input type raises ValueError."""
        from models.modalities.location_input import LocationInput
        
        state = create_time_state()
        location_input = LocationInput(
            latitude=37.7749,
            longitude=-122.4194,
            timestamp=datetime.now(timezone.utc),
        )
        
        with pytest.raises(ValueError, match="TimeState can only apply TimeInput"):
            state.apply_input(location_input)

    def test_apply_input_updates_individual_fields(self):
        """Test that individual fields can be updated independently."""
        state = create_time_state(
            timezone="UTC",
            format_preference="12h",
            date_format="YYYY-MM-DD",
        )
        
        # Change only format preference
        time_input = create_time_input(
            timezone="UTC",
            format_preference="24h",
            date_format="YYYY-MM-DD",
        )
        
        state.apply_input(time_input)
        
        assert state.timezone == "UTC"
        assert state.format_preference == "24h"
        assert state.date_format == "YYYY-MM-DD"


class TestTimeStateGetSnapshot:
    """Test TimeState.get_snapshot() method.
    
    GENERAL PATTERN: All ModalityState subclasses must implement get_snapshot()
    to return JSON-serializable state for API responses.
    """

    def test_get_snapshot_includes_metadata(self):
        """Test that snapshot includes modality_type, last_updated, update_count."""
        state = create_time_state()
        snapshot = state.get_snapshot()
        
        assert snapshot["modality_type"] == "time"
        assert "last_updated" in snapshot
        assert snapshot["update_count"] == 0

    def test_get_snapshot_includes_current_settings(self):
        """Test snapshot includes current timezone and format settings."""
        state = create_time_state(
            timezone="America/New_York",
            format_preference="24h",
        )
        snapshot = state.get_snapshot()
        
        assert "current" in snapshot
        assert snapshot["current"]["timezone"] == "America/New_York"
        assert snapshot["current"]["format_preference"] == "24h"

    def test_get_snapshot_includes_optional_settings(self):
        """Test snapshot includes optional settings when set."""
        state = create_time_state(
            timezone="Europe/London",
            format_preference="24h",
            date_format="DD/MM/YYYY",
            locale="en_GB",
            week_start="monday",
        )
        snapshot = state.get_snapshot()
        
        assert snapshot["current"]["date_format"] == "DD/MM/YYYY"
        assert snapshot["current"]["locale"] == "en_GB"
        assert snapshot["current"]["week_start"] == "monday"

    def test_get_snapshot_omits_none_optional_settings(self):
        """Test snapshot omits optional settings when None."""
        state = create_time_state(
            timezone="UTC",
            format_preference="12h",
        )
        snapshot = state.get_snapshot()
        
        assert "date_format" not in snapshot["current"]
        assert "locale" not in snapshot["current"]
        assert "week_start" not in snapshot["current"]

    def test_get_snapshot_includes_history(self):
        """Test that snapshot includes settings history."""
        state = create_time_state()
        state.apply_input(US_EASTERN_INPUT)
        state.apply_input(UK_INPUT)
        
        snapshot = state.get_snapshot()
        
        assert "history" in snapshot
        assert len(snapshot["history"]) == 2

    def test_get_snapshot_is_json_serializable(self):
        """Test that snapshot can be JSON serialized."""
        import json
        
        state = create_time_state()
        state.apply_input(create_time_input())
        
        snapshot = state.get_snapshot()
        json_str = json.dumps(snapshot)
        
        assert json_str is not None
        assert isinstance(json_str, str)


class TestTimeStateValidateState:
    """Test TimeState.validate_state() method.
    
    GENERAL PATTERN: All ModalityState subclasses must implement validate_state()
    to check internal consistency and return error messages.
    """

    def test_validate_state_valid_state_returns_empty_list(self):
        """Test that valid state returns no issues."""
        state = create_time_state()
        issues = state.validate_state()
        
        assert issues == []

    def test_validate_state_detects_invalid_timezone(self):
        """Test detection of invalid timezone identifier."""
        state = create_time_state()
        # Manually set invalid timezone to bypass field validation
        state.timezone = "Invalid/Timezone"
        
        issues = state.validate_state()
        
        assert len(issues) > 0
        assert any("Invalid timezone" in issue for issue in issues)

    def test_validate_state_detects_history_not_chronological(self):
        """Test detection of non-chronological history entries."""
        state = create_time_state()
        
        # Manually create out-of-order history
        now = datetime.now(timezone.utc)
        state.settings_history = [
            TimeSettingsHistoryEntry(
                timestamp=now,
                timezone="UTC",
                format_preference="12h",
            ),
            TimeSettingsHistoryEntry(
                timestamp=now - timedelta(hours=1),  # Earlier time, wrong order
                timezone="America/New_York",
                format_preference="12h",
            ),
        ]
        
        issues = state.validate_state()
        
        assert any("chronological" in issue.lower() for issue in issues)

    def test_validate_state_detects_history_exceeds_maximum(self):
        """Test detection of history exceeding max_history_size."""
        state = create_time_state(max_history_size=5)
        
        # Manually create oversized history
        now = datetime.now(timezone.utc)
        for i in range(10):
            state.settings_history.append(
                TimeSettingsHistoryEntry(
                    timestamp=now + timedelta(minutes=i),
                    timezone="UTC",
                    format_preference="12h",
                )
            )
        
        issues = state.validate_state()
        
        assert any("exceeds maximum" in issue.lower() for issue in issues)

    def test_validate_state_accepts_valid_timezone(self):
        """Test that valid timezone passes validation."""
        state = create_time_state(timezone="America/New_York")
        issues = state.validate_state()
        
        assert issues == []


class TestTimeStateQuery:
    """Test TimeState.query() method.
    
    TIME-SPECIFIC: Test time-specific query capabilities like filtering by
    time range, timezone, format preference, and limit parameters.
    """

    def test_query_returns_current_settings_by_default(self):
        """Test that query includes current settings by default."""
        state = create_time_state()
        state.apply_input(US_EASTERN_INPUT)
        
        result = state.query({})
        
        assert result["count"] >= 1
        assert any(setting.get("is_current") for setting in result["settings"])

    def test_query_excludes_current_when_requested(self):
        """Test that query can exclude current settings."""
        state = create_time_state()
        state.apply_input(US_EASTERN_INPUT)
        
        result = state.query({"include_current": False})
        
        assert not any(setting.get("is_current") for setting in result["settings"])

    def test_query_filters_by_time_range(self):
        """Test filtering settings by time range."""
        now = datetime.now(timezone.utc)
        state = TimeState(last_updated=now)
        
        # Add settings at different times
        for i, tz_input in enumerate([US_EASTERN_INPUT, UK_INPUT, TOKYO_INPUT]):
            modified_input = create_time_input(
                timezone=tz_input.timezone,
                format_preference=tz_input.format_preference,
                timestamp=now + timedelta(hours=i),
            )
            state.apply_input(modified_input)
        
        # Query for settings after 1 hour
        result = state.query({"since": now + timedelta(hours=1)})
        
        assert result["count"] <= 2  # Should exclude first setting

    def test_query_filters_by_timezone(self):
        """Test filtering settings by timezone."""
        state = create_time_state()
        
        state.apply_input(US_EASTERN_INPUT)
        state.apply_input(UK_INPUT)
        state.apply_input(TOKYO_INPUT)
        
        result = state.query({"timezone": "America/New_York"})
        
        # Should only return settings with America/New_York timezone
        for setting in result["settings"]:
            if "timezone" in setting and not setting.get("is_current"):
                assert setting["timezone"] == "America/New_York"

    def test_query_filters_by_format_preference(self):
        """Test filtering settings by format preference."""
        state = create_time_state()
        
        state.apply_input(create_time_input(format_preference="12h"))
        state.apply_input(create_time_input(format_preference="24h"))
        state.apply_input(create_time_input(format_preference="12h"))
        
        result = state.query({"format_preference": "12h"})
        
        # Should only return 12h format settings
        for setting in result["settings"]:
            if "format_preference" in setting and not setting.get("is_current"):
                assert setting["format_preference"] == "12h"

    def test_query_respects_limit(self):
        """Test that query respects limit parameter."""
        state = create_time_state()
        
        # Add multiple settings
        for i in range(10):
            state.apply_input(create_time_input())
        
        result = state.query({"limit": 3})
        
        assert result["count"] <= 3
        assert len(result["settings"]) <= 3

    def test_query_empty_history(self):
        """Test querying state with no history returns only current."""
        state = create_time_state()
        
        result = state.query({})
        
        assert result["count"] == 1
        assert result["settings"][0]["is_current"]


class TestTimeStateFormatMethods:
    """Test TimeState time formatting helper methods.
    
    TIME-SPECIFIC: Test format_time() and format_datetime() methods that
    convert times according to user preferences.
    """

    def test_format_time_12h_format(self):
        """Test formatting time with 12-hour preference."""
        state = create_time_state(
            timezone="America/New_York",
            format_preference="12h",
        )
        
        test_time = datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc)
        formatted = state.format_time(test_time)
        
        assert "AM" in formatted or "PM" in formatted
        assert ":" in formatted

    def test_format_time_24h_format(self):
        """Test formatting time with 24-hour preference."""
        state = create_time_state(
            timezone="Europe/London",
            format_preference="24h",
        )
        
        test_time = datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc)
        formatted = state.format_time(test_time)
        
        assert "AM" not in formatted and "PM" not in formatted
        assert ":" in formatted

    def test_format_time_respects_timezone(self):
        """Test that format_time converts to user's timezone."""
        state = create_time_state(
            timezone="Asia/Tokyo",
            format_preference="24h",
        )
        
        # UTC time should be converted to Tokyo time
        test_time = datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc)
        formatted = state.format_time(test_time)
        
        # Tokyo is UTC+9, so 00:00 UTC should be 09:00 JST
        assert "09:" in formatted

    def test_format_datetime_includes_date_and_time(self):
        """Test that format_datetime includes both date and time."""
        state = create_time_state(
            timezone="UTC",
            format_preference="24h",
            date_format="YYYY-MM-DD",
        )
        
        test_time = datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc)
        formatted = state.format_datetime(test_time)
        
        assert "2024" in formatted
        assert "01" in formatted or "15" in formatted
        assert "14:30" in formatted

    def test_format_datetime_uses_date_format_preference(self):
        """Test that format_datetime respects date_format setting."""
        state_us = create_time_state(
            timezone="UTC",
            format_preference="12h",
            date_format="MM/DD/YYYY",
        )
        
        test_time = datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc)
        formatted_us = state_us.format_datetime(test_time)
        
        assert "01/15/2024" in formatted_us or "01-15-2024" in formatted_us


class TestTimeSettingsHistoryEntry:
    """Test TimeSettingsHistoryEntry helper class.
    
    TIME-SPECIFIC: Test the history entry data structure.
    """

    def test_history_entry_creation(self):
        """Test creating a TimeSettingsHistoryEntry."""
        now = datetime.now(timezone.utc)
        entry = TimeSettingsHistoryEntry(
            timestamp=now,
            timezone="America/New_York",
            format_preference="12h",
            date_format="MM/DD/YYYY",
            locale="en_US",
            week_start="sunday",
        )
        
        assert entry.timestamp == now
        assert entry.timezone == "America/New_York"
        assert entry.format_preference == "12h"
        assert entry.date_format == "MM/DD/YYYY"
        assert entry.locale == "en_US"
        assert entry.week_start == "sunday"

    def test_history_entry_to_dict(self):
        """Test converting history entry to dictionary."""
        now = datetime.now(timezone.utc)
        entry = TimeSettingsHistoryEntry(
            timestamp=now,
            timezone="Europe/London",
            format_preference="24h",
            date_format="DD/MM/YYYY",
        )
        
        entry_dict = entry.to_dict()
        
        assert entry_dict["timezone"] == "Europe/London"
        assert entry_dict["format_preference"] == "24h"
        assert entry_dict["date_format"] == "DD/MM/YYYY"
        assert "timestamp" in entry_dict

    def test_history_entry_to_dict_omits_none_values(self):
        """Test that to_dict omits None optional fields."""
        entry = TimeSettingsHistoryEntry(
            timestamp=datetime.now(timezone.utc),
            timezone="UTC",
            format_preference="12h",
        )
        
        entry_dict = entry.to_dict()
        
        assert "date_format" not in entry_dict
        assert "locale" not in entry_dict
        assert "week_start" not in entry_dict


class TestTimeStateSerialization:
    """Test TimeState serialization and deserialization.
    
    GENERAL PATTERN: All ModalityState subclasses should support Pydantic
    serialization via model_dump() and model_validate() for state persistence.
    """

    def test_serialization_to_dict(self):
        """Test serializing TimeState to dictionary."""
        state = create_time_state(
            timezone="America/Los_Angeles",
            format_preference="12h",
            date_format="MM/DD/YYYY",
        )
        
        data = state.model_dump()
        
        assert data["modality_type"] == "time"
        assert data["timezone"] == "America/Los_Angeles"
        assert data["format_preference"] == "12h"
        assert data["date_format"] == "MM/DD/YYYY"
        assert "settings_history" in data

    def test_deserialization_from_dict(self):
        """Test deserializing TimeState from dictionary."""
        state = create_time_state(
            timezone="Europe/London",
            format_preference="24h",
        )
        state.apply_input(create_time_input(
            timezone="Europe/Paris",
            format_preference="24h",
        ))
        
        data = state.model_dump()
        restored = TimeState.model_validate(data)
        
        assert restored.modality_type == state.modality_type
        assert restored.timezone == state.timezone
        assert restored.format_preference == state.format_preference
        assert restored.update_count == state.update_count
        assert len(restored.settings_history) == len(state.settings_history)

    def test_serialization_roundtrip(self):
        """Test complete serialization/deserialization roundtrip."""
        original = create_time_state(
            timezone="Asia/Tokyo",
            format_preference="24h",
            date_format="YYYY-MM-DD",
            locale="ja_JP",
        )
        original.apply_input(create_time_input(
            timezone="Asia/Seoul",
            format_preference="12h",
        ))
        
        data = original.model_dump()
        restored = TimeState.model_validate(data)
        
        assert restored.timezone == original.timezone
        assert restored.format_preference == original.format_preference
        assert restored.date_format == original.date_format
        assert restored.locale == original.locale
        assert len(restored.settings_history) == len(original.settings_history)

    def test_serialization_with_all_optional_fields(self):
        """Test serialization preserves all optional settings fields."""
        state = create_time_state(
            timezone="America/New_York",
            format_preference="12h",
            date_format="MM/DD/YYYY",
            locale="en_US",
            week_start="sunday",
        )
        
        data = state.model_dump()
        restored = TimeState.model_validate(data)
        
        assert restored.date_format == "MM/DD/YYYY"
        assert restored.locale == "en_US"
        assert restored.week_start == "sunday"

    def test_serialization_preserves_history(self):
        """Test that settings history is properly serialized."""
        state = create_time_state(timezone="UTC", format_preference="24h")
        now = datetime.now(timezone.utc)
        
        timezones = ["America/New_York", "Europe/London", "Asia/Tokyo"]
        for i, tz in enumerate(timezones):
            state.apply_input(create_time_input(
                timezone=tz,
                format_preference="24h",
                timestamp=now + timedelta(hours=i),
            ))
        
        data = state.model_dump()
        restored = TimeState.model_validate(data)
        
        assert len(restored.settings_history) == len(state.settings_history)
        for i in range(len(state.settings_history)):
            assert restored.settings_history[i].timezone == state.settings_history[i].timezone
            assert restored.settings_history[i].format_preference == state.settings_history[i].format_preference


class TestTimeStateIntegration:
    """Integration tests for TimeState with multiple operations.
    
    TIME-SPECIFIC: Test realistic usage patterns.
    """

    def test_tracking_timezone_changes_during_travel(self):
        """Test tracking timezone changes during international travel."""
        departure_time = datetime.now(timezone.utc).replace(hour=8, minute=0)
        state = TimeState(
            timezone="America/New_York",
            format_preference="12h",
            last_updated=departure_time,
        )
        
        # Flight to London
        state.apply_input(create_time_input(
            timezone="Europe/London",
            format_preference="24h",
            timestamp=departure_time + timedelta(hours=8),
        ))
        
        # Train to Paris
        state.apply_input(create_time_input(
            timezone="Europe/Paris",
            format_preference="24h",
            timestamp=departure_time + timedelta(days=2),
        ))
        
        # Flight to Tokyo
        state.apply_input(create_time_input(
            timezone="Asia/Tokyo",
            format_preference="24h",
            timestamp=departure_time + timedelta(days=5),
        ))
        
        assert state.update_count == 3
        assert len(state.settings_history) == 3
        assert state.timezone == "Asia/Tokyo"

    def test_format_consistency_across_timezone_changes(self):
        """Test that time formatting works correctly after timezone changes."""
        state = create_time_state(
            timezone="America/New_York",
            format_preference="12h",
        )
        
        test_time = datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc)
        
        # Format in NY time
        ny_formatted = state.format_time(test_time)
        
        # Change to London time
        state.apply_input(create_time_input(
            timezone="Europe/London",
            format_preference="24h",
        ))
        
        # Format in London time
        london_formatted = state.format_time(test_time)
        
        # Times should be different (different timezones)
        assert ny_formatted != london_formatted

    def test_state_consistency_after_many_updates(self):
        """Test that state remains consistent after many updates."""
        state = create_time_state(max_history_size=20)
        
        timezones = [
            "UTC", "America/New_York", "Europe/London", "Asia/Tokyo",
            "Australia/Sydney", "America/Los_Angeles", "America/Chicago",
        ]
        
        # Apply 50 settings updates
        now = datetime.now(timezone.utc)
        for i in range(50):
            time_input = create_time_input(
                timezone=timezones[i % len(timezones)],
                format_preference="12h" if i % 2 == 0 else "24h",
                timestamp=now + timedelta(minutes=i),
            )
            state.apply_input(time_input)
        
        # Validate state consistency
        issues = state.validate_state()
        assert issues == []
        
        # Check history is properly managed
        assert len(state.settings_history) == 20
        assert state.update_count == 50
