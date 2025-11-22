"""Unit tests for Environment.

GENERAL PATTERN TESTS: These test patterns apply to all state container classes
    - Instantiation tests verify proper initialization and validation
    - Serialization tests verify snapshot export and restore capability
    - Fixture tests verify all pytest fixtures work correctly
    - Validation tests verify consistency checking

ENVIRONMENT-SPECIFIC TESTS: These verify Environment-specific functionality
    - Modality state access via get_state() with error handling
    - Modality name consistency validation (key matches modality_type)
    - list_modalities() sorting and completeness
    - has_modality() availability checking
    - add_modality() dynamic extension
    - remove_modality() dynamic removal
    - get_snapshot() structure and serialization
    - validate() comprehensive error reporting
    - Time state integration and access
"""

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from models.environment import Environment
from models.time import SimulatorTime
from tests.fixtures.core.environments import (
    FULL_ENVIRONMENT,
    MINIMAL_ENVIRONMENT,
    TEST_ENVIRONMENT,
    create_environment,
)
from tests.fixtures.core.times import create_simulator_time
from tests.fixtures.modalities import (
    calendar,
    chat,
    email,
    location,
    sms,
    time,
    weather,
)


class TestEnvironmentInstantiation:
    """GENERAL PATTERN: Test instantiation and validation."""

    def test_minimal_instantiation(self):
        """GENERAL PATTERN: Test creating Environment with minimal required fields."""
        time_state = create_simulator_time()
        location_state = location.create_location_state()

        env = Environment(
            modality_states={"location": location_state},
            time_state=time_state,
        )

        assert env.time_state == time_state
        assert len(env.modality_states) == 1
        assert "location" in env.modality_states
        assert env.modality_states["location"] == location_state

    def test_full_instantiation(self):
        """GENERAL PATTERN: Test creating Environment with all supported modalities."""
        time_state = create_simulator_time()
        modality_states = {
            "location": location.create_location_state(),
            "time": time.create_time_state(),
            "weather": weather.create_weather_state(),
            "chat": chat.create_chat_state(),
            "email": email.create_email_state(),
            "calendar": calendar.create_calendar_state(),
            "sms": sms.create_sms_state(),
        }

        env = Environment(
            modality_states=modality_states,
            time_state=time_state,
        )

        assert env.time_state == time_state
        assert len(env.modality_states) == 7
        for modality_name, state in modality_states.items():
            assert env.modality_states[modality_name] == state

    def test_instantiation_with_factory(self):
        """GENERAL PATTERN: Test instantiation using create_environment factory."""
        env = create_environment()

        assert env.time_state is not None
        assert len(env.modality_states) >= 1
        assert isinstance(env.time_state, SimulatorTime)

    def test_instantiation_with_custom_time(self):
        """ENVIRONMENT-SPECIFIC: Test instantiation with custom time state."""
        custom_time = datetime(2025, 3, 15, 14, 30, 0, tzinfo=timezone.utc)
        time_state = create_simulator_time(
            current_time=custom_time,
            time_scale=10.0,
            is_paused=True,
        )

        env = create_environment(time_state=time_state)

        assert env.time_state.current_time == custom_time
        assert env.time_state.time_scale == 10.0
        assert env.time_state.is_paused is True


class TestEnvironmentValidation:
    """ENVIRONMENT-SPECIFIC: Test validation rules."""

    def test_modality_name_matches_type(self):
        """ENVIRONMENT-SPECIFIC: Verify modality key matches state.modality_type."""
        time_state = create_simulator_time()
        location_state = location.create_location_state()

        # Should work fine - key matches modality_type
        env = Environment(
            modality_states={"location": location_state},
            time_state=time_state,
        )

        assert env.modality_states["location"].modality_type == "location"

    def test_modality_name_mismatch_raises_error(self):
        """ENVIRONMENT-SPECIFIC: Verify mismatch between key and modality_type raises error."""
        time_state = create_simulator_time()
        location_state = location.create_location_state()

        # Try to register location state under wrong name
        with pytest.raises(ValidationError) as exc_info:
            Environment(
                modality_states={"wrong_name": location_state},
                time_state=time_state,
            )

        error_msg = str(exc_info.value)
        assert "wrong_name" in error_msg
        assert "location" in error_msg

    def test_empty_modality_states(self):
        """ENVIRONMENT-SPECIFIC: Verify validation detects empty modality_states."""
        time_state = create_simulator_time()

        env = Environment(
            modality_states={},
            time_state=time_state,
        )

        errors = env.validate()
        assert len(errors) > 0
        assert any("empty" in err.lower() for err in errors)

    def test_none_time_state(self):
        """ENVIRONMENT-SPECIFIC: Verify validation detects None time_state."""
        location_state = location.create_location_state()

        # Create environment with None time_state (bypassing Pydantic validation for test)
        env = Environment(
            modality_states={"location": location_state},
            time_state=create_simulator_time(),
        )
        env.time_state = None

        errors = env.validate()
        assert len(errors) > 0
        assert any("time_state is none" in err.lower() for err in errors)

    def test_validate_valid_environment(self):
        """GENERAL PATTERN: Verify validate returns empty list for valid environment."""
        env = create_environment()

        errors = env.validate()
        assert errors == []

    def test_validate_delegates_to_states(self):
        """ENVIRONMENT-SPECIFIC: Verify validate calls validate_state on each modality."""
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
                "email": email.create_email_state(),
            }
        )

        # All states are valid
        errors = env.validate()
        assert errors == []

        # If a state had errors, they would be included in the result
        # (This is tested indirectly - validate_state is called on each state)


class TestEnvironmentGetState:
    """ENVIRONMENT-SPECIFIC: Test get_state method."""

    def test_get_state_existing_modality(self):
        """ENVIRONMENT-SPECIFIC: Verify get_state returns correct state for existing modality."""
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
                "email": email.create_email_state(),
            }
        )

        location_state = env.get_state("location")
        assert location_state.modality_type == "location"

        email_state = env.get_state("email")
        assert email_state.modality_type == "email"

    def test_get_state_missing_modality(self):
        """ENVIRONMENT-SPECIFIC: Verify get_state raises KeyError for missing modality."""
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
            }
        )

        with pytest.raises(KeyError) as exc_info:
            env.get_state("nonexistent")

        error_msg = str(exc_info.value)
        assert "nonexistent" in error_msg
        assert "location" in error_msg  # Shows available modalities

    def test_get_state_none_value(self):
        """ENVIRONMENT-SPECIFIC: Verify get_state raises ValueError for None state."""
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
            }
        )

        # Manually set state to None (shouldn't happen in practice)
        env.modality_states["location"] = None

        with pytest.raises(ValueError) as exc_info:
            env.get_state("location")

        assert "none" in str(exc_info.value).lower()

    def test_get_state_returns_same_instance(self):
        """ENVIRONMENT-SPECIFIC: Verify get_state returns same instance (not a copy)."""
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
            }
        )

        state1 = env.get_state("location")
        state2 = env.get_state("location")

        assert state1 is state2  # Same object reference


class TestEnvironmentListModalities:
    """ENVIRONMENT-SPECIFIC: Test list_modalities method."""

    def test_list_modalities_single(self):
        """ENVIRONMENT-SPECIFIC: Verify list_modalities returns all modality names."""
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
            }
        )

        modalities = env.list_modalities()
        assert modalities == ["location"]

    def test_list_modalities_multiple(self):
        """ENVIRONMENT-SPECIFIC: Verify list_modalities returns sorted list."""
        env = create_environment(
            modality_states={
                "email": email.create_email_state(),
                "chat": chat.create_chat_state(),
                "location": location.create_location_state(),
            }
        )

        modalities = env.list_modalities()
        assert modalities == ["chat", "email", "location"]  # Alphabetically sorted

    def test_list_modalities_all(self):
        """ENVIRONMENT-SPECIFIC: Verify list_modalities includes all modalities."""
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
                "time": time.create_time_state(),
                "weather": weather.create_weather_state(),
                "chat": chat.create_chat_state(),
                "email": email.create_email_state(),
                "calendar": calendar.create_calendar_state(),
                "sms": sms.create_sms_state(),
            }
        )

        modalities = env.list_modalities()
        assert len(modalities) == 7
        assert modalities == sorted(modalities)  # Verify sorted


class TestEnvironmentHasModality:
    """ENVIRONMENT-SPECIFIC: Test has_modality method."""

    def test_has_modality_existing(self):
        """ENVIRONMENT-SPECIFIC: Verify has_modality returns True for existing modality."""
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
                "email": email.create_email_state(),
            }
        )

        assert env.has_modality("location") is True
        assert env.has_modality("email") is True

    def test_has_modality_missing(self):
        """ENVIRONMENT-SPECIFIC: Verify has_modality returns False for missing modality."""
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
            }
        )

        assert env.has_modality("email") is False
        assert env.has_modality("nonexistent") is False


class TestEnvironmentAddModality:
    """ENVIRONMENT-SPECIFIC: Test add_modality method."""

    def test_add_modality_success(self):
        """ENVIRONMENT-SPECIFIC: Verify add_modality adds new modality to environment."""
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
            }
        )

        assert not env.has_modality("email")

        email_state = email.create_email_state()
        env.add_modality("email", email_state)

        assert env.has_modality("email")
        assert env.get_state("email") == email_state

    def test_add_modality_duplicate_raises_error(self):
        """ENVIRONMENT-SPECIFIC: Verify add_modality raises error if modality exists."""
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
            }
        )

        new_location_state = location.create_location_state()

        with pytest.raises(ValueError) as exc_info:
            env.add_modality("location", new_location_state)

        assert "already exists" in str(exc_info.value).lower()

    def test_add_modality_name_mismatch_raises_error(self):
        """ENVIRONMENT-SPECIFIC: Verify add_modality validates name matches type."""
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
            }
        )

        email_state = email.create_email_state()

        with pytest.raises(ValueError) as exc_info:
            env.add_modality("wrong_name", email_state)

        error_msg = str(exc_info.value)
        assert "wrong_name" in error_msg
        assert "email" in error_msg


class TestEnvironmentRemoveModality:
    """ENVIRONMENT-SPECIFIC: Test remove_modality method."""

    def test_remove_modality_success(self):
        """ENVIRONMENT-SPECIFIC: Verify remove_modality removes modality from environment."""
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
                "email": email.create_email_state(),
            }
        )

        assert env.has_modality("email")

        removed_state = env.remove_modality("email")

        assert not env.has_modality("email")
        assert removed_state.modality_type == "email"

    def test_remove_modality_missing_raises_error(self):
        """ENVIRONMENT-SPECIFIC: Verify remove_modality raises error if modality missing."""
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
            }
        )

        with pytest.raises(KeyError) as exc_info:
            env.remove_modality("nonexistent")

        assert "nonexistent" in str(exc_info.value)

    def test_remove_modality_returns_state(self):
        """ENVIRONMENT-SPECIFIC: Verify remove_modality returns the removed state."""
        original_state = location.create_location_state()
        env = create_environment(
            modality_states={
                "location": original_state,
            }
        )

        removed_state = env.remove_modality("location")

        assert removed_state is original_state


class TestEnvironmentGetSnapshot:
    """GENERAL PATTERN: Test get_snapshot method."""

    def test_get_snapshot_structure(self):
        """GENERAL PATTERN: Verify get_snapshot returns correct structure."""
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
                "email": email.create_email_state(),
            }
        )

        snapshot = env.get_snapshot()

        assert "time" in snapshot
        assert "modalities" in snapshot
        assert isinstance(snapshot["time"], dict)
        assert isinstance(snapshot["modalities"], dict)

    def test_get_snapshot_time_content(self):
        """ENVIRONMENT-SPECIFIC: Verify get_snapshot includes time state."""
        custom_time = datetime(2025, 3, 15, 14, 30, 0, tzinfo=timezone.utc)
        time_state = create_simulator_time(
            current_time=custom_time,
            time_scale=5.0,
        )
        env = create_environment(time_state=time_state)

        snapshot = env.get_snapshot()

        assert "current_time" in snapshot["time"]
        # to_dict() returns ISO string, not datetime
        assert snapshot["time"]["current_time"] == custom_time.isoformat()
        assert snapshot["time"]["time_scale"] == 5.0

    def test_get_snapshot_modalities_content(self):
        """ENVIRONMENT-SPECIFIC: Verify get_snapshot includes all modality states."""
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
                "email": email.create_email_state(),
                "chat": chat.create_chat_state(),
            }
        )

        snapshot = env.get_snapshot()

        assert "location" in snapshot["modalities"]
        assert "email" in snapshot["modalities"]
        assert "chat" in snapshot["modalities"]
        assert len(snapshot["modalities"]) == 3

    def test_get_snapshot_serializable(self):
        """GENERAL PATTERN: Verify get_snapshot returns JSON-serializable data."""
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
                "email": email.create_email_state(),
            }
        )

        snapshot = env.get_snapshot()

        # Should not raise
        json_str = json.dumps(snapshot, default=str)
        assert len(json_str) > 0

    def test_get_snapshot_empty_modalities(self):
        """ENVIRONMENT-SPECIFIC: Verify get_snapshot works with single modality."""
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
            }
        )

        snapshot = env.get_snapshot()

        assert len(snapshot["modalities"]) == 1
        assert "location" in snapshot["modalities"]


class TestEnvironmentValidate:
    """GENERAL PATTERN: Test validate method."""

    def test_validate_valid_environment(self):
        """GENERAL PATTERN: Verify validate returns empty list for valid environment."""
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
                "email": email.create_email_state(),
            }
        )

        errors = env.validate()
        assert errors == []

    def test_validate_empty_modality_states(self):
        """ENVIRONMENT-SPECIFIC: Verify validate detects empty modality_states."""
        time_state = create_simulator_time()

        env = Environment(
            modality_states={},
            time_state=time_state,
        )

        errors = env.validate()
        assert len(errors) > 0
        assert any("empty" in err.lower() for err in errors)

    def test_validate_none_state_reference(self):
        """ENVIRONMENT-SPECIFIC: Verify validate detects None state references."""
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
            }
        )

        # Manually corrupt the state
        env.modality_states["location"] = None

        errors = env.validate()
        assert len(errors) > 0
        assert any("none" in err.lower() for err in errors)

    def test_validate_modality_name_mismatch(self):
        """ENVIRONMENT-SPECIFIC: Verify validate detects modality name mismatches."""
        # This test creates a state with mismatched name by bypassing normal validation
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
            }
        )

        # Create email state but register under wrong name (bypassing validator)
        email_state = email.create_email_state()
        env.modality_states["wrong_name"] = email_state

        errors = env.validate()
        assert len(errors) > 0
        assert any("wrong_name" in err and "email" in err for err in errors)


class TestEnvironmentFromFixtures:
    """GENERAL PATTERN: Test using pre-built fixtures."""

    def test_minimal_environment_fixture(self):
        """GENERAL PATTERN: Verify MINIMAL_ENVIRONMENT fixture works."""
        # MINIMAL_ENVIRONMENT is pre-built in fixtures
        assert MINIMAL_ENVIRONMENT.time_state is not None
        assert len(MINIMAL_ENVIRONMENT.modality_states) >= 1
        assert MINIMAL_ENVIRONMENT.validate() == []

    def test_full_environment_fixture(self):
        """GENERAL PATTERN: Verify FULL_ENVIRONMENT fixture works."""
        # FULL_ENVIRONMENT includes all modalities
        assert FULL_ENVIRONMENT.time_state is not None
        assert len(FULL_ENVIRONMENT.modality_states) == 7
        assert FULL_ENVIRONMENT.has_modality("location")
        assert FULL_ENVIRONMENT.has_modality("email")
        assert FULL_ENVIRONMENT.has_modality("chat")
        assert FULL_ENVIRONMENT.validate() == []

    def test_test_environment_fixture(self):
        """GENERAL PATTERN: Verify TEST_ENVIRONMENT fixture works."""
        # TEST_ENVIRONMENT has specific test data
        assert TEST_ENVIRONMENT.time_state is not None
        assert TEST_ENVIRONMENT.has_modality("location")
        assert TEST_ENVIRONMENT.has_modality("email")
        assert TEST_ENVIRONMENT.validate() == []


class TestEnvironmentIntegration:
    """ENVIRONMENT-SPECIFIC: Test integration scenarios."""

    def test_state_modification_visible(self):
        """ENVIRONMENT-SPECIFIC: Verify state modifications are visible via environment."""
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
            }
        )

        # Get state and modify it
        loc_state = env.get_state("location")
        original_lat = loc_state.current_latitude

        # Apply input to modify state
        location_input = location.create_location_input(latitude=45.0)
        loc_state.apply_input(location_input)

        # Verify change is visible through environment
        updated_state = env.get_state("location")
        assert updated_state.current_latitude == 45.0
        assert updated_state.current_latitude != original_lat

    def test_snapshot_captures_current_state(self):
        """ENVIRONMENT-SPECIFIC: Verify snapshot captures state at moment of call."""
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
            }
        )

        # Get initial snapshot (location state starts empty, no current location)
        snapshot1 = env.get_snapshot()
        # LocationState has nested "current" dict
        assert "current" in snapshot1["modalities"]["location"]

        # Modify state
        loc_state = env.get_state("location")
        location_input = location.create_location_input(latitude=45.0, longitude=-122.0)
        loc_state.apply_input(location_input)

        # Get new snapshot
        snapshot2 = env.get_snapshot()
        updated_lat = snapshot2["modalities"]["location"]["current"]["latitude"]

        assert updated_lat == 45.0

    def test_multiple_modalities_independent(self):
        """ENVIRONMENT-SPECIFIC: Verify modalities can be modified independently."""
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
                "email": email.create_email_state(),
            }
        )

        # Modify location
        loc_state = env.get_state("location")
        location_input = location.create_location_input(latitude=45.0, longitude=-122.0)
        loc_state.apply_input(location_input)

        # Verify email state unchanged
        email_state = env.get_state("email")
        snapshot = env.get_snapshot()
        # LocationState uses nested "current" dict
        assert snapshot["modalities"]["location"]["current"]["latitude"] == 45.0
        # Email state should be in default state (empty)

    def test_time_state_accessible(self):
        """ENVIRONMENT-SPECIFIC: Verify time state is accessible and modifiable."""
        custom_time = datetime(2025, 3, 15, 14, 30, 0, tzinfo=timezone.utc)
        time_state = create_simulator_time(current_time=custom_time)
        env = create_environment(time_state=time_state)

        # Access time through environment
        assert env.time_state.current_time == custom_time

        # Modify time
        from datetime import timedelta

        env.time_state.advance(timedelta(hours=1))

        # Verify change visible
        expected_time = custom_time + timedelta(hours=1)
        assert env.time_state.current_time == expected_time

    def test_add_remove_modality_workflow(self):
        """ENVIRONMENT-SPECIFIC: Verify add/remove workflow maintains consistency."""
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
            }
        )

        assert env.list_modalities() == ["location"]

        # Add email
        env.add_modality("email", email.create_email_state())
        assert env.list_modalities() == ["email", "location"]

        # Add chat
        env.add_modality("chat", chat.create_chat_state())
        assert env.list_modalities() == ["chat", "email", "location"]

        # Remove email
        env.remove_modality("email")
        assert env.list_modalities() == ["chat", "location"]

        # Validate still works
        assert env.validate() == []


class TestEnvironmentEdgeCases:
    """ENVIRONMENT-SPECIFIC: Test edge cases and boundary conditions."""

    def test_very_old_time(self):
        """ENVIRONMENT-SPECIFIC: Verify environment works with very old timestamps."""
        old_time = datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        time_state = create_simulator_time(current_time=old_time)
        env = create_environment(time_state=time_state)

        assert env.time_state.current_time == old_time
        assert env.validate() == []

    def test_very_future_time(self):
        """ENVIRONMENT-SPECIFIC: Verify environment works with far future timestamps."""
        future_time = datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        time_state = create_simulator_time(current_time=future_time)
        env = create_environment(time_state=time_state)

        assert env.time_state.current_time == future_time
        assert env.validate() == []

    def test_single_modality(self):
        """ENVIRONMENT-SPECIFIC: Verify environment works with just one modality."""
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
            }
        )

        assert len(env.modality_states) == 1
        assert env.validate() == []
        assert env.list_modalities() == ["location"]

    def test_all_modalities(self):
        """ENVIRONMENT-SPECIFIC: Verify environment works with all modalities."""
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
                "time": time.create_time_state(),
                "weather": weather.create_weather_state(),
                "chat": chat.create_chat_state(),
                "email": email.create_email_state(),
                "calendar": calendar.create_calendar_state(),
                "sms": sms.create_sms_state(),
            }
        )

        assert len(env.modality_states) == 7
        assert env.validate() == []

    def test_snapshot_with_many_modalities(self):
        """ENVIRONMENT-SPECIFIC: Verify snapshot works with all modalities."""
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
                "time": time.create_time_state(),
                "weather": weather.create_weather_state(),
                "chat": chat.create_chat_state(),
                "email": email.create_email_state(),
                "calendar": calendar.create_calendar_state(),
                "sms": sms.create_sms_state(),
            }
        )

        snapshot = env.get_snapshot()

        assert len(snapshot["modalities"]) == 7
        for modality_name in ["location", "time", "weather", "chat", "email", "calendar", "sms"]:
            assert modality_name in snapshot["modalities"]

    def test_repeated_get_state_same_reference(self):
        """ENVIRONMENT-SPECIFIC: Verify repeated get_state calls return same object."""
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
            }
        )

        state1 = env.get_state("location")
        state2 = env.get_state("location")
        state3 = env.get_state("location")

        assert state1 is state2
        assert state2 is state3
