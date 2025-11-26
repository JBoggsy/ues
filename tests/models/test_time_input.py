"""Unit tests for TimeInput.

This test suite covers:
1. General ModalityInput behavior (applicable to all modalities)
2. Time-specific validation and features
"""

from datetime import datetime, timezone

import pytest

from models.modalities.time_input import TimeInput
from tests.fixtures.modalities.time import (
    PARIS_INPUT,
    TOKYO_INPUT,
    UK_INPUT,
    US_EASTERN_INPUT,
    US_PACIFIC_INPUT,
    UTC_INPUT,
    create_time_input,
)


class TestTimeInputInstantiation:
    """Test TimeInput instantiation and basic properties.
    
    GENERAL PATTERN: All ModalityInput subclasses should test instantiation,
    default values, required fields, and proper inheritance from ModalityInput.
    """

    def test_instantiation_with_minimal_fields(self):
        """Test creating TimeInput with only required fields."""
        timestamp = datetime.now(timezone.utc)
        time_input = TimeInput(
            timezone="UTC",
            format_preference="12h",
            timestamp=timestamp,
        )
        
        assert time_input.timezone == "UTC"
        assert time_input.format_preference == "12h"
        assert time_input.timestamp == timestamp
        assert time_input.modality_type == "time"
        assert time_input.input_id is not None
        assert time_input.date_format is None
        assert time_input.locale is None
        assert time_input.week_start is None

    def test_instantiation_with_all_fields(self):
        """Test creating TimeInput with all optional fields."""
        timestamp = datetime.now(timezone.utc)
        time_input = TimeInput(
            timezone="America/New_York",
            format_preference="24h",
            date_format="MM/DD/YYYY",
            locale="en_US",
            week_start="sunday",
            timestamp=timestamp,
            input_id="test-id-123",
        )
        
        assert time_input.timezone == "America/New_York"
        assert time_input.format_preference == "24h"
        assert time_input.date_format == "MM/DD/YYYY"
        assert time_input.locale == "en_US"
        assert time_input.week_start == "sunday"
        assert time_input.input_id == "test-id-123"

    def test_instantiation_modality_type_is_frozen(self):
        """Test that modality_type cannot be changed after instantiation."""
        time_input = create_time_input()
        
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            time_input.modality_type = "other"

    def test_instantiation_auto_generates_input_id(self):
        """Test that input_id is auto-generated if not provided."""
        time_input1 = create_time_input()
        time_input2 = create_time_input()
        
        assert time_input1.input_id is not None
        assert time_input2.input_id is not None
        assert time_input1.input_id != time_input2.input_id


class TestTimeInputValidation:
    """Test TimeInput field validation.
    
    TIME-SPECIFIC: These tests verify timezone validation, format preferences,
    and date format validation which are unique to TimeInput.
    """

    def test_validate_timezone_valid_iana_identifiers(self):
        """Test that valid IANA timezone identifiers are accepted."""
        valid_timezones = [
            "UTC",
            "America/New_York",
            "America/Los_Angeles",
            "Europe/London",
            "Asia/Tokyo",
            "Australia/Sydney",
        ]
        
        for tz in valid_timezones:
            time_input = create_time_input(timezone=tz)
            assert time_input.timezone == tz

    def test_validate_timezone_invalid_identifier(self):
        """Test that invalid timezone identifiers are rejected."""
        with pytest.raises(ValueError, match="Invalid timezone"):
            create_time_input(timezone="Invalid/Timezone")

    def test_validate_timezone_empty_string(self):
        """Test that empty timezone string is rejected."""
        with pytest.raises(ValueError, match="Invalid timezone"):
            create_time_input(timezone="")

    def test_validate_format_preference_12h(self):
        """Test that 12h format preference is accepted."""
        time_input = create_time_input(format_preference="12h")
        assert time_input.format_preference == "12h"

    def test_validate_format_preference_24h(self):
        """Test that 24h format preference is accepted."""
        time_input = create_time_input(format_preference="24h")
        assert time_input.format_preference == "24h"

    def test_validate_format_preference_invalid_value(self):
        """Test that invalid format preference is rejected."""
        with pytest.raises(ValueError):
            create_time_input(format_preference="invalid")

    def test_validate_date_format_valid_formats(self):
        """Test that valid date formats are accepted."""
        valid_formats = [
            "MM/DD/YYYY",
            "DD/MM/YYYY",
            "YYYY-MM-DD",
            "YYYY/MM/DD",
            "DD.MM.YYYY",
            "DD-MM-YYYY",
        ]
        
        for fmt in valid_formats:
            time_input = create_time_input(date_format=fmt)
            assert time_input.date_format == fmt

    def test_validate_date_format_invalid_format(self):
        """Test that invalid date formats are rejected."""
        with pytest.raises(ValueError, match="Date format must be one of"):
            create_time_input(date_format="INVALID")

    def test_validate_date_format_none_is_allowed(self):
        """Test that None date_format is allowed."""
        time_input = create_time_input(date_format=None)
        assert time_input.date_format is None

    def test_validate_week_start_sunday(self):
        """Test that 'sunday' week start is accepted."""
        time_input = create_time_input(week_start="sunday")
        assert time_input.week_start == "sunday"

    def test_validate_week_start_monday(self):
        """Test that 'monday' week start is accepted."""
        time_input = create_time_input(week_start="monday")
        assert time_input.week_start == "monday"

    def test_validate_week_start_invalid_value(self):
        """Test that invalid week start is rejected."""
        with pytest.raises(ValueError):
            create_time_input(week_start="tuesday")


class TestTimeInputAbstractMethods:
    """Test implementation of ModalityInput abstract methods.
    
    GENERAL PATTERN: All ModalityInput subclasses must implement validate_input(),
    get_affected_entities(), get_summary(), and should_merge_with().
    """

    def test_validate_input_succeeds(self):
        """Test that validate_input() does not raise errors for valid input."""
        time_input = create_time_input()
        time_input.validate_input()  # Should not raise

    def test_get_affected_entities_returns_preferences(self):
        """Test get_affected_entities() returns user preferences entity."""
        time_input = create_time_input()
        entities = time_input.get_affected_entities()
        
        assert "user_time_preferences" in entities
        assert len(entities) == 1

    def test_get_summary_timezone_and_format_only(self):
        """Test get_summary() with only timezone and format."""
        time_input = create_time_input(
            timezone="America/New_York",
            format_preference="12h",
        )
        summary = time_input.get_summary()
        
        assert "America/New_York" in summary
        assert "12h" in summary

    def test_get_summary_with_date_format(self):
        """Test get_summary() includes date format when provided."""
        time_input = create_time_input(
            timezone="Europe/London",
            format_preference="24h",
            date_format="DD/MM/YYYY",
        )
        summary = time_input.get_summary()
        
        assert "Europe/London" in summary
        assert "24h" in summary
        assert "DD/MM/YYYY" in summary

    def test_get_summary_with_all_fields(self):
        """Test get_summary() with all optional fields."""
        time_input = create_time_input(
            timezone="Asia/Tokyo",
            format_preference="24h",
            date_format="YYYY-MM-DD",
            locale="ja_JP",
            week_start="monday",
        )
        summary = time_input.get_summary()
        
        assert "Asia/Tokyo" in summary or "timezone" in summary.lower()
        # Summary should be comprehensive but readable

    def test_should_merge_with_same_type_within_threshold(self):
        """Test that time settings within 5 seconds should merge."""
        timestamp = datetime.now(timezone.utc)
        time_input1 = create_time_input(
            timezone="UTC",
            timestamp=timestamp,
        )
        time_input2 = create_time_input(
            timezone="America/New_York",
            timestamp=timestamp,
        )
        
        assert time_input1.should_merge_with(time_input2)

    def test_should_merge_with_same_type_outside_threshold(self):
        """Test that time settings more than 5 seconds apart should not merge."""
        from datetime import timedelta
        
        timestamp1 = datetime.now(timezone.utc)
        timestamp2 = timestamp1 + timedelta(seconds=6)
        
        time_input1 = create_time_input(timestamp=timestamp1)
        time_input2 = create_time_input(timestamp=timestamp2)
        
        assert not time_input1.should_merge_with(time_input2)

    def test_should_merge_with_different_type(self):
        """Test that time settings should not merge with other modality types."""
        from models.modalities.location_input import LocationInput
        
        time_input = create_time_input()
        location_input = LocationInput(
            latitude=37.7749,
            longitude=-122.4194,
            timestamp=time_input.timestamp,
        )
        
        assert not time_input.should_merge_with(location_input)


class TestTimeInputSerialization:
    """Test TimeInput serialization and deserialization.
    
    GENERAL PATTERN: All ModalityInput subclasses should be serializable to/from
    JSON via Pydantic's model_dump() and model_validate().
    """

    def test_serialization_to_dict(self):
        """Test serializing TimeInput to dictionary."""
        time_input = create_time_input(
            timezone="America/New_York",
            format_preference="12h",
            date_format="MM/DD/YYYY",
            locale="en_US",
        )
        data = time_input.model_dump()
        
        assert data["timezone"] == "America/New_York"
        assert data["format_preference"] == "12h"
        assert data["date_format"] == "MM/DD/YYYY"
        assert data["locale"] == "en_US"
        assert data["modality_type"] == "time"

    def test_deserialization_from_dict(self):
        """Test deserializing TimeInput from dictionary."""
        timestamp = datetime.now(timezone.utc)
        data = {
            "timezone": "Europe/London",
            "format_preference": "24h",
            "date_format": "DD/MM/YYYY",
            "timestamp": timestamp,
            "modality_type": "time",
        }
        
        time_input = TimeInput.model_validate(data)
        
        assert time_input.timezone == "Europe/London"
        assert time_input.format_preference == "24h"
        assert time_input.date_format == "DD/MM/YYYY"

    def test_serialization_roundtrip(self):
        """Test that serialization and deserialization preserves data."""
        original = create_time_input(
            timezone="Asia/Tokyo",
            format_preference="24h",
            date_format="YYYY-MM-DD",
            locale="ja_JP",
            week_start="monday",
        )
        
        data = original.model_dump()
        restored = TimeInput.model_validate(data)
        
        assert restored.timezone == original.timezone
        assert restored.format_preference == original.format_preference
        assert restored.date_format == original.date_format
        assert restored.locale == original.locale
        assert restored.week_start == original.week_start

    def test_serialization_with_none_values(self):
        """Test serialization handles None optional fields correctly."""
        time_input = create_time_input(
            timezone="UTC",
            format_preference="12h",
            date_format=None,
            locale=None,
            week_start=None,
        )
        
        data = time_input.model_dump()
        restored = TimeInput.model_validate(data)
        
        assert restored.date_format is None
        assert restored.locale is None
        assert restored.week_start is None


class TestTimeInputFixtures:
    """Test the pre-built fixture time inputs.
    
    TIME-SPECIFIC: Verify that fixture data is correctly structured.
    """

    def test_utc_input_fixture(self):
        """Test UTC_INPUT fixture has expected values."""
        assert UTC_INPUT.timezone == "UTC"
        assert UTC_INPUT.format_preference == "24h"

    def test_us_eastern_input_fixture(self):
        """Test US_EASTERN_INPUT fixture has expected values."""
        assert US_EASTERN_INPUT.timezone == "America/New_York"
        assert US_EASTERN_INPUT.format_preference == "12h"
        assert US_EASTERN_INPUT.date_format == "MM/DD/YYYY"
        assert US_EASTERN_INPUT.locale == "en_US"

    def test_us_pacific_input_fixture(self):
        """Test US_PACIFIC_INPUT fixture has expected values."""
        assert US_PACIFIC_INPUT.timezone == "America/Los_Angeles"
        assert US_PACIFIC_INPUT.format_preference == "12h"

    def test_uk_input_fixture(self):
        """Test UK_INPUT fixture has expected values."""
        assert UK_INPUT.timezone == "Europe/London"
        assert UK_INPUT.format_preference == "24h"
        assert UK_INPUT.date_format == "DD/MM/YYYY"
        assert UK_INPUT.week_start == "monday"

    def test_tokyo_input_fixture(self):
        """Test TOKYO_INPUT fixture has expected values."""
        assert TOKYO_INPUT.timezone == "Asia/Tokyo"
        assert TOKYO_INPUT.format_preference == "24h"
        assert TOKYO_INPUT.locale == "ja_JP"

    def test_paris_input_fixture(self):
        """Test PARIS_INPUT fixture has expected values."""
        assert PARIS_INPUT.timezone == "Europe/Paris"
        assert PARIS_INPUT.format_preference == "24h"
        assert PARIS_INPUT.week_start == "monday"


class TestTimeInputEdgeCases:
    """Test edge cases and boundary conditions.
    
    TIME-SPECIFIC: Test unusual but valid configurations.
    """

    def test_multiple_timezone_changes_same_session(self):
        """Test creating multiple timezone changes in sequence."""
        timezones = [
            "America/New_York",
            "America/Chicago",
            "America/Denver",
            "America/Los_Angeles",
        ]
        
        inputs = [create_time_input(timezone=tz) for tz in timezones]
        
        for i, time_input in enumerate(inputs):
            assert time_input.timezone == timezones[i]

    def test_changing_only_format_preference(self):
        """Test changing only format preference, keeping timezone same."""
        time_input = create_time_input(
            timezone="UTC",
            format_preference="12h",
        )
        
        assert time_input.timezone == "UTC"
        assert time_input.format_preference == "12h"

    def test_all_date_formats_with_all_timezones(self):
        """Test that any date format works with any timezone."""
        date_formats = ["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD"]
        timezones = ["UTC", "America/New_York", "Asia/Tokyo"]
        
        for tz in timezones:
            for fmt in date_formats:
                time_input = create_time_input(
                    timezone=tz,
                    date_format=fmt,
                )
                assert time_input.timezone == tz
                assert time_input.date_format == fmt
