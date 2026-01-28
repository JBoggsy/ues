"""Unit tests for EventQueue scenario serialization.

Tests the to_scenario_dict() and from_scenario_dict() methods that enable
saving and loading EventQueue state for scenario files.

SERIALIZATION TESTS:
    - Round-trip serialization (serialize -> deserialize -> compare)
    - JSON compatibility (ensure dict is JSON-serializable)
    - Event data preserved accurately
    - Event metadata preserved accurately

DESERIALIZATION TESTS:
    - Successful loading of valid data
    - Event ID regeneration (default behavior)
    - Event ID preservation (when regenerate_ids=False)
    - Missing field error handling
    - Invalid data validation errors
    - Proper sorting of loaded events

POLYMORPHIC DESERIALIZATION TESTS:
    - ModalityInput subclasses correctly instantiated
    - Multiple modality types in same queue
"""

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from ues.models.event import EventStatus, SimulatorEvent
from ues.models.queue import EventQueue
from tests.fixtures.core.events import create_simulator_event
from tests.fixtures.core.queues import create_event_queue
from tests.fixtures.modalities.email import create_email_input
from tests.fixtures.modalities.location import create_location_input
from tests.fixtures.modalities.weather import create_weather_input


class TestToScenarioDict:
    """Test to_scenario_dict() serialization method."""

    def test_empty_queue_serialization(self):
        """Test serializing empty event queue."""
        queue = EventQueue()

        result = queue.to_scenario_dict()

        assert "events" in result
        assert result["events"] == []

    def test_single_event_serialization(self):
        """Test serializing queue with single event."""
        event = create_simulator_event()
        queue = EventQueue(events=[event])

        result = queue.to_scenario_dict()

        assert len(result["events"]) == 1
        assert result["events"][0]["event_id"] == event.event_id
        assert result["events"][0]["modality"] == event.modality

    def test_multiple_events_serialization(self):
        """Test serializing queue with multiple events."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        events = [
            create_simulator_event(scheduled_time=now + timedelta(hours=1)),
            create_simulator_event(scheduled_time=now + timedelta(hours=2)),
            create_simulator_event(scheduled_time=now + timedelta(hours=3)),
        ]
        queue = EventQueue(events=events)

        result = queue.to_scenario_dict()

        assert len(result["events"]) == 3

    def test_event_fields_serialized(self):
        """Test all event fields are included in serialization."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        event = create_simulator_event(
            scheduled_time=now + timedelta(hours=1),
            created_at=now,
            priority=5,
            agent_id="test-agent",
            metadata={"custom": "value"},
        )
        queue = EventQueue(events=[event])

        result = queue.to_scenario_dict()

        event_data = result["events"][0]
        assert "event_id" in event_data
        assert "scheduled_time" in event_data
        assert "modality" in event_data
        assert "data" in event_data
        assert "status" in event_data
        assert "created_at" in event_data
        assert "priority" in event_data
        assert event_data["priority"] == 5
        assert event_data["agent_id"] == "test-agent"
        assert event_data["metadata"] == {"custom": "value"}

    def test_result_is_json_serializable(self):
        """Test to_scenario_dict result can be serialized to JSON."""
        queue = EventQueue(events=[create_simulator_event()])

        result = queue.to_scenario_dict()

        # Should not raise
        json_str = json.dumps(result, indent=2)
        assert isinstance(json_str, str)
        assert len(json_str) > 0

    def test_datetime_fields_are_strings(self):
        """Test datetime fields are serialized as ISO strings (mode='json')."""
        queue = EventQueue(events=[create_simulator_event()])

        result = queue.to_scenario_dict()

        event_data = result["events"][0]
        assert isinstance(event_data["scheduled_time"], str)
        assert isinstance(event_data["created_at"], str)

    def test_modality_input_data_preserved(self):
        """Test ModalityInput data is correctly serialized."""
        location_input = create_location_input(
            latitude=40.7128,
            longitude=-74.0060,
        )
        event = create_simulator_event(
            modality="location",
            data=location_input,
        )
        queue = EventQueue(events=[event])

        result = queue.to_scenario_dict()

        event_data = result["events"][0]
        assert event_data["data"]["modality_type"] == "location"
        assert event_data["data"]["latitude"] == 40.7128
        assert event_data["data"]["longitude"] == -74.0060


class TestFromScenarioDict:
    """Test from_scenario_dict() deserialization method."""

    def test_round_trip_empty_queue(self):
        """Test serialize -> deserialize round trip with empty queue."""
        original = EventQueue()

        data = original.to_scenario_dict()
        restored = EventQueue.from_scenario_dict(data)

        assert len(restored.events) == 0

    def test_round_trip_single_event(self):
        """Test serialize -> deserialize round trip with single event."""
        original = EventQueue(events=[create_simulator_event()])

        data = original.to_scenario_dict()
        restored = EventQueue.from_scenario_dict(data)

        assert len(restored.events) == 1
        assert restored.events[0].modality == original.events[0].modality

    def test_round_trip_multiple_events(self):
        """Test serialize -> deserialize round trip with multiple events."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        original = EventQueue(events=[
            create_simulator_event(scheduled_time=now + timedelta(hours=1)),
            create_simulator_event(scheduled_time=now + timedelta(hours=2)),
            create_simulator_event(scheduled_time=now + timedelta(hours=3)),
        ])

        data = original.to_scenario_dict()
        restored = EventQueue.from_scenario_dict(data)

        assert len(restored.events) == 3

    def test_round_trip_via_json(self):
        """Test full JSON round trip (serialize -> JSON -> parse -> deserialize)."""
        original = EventQueue(events=[create_simulator_event()])

        # Serialize to JSON string
        data = original.to_scenario_dict()
        json_str = json.dumps(data)

        # Parse back and deserialize
        parsed_data = json.loads(json_str)
        restored = EventQueue.from_scenario_dict(parsed_data)

        assert len(restored.events) == 1

    def test_event_fields_preserved(self):
        """Test event metadata fields are preserved through round trip."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        event = create_simulator_event(
            scheduled_time=now + timedelta(hours=2),
            created_at=now,
            priority=10,
            agent_id="my-agent",
            metadata={"key": "value"},
        )
        original = EventQueue(events=[event])

        data = original.to_scenario_dict()
        # Use regenerate_ids=False to preserve event_id for comparison
        restored = EventQueue.from_scenario_dict(data, regenerate_ids=False)

        restored_event = restored.events[0]
        assert restored_event.scheduled_time == event.scheduled_time
        assert restored_event.created_at == event.created_at
        assert restored_event.priority == 10
        assert restored_event.agent_id == "my-agent"
        assert restored_event.metadata == {"key": "value"}
        assert restored_event.event_id == event.event_id


class TestEventIdRegeneration:
    """Test event ID regeneration behavior."""

    def test_regenerate_ids_true_generates_new_ids(self):
        """Test regenerate_ids=True (default) creates new event IDs."""
        original_id = str(uuid4())
        event = create_simulator_event()
        event.event_id = original_id
        original = EventQueue(events=[event])

        data = original.to_scenario_dict()
        restored = EventQueue.from_scenario_dict(data, regenerate_ids=True)

        assert restored.events[0].event_id != original_id

    def test_regenerate_ids_false_preserves_ids(self):
        """Test regenerate_ids=False preserves original event IDs."""
        original_id = str(uuid4())
        event = create_simulator_event()
        event.event_id = original_id
        original = EventQueue(events=[event])

        data = original.to_scenario_dict()
        restored = EventQueue.from_scenario_dict(data, regenerate_ids=False)

        assert restored.events[0].event_id == original_id

    def test_regenerate_ids_default_is_true(self):
        """Test that regenerate_ids defaults to True."""
        original_id = str(uuid4())
        event = create_simulator_event()
        event.event_id = original_id
        original = EventQueue(events=[event])

        data = original.to_scenario_dict()
        # Call without regenerate_ids argument
        restored = EventQueue.from_scenario_dict(data)

        assert restored.events[0].event_id != original_id

    def test_regenerated_ids_are_unique(self):
        """Test regenerated IDs are unique across events."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        original = EventQueue(events=[
            create_simulator_event(scheduled_time=now + timedelta(hours=1)),
            create_simulator_event(scheduled_time=now + timedelta(hours=2)),
            create_simulator_event(scheduled_time=now + timedelta(hours=3)),
        ])

        data = original.to_scenario_dict()
        restored = EventQueue.from_scenario_dict(data, regenerate_ids=True)

        ids = [e.event_id for e in restored.events]
        assert len(ids) == len(set(ids))  # All unique


class TestFromScenarioDictErrorHandling:
    """Test error handling in from_scenario_dict()."""

    def test_missing_events_field_raises_error(self):
        """Test ValueError raised when events field is missing."""
        data = {}

        with pytest.raises(ValueError) as exc_info:
            EventQueue.from_scenario_dict(data)

        assert "events" in str(exc_info.value)

    def test_events_not_list_raises_error(self):
        """Test ValueError raised when events is not a list."""
        data = {"events": "not-a-list"}

        with pytest.raises(ValueError) as exc_info:
            EventQueue.from_scenario_dict(data)

        assert "must be a list" in str(exc_info.value)

    def test_invalid_event_data_raises_validation_error(self):
        """Test ValidationError raised for invalid event data."""
        data = {
            "events": [
                {"invalid": "data", "no_required_fields": True}
            ]
        }

        with pytest.raises(ValidationError):
            EventQueue.from_scenario_dict(data)


class TestSortingOnLoad:
    """Test that events are properly sorted after loading."""

    def test_unsorted_events_are_sorted_on_load(self):
        """Test events are sorted by scheduled_time after loading."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        
        # Create events in reverse order
        event1 = create_simulator_event(scheduled_time=now + timedelta(hours=3))
        event2 = create_simulator_event(scheduled_time=now + timedelta(hours=1))
        event3 = create_simulator_event(scheduled_time=now + timedelta(hours=2))
        
        original = EventQueue(events=[event1, event2, event3])

        data = original.to_scenario_dict()
        restored = EventQueue.from_scenario_dict(data)

        # Events should be sorted by scheduled_time
        times = [e.scheduled_time for e in restored.events]
        assert times == sorted(times)

    def test_same_time_events_sorted_by_priority(self):
        """Test events at same time are sorted by priority (higher first)."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        same_time = now + timedelta(hours=1)
        
        event_low = create_simulator_event(scheduled_time=same_time, priority=1)
        event_high = create_simulator_event(scheduled_time=same_time, priority=10)
        event_mid = create_simulator_event(scheduled_time=same_time, priority=5)
        
        original = EventQueue(events=[event_low, event_high, event_mid])

        data = original.to_scenario_dict()
        restored = EventQueue.from_scenario_dict(data)

        priorities = [e.priority for e in restored.events]
        assert priorities == [10, 5, 1]  # Highest first


class TestPolymorphicDeserialization:
    """Test ModalityInput polymorphic deserialization through queue."""

    def test_location_input_deserialized_correctly(self):
        """Test LocationInput is correctly deserialized from queue."""
        from ues.models.modalities import LocationInput

        location_input = create_location_input(
            latitude=37.7749,
            longitude=-122.4194,
        )
        event = create_simulator_event(modality="location", data=location_input)
        original = EventQueue(events=[event])

        data = original.to_scenario_dict()
        json_str = json.dumps(data)
        parsed = json.loads(json_str)
        restored = EventQueue.from_scenario_dict(parsed)

        restored_input = restored.events[0].data
        assert isinstance(restored_input, LocationInput)
        assert restored_input.latitude == 37.7749
        assert restored_input.longitude == -122.4194

    def test_email_input_deserialized_correctly(self):
        """Test EmailInput is correctly deserialized from queue."""
        from ues.models.modalities import EmailInput

        email_input = create_email_input(
            from_address="test@example.com",
            to_addresses=["recipient@example.com"],
            subject="Test Subject",
        )
        event = create_simulator_event(modality="email", data=email_input)
        original = EventQueue(events=[event])

        data = original.to_scenario_dict()
        json_str = json.dumps(data)
        parsed = json.loads(json_str)
        restored = EventQueue.from_scenario_dict(parsed)

        restored_input = restored.events[0].data
        assert isinstance(restored_input, EmailInput)
        assert restored_input.from_address == "test@example.com"
        assert restored_input.subject == "Test Subject"

    def test_mixed_modality_inputs_deserialized(self):
        """Test queue with multiple modality types deserializes correctly."""
        from ues.models.modalities import EmailInput, LocationInput

        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_event = create_simulator_event(
            modality="location",
            scheduled_time=now + timedelta(hours=1),
            data=create_location_input(),
        )
        email_event = create_simulator_event(
            modality="email",
            scheduled_time=now + timedelta(hours=2),
            data=create_email_input(),
        )
        original = EventQueue(events=[location_event, email_event])

        data = original.to_scenario_dict()
        json_str = json.dumps(data)
        parsed = json.loads(json_str)
        restored = EventQueue.from_scenario_dict(parsed)

        assert len(restored.events) == 2
        assert isinstance(restored.events[0].data, LocationInput)
        assert isinstance(restored.events[1].data, EmailInput)


class TestEventStatusSerialization:
    """Test event status is properly serialized and deserialized."""

    def test_pending_status_preserved(self):
        """Test PENDING status is preserved through round trip."""
        event = create_simulator_event()
        event.status = EventStatus.PENDING
        original = EventQueue(events=[event])

        data = original.to_scenario_dict()
        restored = EventQueue.from_scenario_dict(data, regenerate_ids=False)

        assert restored.events[0].status == EventStatus.PENDING

    def test_executed_status_preserved(self):
        """Test EXECUTED status is preserved through round trip."""
        event = create_simulator_event()
        event.status = EventStatus.EXECUTED
        event.executed_at = datetime.now(timezone.utc)
        original = EventQueue(events=[event])

        data = original.to_scenario_dict()
        restored = EventQueue.from_scenario_dict(data, regenerate_ids=False)

        assert restored.events[0].status == EventStatus.EXECUTED
        assert restored.events[0].executed_at is not None

    def test_failed_status_with_error_message(self):
        """Test FAILED status and error_message preserved."""
        event = create_simulator_event()
        event.status = EventStatus.FAILED
        event.error_message = "Something went wrong"
        original = EventQueue(events=[event])

        data = original.to_scenario_dict()
        restored = EventQueue.from_scenario_dict(data, regenerate_ids=False)

        assert restored.events[0].status == EventStatus.FAILED
        assert restored.events[0].error_message == "Something went wrong"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_large_queue_serialization(self):
        """Test serialization of queue with many events."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        events = [
            create_simulator_event(scheduled_time=now + timedelta(minutes=i))
            for i in range(100)
        ]
        original = EventQueue(events=events)

        data = original.to_scenario_dict()
        json_str = json.dumps(data)
        parsed = json.loads(json_str)
        restored = EventQueue.from_scenario_dict(parsed)

        assert len(restored.events) == 100

    def test_does_not_mutate_input_data(self):
        """Test from_scenario_dict doesn't mutate input data."""
        event = create_simulator_event()
        original = EventQueue(events=[event])
        data = original.to_scenario_dict()
        
        original_event_id = data["events"][0]["event_id"]
        
        # Load with ID regeneration
        EventQueue.from_scenario_dict(data, regenerate_ids=True)
        
        # Original data should be unchanged
        assert data["events"][0]["event_id"] == original_event_id

    def test_handles_special_characters_in_metadata(self):
        """Test special characters in metadata are preserved."""
        event = create_simulator_event()
        event.metadata = {
            "emoji": "🎉",
            "unicode": "日本語",
            "quotes": 'He said "hello"',
            "newlines": "line1\nline2",
        }
        original = EventQueue(events=[event])

        data = original.to_scenario_dict()
        json_str = json.dumps(data)
        parsed = json.loads(json_str)
        restored = EventQueue.from_scenario_dict(parsed, regenerate_ids=False)

        assert restored.events[0].metadata == event.metadata
