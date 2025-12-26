"""Unit tests for SimulationEngine scenario export/load methods.

Tests the Phase 2 scenario save/load functionality in SimulationEngine:
- export_environment()
- export_event_queue()
- export_scenario()
- load_environment()
- load_event_queue()
- load_scenario()

EXPORT TESTS:
    - Verify export methods produce valid serializable data
    - Test export with various environment configurations
    - Test export preserves all data for round-trip

LOAD TESTS:
    - Test loading previously exported data
    - Test error handling when simulation is running
    - Test historic event handling options
    - Test strict vs lenient modality loading
    - Test merge vs replace for event queue loading

INTEGRATION TESTS:
    - Full round-trip: export -> modify -> load -> verify
    - Cross-scenario loading patterns
"""

from datetime import datetime, timedelta, timezone

import pytest

from models.environment import Environment
from models.event import EventStatus, SimulatorEvent
from models.queue import EventQueue
from models.scenario import Scenario
from models.simulation import SimulationEngine
from models.time import SimulatorTime
from tests.fixtures.core.environments import create_environment
from tests.fixtures.core.events import create_simulator_event
from tests.fixtures.core.queues import create_event_queue
from tests.fixtures.core.times import create_simulator_time
from tests.fixtures.modalities import email, location


def create_simulation_engine(
    environment: Environment | None = None,
    event_queue: EventQueue | None = None,
) -> SimulationEngine:
    """Create a SimulationEngine with sensible defaults."""
    if environment is None:
        environment = create_environment()
    if event_queue is None:
        event_queue = create_event_queue()
    return SimulationEngine(
        environment=environment,
        event_queue=event_queue,
    )


class TestExportEnvironment:
    """Tests for SimulationEngine.export_environment()."""

    def test_export_environment_basic(self):
        """Test basic environment export produces valid dict."""
        engine = create_simulation_engine()
        
        data = engine.export_environment()
        
        assert isinstance(data, dict)
        assert "time_state" in data
        assert "modality_states" in data

    def test_export_environment_preserves_time(self):
        """Test exported environment preserves time state."""
        time_state = create_simulator_time(
            current_time=datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        env = create_environment(time_state=time_state)
        engine = create_simulation_engine(environment=env)
        
        data = engine.export_environment()
        
        # Check time is preserved (handle both Z and +00:00 formats)
        exported_time = data["time_state"]["current_time"]
        assert exported_time in ("2025-06-15T12:00:00+00:00", "2025-06-15T12:00:00Z")

    def test_export_environment_preserves_modalities(self):
        """Test exported environment preserves all modality states."""
        env = create_environment(
            modality_states={
                "location": location.create_location_state(
                    current_latitude=40.0,
                    current_longitude=-75.0,
                ),
                "email": email.create_email_state(),
            }
        )
        engine = create_simulation_engine(environment=env)
        
        data = engine.export_environment()
        
        assert "location" in data["modality_states"]
        assert "email" in data["modality_states"]
        assert data["modality_states"]["location"]["current_latitude"] == 40.0
        assert data["modality_states"]["location"]["current_longitude"] == -75.0

    def test_export_environment_serializable(self):
        """Test exported environment is JSON serializable."""
        import json
        
        engine = create_simulation_engine()
        data = engine.export_environment()
        
        # Should not raise
        json_str = json.dumps(data)
        assert isinstance(json_str, str)


class TestExportEventQueue:
    """Tests for SimulationEngine.export_event_queue()."""

    def test_export_event_queue_empty(self):
        """Test exporting empty event queue."""
        engine = create_simulation_engine()
        
        data = engine.export_event_queue()
        
        assert isinstance(data, dict)
        assert "events" in data
        assert data["events"] == []

    def test_export_event_queue_with_events(self):
        """Test exporting event queue with events."""
        now = datetime.now(timezone.utc)
        event1 = create_simulator_event(
            modality="location",
            scheduled_time=now + timedelta(hours=1),
        )
        event2 = create_simulator_event(
            modality="location",
            scheduled_time=now + timedelta(hours=2),
        )
        queue = create_event_queue(events=[event1, event2])
        engine = create_simulation_engine(event_queue=queue)
        
        data = engine.export_event_queue()
        
        assert len(data["events"]) == 2

    def test_export_event_queue_preserves_event_ids(self):
        """Test that exported events preserve their event IDs."""
        event = create_simulator_event(modality="location")
        original_id = event.event_id
        queue = create_event_queue(events=[event])
        engine = create_simulation_engine(event_queue=queue)
        
        data = engine.export_event_queue()
        
        assert data["events"][0]["event_id"] == original_id

    def test_export_event_queue_serializable(self):
        """Test exported event queue is JSON serializable."""
        import json
        
        event = create_simulator_event(modality="location")
        queue = create_event_queue(events=[event])
        engine = create_simulation_engine(event_queue=queue)
        
        data = engine.export_event_queue()
        json_str = json.dumps(data)
        
        assert isinstance(json_str, str)


class TestExportScenario:
    """Tests for SimulationEngine.export_scenario()."""

    def test_export_scenario_basic(self):
        """Test basic scenario export returns Scenario object."""
        engine = create_simulation_engine()
        
        scenario = engine.export_scenario()
        
        assert isinstance(scenario, Scenario)
        assert scenario.metadata is not None

    def test_export_scenario_with_metadata(self):
        """Test scenario export with author and description."""
        engine = create_simulation_engine()
        
        scenario = engine.export_scenario(
            author="Test Author",
            description="Test scenario description",
        )
        
        assert scenario.metadata.author == "Test Author"
        assert scenario.metadata.description == "Test scenario description"

    def test_export_scenario_contains_environment(self):
        """Test exported scenario contains environment data."""
        time_state = create_simulator_time(
            current_time=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        )
        env = create_environment(time_state=time_state)
        engine = create_simulation_engine(environment=env)
        
        scenario = engine.export_scenario()
        
        assert "time_state" in scenario.environment
        assert "modality_states" in scenario.environment

    def test_export_scenario_contains_events(self):
        """Test exported scenario contains event data."""
        event = create_simulator_event(modality="location")
        queue = create_event_queue(events=[event])
        engine = create_simulation_engine(event_queue=queue)
        
        scenario = engine.export_scenario()
        
        assert "events" in scenario.events
        assert len(scenario.events["events"]) == 1

    def test_export_scenario_to_json(self):
        """Test exported scenario can be serialized to JSON."""
        engine = create_simulation_engine()
        scenario = engine.export_scenario()
        
        json_str = scenario.to_json()
        
        assert isinstance(json_str, str)
        assert "metadata" in json_str
        assert "environment" in json_str
        assert "events" in json_str


class TestLoadEnvironment:
    """Tests for SimulationEngine.load_environment()."""

    def test_load_environment_rejects_running_simulation(self):
        """Test that load_environment raises error when simulation is running."""
        engine = create_simulation_engine()
        engine.start()
        
        try:
            with pytest.raises(RuntimeError, match="Cannot load environment while simulation is running"):
                engine.load_environment({})
        finally:
            engine.stop()

    def test_load_environment_basic(self):
        """Test basic environment load."""
        # Create source engine and export
        source_env = create_environment(
            modality_states={
                "location": location.create_location_state(
                    current_latitude=50.0,
                    current_longitude=-100.0,
                ),
            }
        )
        source_engine = create_simulation_engine(environment=source_env)
        exported_data = source_engine.export_environment()
        
        # Create target engine and load
        target_engine = create_simulation_engine()
        result = target_engine.load_environment(exported_data)
        
        assert result["success"] is True
        assert "location" in result["modalities_loaded"]
        assert target_engine.environment.get_state("location").current_latitude == 50.0

    def test_load_environment_clears_undo_stack(self):
        """Test that loading environment clears the undo stack."""
        engine = create_simulation_engine()
        # Simulate some history in undo stack
        engine.undo_stack.undo_entries.append(
            engine.undo_stack.undo_entries.__class__.__bases__[0].__new__(
                engine.undo_stack.undo_entries.__class__.__bases__[0]
            ) if False else None
        )
        # Actually, let's just verify via the interface
        
        exported_data = engine.export_environment()
        result = engine.load_environment(exported_data)
        
        assert result["success"] is True
        assert engine.undo_stack.can_undo is False
        assert engine.undo_stack.can_redo is False

    def test_load_environment_invalid_handling_option(self):
        """Test that invalid historic_event_handling raises ValueError."""
        engine = create_simulation_engine()
        
        with pytest.raises(ValueError, match="historic_event_handling must be one of"):
            engine.load_environment({}, historic_event_handling="invalid")

    def test_load_environment_historic_events_ignore(self):
        """Test load_environment with historic_event_handling='ignore'."""
        now = datetime.now(timezone.utc)
        
        # Create an event scheduled before the new environment time
        past_event = create_simulator_event(
            modality="location",
            scheduled_time=now - timedelta(hours=1),
        )
        queue = create_event_queue(events=[past_event])
        
        # Create environment with time in the future relative to event
        time_state = create_simulator_time(current_time=now + timedelta(hours=1))
        exported_env = create_environment(
            modality_states={"location": location.create_location_state()},
            time_state=time_state,
        ).to_scenario_dict()
        
        engine = create_simulation_engine(event_queue=queue)
        result = engine.load_environment(
            exported_env,
            historic_event_handling="ignore",
        )
        
        assert result["success"] is True
        assert result["historic_events_count"] == 1
        assert result["historic_events_action"] == "ignore"
        # Event should still be in queue
        assert len(engine.event_queue.events) == 1

    def test_load_environment_historic_events_delete(self):
        """Test load_environment with historic_event_handling='delete'."""
        now = datetime.now(timezone.utc)
        
        # Create events: one past, one future
        past_event = create_simulator_event(
            modality="location",
            scheduled_time=now - timedelta(hours=2),
        )
        future_event = create_simulator_event(
            modality="location",
            scheduled_time=now + timedelta(hours=2),
        )
        queue = create_event_queue(events=[past_event, future_event])
        
        # Create environment with current time
        time_state = create_simulator_time(current_time=now)
        exported_env = create_environment(
            modality_states={"location": location.create_location_state()},
            time_state=time_state,
        ).to_scenario_dict()
        
        engine = create_simulation_engine(event_queue=queue)
        result = engine.load_environment(
            exported_env,
            historic_event_handling="delete",
        )
        
        assert result["success"] is True
        assert result["historic_events_count"] == 1
        assert result["historic_events_action"] == "delete"
        # Only future event should remain
        assert len(engine.event_queue.events) == 1

    def test_load_environment_strict_modalities(self):
        """Test load_environment with strict_modalities=True rejects unknown."""
        # Create data with unknown modality type
        data = {
            "time_state": create_simulator_time().model_dump(mode="json"),
            "modality_states": {
                "unknown_modality": {"modality_type": "unknown_modality"},
            },
        }
        
        engine = create_simulation_engine()
        
        with pytest.raises(ValueError, match="Unknown modality type"):
            engine.load_environment(data, strict_modalities=True)

    def test_load_environment_lenient_skips_unknown(self):
        """Test load_environment with strict_modalities=False skips unknown."""
        # Create data with known and unknown modality
        data = {
            "time_state": create_simulator_time().model_dump(mode="json"),
            "modality_states": {
                "location": location.create_location_state().model_dump(mode="json"),
                "unknown_modality": {"modality_type": "unknown_modality"},
            },
        }
        
        engine = create_simulation_engine()
        result = engine.load_environment(data, strict_modalities=False)
        
        assert result["success"] is True
        assert "location" in result["modalities_loaded"]
        assert "unknown_modality" in result["modalities_skipped"]


class TestLoadEventQueue:
    """Tests for SimulationEngine.load_event_queue()."""

    def test_load_event_queue_rejects_running_simulation(self):
        """Test that load_event_queue raises error when simulation is running."""
        engine = create_simulation_engine()
        engine.start()
        
        try:
            with pytest.raises(RuntimeError, match="Cannot load event queue while simulation is running"):
                engine.load_event_queue({"events": []})
        finally:
            engine.stop()

    def test_load_event_queue_replace(self):
        """Test loading event queue in replace mode."""
        # Create engine with existing events
        existing_event = create_simulator_event(modality="location")
        queue = create_event_queue(events=[existing_event])
        engine = create_simulation_engine(event_queue=queue)
        
        # Create new events to load
        new_event = create_simulator_event(
            modality="location",
            scheduled_time=datetime.now(timezone.utc) + timedelta(hours=5),
        )
        new_queue = create_event_queue(events=[new_event])
        new_data = new_queue.to_scenario_dict()
        
        result = engine.load_event_queue(new_data, merge=False)
        
        assert result["success"] is True
        assert result["events_loaded"] == 1
        assert result["previous_events"] == 1
        assert len(engine.event_queue.events) == 1

    def test_load_event_queue_merge(self):
        """Test loading event queue in merge mode."""
        # Create engine with existing events
        existing_event = create_simulator_event(modality="location")
        queue = create_event_queue(events=[existing_event])
        engine = create_simulation_engine(event_queue=queue)
        
        # Create new events to load
        new_event = create_simulator_event(
            modality="location",
            scheduled_time=datetime.now(timezone.utc) + timedelta(hours=5),
        )
        new_queue = create_event_queue(events=[new_event])
        new_data = new_queue.to_scenario_dict()
        
        result = engine.load_event_queue(new_data, merge=True)
        
        assert result["success"] is True
        assert result["events_loaded"] == 1
        assert result["events_merged"] == 1
        assert result["previous_events"] == 1
        # Should have both events
        assert len(engine.event_queue.events) == 2

    def test_load_event_queue_regenerates_ids(self):
        """Test that loaded events get new IDs."""
        event = create_simulator_event(modality="location")
        original_id = event.event_id
        queue = create_event_queue(events=[event])
        data = queue.to_scenario_dict()
        
        engine = create_simulation_engine()
        engine.load_event_queue(data)
        
        # New ID should be different
        assert engine.event_queue.events[0].event_id != original_id

    def test_load_event_queue_replace_clears_undo_stack(self):
        """Test that replace mode clears the undo stack."""
        engine = create_simulation_engine()
        
        # Load empty queue (replace)
        result = engine.load_event_queue({"events": []}, merge=False)
        
        assert result["success"] is True
        assert engine.undo_stack.can_undo is False
        assert engine.undo_stack.can_redo is False

    def test_load_event_queue_historic_events_warning(self):
        """Test that loading events before current time generates warning."""
        now = datetime.now(timezone.utc)
        
        # Create event in the past
        past_event = create_simulator_event(
            modality="location",
            scheduled_time=now - timedelta(hours=1),
        )
        queue = create_event_queue(events=[past_event])
        data = queue.to_scenario_dict()
        
        # Engine with current time "now"
        time_state = create_simulator_time(current_time=now)
        env = create_environment(
            modality_states={"location": location.create_location_state()},
            time_state=time_state,
        )
        engine = create_simulation_engine(environment=env)
        
        result = engine.load_event_queue(data)
        
        assert result["historic_events_warning"] is True
        assert result["historic_event_count"] == 1


class TestLoadScenario:
    """Tests for SimulationEngine.load_scenario()."""

    def test_load_scenario_rejects_running_simulation(self):
        """Test that load_scenario raises error when simulation is running."""
        engine = create_simulation_engine()
        engine.start()
        
        try:
            scenario = Scenario.create(
                environment=create_environment(),
                event_queue=EventQueue(),
            )
            with pytest.raises(RuntimeError, match="Cannot load scenario while simulation is running"):
                engine.load_scenario(scenario)
        finally:
            engine.stop()

    def test_load_scenario_basic(self):
        """Test basic scenario load."""
        # Create source scenario
        source_env = create_environment(
            modality_states={
                "location": location.create_location_state(
                    current_latitude=45.0,
                    current_longitude=-90.0,
                ),
            },
            time_state=create_simulator_time(
                current_time=datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
            ),
        )
        source_event = create_simulator_event(
            modality="location",
            scheduled_time=datetime(2025, 6, 1, 13, 0, 0, tzinfo=timezone.utc),
        )
        source_queue = create_event_queue(events=[source_event])
        scenario = Scenario.create(
            environment=source_env,
            event_queue=source_queue,
            author="Test Author",
            description="Test scenario",
        )
        
        # Load into fresh engine
        engine = create_simulation_engine()
        result = engine.load_scenario(scenario)
        
        assert result["success"] is True
        assert result["environment_loaded"] is True
        assert result["events_loaded"] == 1
        assert "location" in result["modalities_loaded"]
        assert result["scenario_metadata"]["author"] == "Test Author"

    def test_load_scenario_replaces_environment(self):
        """Test that load_scenario replaces environment."""
        # Original engine with different state
        original_env = create_environment(
            modality_states={
                "location": location.create_location_state(
                    current_latitude=0.0,
                    current_longitude=0.0,
                ),
            },
        )
        engine = create_simulation_engine(environment=original_env)
        
        # Scenario with different state
        scenario_env = create_environment(
            modality_states={
                "location": location.create_location_state(
                    current_latitude=99.0,
                    current_longitude=-99.0,
                ),
            },
        )
        scenario = Scenario.create(
            environment=scenario_env,
            event_queue=EventQueue(),
        )
        
        engine.load_scenario(scenario)
        
        loc_state = engine.environment.get_state("location")
        # Note: latitude is clamped to [-90, 90] by the model
        assert loc_state.current_longitude == -99.0

    def test_load_scenario_replaces_events(self):
        """Test that load_scenario replaces event queue."""
        # Original engine with events
        original_event = create_simulator_event(modality="location")
        original_queue = create_event_queue(events=[original_event])
        engine = create_simulation_engine(event_queue=original_queue)
        
        # Scenario with no events
        scenario = Scenario.create(
            environment=create_environment(),
            event_queue=EventQueue(),
        )
        
        engine.load_scenario(scenario)
        
        assert len(engine.event_queue.events) == 0

    def test_load_scenario_clears_undo_stack(self):
        """Test that load_scenario clears undo stack."""
        engine = create_simulation_engine()
        
        scenario = Scenario.create(
            environment=create_environment(),
            event_queue=EventQueue(),
        )
        
        engine.load_scenario(scenario)
        
        assert engine.undo_stack.can_undo is False
        assert engine.undo_stack.can_redo is False

    def test_load_scenario_strict_modalities(self):
        """Test load_scenario with strict_modalities."""
        # Create scenario with unknown modality in raw data
        scenario = Scenario(
            metadata=Scenario.create(
                environment=create_environment(),
                event_queue=EventQueue(),
            ).metadata,
            environment={
                "time_state": create_simulator_time().model_dump(mode="json"),
                "modality_states": {
                    "unknown_type": {"modality_type": "unknown_type"},
                },
            },
            events={"events": []},
        )
        
        engine = create_simulation_engine()
        
        with pytest.raises(ValueError, match="Unknown modality type"):
            engine.load_scenario(scenario, strict_modalities=True)

    def test_load_scenario_lenient_modalities(self):
        """Test load_scenario with lenient modality handling."""
        # Create scenario with known and unknown modality
        scenario = Scenario(
            metadata=Scenario.create(
                environment=create_environment(),
                event_queue=EventQueue(),
            ).metadata,
            environment={
                "time_state": create_simulator_time().model_dump(mode="json"),
                "modality_states": {
                    "location": location.create_location_state().model_dump(mode="json"),
                    "unknown_type": {"modality_type": "unknown_type"},
                },
            },
            events={"events": []},
        )
        
        engine = create_simulation_engine()
        result = engine.load_scenario(scenario, strict_modalities=False)
        
        assert result["success"] is True
        assert "location" in result["modalities_loaded"]
        assert "unknown_type" in result["modalities_skipped"]


class TestScenarioRoundTrip:
    """Integration tests for full export/load round-trips."""

    def test_environment_round_trip(self):
        """Test exporting and loading environment preserves state."""
        # Setup original state
        original_env = create_environment(
            modality_states={
                "location": location.create_location_state(
                    current_latitude=37.7749,
                    current_longitude=-122.4194,
                    current_address="San Francisco, CA",
                ),
                "email": email.create_email_state(),
            },
            time_state=create_simulator_time(
                current_time=datetime(2025, 3, 15, 10, 30, 0, tzinfo=timezone.utc),
            ),
        )
        source_engine = create_simulation_engine(environment=original_env)
        
        # Export
        exported_data = source_engine.export_environment()
        
        # Load into new engine
        target_engine = create_simulation_engine()
        target_engine.load_environment(exported_data)
        
        # Verify state matches
        target_loc = target_engine.environment.get_state("location")
        assert target_loc.current_latitude == 37.7749
        assert target_loc.current_longitude == -122.4194
        
        target_time = target_engine.environment.time_state.current_time
        assert target_time == datetime(2025, 3, 15, 10, 30, 0, tzinfo=timezone.utc)

    def test_event_queue_round_trip(self):
        """Test exporting and loading event queue preserves events."""
        # Setup original events
        event1 = create_simulator_event(
            modality="location",
            scheduled_time=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            priority=5,
        )
        event2 = create_simulator_event(
            modality="location",
            scheduled_time=datetime(2025, 1, 1, 13, 0, 0, tzinfo=timezone.utc),
            priority=10,
        )
        original_queue = create_event_queue(events=[event1, event2])
        source_engine = create_simulation_engine(event_queue=original_queue)
        
        # Export
        exported_data = source_engine.export_event_queue()
        
        # Load into new engine
        target_engine = create_simulation_engine()
        target_engine.load_event_queue(exported_data)
        
        # Verify events (IDs will differ, but data should match)
        assert len(target_engine.event_queue.events) == 2
        assert target_engine.event_queue.events[0].priority == 5
        assert target_engine.event_queue.events[1].priority == 10

    def test_full_scenario_round_trip(self):
        """Test exporting and loading full scenario preserves everything."""
        # Setup complete scenario
        env = create_environment(
            modality_states={
                "location": location.create_location_state(
                    current_latitude=40.7128,
                    current_longitude=-74.0060,
                ),
            },
            time_state=create_simulator_time(
                current_time=datetime(2025, 7, 4, 12, 0, 0, tzinfo=timezone.utc),
            ),
        )
        event = create_simulator_event(
            modality="location",
            scheduled_time=datetime(2025, 7, 4, 14, 0, 0, tzinfo=timezone.utc),
        )
        queue = create_event_queue(events=[event])
        
        source_engine = create_simulation_engine(environment=env, event_queue=queue)
        
        # Export scenario
        scenario = source_engine.export_scenario(
            author="Round Trip Test",
            description="Testing full round-trip",
        )
        
        # Convert to JSON and back (simulating file save/load)
        json_str = scenario.to_json()
        loaded_scenario = Scenario.from_json(json_str)
        
        # Load into new engine
        target_engine = create_simulation_engine()
        result = target_engine.load_scenario(loaded_scenario)
        
        # Verify everything
        assert result["success"] is True
        assert result["scenario_metadata"]["author"] == "Round Trip Test"
        
        target_loc = target_engine.environment.get_state("location")
        assert target_loc.current_latitude == 40.7128
        assert target_loc.current_longitude == -74.0060
        
        assert len(target_engine.event_queue.events) == 1

    def test_modify_and_reload(self):
        """Test modifying exported data and reloading."""
        # Export initial state
        engine = create_simulation_engine()
        scenario = engine.export_scenario()
        
        # Modify the exported data
        scenario_dict = scenario.to_dict()
        scenario_dict["environment"]["time_state"]["current_time"] = "2030-01-01T00:00:00+00:00"
        
        # Create new scenario from modified data
        modified_scenario = Scenario.from_dict(scenario_dict)
        
        # Load modified scenario
        new_engine = create_simulation_engine()
        new_engine.load_scenario(modified_scenario)
        
        # Verify modification took effect
        assert new_engine.environment.time_state.current_time.year == 2030


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_load_empty_environment(self):
        """Test loading environment with no modalities."""
        data = {
            "time_state": create_simulator_time().model_dump(mode="json"),
            "modality_states": {},
        }
        
        engine = create_simulation_engine()
        result = engine.load_environment(data)
        
        assert result["success"] is True
        assert result["modalities_loaded"] == []

    def test_load_event_queue_empty(self):
        """Test loading empty event queue."""
        engine = create_simulation_engine()
        
        result = engine.load_event_queue({"events": []})
        
        assert result["success"] is True
        assert result["events_loaded"] == 0

    def test_load_environment_missing_time_state(self):
        """Test load_environment raises on missing time_state."""
        engine = create_simulation_engine()
        
        with pytest.raises(ValueError, match="Missing required field: 'time_state'"):
            engine.load_environment({"modality_states": {}})

    def test_load_event_queue_missing_events(self):
        """Test load_event_queue raises on missing events field."""
        engine = create_simulation_engine()
        
        with pytest.raises(ValueError, match="Missing required field: 'events'"):
            engine.load_event_queue({})

    def test_export_after_event_execution(self):
        """Test exporting after some events have been executed."""
        now = datetime.now(timezone.utc)
        
        # Create event that's already due
        event = create_simulator_event(
            modality="location",
            scheduled_time=now - timedelta(seconds=1),
        )
        queue = create_event_queue(events=[event])
        env = create_environment(
            modality_states={"location": location.create_location_state()},
            time_state=create_simulator_time(current_time=now),
        )
        engine = create_simulation_engine(environment=env, event_queue=queue)
        
        # Start and execute
        engine.start()
        engine.execute_due_events()
        engine.stop()
        
        # Export should include executed event
        data = engine.export_event_queue()
        
        assert len(data["events"]) == 1
        assert data["events"][0]["status"] == "executed"
