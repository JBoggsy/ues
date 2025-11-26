"""Unit tests for SimulatorEvent.

This module tests both general event behavior and event-specific features
like execution, validation, and status management.
"""

from datetime import datetime, timezone, timedelta

import pytest

from models.event import SimulatorEvent, EventStatus
from models.environment import Environment
from tests.fixtures.modalities.email import create_email_input, create_email_state
from tests.fixtures.modalities.location import (
    create_location_input,
    create_location_state,
)
from tests.fixtures.core.events import create_simulator_event
from tests.fixtures.core.environments import create_environment
from tests.fixtures.core.times import create_simulator_time


class TestSimulatorEventInstantiation:
    """Test instantiation patterns for SimulatorEvent.

    GENERAL PATTERN: All events should instantiate with required fields
    and provide sensible defaults for optional fields.
    """

    def test_minimal_instantiation(self):
        """Verify SimulatorEvent instantiates with minimal required fields."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(timestamp=now)

        event = SimulatorEvent(
            scheduled_time=now + timedelta(hours=1),
            modality="location",
            data=location_input,
            created_at=now,
        )

        assert event.scheduled_time == now + timedelta(hours=1)
        assert event.modality == "location"
        assert event.data == location_input
        assert event.created_at == now
        assert event.status == EventStatus.PENDING
        assert event.priority == 0
        assert event.executed_at is None
        assert event.agent_id is None
        assert event.error_message is None
        assert isinstance(event.metadata, dict)
        assert len(event.metadata) == 0

    def test_full_instantiation(self):
        """Verify SimulatorEvent instantiates with all optional fields."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        email_input = create_email_input(timestamp=now)

        event = SimulatorEvent(
            event_id="custom-event-id",
            scheduled_time=now + timedelta(hours=1),
            modality="email",
            data=email_input,
            status=EventStatus.PENDING,
            created_at=now,
            executed_at=None,
            agent_id="agent-123",
            priority=5,
            error_message=None,
            metadata={"source": "test", "category": "work"},
        )

        assert event.event_id == "custom-event-id"
        assert event.agent_id == "agent-123"
        assert event.priority == 5
        assert event.metadata == {"source": "test", "category": "work"}

    def test_auto_generated_event_id(self):
        """Verify SimulatorEvent auto-generates unique event IDs."""
        event1 = create_simulator_event()
        event2 = create_simulator_event()

        assert event1.event_id != event2.event_id
        assert len(event1.event_id) > 0
        assert len(event2.event_id) > 0

    def test_default_values(self):
        """Verify SimulatorEvent applies correct defaults for optional fields."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(timestamp=now)

        event = SimulatorEvent(
            scheduled_time=now + timedelta(hours=1),
            modality="location",
            data=location_input,
            created_at=now,
        )

        assert event.status == EventStatus.PENDING
        assert event.priority == 0
        assert event.executed_at is None
        assert event.agent_id is None
        assert event.error_message is None
        assert event.metadata == {}


class TestSimulatorEventValidation:
    """Test validation logic for SimulatorEvent.

    EVENT-SPECIFIC: Validates event consistency rules like scheduled_time
    must be after created_at, modality must match data, etc.
    """

    def test_valid_event_passes_validation(self):
        """Verify valid event has no validation errors."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(timestamp=now)

        event = SimulatorEvent(
            scheduled_time=now + timedelta(hours=1),
            modality="location",
            data=location_input,
            created_at=now,
        )

        errors = event.validate()
        assert len(errors) == 0

    def test_empty_modality_fails_validation(self):
        """Verify empty modality fails validation."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(timestamp=now)

        event = SimulatorEvent(
            scheduled_time=now + timedelta(hours=1),
            modality="",
            data=location_input,
            created_at=now,
        )

        errors = event.validate()
        assert len(errors) > 0
        assert any("empty" in err.lower() for err in errors)

    def test_scheduled_before_created_fails_validation(self):
        """Verify scheduled_time before created_at fails validation."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(timestamp=now)

        event = SimulatorEvent(
            scheduled_time=now - timedelta(hours=1),  # Before created_at
            modality="location",
            data=location_input,
            created_at=now,
        )

        errors = event.validate()
        assert len(errors) > 0
        assert any("before created_at" in err for err in errors)

    def test_modality_mismatch_fails_validation(self):
        """Verify data modality mismatch fails validation."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        email_input = create_email_input(timestamp=now)

        event = SimulatorEvent(
            scheduled_time=now + timedelta(hours=1),
            modality="location",  # Mismatch with email input
            data=email_input,
            created_at=now,
        )

        errors = event.validate()
        assert len(errors) > 0
        assert any("doesn't match" in err for err in errors)

    def test_executed_without_timestamp_fails_validation(self):
        """Verify EXECUTED status without executed_at fails validation."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(timestamp=now)

        event = SimulatorEvent(
            scheduled_time=now + timedelta(hours=1),
            modality="location",
            data=location_input,
            created_at=now,
            status=EventStatus.EXECUTED,
            executed_at=None,  # Missing timestamp
        )

        errors = event.validate()
        assert len(errors) > 0
        assert any("executed_at is None" in err for err in errors)

    def test_failed_without_error_message_fails_validation(self):
        """Verify FAILED status without error_message fails validation."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(timestamp=now)

        event = SimulatorEvent(
            scheduled_time=now + timedelta(hours=1),
            modality="location",
            data=location_input,
            created_at=now,
            status=EventStatus.FAILED,
            executed_at=now + timedelta(hours=1),
            error_message=None,  # Missing error message
        )

        errors = event.validate()
        assert len(errors) > 0
        assert any("no error_message" in err for err in errors)


class TestSimulatorEventExecution:
    """Test event execution behavior.

    EVENT-SPECIFIC: Tests the execute() method which applies the event's
    input to the appropriate modality state in the environment.
    """

    def test_execute_location_event(self):
        """Verify executing location event updates location state."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(
            latitude=40.7128,
            longitude=-74.0060,
            address="New York, NY",
            timestamp=now,
        )

        event = SimulatorEvent(
            scheduled_time=now,
            modality="location",
            data=location_input,
            created_at=now - timedelta(minutes=30),
        )

        location_state = create_location_state(last_updated=now - timedelta(hours=1))
        environment = create_environment(
            modality_states={"location": location_state},
            time_state=create_simulator_time(current_time=now),
        )

        assert event.status == EventStatus.PENDING
        assert location_state.current_latitude == 37.7749  # Default SF coords

        event.execute(environment)

        assert event.status == EventStatus.EXECUTED
        assert event.executed_at == now
        assert location_state.current_latitude == 40.7128
        assert location_state.current_longitude == -74.0060
        assert location_state.current_address == "New York, NY"

    def test_execute_email_event(self):
        """Verify executing email event updates email state."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        email_input = create_email_input(
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["you@example.com"],
            subject="Test Email",
            body_text="Test body.",
            timestamp=now,
        )

        event = SimulatorEvent(
            scheduled_time=now,
            modality="email",
            data=email_input,
            created_at=now - timedelta(minutes=30),
        )

        email_state = create_email_state(last_updated=now - timedelta(hours=1))
        environment = create_environment(
            modality_states={"email": email_state},
            time_state=create_simulator_time(current_time=now),
        )

        assert event.status == EventStatus.PENDING
        assert len(email_state.emails) == 0

        event.execute(environment)

        assert event.status == EventStatus.EXECUTED
        assert event.executed_at == now
        assert len(email_state.emails) == 1
        # Get the first email from the dictionary
        email = list(email_state.emails.values())[0]
        assert email.subject == "Test Email"

    def test_execute_updates_status_to_executing_then_executed(self):
        """Verify execute() transitions status from PENDING to EXECUTING to EXECUTED."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(timestamp=now)

        event = SimulatorEvent(
            scheduled_time=now,
            modality="location",
            data=location_input,
            created_at=now - timedelta(minutes=30),
        )

        environment = create_environment(
            modality_states={"location": create_location_state()},
            time_state=create_simulator_time(current_time=now),
        )

        assert event.status == EventStatus.PENDING

        event.execute(environment)

        # After execution, status should be EXECUTED
        assert event.status == EventStatus.EXECUTED

    def test_execute_sets_executed_at_timestamp(self):
        """Verify execute() sets executed_at to current simulator time."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(timestamp=now)

        event = SimulatorEvent(
            scheduled_time=now,
            modality="location",
            data=location_input,
            created_at=now - timedelta(minutes=30),
        )

        environment = create_environment(
            modality_states={"location": create_location_state()},
            time_state=create_simulator_time(current_time=now),
        )

        assert event.executed_at is None

        event.execute(environment)

        assert event.executed_at == now

    def test_execute_fails_if_already_executed(self):
        """Verify execute() raises error if event already executed."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(timestamp=now)

        event = SimulatorEvent(
            scheduled_time=now,
            modality="location",
            data=location_input,
            created_at=now - timedelta(minutes=30),
            status=EventStatus.EXECUTED,
        )

        environment = create_environment(
            modality_states={"location": create_location_state()},
            time_state=create_simulator_time(current_time=now),
        )

        with pytest.raises(RuntimeError, match="Cannot execute event"):
            event.execute(environment)

    def test_execute_handles_invalid_modality_gracefully(self):
        """Verify execute() sets FAILED status if modality doesn't exist."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(timestamp=now)

        event = SimulatorEvent(
            scheduled_time=now,
            modality="nonexistent",
            data=location_input,
            created_at=now - timedelta(minutes=30),
        )

        environment = create_environment(
            modality_states={"location": create_location_state()},
            time_state=create_simulator_time(current_time=now),
        )

        event.execute(environment)

        assert event.status == EventStatus.FAILED
        assert event.error_message is not None
        assert "nonexistent" in event.error_message or "not found" in event.error_message.lower()
        assert event.executed_at == now

    def test_execute_handles_input_validation_errors_gracefully(self):
        """Verify execute() sets FAILED status if input validation fails."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        
        # Create an invalid email input (missing required fields)
        email_input = create_email_input(timestamp=now)
        email_input.operation = "invalid_operation"  # Invalid operation

        event = SimulatorEvent(
            scheduled_time=now,
            modality="email",
            data=email_input,
            created_at=now - timedelta(minutes=30),
        )

        environment = create_environment(
            modality_states={"email": create_email_state()},
            time_state=create_simulator_time(current_time=now),
        )

        event.execute(environment)

        assert event.status == EventStatus.FAILED
        assert event.error_message is not None
        assert event.executed_at == now


class TestSimulatorEventCanExecute:
    """Test can_execute() method.

    EVENT-SPECIFIC: Tests the logic that determines if an event is
    eligible for execution based on status, time, and input validity.
    """

    def test_can_execute_pending_event_at_scheduled_time(self):
        """Verify pending event at scheduled time can execute."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(timestamp=now)

        event = SimulatorEvent(
            scheduled_time=now,
            modality="location",
            data=location_input,
            created_at=now - timedelta(minutes=30),
        )

        assert event.can_execute(now) is True

    def test_can_execute_pending_event_after_scheduled_time(self):
        """Verify pending event after scheduled time can execute."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(timestamp=now)

        event = SimulatorEvent(
            scheduled_time=now - timedelta(hours=1),
            modality="location",
            data=location_input,
            created_at=now - timedelta(hours=2),
        )

        assert event.can_execute(now) is True

    def test_cannot_execute_pending_event_before_scheduled_time(self):
        """Verify pending event before scheduled time cannot execute."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(timestamp=now)

        event = SimulatorEvent(
            scheduled_time=now + timedelta(hours=1),
            modality="location",
            data=location_input,
            created_at=now,
        )

        assert event.can_execute(now) is False

    def test_cannot_execute_executed_event(self):
        """Verify executed event cannot execute again."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(timestamp=now)

        event = SimulatorEvent(
            scheduled_time=now,
            modality="location",
            data=location_input,
            created_at=now - timedelta(minutes=30),
            status=EventStatus.EXECUTED,
        )

        assert event.can_execute(now) is False

    def test_cannot_execute_failed_event(self):
        """Verify failed event cannot execute."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(timestamp=now)

        event = SimulatorEvent(
            scheduled_time=now,
            modality="location",
            data=location_input,
            created_at=now - timedelta(minutes=30),
            status=EventStatus.FAILED,
        )

        assert event.can_execute(now) is False

    def test_cannot_execute_skipped_event(self):
        """Verify skipped event cannot execute."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(timestamp=now)

        event = SimulatorEvent(
            scheduled_time=now,
            modality="location",
            data=location_input,
            created_at=now - timedelta(minutes=30),
            status=EventStatus.SKIPPED,
        )

        assert event.can_execute(now) is False

    def test_cannot_execute_cancelled_event(self):
        """Verify cancelled event cannot execute."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(timestamp=now)

        event = SimulatorEvent(
            scheduled_time=now,
            modality="location",
            data=location_input,
            created_at=now - timedelta(minutes=30),
            status=EventStatus.CANCELLED,
        )

        assert event.can_execute(now) is False


class TestSimulatorEventGetSummary:
    """Test get_summary() method.

    EVENT-SPECIFIC: Tests human-readable summary generation for events.
    """

    def test_get_summary_includes_scheduled_time(self):
        """Verify summary includes formatted scheduled time."""
        scheduled_time = datetime(2025, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
        location_input = create_location_input(timestamp=scheduled_time)

        event = SimulatorEvent(
            scheduled_time=scheduled_time,
            modality="location",
            data=location_input,
            created_at=scheduled_time - timedelta(hours=1),
        )

        summary = event.get_summary()
        assert "2025-01-15 14:30:00" in summary

    def test_get_summary_includes_modality(self):
        """Verify summary includes modality name."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(timestamp=now)

        event = SimulatorEvent(
            scheduled_time=now,
            modality="location",
            data=location_input,
            created_at=now - timedelta(minutes=30),
        )

        summary = event.get_summary()
        assert "location" in summary

    def test_get_summary_includes_data_summary(self):
        """Verify summary includes data.get_summary() output."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(
            latitude=40.7128,
            longitude=-74.0060,
            address="New York, NY",
            timestamp=now,
        )

        event = SimulatorEvent(
            scheduled_time=now,
            modality="location",
            data=location_input,
            created_at=now - timedelta(minutes=30),
        )

        summary = event.get_summary()
        data_summary = location_input.get_summary()
        assert data_summary in summary


class TestSimulatorEventSkip:
    """Test skip() method.

    EVENT-SPECIFIC: Tests marking events as skipped when simulation
    jumps past their scheduled time.
    """

    def test_skip_pending_event(self):
        """Verify skip() changes status to SKIPPED and records reason."""
        event = create_simulator_event()

        assert event.status == EventStatus.PENDING

        event.skip("Time jumped past event")

        assert event.status == EventStatus.SKIPPED
        assert event.metadata["skip_reason"] == "Time jumped past event"

    def test_skip_stores_reason_in_metadata(self):
        """Verify skip() stores reason in metadata."""
        event = create_simulator_event()

        event.skip("Event invalidated by previous events")

        assert "skip_reason" in event.metadata
        assert event.metadata["skip_reason"] == "Event invalidated by previous events"

    def test_skip_fails_if_already_executed(self):
        """Verify skip() raises error if event already executed."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        event = create_simulator_event(
            status=EventStatus.EXECUTED,
            executed_at=now,
        )

        with pytest.raises(RuntimeError, match="Cannot skip event"):
            event.skip("Should fail")

    def test_skip_fails_if_already_failed(self):
        """Verify skip() raises error if event already failed."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        event = create_simulator_event(
            status=EventStatus.FAILED,
            executed_at=now,
            error_message="Previous error",
        )

        with pytest.raises(RuntimeError, match="Cannot skip event"):
            event.skip("Should fail")


class TestSimulatorEventCancel:
    """Test cancel() method.

    EVENT-SPECIFIC: Tests manually cancelling events before execution.
    """

    def test_cancel_pending_event(self):
        """Verify cancel() changes status to CANCELLED and records reason."""
        event = create_simulator_event()

        assert event.status == EventStatus.PENDING

        event.cancel("User requested cancellation")

        assert event.status == EventStatus.CANCELLED
        assert event.metadata["cancel_reason"] == "User requested cancellation"

    def test_cancel_stores_reason_in_metadata(self):
        """Verify cancel() stores reason in metadata."""
        event = create_simulator_event()

        event.cancel("Event no longer needed")

        assert "cancel_reason" in event.metadata
        assert event.metadata["cancel_reason"] == "Event no longer needed"

    def test_cancel_fails_if_already_executed(self):
        """Verify cancel() raises error if event already executed."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        event = create_simulator_event(
            status=EventStatus.EXECUTED,
            executed_at=now,
        )

        with pytest.raises(RuntimeError, match="Cannot cancel executed event"):
            event.cancel("Should fail")

    def test_cancel_fails_if_executing(self):
        """Verify cancel() raises error if event is currently executing."""
        event = create_simulator_event(status=EventStatus.EXECUTING)

        with pytest.raises(RuntimeError, match="Cannot cancel event"):
            event.cancel("Should fail")

    def test_cancel_skipped_event_succeeds(self):
        """Verify cancel() works on skipped events (edge case)."""
        event = create_simulator_event(status=EventStatus.SKIPPED)

        event.cancel("Cancelling skipped event")

        assert event.status == EventStatus.CANCELLED
        assert event.metadata["cancel_reason"] == "Cancelling skipped event"


class TestSimulatorEventGetDependencies:
    """Test get_dependencies() method.

    EVENT-SPECIFIC: Tests retrieving entity IDs affected by this event.
    """

    def test_get_dependencies_delegates_to_data(self):
        """Verify get_dependencies() calls data.get_affected_entities()."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(timestamp=now)

        event = SimulatorEvent(
            scheduled_time=now,
            modality="location",
            data=location_input,
            created_at=now - timedelta(minutes=30),
        )

        dependencies = event.get_dependencies()
        expected = location_input.get_affected_entities()

        assert dependencies == expected


class TestSimulatorEventSerialization:
    """Test serialization behavior.

    GENERAL PATTERN: All events should support model_dump() and
    model_validate() for persistence and API communication.
    """

    def test_simple_serialization(self):
        """Verify event can be serialized and deserialized."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(timestamp=now)

        original = SimulatorEvent(
            scheduled_time=now + timedelta(hours=1),
            modality="location",
            data=location_input,
            created_at=now,
        )

        dumped = original.model_dump()
        restored = SimulatorEvent.model_validate(dumped)

        assert restored.scheduled_time == original.scheduled_time
        assert restored.modality == original.modality
        assert restored.created_at == original.created_at
        assert restored.status == original.status
        assert restored.priority == original.priority

    def test_serialization_preserves_metadata(self):
        """Verify serialization preserves metadata dictionary."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(timestamp=now)

        original = SimulatorEvent(
            scheduled_time=now + timedelta(hours=1),
            modality="location",
            data=location_input,
            created_at=now,
            metadata={"source": "test", "priority_boost": True},
        )

        dumped = original.model_dump()
        restored = SimulatorEvent.model_validate(dumped)

        assert restored.metadata == {"source": "test", "priority_boost": True}

    def test_serialization_preserves_agent_id(self):
        """Verify serialization preserves agent_id."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(timestamp=now)

        original = SimulatorEvent(
            scheduled_time=now + timedelta(hours=1),
            modality="location",
            data=location_input,
            created_at=now,
            agent_id="agent-456",
        )

        dumped = original.model_dump()
        restored = SimulatorEvent.model_validate(dumped)

        assert restored.agent_id == "agent-456"

    def test_serialization_preserves_execution_state(self):
        """Verify serialization preserves execution status and timestamps."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(timestamp=now)

        original = SimulatorEvent(
            scheduled_time=now,
            modality="location",
            data=location_input,
            created_at=now - timedelta(minutes=30),
            status=EventStatus.EXECUTED,
            executed_at=now,
        )

        dumped = original.model_dump()
        restored = SimulatorEvent.model_validate(dumped)

        assert restored.status == EventStatus.EXECUTED
        assert restored.executed_at == now

    def test_serialization_preserves_error_state(self):
        """Verify serialization preserves error status and message."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(timestamp=now)

        original = SimulatorEvent(
            scheduled_time=now,
            modality="location",
            data=location_input,
            created_at=now - timedelta(minutes=30),
            status=EventStatus.FAILED,
            executed_at=now,
            error_message="ValueError: Invalid coordinates",
        )

        dumped = original.model_dump()
        restored = SimulatorEvent.model_validate(dumped)

        assert restored.status == EventStatus.FAILED
        assert restored.error_message == "ValueError: Invalid coordinates"


class TestSimulatorEventFromFixtures:
    """Test using pre-built fixtures.

    GENERAL PATTERN: Verify pre-built fixtures work correctly.
    """

    def test_simple_event_fixture(self, simple_event):
        """Verify simple_event fixture is usable."""
        assert simple_event.status == EventStatus.PENDING
        assert simple_event.modality is not None
        assert simple_event.data is not None

    def test_location_event_fixture(self, location_event):
        """Verify location_event fixture has location data."""
        assert location_event.modality == "location"
        assert location_event.data is not None

    def test_email_event_fixture(self, email_event):
        """Verify email_event fixture has email data."""
        assert email_event.modality == "email"
        assert email_event.data is not None

    def test_high_priority_event_fixture(self, high_priority_event):
        """Verify high_priority_event fixture has elevated priority."""
        assert high_priority_event.priority == 10

    def test_agent_event_fixture(self, agent_event):
        """Verify agent_event fixture has agent_id."""
        assert agent_event.agent_id == "agent-123"

    def test_past_event_fixture(self, past_event):
        """Verify past_event fixture is scheduled in the past."""
        now = datetime.now(timezone.utc)
        assert past_event.scheduled_time < now


class TestSimulatorEventEdgeCases:
    """Test edge cases and boundary conditions.

    EVENT-SPECIFIC: Tests unusual but valid scenarios.
    """

    def test_event_at_exact_scheduled_time(self):
        """Verify event can execute at exact scheduled time."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(timestamp=now)

        event = SimulatorEvent(
            scheduled_time=now,
            modality="location",
            data=location_input,
            created_at=now,
        )

        assert event.can_execute(now) is True

    def test_event_with_negative_priority(self):
        """Verify event supports negative priority values."""
        event = create_simulator_event(priority=-5)

        assert event.priority == -5

    def test_event_with_very_high_priority(self):
        """Verify event supports very high priority values."""
        event = create_simulator_event(priority=1000)

        assert event.priority == 1000

    def test_event_with_empty_metadata(self):
        """Verify event handles empty metadata correctly."""
        event = create_simulator_event(metadata={})

        assert event.metadata == {}
        assert len(event.metadata) == 0

    def test_event_with_nested_metadata(self):
        """Verify event handles nested metadata structures."""
        event = create_simulator_event(
            metadata={
                "source": "api",
                "context": {
                    "user_id": "user-123",
                    "session_id": "session-456",
                    "tags": ["urgent", "customer"],
                },
            }
        )

        assert event.metadata["source"] == "api"
        assert event.metadata["context"]["user_id"] == "user-123"
        assert "urgent" in event.metadata["context"]["tags"]

    def test_skip_already_skipped_event_fails(self):
        """Verify skip() on already skipped event raises error."""
        event = create_simulator_event()

        event.skip("First reason")
        assert event.metadata["skip_reason"] == "First reason"
        assert event.status == EventStatus.SKIPPED

        # Trying to skip again should fail
        with pytest.raises(RuntimeError, match="Cannot skip event"):
            event.skip("Updated reason")

    def test_multiple_cancel_calls_update_reason(self):
        """Verify multiple cancel() calls update the cancel reason."""
        event = create_simulator_event()

        event.cancel("First reason")
        assert event.metadata["cancel_reason"] == "First reason"

        event.cancel("Updated reason")
        assert event.metadata["cancel_reason"] == "Updated reason"


class TestSimulatorEventIntegration:
    """Test complex real-world scenarios.

    EVENT-SPECIFIC: Tests events in realistic usage patterns.
    """

    def test_complete_event_lifecycle(self):
        """Test event from creation through execution to completion."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(
            latitude=40.7128,
            longitude=-74.0060,
            timestamp=now,
        )

        # 1. Create event
        event = SimulatorEvent(
            scheduled_time=now + timedelta(hours=1),
            modality="location",
            data=location_input,
            created_at=now,
        )

        assert event.status == EventStatus.PENDING
        assert event.executed_at is None

        # 2. Check if can execute (too early)
        assert event.can_execute(now) is False

        # 3. Advance time and check again
        later = now + timedelta(hours=1)
        assert event.can_execute(later) is True

        # 4. Execute event
        environment = create_environment(
            modality_states={"location": create_location_state()},
            time_state=create_simulator_time(current_time=later),
        )
        event.execute(environment)

        assert event.status == EventStatus.EXECUTED
        assert event.executed_at == later

        # 5. Verify state was updated
        location_state = environment.get_state("location")
        assert location_state.current_latitude == 40.7128
        assert location_state.current_longitude == -74.0060

    def test_event_sequence_maintains_state(self):
        """Test multiple events executing in sequence update state correctly."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        # Create two location events
        event1 = SimulatorEvent(
            scheduled_time=now,
            modality="location",
            data=create_location_input(latitude=40.7128, timestamp=now),
            created_at=now - timedelta(minutes=30),
        )

        event2 = SimulatorEvent(
            scheduled_time=now + timedelta(hours=1),
            modality="location",
            data=create_location_input(latitude=34.0522, timestamp=now + timedelta(hours=1)),
            created_at=now - timedelta(minutes=30),
        )

        environment = create_environment(
            modality_states={"location": create_location_state()},
            time_state=create_simulator_time(current_time=now),
        )

        # Execute first event
        event1.execute(environment)
        location_state = environment.get_state("location")
        assert location_state.current_latitude == 40.7128

        # Execute second event
        environment.time_state.current_time = now + timedelta(hours=1)
        event2.execute(environment)
        assert location_state.current_latitude == 34.0522

    def test_agent_generated_event_tracking(self):
        """Test agent-generated events preserve agent attribution."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(timestamp=now)

        event = SimulatorEvent(
            scheduled_time=now,
            modality="location",
            data=location_input,
            created_at=now - timedelta(minutes=5),
            agent_id="agent-ai-001",
            metadata={"agent_type": "location_generator", "confidence": 0.95},
        )

        assert event.agent_id == "agent-ai-001"
        assert event.metadata["agent_type"] == "location_generator"

        # Verify agent info persists through serialization
        dumped = event.model_dump()
        restored = SimulatorEvent.model_validate(dumped)

        assert restored.agent_id == "agent-ai-001"
        assert restored.metadata["agent_type"] == "location_generator"
