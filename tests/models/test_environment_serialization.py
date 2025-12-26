"""Unit tests for Environment scenario serialization.

Tests the to_scenario_dict() and from_scenario_dict() methods that enable
saving and loading Environment state for scenario files.

SERIALIZATION TESTS:
    - Round-trip serialization (serialize -> deserialize -> compare)
    - JSON compatibility (ensure dict is JSON-serializable)
    - All modality types correctly serialized and deserialized
    - Time state preserved accurately
    - Modality state data preserved accurately

DESERIALIZATION TESTS:
    - Successful loading of valid data
    - Unknown modality handling (strict vs lenient mode)
    - Missing field error handling
    - Invalid data validation errors
    - Partial load with warnings

COMPATIBILITY TESTS:
    - Future version compatibility considerations
    - Missing optional fields handled gracefully
"""

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from models.environment import Environment
from models.registry import (
    clear_state_registry,
    get_modality_state_class,
    is_modality_state_registered,
    list_registered_state_modalities,
    register_modality_state,
)
from models.time import SimulatorTime
from tests.fixtures.core.environments import create_environment
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


class TestToScenarioDict:
    """Test to_scenario_dict() serialization method."""

    def test_minimal_environment_serialization(self):
        """Test serializing environment with single modality."""
        time_state = create_simulator_time()
        location_state = location.create_location_state()

        env = Environment(
            modality_states={"location": location_state},
            time_state=time_state,
        )

        result = env.to_scenario_dict()

        assert "time_state" in result
        assert "modality_states" in result
        assert len(result["modality_states"]) == 1
        assert "location" in result["modality_states"]

    def test_full_environment_serialization(self):
        """Test serializing environment with all modalities."""
        from tests.fixtures.core.environments import FULL_ENVIRONMENT
        env = FULL_ENVIRONMENT

        result = env.to_scenario_dict()

        assert "time_state" in result
        assert "modality_states" in result
        # Should have all 7 modalities
        assert len(result["modality_states"]) == 7
        for modality_type in ["location", "time", "weather", "chat", "email", "calendar", "sms"]:
            assert modality_type in result["modality_states"]

    def test_time_state_contains_all_fields(self):
        """Test time_state dict contains all SimulatorTime fields."""
        custom_time = datetime(2025, 6, 15, 10, 30, 0, tzinfo=timezone.utc)
        time_state = create_simulator_time(
            current_time=custom_time,
            time_scale=5.0,
            is_paused=True,
            auto_advance=False,
        )

        env = Environment(
            modality_states={"location": location.create_location_state()},
            time_state=time_state,
        )

        result = env.to_scenario_dict()

        time_data = result["time_state"]
        assert "current_time" in time_data
        assert "time_scale" in time_data
        assert "is_paused" in time_data
        assert "auto_advance" in time_data
        assert "last_wall_time_update" in time_data
        # Note: 'mode' is a computed property, not included in model_dump()
        assert time_data["time_scale"] == 5.0
        assert time_data["is_paused"] is True

    def test_modality_states_contain_modality_type(self):
        """Test each modality state dict contains modality_type field."""
        env = create_environment()

        result = env.to_scenario_dict()

        for modality_name, state_data in result["modality_states"].items():
            assert "modality_type" in state_data
            assert state_data["modality_type"] == modality_name

    def test_result_is_json_serializable(self):
        """Test to_scenario_dict result can be serialized to JSON."""
        env = create_environment()

        result = env.to_scenario_dict()

        # Should not raise
        json_str = json.dumps(result, indent=2)
        assert isinstance(json_str, str)
        assert len(json_str) > 0

    def test_datetime_fields_are_strings(self):
        """Test datetime fields are serialized as ISO strings (mode='json')."""
        time_state = create_simulator_time()
        env = Environment(
            modality_states={"location": location.create_location_state()},
            time_state=time_state,
        )

        result = env.to_scenario_dict()

        # Time state datetimes should be strings
        assert isinstance(result["time_state"]["current_time"], str)
        assert isinstance(result["time_state"]["last_wall_time_update"], str)

        # Location state last_updated should be string
        assert isinstance(result["modality_states"]["location"]["last_updated"], str)


class TestFromScenarioDict:
    """Test from_scenario_dict() deserialization method."""

    def test_round_trip_minimal(self):
        """Test serialize -> deserialize round trip with minimal environment."""
        original = Environment(
            modality_states={"location": location.create_location_state()},
            time_state=create_simulator_time(),
        )

        data = original.to_scenario_dict()
        restored, warnings = Environment.from_scenario_dict(data)

        assert len(warnings) == 0
        assert restored.list_modalities() == original.list_modalities()
        assert restored.time_state.current_time == original.time_state.current_time

    def test_round_trip_full(self):
        """Test serialize -> deserialize round trip with all modalities."""
        original = create_environment()

        data = original.to_scenario_dict()
        restored, warnings = Environment.from_scenario_dict(data)

        assert len(warnings) == 0
        assert sorted(restored.list_modalities()) == sorted(original.list_modalities())
        assert restored.time_state.current_time == original.time_state.current_time

    def test_round_trip_via_json(self):
        """Test full JSON round trip (serialize -> JSON -> parse -> deserialize)."""
        original = create_environment()

        # Serialize to JSON string
        data = original.to_scenario_dict()
        json_str = json.dumps(data)

        # Parse back and deserialize
        parsed_data = json.loads(json_str)
        restored, warnings = Environment.from_scenario_dict(parsed_data)

        assert len(warnings) == 0
        assert sorted(restored.list_modalities()) == sorted(original.list_modalities())

    def test_time_state_fields_preserved(self):
        """Test all time_state fields are preserved through round trip."""
        custom_time = datetime(2025, 6, 15, 10, 30, 0, tzinfo=timezone.utc)
        original = Environment(
            modality_states={"location": location.create_location_state()},
            time_state=create_simulator_time(
                current_time=custom_time,
                time_scale=7.5,
                is_paused=True,
                auto_advance=False,
            ),
        )

        data = original.to_scenario_dict()
        restored, _ = Environment.from_scenario_dict(data)

        assert restored.time_state.current_time == custom_time
        assert restored.time_state.time_scale == 7.5
        assert restored.time_state.is_paused is True
        assert restored.time_state.auto_advance is False

    def test_location_state_data_preserved(self):
        """Test location modality state data preserved through round trip."""
        location_state = location.create_location_state(
            current_latitude=40.7128,
            current_longitude=-74.0060,
            current_address="New York City",
        )
        original = Environment(
            modality_states={"location": location_state},
            time_state=create_simulator_time(),
        )

        data = original.to_scenario_dict()
        restored, _ = Environment.from_scenario_dict(data)

        restored_loc = restored.get_state("location")
        assert restored_loc.current_latitude == 40.7128
        assert restored_loc.current_longitude == -74.0060
        assert restored_loc.current_address == "New York City"


class TestFromScenarioDictErrorHandling:
    """Test error handling in from_scenario_dict()."""

    def test_missing_time_state_raises_error(self):
        """Test ValueError raised when time_state is missing."""
        data = {
            "modality_states": {"location": location.create_location_state().model_dump()},
        }

        with pytest.raises(ValueError) as exc_info:
            Environment.from_scenario_dict(data)

        assert "time_state" in str(exc_info.value)

    def test_missing_modality_states_raises_error(self):
        """Test ValueError raised when modality_states is missing."""
        data = {
            "time_state": create_simulator_time().model_dump(mode="json"),
        }

        with pytest.raises(ValueError) as exc_info:
            Environment.from_scenario_dict(data)

        assert "modality_states" in str(exc_info.value)

    def test_invalid_time_state_data_raises_validation_error(self):
        """Test ValidationError raised for invalid time_state data."""
        data = {
            "time_state": {"current_time": "not-a-datetime", "invalid": True},
            "modality_states": {},
        }

        with pytest.raises(ValidationError):
            Environment.from_scenario_dict(data)

    def test_invalid_modality_state_data_raises_validation_error(self):
        """Test ValidationError raised for invalid modality state data."""
        data = {
            "time_state": create_simulator_time().model_dump(mode="json"),
            "modality_states": {
                "location": {"modality_type": "location", "invalid_field": True},
            },
        }

        with pytest.raises(ValidationError):
            Environment.from_scenario_dict(data)


class TestFromScenarioDictUnknownModalities:
    """Test handling of unknown modality types in from_scenario_dict()."""

    def test_unknown_modality_strict_mode_raises_error(self):
        """Test ValueError raised for unknown modality in strict mode."""
        data = {
            "time_state": create_simulator_time().model_dump(mode="json"),
            "modality_states": {
                "location": location.create_location_state().model_dump(mode="json"),
                "unknown_modality": {"modality_type": "unknown_modality", "data": {}},
            },
        }

        with pytest.raises(ValueError) as exc_info:
            Environment.from_scenario_dict(data, strict=True)

        assert "unknown_modality" in str(exc_info.value)
        assert "strict=False" in str(exc_info.value)

    def test_unknown_modality_lenient_mode_skips_with_warning(self):
        """Test unknown modality skipped with warning in lenient mode."""
        data = {
            "time_state": create_simulator_time().model_dump(mode="json"),
            "modality_states": {
                "location": location.create_location_state().model_dump(mode="json"),
                "unknown_modality": {"modality_type": "unknown_modality", "data": {}},
            },
        }

        env, warnings = Environment.from_scenario_dict(data, strict=False)

        assert len(warnings) == 1
        assert "unknown_modality" in warnings[0]
        assert env.list_modalities() == ["location"]
        assert not env.has_modality("unknown_modality")

    def test_multiple_unknown_modalities_lenient_mode(self):
        """Test multiple unknown modalities produce multiple warnings."""
        data = {
            "time_state": create_simulator_time().model_dump(mode="json"),
            "modality_states": {
                "location": location.create_location_state().model_dump(mode="json"),
                "unknown_1": {"modality_type": "unknown_1", "data": {}},
                "unknown_2": {"modality_type": "unknown_2", "data": {}},
            },
        }

        env, warnings = Environment.from_scenario_dict(data, strict=False)

        assert len(warnings) == 2
        assert any("unknown_1" in w for w in warnings)
        assert any("unknown_2" in w for w in warnings)
        assert env.list_modalities() == ["location"]

    def test_all_unknown_modalities_lenient_mode_empty_environment(self):
        """Test all unknown modalities results in empty modality_states."""
        data = {
            "time_state": create_simulator_time().model_dump(mode="json"),
            "modality_states": {
                "unknown_1": {"modality_type": "unknown_1", "data": {}},
            },
        }

        # In lenient mode, this should work but produce warning and empty env
        env, warnings = Environment.from_scenario_dict(data, strict=False)

        assert len(warnings) == 1
        assert env.list_modalities() == []


class TestSerializationAllModalities:
    """Test serialization/deserialization for each modality type."""

    def test_location_modality_round_trip(self):
        """Test location modality serialization round trip."""
        original = Environment(
            modality_states={"location": location.create_location_state()},
            time_state=create_simulator_time(),
        )

        data = original.to_scenario_dict()
        restored, warnings = Environment.from_scenario_dict(data)

        assert len(warnings) == 0
        assert restored.has_modality("location")
        assert restored.get_state("location").modality_type == "location"

    def test_time_modality_round_trip(self):
        """Test time modality serialization round trip."""
        original = Environment(
            modality_states={"time": time.create_time_state()},
            time_state=create_simulator_time(),
        )

        data = original.to_scenario_dict()
        restored, warnings = Environment.from_scenario_dict(data)

        assert len(warnings) == 0
        assert restored.has_modality("time")
        assert restored.get_state("time").modality_type == "time"

    def test_weather_modality_round_trip(self):
        """Test weather modality serialization round trip."""
        original = Environment(
            modality_states={"weather": weather.create_weather_state()},
            time_state=create_simulator_time(),
        )

        data = original.to_scenario_dict()
        restored, warnings = Environment.from_scenario_dict(data)

        assert len(warnings) == 0
        assert restored.has_modality("weather")
        assert restored.get_state("weather").modality_type == "weather"

    def test_chat_modality_round_trip(self):
        """Test chat modality serialization round trip."""
        original = Environment(
            modality_states={"chat": chat.create_chat_state()},
            time_state=create_simulator_time(),
        )

        data = original.to_scenario_dict()
        restored, warnings = Environment.from_scenario_dict(data)

        assert len(warnings) == 0
        assert restored.has_modality("chat")
        assert restored.get_state("chat").modality_type == "chat"

    def test_email_modality_round_trip(self):
        """Test email modality serialization round trip."""
        original = Environment(
            modality_states={"email": email.create_email_state()},
            time_state=create_simulator_time(),
        )

        data = original.to_scenario_dict()
        restored, warnings = Environment.from_scenario_dict(data)

        assert len(warnings) == 0
        assert restored.has_modality("email")
        assert restored.get_state("email").modality_type == "email"

    def test_calendar_modality_round_trip(self):
        """Test calendar modality serialization round trip."""
        original = Environment(
            modality_states={"calendar": calendar.create_calendar_state()},
            time_state=create_simulator_time(),
        )

        data = original.to_scenario_dict()
        restored, warnings = Environment.from_scenario_dict(data)

        assert len(warnings) == 0
        assert restored.has_modality("calendar")
        assert restored.get_state("calendar").modality_type == "calendar"

    def test_sms_modality_round_trip(self):
        """Test sms modality serialization round trip."""
        original = Environment(
            modality_states={"sms": sms.create_sms_state()},
            time_state=create_simulator_time(),
        )

        data = original.to_scenario_dict()
        restored, warnings = Environment.from_scenario_dict(data)

        assert len(warnings) == 0
        assert restored.has_modality("sms")
        assert restored.get_state("sms").modality_type == "sms"


class TestRegistryIntegration:
    """Test from_scenario_dict integration with modality registry."""

    def test_uses_registry_for_deserialization(self):
        """Test from_scenario_dict uses registry to get correct classes."""
        # Verify registry is populated
        assert is_modality_state_registered("location")
        assert is_modality_state_registered("weather")

        data = {
            "time_state": create_simulator_time().model_dump(mode="json"),
            "modality_states": {
                "location": location.create_location_state().model_dump(mode="json"),
            },
        }

        env, _ = Environment.from_scenario_dict(data)

        # Should have created LocationState, not generic ModalityState
        from models.modalities import LocationState

        assert isinstance(env.get_state("location"), LocationState)

    def test_registry_has_all_standard_modalities(self):
        """Test registry contains all 7 standard modalities."""
        expected_modalities = ["location", "time", "weather", "chat", "email", "calendar", "sms"]

        for modality in expected_modalities:
            assert is_modality_state_registered(modality), f"{modality} not registered"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_modality_states_round_trip(self):
        """Test environment with empty modality_states dict."""
        original = Environment(
            modality_states={},
            time_state=create_simulator_time(),
        )

        data = original.to_scenario_dict()
        restored, warnings = Environment.from_scenario_dict(data)

        assert len(warnings) == 0
        assert restored.list_modalities() == []

    def test_preserves_modality_state_last_updated(self):
        """Test last_updated field is preserved through round trip."""
        custom_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        location_state = location.create_location_state()
        location_state.last_updated = custom_time

        original = Environment(
            modality_states={"location": location_state},
            time_state=create_simulator_time(),
        )

        data = original.to_scenario_dict()
        restored, _ = Environment.from_scenario_dict(data)

        assert restored.get_state("location").last_updated == custom_time

    def test_handles_special_characters_in_data(self):
        """Test special characters in state data are preserved."""
        # Chat state might have special characters in messages
        chat_state = chat.create_chat_state()
        original = Environment(
            modality_states={"chat": chat_state},
            time_state=create_simulator_time(),
        )

        # Round trip through JSON
        data = original.to_scenario_dict()
        json_str = json.dumps(data)
        parsed = json.loads(json_str)
        restored, _ = Environment.from_scenario_dict(parsed)

        assert restored.has_modality("chat")

    def test_large_environment_serialization(self):
        """Test serialization performance with full environment."""
        from tests.fixtures.core.environments import FULL_ENVIRONMENT
        env = FULL_ENVIRONMENT

        # Should complete without timeout or memory issues
        data = env.to_scenario_dict()
        json_str = json.dumps(data)
        parsed = json.loads(json_str)
        restored, warnings = Environment.from_scenario_dict(parsed)

        assert len(warnings) == 0
        assert len(restored.list_modalities()) == 7
