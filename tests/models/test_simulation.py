"""Unit tests for SimulationEngine and SimulationLoop.

GENERAL PATTERN TESTS: These test patterns apply to all orchestration classes
    - Instantiation tests verify proper initialization and validation
    - Lifecycle tests verify start/stop/reset behavior
    - State access tests verify get_state/get_snapshot/validate methods
    - Serialization tests verify state persistence

SIMULATION_ENGINE-SPECIFIC TESTS: These verify SimulationEngine-specific functionality
    - Time control: advance_time, set_time, skip_to_next_event, pause, resume
    - Event management: add_event, execute_due_events
    - Mode coordination: manual, event-driven, auto-advance
    - Validation: environment and event queue consistency
    - Thread management: auto-advance loop lifecycle
    - Error handling: graceful degradation and logging

SIMULATION_LOOP-SPECIFIC TESTS: These verify SimulationLoop-specific functionality
    - Thread lifecycle: start, stop, is_running state
    - Loop execution: continuous tick calls
    - Pause handling: idle when paused
    - Error isolation: catch tick errors without crashing
    - Stop signal: graceful shutdown
"""

import time
from datetime import datetime, timedelta, timezone

import pytest

from models.environment import Environment
from models.event import EventStatus, SimulatorEvent
from models.queue import EventQueue
from models.simulation import SimulationEngine, SimulationLoop
from models.time import SimulatorTime
from tests.fixtures.core.environments import create_environment
from tests.fixtures.core.events import create_simulator_event
from tests.fixtures.core.queues import create_event_queue
from tests.fixtures.modalities import email, location


def create_simulation_engine(
    environment: Environment | None = None,
    event_queue: EventQueue | None = None,
) -> SimulationEngine:
    """Create a SimulationEngine with sensible defaults.
    
    Args:
        environment: Environment instance (defaults to minimal environment).
        event_queue: EventQueue instance (defaults to empty queue).
    
    Returns:
        SimulationEngine instance ready for testing.
    """
    if environment is None:
        environment = create_environment()
    
    if event_queue is None:
        event_queue = create_event_queue()
    
    return SimulationEngine(
        environment=environment,
        event_queue=event_queue,
    )


class TestSimulationEngineInstantiation:
    """GENERAL PATTERN: Test instantiation and validation."""

    def test_minimal_instantiation(self):
        """GENERAL PATTERN: Test creating SimulationEngine with required fields only."""
        environment = create_environment()
        event_queue = create_event_queue()

        engine = SimulationEngine(
            environment=environment,
            event_queue=event_queue,
        )

        assert engine.environment == environment
        assert engine.event_queue == event_queue
        assert engine.is_running is False
        assert engine.simulation_id is not None
        assert len(engine.simulation_id) > 0

    def test_instantiation_with_factory(self):
        """GENERAL PATTERN: Test instantiation using create_simulation_engine factory."""
        engine = create_simulation_engine()

        assert engine.environment is not None
        assert engine.event_queue is not None
        assert engine.is_running is False

    def test_unique_simulation_ids(self):
        """SIMULATION_ENGINE-SPECIFIC: Verify each instance gets unique ID."""
        engine1 = create_simulation_engine()
        engine2 = create_simulation_engine()

        assert engine1.simulation_id != engine2.simulation_id

    def test_private_attributes_initialized(self):
        """SIMULATION_ENGINE-SPECIFIC: Verify private attributes are initialized."""
        engine = create_simulation_engine()

        assert hasattr(engine, "_loop")
        assert engine._loop is None
        assert hasattr(engine, "_operation_lock")


class TestSimulationEngineLifecycle:
    """SIMULATION_ENGINE-SPECIFIC: Test lifecycle methods."""

    def test_start_manual_mode(self):
        """SIMULATION_ENGINE-SPECIFIC: Test starting simulation in manual mode."""
        engine = create_simulation_engine()

        result = engine.start(auto_advance=False)

        assert engine.is_running is True
        assert result["status"] == "running"
        assert result["mode"] == "manual"
        assert "simulation_id" in result
        assert "current_time" in result
        assert result["time_scale"] is None

    def test_start_auto_advance_mode(self):
        """SIMULATION_ENGINE-SPECIFIC: Test starting simulation in auto-advance mode."""
        engine = create_simulation_engine()

        result = engine.start(auto_advance=True, time_scale=5.0)

        assert engine.is_running is True
        assert result["status"] == "running"
        assert result["mode"] == "auto_advance"
        assert result["time_scale"] == 5.0
        assert engine._loop is not None
        assert engine._loop.is_running is True
        assert engine.environment.time_state.auto_advance is True
        assert engine.environment.time_state.time_scale == 5.0

        # Clean up
        engine.stop()

    def test_start_already_running_raises_error(self):
        """SIMULATION_ENGINE-SPECIFIC: Verify starting already-running simulation fails."""
        engine = create_simulation_engine()
        engine.start(auto_advance=False)

        with pytest.raises(RuntimeError, match="already running"):
            engine.start(auto_advance=False)

    def test_start_validates_environment(self):
        """SIMULATION_ENGINE-SPECIFIC: Verify start fails if environment is invalid."""
        # Create environment with no modalities (invalid)
        time_state = SimulatorTime(
            current_time=datetime.now(timezone.utc),
            last_wall_time_update=datetime.now(timezone.utc),
        )
        environment = Environment(
            modality_states={},
            time_state=time_state,
        )
        engine = create_simulation_engine(environment=environment)

        with pytest.raises(ValueError, match="validation errors"):
            engine.start(auto_advance=False)

    def test_stop_manual_mode(self):
        """SIMULATION_ENGINE-SPECIFIC: Test stopping simulation in manual mode."""
        engine = create_simulation_engine()
        engine.start(auto_advance=False)

        result = engine.stop()

        assert engine.is_running is False
        assert result["status"] == "stopped"
        assert "final_time" in result
        assert "total_events" in result
        assert result["total_events"] >= 0

    def test_stop_auto_advance_mode(self):
        """SIMULATION_ENGINE-SPECIFIC: Test stopping simulation in auto-advance mode."""
        engine = create_simulation_engine()
        engine.start(auto_advance=True)

        # Give loop time to start
        time.sleep(0.05)

        result = engine.stop()

        assert engine.is_running is False
        assert engine._loop is None
        assert result["status"] == "stopped"

    def test_stop_not_running(self):
        """SIMULATION_ENGINE-SPECIFIC: Verify stopping non-running simulation is safe."""
        engine = create_simulation_engine()

        result = engine.stop()

        assert result["status"] == "stopped"
        # When stopping a non-running simulation, optional fields are None
        assert result["final_time"] is None
        assert result["total_events"] is None

    def test_reset(self):
        """SIMULATION_ENGINE-SPECIFIC: Test resetting simulation state."""
        engine = create_simulation_engine()
        
        # Add and execute an event - schedule it relative to simulator time
        current_time = engine.environment.time_state.current_time
        event = create_simulator_event(
            modality="location",
            data=location.create_location_input(),
            scheduled_time=current_time + timedelta(minutes=30),
            created_at=current_time,
        )
        engine.event_queue.add_event(event)
        engine.start(auto_advance=False)
        engine.advance_time(timedelta(hours=1))
        
        # Verify event was executed
        assert event.status == EventStatus.EXECUTED
        assert event.executed_at is not None

        # Reset
        engine.reset()

        # Verify reset
        assert engine.is_running is False
        assert event.status == EventStatus.PENDING
        assert event.executed_at is None
        assert event.error_message is None


class TestSimulationEngineTimeControl:
    """SIMULATION_ENGINE-SPECIFIC: Test time control methods."""

    def test_advance_time_basic(self):
        """SIMULATION_ENGINE-SPECIFIC: Test basic time advancement."""
        engine = create_simulation_engine()
        initial_time = engine.environment.time_state.current_time
        engine.start(auto_advance=False)

        result = engine.advance_time(timedelta(hours=1))

        expected_time = initial_time + timedelta(hours=1)
        assert engine.environment.time_state.current_time == expected_time
        assert result["events_executed"] == 0
        assert "current_time" in result

    def test_advance_time_executes_due_events(self):
        """SIMULATION_ENGINE-SPECIFIC: Test that advancing time executes due events."""
        engine = create_simulation_engine()
        current_time = engine.environment.time_state.current_time
        
        # Add event in 30 minutes
        event = create_simulator_event(
            scheduled_time=current_time + timedelta(minutes=30),
            modality="location",
            data=location.create_location_input(),
        )
        engine.event_queue.add_event(event)
        engine.start(auto_advance=False)

        # Advance past event
        result = engine.advance_time(timedelta(hours=1))

        assert result["events_executed"] == 1
        assert event.status == EventStatus.EXECUTED

    def test_advance_time_not_running_raises_error(self):
        """SIMULATION_ENGINE-SPECIFIC: Verify advancing time requires running simulation."""
        engine = create_simulation_engine()

        with pytest.raises(ValueError, match="not running"):
            engine.advance_time(timedelta(hours=1))

    def test_advance_time_negative_delta_raises_error(self):
        """SIMULATION_ENGINE-SPECIFIC: Verify negative time delta is rejected."""
        engine = create_simulation_engine()
        engine.start(auto_advance=False)

        with pytest.raises(ValueError, match="must be positive"):
            engine.advance_time(timedelta(hours=-1))

    def test_advance_time_zero_delta_raises_error(self):
        """SIMULATION_ENGINE-SPECIFIC: Verify zero time delta is rejected."""
        engine = create_simulation_engine()
        engine.start(auto_advance=False)

        with pytest.raises(ValueError, match="must be positive"):
            engine.advance_time(timedelta(0))

    def test_set_time_basic(self):
        """SIMULATION_ENGINE-SPECIFIC: Test jumping to specific time."""
        engine = create_simulation_engine()
        current_time = engine.environment.time_state.current_time
        target_time = current_time + timedelta(days=7)
        engine.start(auto_advance=False)

        result = engine.set_time(target_time, execute_skipped=False)

        assert engine.environment.time_state.current_time == target_time
        assert result["skipped_events"] == 0
        assert result["executed_events"] == 0

    def test_set_time_skips_events(self):
        """SIMULATION_ENGINE-SPECIFIC: Test that set_time marks skipped events."""
        engine = create_simulation_engine()
        current_time = engine.environment.time_state.current_time
        
        # Add event in middle of jump
        event = create_simulator_event(
            scheduled_time=current_time + timedelta(hours=12),
            modality="location",
            data=location.create_location_input(),
        )
        engine.event_queue.add_event(event)
        engine.start(auto_advance=False)

        # Jump past event without executing
        target_time = current_time + timedelta(days=1)
        result = engine.set_time(target_time, execute_skipped=False)

        assert result["skipped_events"] == 1
        assert result["executed_events"] == 0
        assert event.status == EventStatus.SKIPPED

    def test_set_time_executes_skipped_events(self):
        """SIMULATION_ENGINE-SPECIFIC: Test that set_time can execute skipped events."""
        engine = create_simulation_engine()
        current_time = engine.environment.time_state.current_time
        
        # Add event in middle of jump
        event = create_simulator_event(
            scheduled_time=current_time + timedelta(hours=12),
            modality="location",
            data=location.create_location_input(),
        )
        engine.event_queue.add_event(event)
        engine.start(auto_advance=False)

        # Jump past event with execution
        target_time = current_time + timedelta(days=1)
        result = engine.set_time(target_time, execute_skipped=True)

        assert result["skipped_events"] == 1
        assert result["executed_events"] == 1
        assert event.status == EventStatus.EXECUTED

    def test_set_time_backwards_raises_error(self):
        """SIMULATION_ENGINE-SPECIFIC: Verify cannot travel backwards in time."""
        engine = create_simulation_engine()
        current_time = engine.environment.time_state.current_time
        engine.start(auto_advance=False)

        with pytest.raises(ValueError, match="backwards"):
            engine.set_time(current_time - timedelta(hours=1))

    def test_skip_to_next_event_basic(self):
        """SIMULATION_ENGINE-SPECIFIC: Test skipping to next event."""
        engine = create_simulation_engine()
        current_time = engine.environment.time_state.current_time
        
        # Add event in future
        event_time = current_time + timedelta(hours=3)
        event = create_simulator_event(
            scheduled_time=event_time,
            modality="location",
            data=location.create_location_input(),
        )
        engine.event_queue.add_event(event)
        engine.start(auto_advance=False)

        result = engine.skip_to_next_event()

        assert engine.environment.time_state.current_time == event_time
        assert result["events_executed"] == 1
        assert event.status == EventStatus.EXECUTED

    def test_skip_to_next_event_multiple_at_same_time(self):
        """SIMULATION_ENGINE-SPECIFIC: Test skipping executes all events at target time."""
        # Create environment with both location and email modalities
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
                "email": email.create_email_state(),
            }
        )
        engine = create_simulation_engine(environment=env)
        current_time = engine.environment.time_state.current_time
        event_time = current_time + timedelta(hours=2)
        
        # Add multiple events at same time
        event1 = create_simulator_event(
            scheduled_time=event_time,
            modality="location",
            data=location.create_location_input(),
            created_at=current_time,
        )
        event2 = create_simulator_event(
            scheduled_time=event_time,
            modality="email",
            data=email.create_email_input(),
            created_at=current_time,
        )
        engine.event_queue.add_event(event1)
        engine.event_queue.add_event(event2)
        engine.start(auto_advance=False)

        result = engine.skip_to_next_event()

        assert result["events_executed"] == 2
        assert event1.status == EventStatus.EXECUTED
        assert event2.status == EventStatus.EXECUTED

    def test_skip_to_next_event_no_events(self):
        """SIMULATION_ENGINE-SPECIFIC: Test skip_to_next with empty queue."""
        engine = create_simulation_engine()
        engine.start(auto_advance=False)

        result = engine.skip_to_next_event()

        assert "No pending events" in result["message"]

    def test_pause(self):
        """SIMULATION_ENGINE-SPECIFIC: Test pausing simulation."""
        engine = create_simulation_engine()
        engine.start(auto_advance=False)

        engine.pause()

        assert engine.environment.time_state.is_paused is True

    def test_resume(self):
        """SIMULATION_ENGINE-SPECIFIC: Test resuming simulation."""
        engine = create_simulation_engine()
        engine.start(auto_advance=False)
        engine.pause()

        engine.resume()

        assert engine.environment.time_state.is_paused is False


class TestSimulationEngineEventManagement:
    """SIMULATION_ENGINE-SPECIFIC: Test event management methods."""

    def test_add_event_basic(self):
        """SIMULATION_ENGINE-SPECIFIC: Test adding event to simulation."""
        engine = create_simulation_engine()
        event = create_simulator_event(
            modality="location",
            data=location.create_location_input(),
        )

        engine.add_event(event)

        assert event in engine.event_queue.events

    def test_add_event_validates(self):
        """SIMULATION_ENGINE-SPECIFIC: Test that add_event validates event."""
        engine = create_simulation_engine()
        current_time = engine.environment.time_state.current_time
        
        # Create invalid event (missing data)
        event = SimulatorEvent(
            scheduled_time=current_time + timedelta(hours=1),
            modality="location",
            data=None,
            created_at=current_time,
        )

        with pytest.raises(ValueError, match="Invalid event"):
            engine.add_event(event)

    def test_execute_due_events_basic(self):
        """SIMULATION_ENGINE-SPECIFIC: Test executing due events."""
        engine = create_simulation_engine()
        current_time = engine.environment.time_state.current_time
        
        # Add event that's already due
        event = create_simulator_event(
            scheduled_time=current_time - timedelta(minutes=5),
            modality="location",
            data=location.create_location_input(),
        )
        engine.event_queue.add_event(event)

        executed = engine.execute_due_events()

        assert len(executed) == 1
        assert event.status == EventStatus.EXECUTED

    def test_execute_due_events_skips_future_events(self):
        """SIMULATION_ENGINE-SPECIFIC: Test that only due events are executed."""
        engine = create_simulation_engine()
        current_time = engine.environment.time_state.current_time
        
        # Add past event
        past_event = create_simulator_event(
            scheduled_time=current_time - timedelta(hours=1),
            modality="location",
            data=location.create_location_input(),
        )
        # Add future event
        future_event = create_simulator_event(
            scheduled_time=current_time + timedelta(hours=1),
            modality="email",
            data=email.create_email_input(),
        )
        engine.event_queue.add_event(past_event)
        engine.event_queue.add_event(future_event)

        executed = engine.execute_due_events()

        assert len(executed) == 1
        assert past_event.status == EventStatus.EXECUTED
        assert future_event.status == EventStatus.PENDING

    def test_execute_due_events_handles_errors(self):
        """SIMULATION_ENGINE-SPECIFIC: Test that execution errors are caught."""
        engine = create_simulation_engine()
        current_time = engine.environment.time_state.current_time
        
        # Add event referencing non-existent modality
        # Bypass validation by adding directly to events list
        bad_event = create_simulator_event(
            scheduled_time=current_time - timedelta(minutes=5),
            modality="nonexistent",
            data=location.create_location_input(),
            created_at=current_time - timedelta(minutes=10),
        )
        engine.event_queue.events.append(bad_event)

        executed = engine.execute_due_events()

        # Event should be marked as failed
        assert len(executed) == 1
        assert bad_event.status == EventStatus.FAILED
        assert bad_event.error_message is not None


class TestSimulationEngineStateAccess:
    """GENERAL PATTERN: Test state access methods."""

    def test_get_state(self):
        """GENERAL PATTERN: Test getting environment state."""
        engine = create_simulation_engine()

        state = engine.get_state()

        assert isinstance(state, Environment)
        assert state is engine.environment

    def test_get_snapshot(self):
        """GENERAL PATTERN: Test getting state snapshot."""
        engine = create_simulation_engine()

        snapshot = engine.get_snapshot()

        assert isinstance(snapshot, dict)
        assert "simulation_id" in snapshot
        assert "is_running" in snapshot
        assert "mode" in snapshot
        assert "environment" in snapshot
        assert "event_queue" in snapshot

    def test_get_snapshot_structure(self):
        """SIMULATION_ENGINE-SPECIFIC: Test snapshot has correct structure."""
        engine = create_simulation_engine()

        snapshot = engine.get_snapshot()

        assert snapshot["is_running"] is False
        assert "time" in snapshot["environment"]
        assert "modalities" in snapshot["environment"]
        assert "total_events" in snapshot["event_queue"]

    def test_validate_valid_engine(self):
        """GENERAL PATTERN: Test validation of valid engine."""
        engine = create_simulation_engine()

        errors = engine.validate()

        assert errors == []

    def test_validate_detects_invalid_environment(self):
        """SIMULATION_ENGINE-SPECIFIC: Test validation detects environment errors."""
        # Create environment with no modalities (invalid)
        time_state = SimulatorTime(
            current_time=datetime.now(timezone.utc),
            last_wall_time_update=datetime.now(timezone.utc),
        )
        environment = Environment(
            modality_states={},
            time_state=time_state,
        )
        engine = create_simulation_engine(environment=environment)

        errors = engine.validate()

        assert len(errors) > 0
        assert any("empty" in err.lower() for err in errors)

    def test_validate_detects_invalid_events(self):
        """SIMULATION_ENGINE-SPECIFIC: Test validation detects invalid events."""
        engine = create_simulation_engine()
        current_time = engine.environment.time_state.current_time
        
        # Add event referencing non-existent modality
        # Bypass validation by adding directly to events list
        bad_event = create_simulator_event(
            modality="nonexistent",
            data=location.create_location_input(),
            created_at=current_time,
        )
        engine.event_queue.events.append(bad_event)

        errors = engine.validate()

        assert len(errors) > 0
        assert any("nonexistent" in err for err in errors)


class TestSimulationEngineTick:
    """SIMULATION_ENGINE-SPECIFIC: Test tick method (for auto-advance)."""

    def test_tick_advances_time(self):
        """SIMULATION_ENGINE-SPECIFIC: Test that tick advances time."""
        engine = create_simulation_engine()
        engine.environment.time_state.auto_advance = True
        engine.environment.time_state.time_scale = 10.0
        initial_time = engine.environment.time_state.current_time

        # Wait a moment for wall time to pass
        time.sleep(0.02)

        engine.tick()

        # Time should have advanced
        assert engine.environment.time_state.current_time > initial_time

    def test_tick_executes_due_events(self):
        """SIMULATION_ENGINE-SPECIFIC: Test that tick executes due events."""
        engine = create_simulation_engine()
        current_time = engine.environment.time_state.current_time
        
        # Add event in very near future
        event = create_simulator_event(
            scheduled_time=current_time + timedelta(milliseconds=50),
            modality="location",
            data=location.create_location_input(),
        )
        engine.event_queue.add_event(event)
        
        engine.environment.time_state.auto_advance = True
        engine.environment.time_state.time_scale = 100.0  # Fast time

        # Wait and tick
        time.sleep(0.02)
        engine.tick()

        # Event should be executed
        assert event.status == EventStatus.EXECUTED

    def test_tick_when_paused(self):
        """SIMULATION_ENGINE-SPECIFIC: Test that tick doesn't advance when paused."""
        engine = create_simulation_engine()
        engine.environment.time_state.auto_advance = True
        engine.environment.time_state.is_paused = True
        initial_time = engine.environment.time_state.current_time

        time.sleep(0.02)
        engine.tick()

        # Time should not advance when paused
        assert engine.environment.time_state.current_time == initial_time


class TestSimulationLoopInstantiation:
    """GENERAL PATTERN: Test instantiation and validation."""

    def test_minimal_instantiation(self):
        """GENERAL PATTERN: Test creating SimulationLoop with required fields."""
        engine = create_simulation_engine()

        loop = SimulationLoop(engine=engine)

        assert loop.engine is engine
        assert loop.tick_interval == 0.01  # Default
        assert loop.is_running is False

    def test_instantiation_with_custom_interval(self):
        """SIMULATION_LOOP-SPECIFIC: Test creating loop with custom tick interval."""
        engine = create_simulation_engine()

        loop = SimulationLoop(engine=engine, tick_interval=0.05)

        assert loop.tick_interval == 0.05

    def test_private_attributes_initialized(self):
        """SIMULATION_LOOP-SPECIFIC: Verify private attributes are initialized."""
        engine = create_simulation_engine()
        loop = SimulationLoop(engine=engine)

        assert loop._thread is None
        assert loop._stop_event is not None
        assert not loop._stop_event.is_set()


class TestSimulationLoopLifecycle:
    """SIMULATION_LOOP-SPECIFIC: Test lifecycle methods."""

    def test_start_loop(self):
        """SIMULATION_LOOP-SPECIFIC: Test starting simulation loop."""
        engine = create_simulation_engine()
        engine.start(auto_advance=False)  # Start engine first
        loop = SimulationLoop(engine=engine)

        loop.start()

        assert loop.is_running is True
        assert loop._thread is not None
        assert loop._thread.is_alive()

        # Clean up
        loop.stop()

    def test_start_already_running_raises_error(self):
        """SIMULATION_LOOP-SPECIFIC: Test starting already-running loop fails."""
        engine = create_simulation_engine()
        engine.start(auto_advance=False)
        loop = SimulationLoop(engine=engine)
        loop.start()

        with pytest.raises(RuntimeError, match="already running"):
            loop.start()

        # Clean up
        loop.stop()

    def test_stop_loop(self):
        """SIMULATION_LOOP-SPECIFIC: Test stopping simulation loop."""
        engine = create_simulation_engine()
        engine.start(auto_advance=False)
        loop = SimulationLoop(engine=engine)
        loop.start()

        time.sleep(0.05)  # Let it run briefly

        loop.stop()

        assert loop.is_running is False
        assert loop._thread is None or not loop._thread.is_alive()

    def test_stop_not_running(self):
        """SIMULATION_LOOP-SPECIFIC: Test stopping non-running loop is safe."""
        engine = create_simulation_engine()
        loop = SimulationLoop(engine=engine)

        loop.stop()  # Should not raise

        assert loop.is_running is False

    def test_loop_calls_tick(self):
        """SIMULATION_LOOP-SPECIFIC: Test that loop calls engine.tick()."""
        engine = create_simulation_engine()
        engine.start(auto_advance=False)
        initial_time = engine.environment.time_state.current_time
        
        # Enable auto-advance so tick will advance time
        engine.environment.time_state.auto_advance = True
        engine.environment.time_state.time_scale = 100.0

        loop = SimulationLoop(engine=engine, tick_interval=0.01)
        loop.start()

        # Let loop run for a bit
        time.sleep(0.1)
        loop.stop()

        # Time should have advanced from tick calls
        assert engine.environment.time_state.current_time > initial_time

    def test_loop_respects_pause(self):
        """SIMULATION_LOOP-SPECIFIC: Test that loop idles when simulation is paused."""
        engine = create_simulation_engine()
        engine.start(auto_advance=False)
        engine.environment.time_state.auto_advance = True
        engine.environment.time_state.time_scale = 100.0
        engine.pause()  # Pause before starting loop
        
        initial_time = engine.environment.time_state.current_time

        loop = SimulationLoop(engine=engine, tick_interval=0.01)
        loop.start()

        # Let loop run while paused
        time.sleep(0.1)
        loop.stop()

        # Time should not have advanced while paused
        assert engine.environment.time_state.current_time == initial_time

    def test_loop_handles_tick_errors(self):
        """SIMULATION_LOOP-SPECIFIC: Test that loop doesn't crash on tick errors."""
        engine = create_simulation_engine()
        current_time = engine.environment.time_state.current_time
        engine.start(auto_advance=False)
        
        # Add event that will fail (non-existent modality)
        # Bypass validation by adding directly to events list
        bad_event = create_simulator_event(
            scheduled_time=current_time - timedelta(hours=1),
            modality="nonexistent",
            data=location.create_location_input(),
            created_at=current_time - timedelta(hours=2),
        )
        engine.event_queue.events.append(bad_event)
        
        engine.environment.time_state.auto_advance = True

        loop = SimulationLoop(engine=engine, tick_interval=0.01)
        loop.start()

        # Loop should keep running despite errors
        time.sleep(0.1)
        
        assert loop.is_running is True

        loop.stop()


class TestSimulationEngineIntegration:
    """SIMULATION_ENGINE-SPECIFIC: Test integration scenarios."""

    def test_manual_mode_workflow(self):
        """SIMULATION_ENGINE-SPECIFIC: Test complete manual mode workflow."""
        # Create environment with both location and email modalities
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
                "email": email.create_email_state(),
            }
        )
        engine = create_simulation_engine(environment=env)
        current_time = engine.environment.time_state.current_time
        
        # Add events
        event1 = create_simulator_event(
            scheduled_time=current_time + timedelta(minutes=30),
            modality="location",
            data=location.create_location_input(),
            created_at=current_time,
        )
        event2 = create_simulator_event(
            scheduled_time=current_time + timedelta(hours=2),
            modality="email",
            data=email.create_email_input(),
            created_at=current_time,
        )
        engine.add_event(event1)
        engine.add_event(event2)

        # Start in manual mode
        engine.start(auto_advance=False)

        # Advance to first event
        engine.advance_time(timedelta(hours=1))
        assert event1.status == EventStatus.EXECUTED
        assert event2.status == EventStatus.PENDING

        # Advance to second event
        engine.advance_time(timedelta(hours=2))
        assert event2.status == EventStatus.EXECUTED

        # Stop
        result = engine.stop()
        assert result["events_executed"] == 2

    def test_event_driven_mode_workflow(self):
        """SIMULATION_ENGINE-SPECIFIC: Test complete event-driven workflow."""
        # Create environment with both location and email modalities
        env = create_environment(
            modality_states={
                "location": location.create_location_state(),
                "email": email.create_email_state(),
            }
        )
        engine = create_simulation_engine(environment=env)
        current_time = engine.environment.time_state.current_time
        
        # Add events
        event1 = create_simulator_event(
            scheduled_time=current_time + timedelta(hours=1),
            modality="location",
            data=location.create_location_input(),
            created_at=current_time,
        )
        event2 = create_simulator_event(
            scheduled_time=current_time + timedelta(hours=3),
            modality="email",
            data=email.create_email_input(),
            created_at=current_time,
        )
        engine.add_event(event1)
        engine.add_event(event2)

        engine.start(auto_advance=False)

        # Skip to first event
        result1 = engine.skip_to_next_event()
        assert result1["events_executed"] == 1
        assert event1.status == EventStatus.EXECUTED

        # Skip to second event
        result2 = engine.skip_to_next_event()
        assert result2["events_executed"] == 1
        assert event2.status == EventStatus.EXECUTED

        # No more events
        result3 = engine.skip_to_next_event()
        assert "No pending events" in result3["message"]

        engine.stop()

    def test_auto_advance_mode_workflow(self):
        """SIMULATION_ENGINE-SPECIFIC: Test complete auto-advance workflow."""
        engine = create_simulation_engine()
        current_time = engine.environment.time_state.current_time
        
        # Add event in very near future
        event = create_simulator_event(
            scheduled_time=current_time + timedelta(milliseconds=50),
            modality="location",
            data=location.create_location_input(),
        )
        engine.add_event(event)

        # Start auto-advance with fast time
        engine.start(auto_advance=True, time_scale=1000.0)

        # Let it run
        time.sleep(0.2)

        # Event should have been executed
        assert event.status == EventStatus.EXECUTED

        # Stop
        engine.stop()

    def test_pause_resume_workflow(self):
        """SIMULATION_ENGINE-SPECIFIC: Test pause and resume behavior."""
        engine = create_simulation_engine()
        current_time = engine.environment.time_state.current_time
        engine.start(auto_advance=True, time_scale=100.0)

        # Let it run
        time.sleep(0.05)
        time_after_run = engine.environment.time_state.current_time

        # Pause
        engine.pause()
        time.sleep(0.05)
        time_after_pause = engine.environment.time_state.current_time

        # Time should not advance while paused
        assert time_after_pause == time_after_run

        # Resume
        engine.resume()
        time.sleep(0.05)
        time_after_resume = engine.environment.time_state.current_time

        # Time should advance after resume
        assert time_after_resume > time_after_pause

        engine.stop()


class TestSimulationEngineEdgeCases:
    """SIMULATION_ENGINE-SPECIFIC: Test edge cases and boundary conditions."""

    def test_empty_event_queue(self):
        """SIMULATION_ENGINE-SPECIFIC: Test simulation with no events."""
        engine = create_simulation_engine()
        engine.start(auto_advance=False)

        result = engine.advance_time(timedelta(hours=1))

        assert result["events_executed"] == 0

    def test_many_simultaneous_events(self):
        """SIMULATION_ENGINE-SPECIFIC: Test handling many events at same time."""
        engine = create_simulation_engine()
        current_time = engine.environment.time_state.current_time
        event_time = current_time + timedelta(hours=1)

        # Add 10 events at same time
        for i in range(10):
            event = create_simulator_event(
                scheduled_time=event_time,
                modality="location",
                data=location.create_location_input(),
            )
            engine.add_event(event)

        engine.start(auto_advance=False)
        result = engine.advance_time(timedelta(hours=2))

        assert result["events_executed"] == 10

    def test_very_fast_time_scale(self):
        """SIMULATION_ENGINE-SPECIFIC: Test extreme time scale."""
        engine = create_simulation_engine()
        engine.start(auto_advance=True, time_scale=10000.0)

        # Should not crash
        time.sleep(0.05)

        engine.stop()

    def test_very_slow_time_scale(self):
        """SIMULATION_ENGINE-SPECIFIC: Test very slow time scale."""
        engine = create_simulation_engine()
        engine.start(auto_advance=True, time_scale=0.001)

        # Should not crash
        time.sleep(0.05)

        engine.stop()
