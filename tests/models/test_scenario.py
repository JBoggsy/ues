"""Unit tests for Scenario model.

Tests the Scenario and ScenarioMetadata classes that enable
saving and loading complete simulation scenarios.

SCENARIO MODEL TESTS:
    - ScenarioMetadata creation and validation
    - Scenario.create() factory method
    - JSON serialization/deserialization round-trip
    - Dict serialization/deserialization
    - get_environment() and get_event_queue() convenience methods
    - Version compatibility checking
    - Summary generation

INTEGRATION TESTS:
    - Full round-trip with actual Environment and EventQueue
    - File I/O simulation
"""

import json
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from ues.models.scenario import (
    Scenario,
    ScenarioMetadata,
    SCENARIO_FORMAT_VERSION,
    UES_VERSION,
)
from ues.models.environment import Environment
from ues.models.queue import EventQueue
from tests.fixtures.core.environments import create_environment
from tests.fixtures.core.events import create_simulator_event
from tests.fixtures.core.queues import create_event_queue
from tests.fixtures.core.times import create_simulator_time


class TestScenarioMetadata:
    """Test ScenarioMetadata model."""

    def test_metadata_creation(self):
        """Test creating ScenarioMetadata with required fields."""
        now = datetime.now(timezone.utc)
        metadata = ScenarioMetadata(
            ues_version="0.1.0",
            created_at=now,
        )

        assert metadata.ues_version == "0.1.0"
        assert metadata.scenario_version == SCENARIO_FORMAT_VERSION
        assert metadata.created_at == now
        assert metadata.author is None
        assert metadata.description is None

    def test_metadata_with_all_fields(self):
        """Test creating ScenarioMetadata with all optional fields."""
        now = datetime.now(timezone.utc)
        metadata = ScenarioMetadata(
            ues_version="1.0.0",
            scenario_version="2",
            created_at=now,
            author="Test Author",
            description="Test description for this scenario",
        )

        assert metadata.ues_version == "1.0.0"
        assert metadata.scenario_version == "2"
        assert metadata.author == "Test Author"
        assert metadata.description == "Test description for this scenario"

    def test_metadata_missing_required_fields(self):
        """Test that missing required fields raises ValidationError."""
        with pytest.raises(ValidationError):
            ScenarioMetadata()  # Missing ues_version and created_at

    def test_metadata_serialization(self):
        """Test ScenarioMetadata serializes to JSON-compatible dict."""
        now = datetime.now(timezone.utc)
        metadata = ScenarioMetadata(
            ues_version="0.1.0",
            created_at=now,
            author="Test",
        )

        data = metadata.model_dump(mode="json")

        assert isinstance(data["created_at"], str)
        assert data["ues_version"] == "0.1.0"
        assert data["author"] == "Test"


class TestScenarioCreate:
    """Test Scenario.create() factory method."""

    def test_create_minimal_scenario(self):
        """Test creating scenario with minimal arguments."""
        env = create_environment()
        queue = EventQueue()

        scenario = Scenario.create(
            environment=env,
            event_queue=queue,
        )

        assert scenario.metadata.ues_version == UES_VERSION
        assert scenario.metadata.scenario_version == SCENARIO_FORMAT_VERSION
        assert scenario.metadata.author is None
        assert scenario.metadata.description is None
        assert "time_state" in scenario.environment
        assert "modality_states" in scenario.environment
        assert "events" in scenario.events

    def test_create_with_author_and_description(self):
        """Test creating scenario with author and description."""
        env = create_environment()
        queue = EventQueue()

        scenario = Scenario.create(
            environment=env,
            event_queue=queue,
            author="Test Author",
            description="A test scenario",
        )

        assert scenario.metadata.author == "Test Author"
        assert scenario.metadata.description == "A test scenario"

    def test_create_sets_created_at_automatically(self):
        """Test that create() sets created_at to current time."""
        before = datetime.now(timezone.utc)
        
        env = create_environment()
        queue = EventQueue()
        scenario = Scenario.create(environment=env, event_queue=queue)
        
        after = datetime.now(timezone.utc)

        assert before <= scenario.metadata.created_at <= after

    def test_create_with_events(self):
        """Test creating scenario with events in the queue."""
        env = create_environment()
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        events = [
            create_simulator_event(scheduled_time=now + timedelta(hours=1)),
            create_simulator_event(scheduled_time=now + timedelta(hours=2)),
        ]
        queue = EventQueue(events=events)

        scenario = Scenario.create(environment=env, event_queue=queue)

        assert len(scenario.events["events"]) == 2


class TestScenarioJsonSerialization:
    """Test Scenario JSON serialization/deserialization."""

    def test_to_json_produces_valid_json(self):
        """Test to_json() produces valid JSON string."""
        env = create_environment()
        queue = EventQueue()
        scenario = Scenario.create(environment=env, event_queue=queue)

        json_str = scenario.to_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert "metadata" in parsed
        assert "environment" in parsed
        assert "events" in parsed

    def test_to_json_with_custom_indent(self):
        """Test to_json() respects indent parameter."""
        env = create_environment()
        queue = EventQueue()
        scenario = Scenario.create(environment=env, event_queue=queue)

        json_4 = scenario.to_json(indent=4)
        json_0 = scenario.to_json(indent=0)

        # Different indentation produces different output
        assert len(json_4) != len(json_0)

    def test_from_json_round_trip(self):
        """Test JSON round trip preserves data."""
        env = create_environment()
        queue = EventQueue()
        original = Scenario.create(
            environment=env,
            event_queue=queue,
            author="Test",
            description="Test scenario",
        )

        json_str = original.to_json()
        restored = Scenario.from_json(json_str)

        assert restored.metadata.ues_version == original.metadata.ues_version
        assert restored.metadata.author == original.metadata.author
        assert restored.metadata.description == original.metadata.description

    def test_from_json_invalid_json_raises_error(self):
        """Test from_json() raises error for invalid JSON."""
        with pytest.raises(Exception):  # Could be JSONDecodeError or ValidationError
            Scenario.from_json("not valid json {{{")

    def test_from_json_missing_fields_raises_error(self):
        """Test from_json() raises error for missing required fields."""
        with pytest.raises(ValidationError):
            Scenario.from_json('{"metadata": {}}')


class TestScenarioDictSerialization:
    """Test Scenario dict serialization/deserialization."""

    def test_to_dict_produces_json_serializable_dict(self):
        """Test to_dict() produces JSON-serializable dictionary."""
        env = create_environment()
        queue = EventQueue()
        scenario = Scenario.create(environment=env, event_queue=queue)

        data = scenario.to_dict()

        # Should be JSON-serializable
        json_str = json.dumps(data)
        assert isinstance(json_str, str)

    def test_from_dict_round_trip(self):
        """Test dict round trip preserves data."""
        env = create_environment()
        queue = EventQueue()
        original = Scenario.create(environment=env, event_queue=queue)

        data = original.to_dict()
        restored = Scenario.from_dict(data)

        assert restored.metadata.ues_version == original.metadata.ues_version

    def test_from_dict_via_json_parse(self):
        """Test from_dict() works with parsed JSON."""
        env = create_environment()
        queue = EventQueue()
        original = Scenario.create(environment=env, event_queue=queue)

        json_str = original.to_json()
        parsed = json.loads(json_str)
        restored = Scenario.from_dict(parsed)

        assert restored.metadata.ues_version == original.metadata.ues_version


class TestScenarioConvenienceMethods:
    """Test get_environment() and get_event_queue() methods."""

    def test_get_environment_returns_environment(self):
        """Test get_environment() deserializes to Environment."""
        original_env = create_environment()
        queue = EventQueue()
        scenario = Scenario.create(environment=original_env, event_queue=queue)

        # Round trip through JSON
        json_str = scenario.to_json()
        restored_scenario = Scenario.from_json(json_str)
        env, warnings = restored_scenario.get_environment()

        assert isinstance(env, Environment)
        assert len(warnings) == 0

    def test_get_environment_with_strict_false(self):
        """Test get_environment() with strict=False skips unknown modalities."""
        original_env = create_environment()
        queue = EventQueue()
        scenario = Scenario.create(environment=original_env, event_queue=queue)

        # Manually inject unknown modality
        scenario.environment["modality_states"]["unknown"] = {"modality_type": "unknown"}

        env, warnings = scenario.get_environment(strict=False)

        assert isinstance(env, Environment)
        assert len(warnings) == 1
        assert "unknown" in warnings[0]

    def test_get_event_queue_returns_event_queue(self):
        """Test get_event_queue() deserializes to EventQueue."""
        env = create_environment()
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        original_queue = EventQueue(events=[
            create_simulator_event(scheduled_time=now + timedelta(hours=1)),
        ])
        scenario = Scenario.create(environment=env, event_queue=original_queue)

        # Round trip through JSON
        json_str = scenario.to_json()
        restored_scenario = Scenario.from_json(json_str)
        queue = restored_scenario.get_event_queue()

        assert isinstance(queue, EventQueue)
        assert len(queue.events) == 1

    def test_get_event_queue_regenerates_ids_by_default(self):
        """Test get_event_queue() regenerates IDs by default."""
        env = create_environment()
        original_queue = EventQueue(events=[create_simulator_event()])
        original_id = original_queue.events[0].event_id
        scenario = Scenario.create(environment=env, event_queue=original_queue)

        json_str = scenario.to_json()
        restored_scenario = Scenario.from_json(json_str)
        queue = restored_scenario.get_event_queue()

        assert queue.events[0].event_id != original_id

    def test_get_event_queue_preserves_ids_when_disabled(self):
        """Test get_event_queue() preserves IDs when regenerate_ids=False."""
        env = create_environment()
        original_queue = EventQueue(events=[create_simulator_event()])
        original_id = original_queue.events[0].event_id
        scenario = Scenario.create(environment=env, event_queue=original_queue)

        json_str = scenario.to_json()
        restored_scenario = Scenario.from_json(json_str)
        queue = restored_scenario.get_event_queue(regenerate_ids=False)

        assert queue.events[0].event_id == original_id


class TestVersionCompatibility:
    """Test version compatibility checking."""

    def test_is_compatible_same_version(self):
        """Test is_compatible returns True for same major version."""
        env = create_environment()
        queue = EventQueue()
        scenario = Scenario.create(environment=env, event_queue=queue)

        assert scenario.is_compatible is True

    def test_is_compatible_different_minor_version(self):
        """Test is_compatible returns True for different minor version."""
        env = create_environment()
        queue = EventQueue()
        scenario = Scenario.create(environment=env, event_queue=queue)
        # Simulate a different minor version
        scenario.metadata.ues_version = "0.2.0"  # Same major (0)

        assert scenario.is_compatible is True

    def test_is_compatible_different_major_version(self):
        """Test is_compatible returns False for different major version."""
        env = create_environment()
        queue = EventQueue()
        scenario = Scenario.create(environment=env, event_queue=queue)
        # Simulate a different major version
        scenario.metadata.ues_version = "1.0.0"  # Different major

        # Only compatible if major version matches
        # Current UES_VERSION is 0.x.x
        assert scenario.is_compatible is False


class TestScenarioSummary:
    """Test scenario summary property."""

    def test_summary_basic_fields(self):
        """Test summary includes basic metadata fields."""
        env = create_environment()
        queue = EventQueue()
        scenario = Scenario.create(
            environment=env,
            event_queue=queue,
            author="Test Author",
            description="Test description",
        )

        summary = scenario.summary

        assert summary["ues_version"] == UES_VERSION
        assert summary["scenario_version"] == SCENARIO_FORMAT_VERSION
        assert summary["author"] == "Test Author"
        assert summary["description"] == "Test description"
        assert "created_at" in summary
        assert "is_compatible" in summary

    def test_summary_counts_modalities(self):
        """Test summary includes modality count."""
        from tests.fixtures.core.environments import FULL_ENVIRONMENT
        
        queue = EventQueue()
        scenario = Scenario.create(environment=FULL_ENVIRONMENT, event_queue=queue)

        summary = scenario.summary

        assert summary["modality_count"] == 8  # All 8 modalities

    def test_summary_counts_events(self):
        """Test summary includes event count."""
        env = create_environment()
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        queue = EventQueue(events=[
            create_simulator_event(scheduled_time=now + timedelta(hours=1)),
            create_simulator_event(scheduled_time=now + timedelta(hours=2)),
            create_simulator_event(scheduled_time=now + timedelta(hours=3)),
        ])
        scenario = Scenario.create(environment=env, event_queue=queue)

        summary = scenario.summary

        assert summary["event_count"] == 3

    def test_summary_empty_scenario(self):
        """Test summary handles empty scenario gracefully."""
        env = Environment(
            modality_states={},
            time_state=create_simulator_time(),
        )
        queue = EventQueue()
        scenario = Scenario.create(environment=env, event_queue=queue)

        summary = scenario.summary

        assert summary["modality_count"] == 0
        assert summary["event_count"] == 0


class TestFullIntegration:
    """Integration tests for complete scenario workflows."""

    def test_full_round_trip_with_data(self):
        """Test complete save/load workflow with real data."""
        from tests.fixtures.core.environments import FULL_ENVIRONMENT
        from tests.fixtures.modalities.location import create_location_input
        from tests.fixtures.modalities.email import create_email_input

        # Create scenario with data
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        events = [
            create_simulator_event(
                modality="location",
                scheduled_time=now + timedelta(hours=1),
                data=create_location_input(latitude=40.7128, longitude=-74.0060),
            ),
            create_simulator_event(
                modality="email",
                scheduled_time=now + timedelta(hours=2),
                data=create_email_input(subject="Test Email"),
            ),
        ]
        queue = EventQueue(events=events)

        scenario = Scenario.create(
            environment=FULL_ENVIRONMENT,
            event_queue=queue,
            author="Integration Test",
            description="Full integration test scenario",
        )

        # Simulate file save/load
        json_str = scenario.to_json()
        loaded_scenario = Scenario.from_json(json_str)

        # Verify metadata
        assert loaded_scenario.metadata.author == "Integration Test"
        assert loaded_scenario.metadata.description == "Full integration test scenario"

        # Verify environment loads correctly
        env, warnings = loaded_scenario.get_environment()
        assert len(warnings) == 0
        assert len(env.list_modalities()) == 8

        # Verify events load correctly
        loaded_queue = loaded_scenario.get_event_queue()
        assert len(loaded_queue.events) == 2

    def test_scenario_file_simulation(self):
        """Simulate complete file I/O workflow."""
        import tempfile
        import os

        env = create_environment()
        queue = EventQueue()
        scenario = Scenario.create(
            environment=env,
            event_queue=queue,
            author="File Test",
        )

        # Write to temp file
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".ues-scenario.json",
            delete=False,
        ) as f:
            f.write(scenario.to_json())
            temp_path = f.name

        try:
            # Read from file
            with open(temp_path, "r") as f:
                loaded = Scenario.from_json(f.read())

            assert loaded.metadata.author == "File Test"
        finally:
            os.unlink(temp_path)


class TestVersionConstants:
    """Test version constants are properly exported."""

    def test_ues_version_format(self):
        """Test UES_VERSION follows semantic versioning format (possibly with -dev suffix)."""
        # Version may be "0.1.0" or "0.1.0-dev" depending on install status
        version = UES_VERSION.split("-")[0]  # Strip -dev suffix if present
        parts = version.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)

    def test_scenario_format_version_is_string(self):
        """Test SCENARIO_FORMAT_VERSION is a string."""
        assert isinstance(SCENARIO_FORMAT_VERSION, str)

    def test_versions_importable_from_models(self):
        """Test version constants can be imported from ues.models package."""
        from ues.models import UES_VERSION as imported_ues
        from ues.models import SCENARIO_FORMAT_VERSION as imported_format

        assert imported_ues == UES_VERSION
        assert imported_format == SCENARIO_FORMAT_VERSION
