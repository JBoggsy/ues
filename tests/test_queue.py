"""Unit tests for EventQueue.

This module tests both general queue behavior and queue-specific features
like ordering, filtering, and bulk operations.
"""

from datetime import datetime, timezone, timedelta

import pytest

from models.queue import EventQueue
from models.event import SimulatorEvent, EventStatus
from tests.fixtures.core.events import create_simulator_event
from tests.fixtures.core.queues import create_event_queue
from tests.fixtures.modalities.location import create_location_input
from tests.fixtures.modalities.email import create_email_input


class TestEventQueueInstantiation:
    """Test instantiation patterns for EventQueue.

    GENERAL PATTERN: All queue instances should support creation
    with empty or populated event lists.
    """

    def test_minimal_instantiation(self):
        """Verify EventQueue instantiates as empty queue."""
        queue = EventQueue()

        assert queue.events == []
        assert len(queue.events) == 0
        assert queue.pending_count == 0
        assert queue.executed_count == 0
        assert queue.next_event_time is None

    def test_instantiation_with_events(self):
        """Verify EventQueue instantiates with provided events."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        events = [
            create_simulator_event(scheduled_time=now + timedelta(hours=1)),
            create_simulator_event(scheduled_time=now + timedelta(hours=2)),
        ]

        queue = EventQueue(events=events)

        assert len(queue.events) == 2
        assert queue.pending_count == 2
        assert queue.events[0].scheduled_time == now + timedelta(hours=1)
        assert queue.events[1].scheduled_time == now + timedelta(hours=2)

    def test_instantiation_with_unsorted_events(self):
        """Verify EventQueue accepts unsorted events (user must sort manually)."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        # Create events in reverse order
        events = [
            create_simulator_event(scheduled_time=now + timedelta(hours=2)),
            create_simulator_event(scheduled_time=now + timedelta(hours=1)),
        ]

        queue = EventQueue(events=events)

        # Queue doesn't auto-sort on instantiation
        assert len(queue.events) == 2
        # Events remain in provided order
        assert queue.events[0].scheduled_time == now + timedelta(hours=2)
        assert queue.events[1].scheduled_time == now + timedelta(hours=1)


class TestEventQueueProperties:
    """Test computed properties for EventQueue.

    QUEUE-SPECIFIC: Tests properties that calculate queue statistics.
    """

    def test_next_event_time_empty_queue(self):
        """Verify next_event_time is None for empty queue."""
        queue = create_event_queue()

        assert queue.next_event_time is None

    def test_next_event_time_with_pending_events(self):
        """Verify next_event_time returns earliest pending event time."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        queue = create_event_queue()
        # Add events in unsorted order
        queue.add_event(create_simulator_event(
            scheduled_time=now + timedelta(hours=2),
            created_at=now - timedelta(minutes=30),
        ))
        queue.add_event(create_simulator_event(
            scheduled_time=now + timedelta(hours=1),
            created_at=now - timedelta(minutes=30),
        ))
        queue.add_event(create_simulator_event(
            scheduled_time=now + timedelta(hours=3),
            created_at=now - timedelta(minutes=30),
        ))

        # Should return earliest event (hour=1)
        assert queue.next_event_time == now + timedelta(hours=1)

    def test_next_event_time_skips_executed_events(self):
        """Verify next_event_time skips executed events."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        queue = create_event_queue(
            events=[
                create_simulator_event(
                    scheduled_time=now + timedelta(hours=1),
                    status=EventStatus.EXECUTED,
                ),
                create_simulator_event(
                    scheduled_time=now + timedelta(hours=2),
                    status=EventStatus.PENDING,
                ),
            ]
        )

        # Should skip executed event and return pending one
        assert queue.next_event_time == now + timedelta(hours=2)

    def test_pending_count_empty_queue(self):
        """Verify pending_count is 0 for empty queue."""
        queue = create_event_queue()

        assert queue.pending_count == 0

    def test_pending_count_with_mixed_status(self):
        """Verify pending_count only counts PENDING events."""
        queue = create_event_queue(
            events=[
                create_simulator_event(status=EventStatus.PENDING),
                create_simulator_event(status=EventStatus.PENDING),
                create_simulator_event(status=EventStatus.EXECUTED),
                create_simulator_event(status=EventStatus.FAILED),
                create_simulator_event(status=EventStatus.PENDING),
            ]
        )

        assert queue.pending_count == 3

    def test_executed_count_empty_queue(self):
        """Verify executed_count is 0 for empty queue."""
        queue = create_event_queue()

        assert queue.executed_count == 0

    def test_executed_count_with_mixed_status(self):
        """Verify executed_count only counts EXECUTED events."""
        queue = create_event_queue(
            events=[
                create_simulator_event(status=EventStatus.PENDING),
                create_simulator_event(status=EventStatus.EXECUTED),
                create_simulator_event(status=EventStatus.EXECUTED),
                create_simulator_event(status=EventStatus.FAILED),
                create_simulator_event(status=EventStatus.EXECUTED),
            ]
        )

        assert queue.executed_count == 3


class TestEventQueueAddEvent:
    """Test add_event() method.

    QUEUE-SPECIFIC: Tests single event insertion with sorting.
    """

    def test_add_event_to_empty_queue(self):
        """Verify adding event to empty queue."""
        queue = create_event_queue()
        event = create_simulator_event()

        assert len(queue.events) == 0

        queue.add_event(event)

        assert len(queue.events) == 1
        assert queue.events[0] == event

    def test_add_event_maintains_time_order(self):
        """Verify add_event maintains chronological order."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        queue = create_event_queue(
            events=[
                create_simulator_event(scheduled_time=now + timedelta(hours=1)),
                create_simulator_event(scheduled_time=now + timedelta(hours=3)),
            ]
        )

        # Add event in middle time-wise
        middle_event = create_simulator_event(scheduled_time=now + timedelta(hours=2))
        queue.add_event(middle_event)

        assert len(queue.events) == 3
        assert queue.events[0].scheduled_time == now + timedelta(hours=1)
        assert queue.events[1].scheduled_time == now + timedelta(hours=2)
        assert queue.events[2].scheduled_time == now + timedelta(hours=3)

    def test_add_event_maintains_priority_order(self):
        """Verify add_event maintains priority order for same time."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        same_time = now + timedelta(hours=1)

        queue = create_event_queue(
            events=[
                create_simulator_event(scheduled_time=same_time, priority=10),
                create_simulator_event(scheduled_time=same_time, priority=1),
            ]
        )

        # Add event with middle priority
        middle_event = create_simulator_event(scheduled_time=same_time, priority=5)
        queue.add_event(middle_event)

        assert len(queue.events) == 3
        # Higher priority comes first
        assert queue.events[0].priority == 10
        assert queue.events[1].priority == 5
        assert queue.events[2].priority == 1

    def test_add_event_rejects_duplicate_id(self):
        """Verify add_event raises error for duplicate event_id."""
        event = create_simulator_event(event_id="test-123")
        queue = create_event_queue(events=[event])

        # Try to add event with same ID
        duplicate = create_simulator_event(event_id="test-123")

        with pytest.raises(ValueError, match="already exists in queue"):
            queue.add_event(duplicate)

    def test_add_event_validates_event(self):
        """Verify add_event rejects invalid events."""
        queue = create_event_queue()
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        # Create invalid event (scheduled before created)
        invalid_event = create_simulator_event(
            scheduled_time=now - timedelta(hours=1),
            created_at=now,
        )

        with pytest.raises(ValueError, match="Invalid event"):
            queue.add_event(invalid_event)


class TestEventQueueAddEvents:
    """Test add_events() bulk insertion method.

    QUEUE-SPECIFIC: Tests efficient bulk event addition.
    """

    def test_add_events_to_empty_queue(self):
        """Verify adding multiple events to empty queue."""
        queue = create_event_queue()
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        events = [
            create_simulator_event(scheduled_time=now + timedelta(hours=i))
            for i in range(5)
        ]

        queue.add_events(events)

        assert len(queue.events) == 5

    def test_add_events_sorts_correctly(self):
        """Verify add_events sorts all events properly."""
        queue = create_event_queue()
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        # Add events in reverse order
        events = [
            create_simulator_event(scheduled_time=now + timedelta(hours=3)),
            create_simulator_event(scheduled_time=now + timedelta(hours=1)),
            create_simulator_event(scheduled_time=now + timedelta(hours=2)),
        ]

        queue.add_events(events)

        # Should be sorted
        assert queue.events[0].scheduled_time == now + timedelta(hours=1)
        assert queue.events[1].scheduled_time == now + timedelta(hours=2)
        assert queue.events[2].scheduled_time == now + timedelta(hours=3)

    def test_add_events_merges_with_existing(self):
        """Verify add_events merges with existing events."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        queue = create_event_queue(
            events=[
                create_simulator_event(scheduled_time=now + timedelta(hours=2)),
                create_simulator_event(scheduled_time=now + timedelta(hours=4)),
            ]
        )

        new_events = [
            create_simulator_event(scheduled_time=now + timedelta(hours=1)),
            create_simulator_event(scheduled_time=now + timedelta(hours=3)),
        ]

        queue.add_events(new_events)

        assert len(queue.events) == 4
        # Should be fully sorted
        assert queue.events[0].scheduled_time == now + timedelta(hours=1)
        assert queue.events[1].scheduled_time == now + timedelta(hours=2)
        assert queue.events[2].scheduled_time == now + timedelta(hours=3)
        assert queue.events[3].scheduled_time == now + timedelta(hours=4)

    def test_add_events_rejects_duplicates_within_batch(self):
        """Verify add_events rejects duplicate IDs in new events."""
        queue = create_event_queue()

        event1 = create_simulator_event(event_id="test-123")
        event2 = create_simulator_event(event_id="test-123")  # Duplicate

        with pytest.raises(ValueError, match="Duplicate event_ids"):
            queue.add_events([event1, event2])

    def test_add_events_rejects_conflicts_with_existing(self):
        """Verify add_events rejects IDs that conflict with existing events."""
        event1 = create_simulator_event(event_id="existing-123")
        queue = create_event_queue(events=[event1])

        event2 = create_simulator_event(event_id="existing-123")

        with pytest.raises(ValueError, match="already exist in queue"):
            queue.add_events([event2])

    def test_add_events_validates_all_events(self):
        """Verify add_events validates all events before adding."""
        queue = create_event_queue()
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        # One valid, one invalid
        events = [
            create_simulator_event(scheduled_time=now + timedelta(hours=1)),
            create_simulator_event(
                scheduled_time=now - timedelta(hours=1),
                created_at=now,  # Invalid: scheduled before created
            ),
        ]

        with pytest.raises(ValueError, match="Invalid event"):
            queue.add_events(events)

        # No events should be added if any is invalid
        assert len(queue.events) == 0


class TestEventQueueGetDueEvents:
    """Test get_due_events() method.

    QUEUE-SPECIFIC: Tests finding events ready for execution.
    """

    def test_get_due_events_empty_queue(self):
        """Verify get_due_events returns empty list for empty queue."""
        queue = create_event_queue()
        now = datetime.now(timezone.utc)

        due_events = queue.get_due_events(now)

        assert due_events == []

    def test_get_due_events_returns_events_at_current_time(self):
        """Verify get_due_events returns events at current time."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        queue = create_event_queue(
            events=[
                create_simulator_event(scheduled_time=now),
                create_simulator_event(scheduled_time=now + timedelta(hours=1)),
            ]
        )

        due_events = queue.get_due_events(now)

        assert len(due_events) == 1
        assert due_events[0].scheduled_time == now

    def test_get_due_events_returns_past_events(self):
        """Verify get_due_events returns events from the past."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        queue = create_event_queue(
            events=[
                create_simulator_event(scheduled_time=now - timedelta(hours=2)),
                create_simulator_event(scheduled_time=now - timedelta(hours=1)),
                create_simulator_event(scheduled_time=now + timedelta(hours=1)),
            ]
        )

        due_events = queue.get_due_events(now)

        assert len(due_events) == 2
        assert all(e.scheduled_time <= now for e in due_events)

    def test_get_due_events_excludes_future_events(self):
        """Verify get_due_events excludes events scheduled in the future."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        queue = create_event_queue(
            events=[
                create_simulator_event(scheduled_time=now + timedelta(hours=1)),
                create_simulator_event(scheduled_time=now + timedelta(hours=2)),
            ]
        )

        due_events = queue.get_due_events(now)

        assert len(due_events) == 0

    def test_get_due_events_only_returns_pending(self):
        """Verify get_due_events only returns PENDING events."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        queue = create_event_queue(
            events=[
                create_simulator_event(
                    scheduled_time=now,
                    status=EventStatus.PENDING,
                ),
                create_simulator_event(
                    scheduled_time=now,
                    status=EventStatus.EXECUTED,
                ),
                create_simulator_event(
                    scheduled_time=now,
                    status=EventStatus.FAILED,
                ),
                create_simulator_event(
                    scheduled_time=now,
                    status=EventStatus.PENDING,
                ),
            ]
        )

        due_events = queue.get_due_events(now)

        assert len(due_events) == 2
        assert all(e.status == EventStatus.PENDING for e in due_events)

    def test_get_due_events_maintains_execution_order(self):
        """Verify get_due_events returns events in execution order."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        same_time = now

        queue = create_event_queue()
        # Add events with different priorities
        queue.add_event(create_simulator_event(
            scheduled_time=same_time,
            created_at=same_time - timedelta(minutes=30),
            priority=1
        ))
        queue.add_event(create_simulator_event(
            scheduled_time=same_time,
            created_at=same_time - timedelta(minutes=30),
            priority=10
        ))
        queue.add_event(create_simulator_event(
            scheduled_time=same_time,
            created_at=same_time - timedelta(minutes=30),
            priority=5
        ))

        due_events = queue.get_due_events(now)

        # Should be ordered by priority (highest first)
        assert len(due_events) == 3
        assert due_events[0].priority == 10
        assert due_events[1].priority == 5
        assert due_events[2].priority == 1

    def test_get_due_events_does_not_modify_queue(self):
        """Verify get_due_events doesn't modify event status."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        queue = create_event_queue(
            events=[
                create_simulator_event(scheduled_time=now),
            ]
        )

        due_events = queue.get_due_events(now)

        assert len(due_events) == 1
        assert due_events[0].status == EventStatus.PENDING
        assert queue.events[0].status == EventStatus.PENDING


class TestEventQueuePeekNext:
    """Test peek_next() method.

    QUEUE-SPECIFIC: Tests looking at next pending event.
    """

    def test_peek_next_empty_queue(self):
        """Verify peek_next returns None for empty queue."""
        queue = create_event_queue()

        assert queue.peek_next() is None

    def test_peek_next_returns_first_pending(self):
        """Verify peek_next returns first pending event."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        queue = create_event_queue(
            events=[
                create_simulator_event(scheduled_time=now + timedelta(hours=1)),
                create_simulator_event(scheduled_time=now + timedelta(hours=2)),
            ]
        )

        next_event = queue.peek_next()

        assert next_event is not None
        assert next_event.scheduled_time == now + timedelta(hours=1)

    def test_peek_next_skips_executed_events(self):
        """Verify peek_next skips non-pending events."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        queue = create_event_queue(
            events=[
                create_simulator_event(
                    scheduled_time=now + timedelta(hours=1),
                    status=EventStatus.EXECUTED,
                ),
                create_simulator_event(
                    scheduled_time=now + timedelta(hours=2),
                    status=EventStatus.PENDING,
                ),
            ]
        )

        next_event = queue.peek_next()

        assert next_event is not None
        assert next_event.scheduled_time == now + timedelta(hours=2)

    def test_peek_next_does_not_remove_event(self):
        """Verify peek_next doesn't remove the event."""
        queue = create_event_queue(
            events=[create_simulator_event()]
        )

        initial_count = len(queue.events)
        next_event = queue.peek_next()

        assert next_event is not None
        assert len(queue.events) == initial_count


class TestEventQueueGetEventsByStatus:
    """Test get_events_by_status() method.

    QUEUE-SPECIFIC: Tests filtering events by execution status.
    """

    def test_get_events_by_status_empty_queue(self):
        """Verify get_events_by_status returns empty list for empty queue."""
        queue = create_event_queue()

        events = queue.get_events_by_status(EventStatus.PENDING)

        assert events == []

    def test_get_events_by_status_pending(self):
        """Verify get_events_by_status filters PENDING events."""
        queue = create_event_queue(
            events=[
                create_simulator_event(status=EventStatus.PENDING),
                create_simulator_event(status=EventStatus.EXECUTED),
                create_simulator_event(status=EventStatus.PENDING),
                create_simulator_event(status=EventStatus.FAILED),
            ]
        )

        pending_events = queue.get_events_by_status(EventStatus.PENDING)

        assert len(pending_events) == 2
        assert all(e.status == EventStatus.PENDING for e in pending_events)

    def test_get_events_by_status_executed(self):
        """Verify get_events_by_status filters EXECUTED events."""
        queue = create_event_queue(
            events=[
                create_simulator_event(status=EventStatus.PENDING),
                create_simulator_event(status=EventStatus.EXECUTED),
                create_simulator_event(status=EventStatus.EXECUTED),
                create_simulator_event(status=EventStatus.FAILED),
            ]
        )

        executed_events = queue.get_events_by_status(EventStatus.EXECUTED)

        assert len(executed_events) == 2
        assert all(e.status == EventStatus.EXECUTED for e in executed_events)

    def test_get_events_by_status_failed(self):
        """Verify get_events_by_status filters FAILED events."""
        queue = create_event_queue(
            events=[
                create_simulator_event(status=EventStatus.PENDING),
                create_simulator_event(status=EventStatus.FAILED),
                create_simulator_event(status=EventStatus.EXECUTED),
            ]
        )

        failed_events = queue.get_events_by_status(EventStatus.FAILED)

        assert len(failed_events) == 1
        assert failed_events[0].status == EventStatus.FAILED

    def test_get_events_by_status_no_matches(self):
        """Verify get_events_by_status returns empty when no matches."""
        queue = create_event_queue(
            events=[
                create_simulator_event(status=EventStatus.PENDING),
                create_simulator_event(status=EventStatus.PENDING),
            ]
        )

        failed_events = queue.get_events_by_status(EventStatus.FAILED)

        assert failed_events == []


class TestEventQueueGetEventsInRange:
    """Test get_events_in_range() method.

    QUEUE-SPECIFIC: Tests time-based event filtering.
    """

    def test_get_events_in_range_empty_queue(self):
        """Verify get_events_in_range returns empty for empty queue."""
        queue = create_event_queue()
        now = datetime.now(timezone.utc)

        events = queue.get_events_in_range(
            start=now,
            end=now + timedelta(hours=1),
        )

        assert events == []

    def test_get_events_in_range_inclusive_boundaries(self):
        """Verify get_events_in_range includes events at boundaries."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        queue = create_event_queue(
            events=[
                create_simulator_event(scheduled_time=now),  # At start
                create_simulator_event(scheduled_time=now + timedelta(hours=1)),  # At end
                create_simulator_event(scheduled_time=now + timedelta(hours=2)),  # After
            ]
        )

        events = queue.get_events_in_range(
            start=now,
            end=now + timedelta(hours=1),
        )

        assert len(events) == 2
        assert events[0].scheduled_time == now
        assert events[1].scheduled_time == now + timedelta(hours=1)

    def test_get_events_in_range_excludes_outside_range(self):
        """Verify get_events_in_range excludes events outside range."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        queue = create_event_queue(
            events=[
                create_simulator_event(scheduled_time=now - timedelta(hours=1)),  # Before
                create_simulator_event(scheduled_time=now + timedelta(hours=1)),  # Inside
                create_simulator_event(scheduled_time=now + timedelta(hours=3)),  # After
            ]
        )

        events = queue.get_events_in_range(
            start=now,
            end=now + timedelta(hours=2),
        )

        assert len(events) == 1
        assert events[0].scheduled_time == now + timedelta(hours=1)

    def test_get_events_in_range_with_status_filter(self):
        """Verify get_events_in_range filters by status."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        queue = create_event_queue(
            events=[
                create_simulator_event(
                    scheduled_time=now,
                    status=EventStatus.PENDING,
                ),
                create_simulator_event(
                    scheduled_time=now + timedelta(minutes=30),
                    status=EventStatus.EXECUTED,
                ),
                create_simulator_event(
                    scheduled_time=now + timedelta(hours=1),
                    status=EventStatus.PENDING,
                ),
            ]
        )

        events = queue.get_events_in_range(
            start=now,
            end=now + timedelta(hours=2),
            status_filter=EventStatus.PENDING,
        )

        assert len(events) == 2
        assert all(e.status == EventStatus.PENDING for e in events)

    def test_get_events_in_range_no_matches(self):
        """Verify get_events_in_range returns empty when no events in range."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        queue = create_event_queue(
            events=[
                create_simulator_event(scheduled_time=now - timedelta(hours=5)),
                create_simulator_event(scheduled_time=now + timedelta(hours=5)),
            ]
        )

        events = queue.get_events_in_range(
            start=now,
            end=now + timedelta(hours=1),
        )

        assert events == []


class TestEventQueueRemoveEvent:
    """Test remove_event() method.

    QUEUE-SPECIFIC: Tests event removal from queue.
    """

    def test_remove_event_by_id(self):
        """Verify remove_event removes event by ID."""
        event = create_simulator_event(event_id="test-123")
        queue = create_event_queue(events=[event])

        assert len(queue.events) == 1

        removed = queue.remove_event("test-123")

        assert len(queue.events) == 0
        assert removed.event_id == "test-123"

    def test_remove_event_returns_removed_event(self):
        """Verify remove_event returns the removed event."""
        event = create_simulator_event(event_id="test-123")
        queue = create_event_queue(events=[event])

        removed = queue.remove_event("test-123")

        assert removed is event

    def test_remove_event_not_found_raises_error(self):
        """Verify remove_event raises KeyError for missing ID."""
        queue = create_event_queue()

        with pytest.raises(KeyError, match="not found in queue"):
            queue.remove_event("nonexistent-id")

    def test_remove_event_from_multiple(self):
        """Verify remove_event removes correct event from multiple."""
        event1 = create_simulator_event(event_id="id-1")
        event2 = create_simulator_event(event_id="id-2")
        event3 = create_simulator_event(event_id="id-3")

        queue = create_event_queue(events=[event1, event2, event3])

        removed = queue.remove_event("id-2")

        assert len(queue.events) == 2
        assert removed.event_id == "id-2"
        assert queue.events[0].event_id == "id-1"
        assert queue.events[1].event_id == "id-3"


class TestEventQueueClearExecuted:
    """Test clear_executed() method.

    QUEUE-SPECIFIC: Tests pruning old events from queue.
    """

    def test_clear_executed_removes_executed_events(self):
        """Verify clear_executed removes EXECUTED events."""
        queue = create_event_queue(
            events=[
                create_simulator_event(status=EventStatus.PENDING),
                create_simulator_event(status=EventStatus.EXECUTED),
                create_simulator_event(status=EventStatus.EXECUTED),
            ]
        )

        count = queue.clear_executed()

        assert count == 2
        assert len(queue.events) == 1
        assert queue.events[0].status == EventStatus.PENDING

    def test_clear_executed_removes_failed_events(self):
        """Verify clear_executed removes FAILED events."""
        queue = create_event_queue(
            events=[
                create_simulator_event(status=EventStatus.PENDING),
                create_simulator_event(status=EventStatus.FAILED),
                create_simulator_event(status=EventStatus.FAILED),
            ]
        )

        count = queue.clear_executed()

        assert count == 2
        assert len(queue.events) == 1

    def test_clear_executed_preserves_pending(self):
        """Verify clear_executed preserves PENDING events."""
        queue = create_event_queue(
            events=[
                create_simulator_event(status=EventStatus.PENDING),
                create_simulator_event(status=EventStatus.EXECUTED),
            ]
        )

        queue.clear_executed()

        assert len(queue.events) == 1
        assert queue.events[0].status == EventStatus.PENDING

    def test_clear_executed_with_time_filter(self):
        """Verify clear_executed only removes events executed before cutoff."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        queue = create_event_queue(
            events=[
                create_simulator_event(
                    status=EventStatus.EXECUTED,
                    executed_at=now - timedelta(hours=2),
                ),
                create_simulator_event(
                    status=EventStatus.EXECUTED,
                    executed_at=now - timedelta(hours=1),
                ),
                create_simulator_event(
                    status=EventStatus.EXECUTED,
                    executed_at=now,
                ),
            ]
        )

        # Remove events executed before (now - 1.5 hours)
        count = queue.clear_executed(before=now - timedelta(hours=1, minutes=30))

        assert count == 1  # Only the -2 hours event
        assert len(queue.events) == 2

    def test_clear_executed_returns_count(self):
        """Verify clear_executed returns number of removed events."""
        queue = create_event_queue(
            events=[
                create_simulator_event(status=EventStatus.EXECUTED),
                create_simulator_event(status=EventStatus.FAILED),
                create_simulator_event(status=EventStatus.EXECUTED),
            ]
        )

        count = queue.clear_executed()

        assert count == 3

    def test_clear_executed_empty_queue(self):
        """Verify clear_executed handles empty queue."""
        queue = create_event_queue()

        count = queue.clear_executed()

        assert count == 0
        assert len(queue.events) == 0


class TestEventQueueValidate:
    """Test validate() method.

    QUEUE-SPECIFIC: Tests queue consistency validation.
    """

    def test_validate_empty_queue(self):
        """Verify validate returns no errors for empty queue."""
        queue = create_event_queue()

        errors = queue.validate()

        assert errors == []

    def test_validate_well_formed_queue(self):
        """Verify validate returns no errors for valid queue."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        queue = create_event_queue()
        queue.add_event(create_simulator_event(
            scheduled_time=now + timedelta(hours=1),
            created_at=now - timedelta(minutes=30),
        ))
        queue.add_event(create_simulator_event(
            scheduled_time=now + timedelta(hours=2),
            created_at=now - timedelta(minutes=30),
        ))

        errors = queue.validate()

        assert errors == []

    def test_validate_detects_duplicate_ids(self):
        """Verify validate detects duplicate event IDs."""
        event1 = create_simulator_event(event_id="test-123")
        event2 = create_simulator_event(event_id="test-123")

        # Bypass add_event validation by constructing queue directly
        queue = EventQueue(events=[event1, event2])

        errors = queue.validate()

        assert len(errors) > 0
        assert any("Duplicate event IDs" in err for err in errors)

    def test_validate_detects_wrong_time_order(self):
        """Verify validate detects incorrect time ordering."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        # Create events in wrong order
        event1 = create_simulator_event(scheduled_time=now + timedelta(hours=2))
        event2 = create_simulator_event(scheduled_time=now + timedelta(hours=1))

        queue = EventQueue(events=[event1, event2])

        errors = queue.validate()

        assert len(errors) > 0
        assert any("not sorted" in err for err in errors)

    def test_validate_detects_wrong_priority_order(self):
        """Verify validate detects incorrect priority ordering."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        same_time = now + timedelta(hours=1)

        # Create events at same time with wrong priority order
        event1 = create_simulator_event(scheduled_time=same_time, priority=1)
        event2 = create_simulator_event(scheduled_time=same_time, priority=10)

        queue = EventQueue(events=[event1, event2])

        errors = queue.validate()

        assert len(errors) > 0
        assert any("priority" in err for err in errors)

    def test_validate_checks_individual_events(self):
        """Verify validate checks each event's validity."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        # Create invalid event (scheduled before created)
        invalid_event = create_simulator_event(
            scheduled_time=now - timedelta(hours=1),
            created_at=now,
        )

        queue = EventQueue(events=[invalid_event])

        errors = queue.validate()

        assert len(errors) > 0


class TestEventQueueSortEvents:
    """Test _sort_events() internal method.

    QUEUE-SPECIFIC: Tests internal sorting logic.
    """

    def test_sort_events_by_time(self):
        """Verify _sort_events orders by scheduled_time."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        queue = create_event_queue()
        queue.events = [
            create_simulator_event(scheduled_time=now + timedelta(hours=3)),
            create_simulator_event(scheduled_time=now + timedelta(hours=1)),
            create_simulator_event(scheduled_time=now + timedelta(hours=2)),
        ]

        queue._sort_events()

        assert queue.events[0].scheduled_time == now + timedelta(hours=1)
        assert queue.events[1].scheduled_time == now + timedelta(hours=2)
        assert queue.events[2].scheduled_time == now + timedelta(hours=3)

    def test_sort_events_by_priority(self):
        """Verify _sort_events orders by priority (high to low) for same time."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        same_time = now + timedelta(hours=1)

        queue = create_event_queue()
        queue.events = [
            create_simulator_event(scheduled_time=same_time, priority=1),
            create_simulator_event(scheduled_time=same_time, priority=10),
            create_simulator_event(scheduled_time=same_time, priority=5),
        ]

        queue._sort_events()

        assert queue.events[0].priority == 10
        assert queue.events[1].priority == 5
        assert queue.events[2].priority == 1

    def test_sort_events_by_created_at(self):
        """Verify _sort_events uses created_at as tiebreaker."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        same_time = now + timedelta(hours=1)
        same_priority = 5

        queue = create_event_queue()
        queue.events = [
            create_simulator_event(
                scheduled_time=same_time,
                priority=same_priority,
                created_at=now + timedelta(minutes=3),
            ),
            create_simulator_event(
                scheduled_time=same_time,
                priority=same_priority,
                created_at=now + timedelta(minutes=1),
            ),
            create_simulator_event(
                scheduled_time=same_time,
                priority=same_priority,
                created_at=now + timedelta(minutes=2),
            ),
        ]

        queue._sort_events()

        assert queue.events[0].created_at == now + timedelta(minutes=1)
        assert queue.events[1].created_at == now + timedelta(minutes=2)
        assert queue.events[2].created_at == now + timedelta(minutes=3)


class TestEventQueueSerialization:
    """Test serialization behavior.

    GENERAL PATTERN: All queues should support model_dump() and
    model_validate() for persistence and API communication.
    """

    def test_simple_serialization(self):
        """Verify queue can be serialized and deserialized."""
        queue = create_event_queue()

        dumped = queue.model_dump()
        restored = EventQueue.model_validate(dumped)

        assert len(restored.events) == 0
        assert restored.pending_count == 0

    def test_serialization_preserves_events(self):
        """Verify serialization preserves all events."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        location_input = create_location_input(timestamp=now)

        original = create_event_queue(
            events=[
                SimulatorEvent(
                    scheduled_time=now + timedelta(hours=1),
                    modality="location",
                    data=location_input,
                    created_at=now,
                ),
            ]
        )

        dumped = original.model_dump()
        restored = EventQueue.model_validate(dumped)

        assert len(restored.events) == 1
        assert restored.events[0].modality == "location"
        assert restored.events[0].scheduled_time == now + timedelta(hours=1)

    def test_serialization_preserves_event_order(self):
        """Verify serialization preserves event ordering."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        original = create_event_queue(
            events=[
                create_simulator_event(scheduled_time=now + timedelta(hours=1)),
                create_simulator_event(scheduled_time=now + timedelta(hours=2)),
                create_simulator_event(scheduled_time=now + timedelta(hours=3)),
            ]
        )

        dumped = original.model_dump()
        restored = EventQueue.model_validate(dumped)

        for i in range(3):
            assert (
                restored.events[i].scheduled_time
                == original.events[i].scheduled_time
            )


class TestEventQueueFromFixtures:
    """Test using pre-built fixtures.

    GENERAL PATTERN: Verify pre-built fixtures work correctly.
    """

    def test_empty_queue_fixture(self, empty_queue):
        """Verify empty_queue fixture is usable."""
        assert len(empty_queue.events) == 0
        assert empty_queue.pending_count == 0

    def test_queue_with_events_fixture(self, queue_with_events):
        """Verify queue_with_events fixture has events."""
        assert len(queue_with_events.events) > 0
        assert queue_with_events.pending_count > 0

    def test_queue_with_mixed_status_fixture(self, queue_with_mixed_status):
        """Verify queue_with_mixed_status fixture has various statuses."""
        statuses = {e.status for e in queue_with_mixed_status.events}
        assert len(statuses) > 1  # Multiple different statuses

    def test_queue_with_priorities_fixture(self, queue_with_priorities):
        """Verify queue_with_priorities fixture has priority events."""
        priorities = {e.priority for e in queue_with_priorities.events}
        assert len(priorities) > 1  # Multiple different priorities


class TestEventQueueEdgeCases:
    """Test edge cases and boundary conditions.

    QUEUE-SPECIFIC: Tests unusual but valid scenarios.
    """

    def test_queue_with_many_events(self):
        """Verify queue handles large number of events."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        events = [
            create_simulator_event(scheduled_time=now + timedelta(minutes=i))
            for i in range(1000)
        ]

        queue = create_event_queue()
        queue.add_events(events)

        assert len(queue.events) == 1000
        assert queue.pending_count == 1000

    def test_queue_with_all_same_time(self):
        """Verify queue handles many events at same time."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        same_time = now + timedelta(hours=1)

        events = [
            create_simulator_event(scheduled_time=same_time)
            for _ in range(10)
        ]

        queue = create_event_queue()
        queue.add_events(events)

        assert len(queue.events) == 10
        assert all(e.scheduled_time == same_time for e in queue.events)

    def test_queue_with_negative_priorities(self):
        """Verify queue handles negative priorities."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        same_time = now + timedelta(hours=1)

        queue = create_event_queue()
        queue.events = [
            create_simulator_event(scheduled_time=same_time, priority=-10),
            create_simulator_event(scheduled_time=same_time, priority=-5),
            create_simulator_event(scheduled_time=same_time, priority=-1),
        ]

        queue._sort_events()

        # Higher (less negative) comes first
        assert queue.events[0].priority == -1
        assert queue.events[1].priority == -5
        assert queue.events[2].priority == -10

    def test_add_event_to_queue_with_thousands(self):
        """Verify add_event remains efficient with large queues."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        queue = create_event_queue()
        queue.add_events([
            create_simulator_event(scheduled_time=now + timedelta(hours=i))
            for i in range(1000)
        ])

        # Add one more in the middle
        middle_event = create_simulator_event(
            scheduled_time=now + timedelta(hours=500, minutes=30)
        )
        queue.add_event(middle_event)

        assert len(queue.events) == 1001


class TestEventQueueIntegration:
    """Test complex real-world scenarios.

    QUEUE-SPECIFIC: Tests queues in realistic usage patterns.
    """

    def test_simulation_event_cycle(self):
        """Test complete simulation cycle with queue."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        # 1. Create queue with scheduled events
        queue = create_event_queue(
            events=[
                create_simulator_event(scheduled_time=now + timedelta(hours=1)),
                create_simulator_event(scheduled_time=now + timedelta(hours=2)),
                create_simulator_event(scheduled_time=now + timedelta(hours=3)),
            ]
        )

        assert queue.pending_count == 3

        # 2. Time advances - get due events
        current_time = now + timedelta(hours=1, minutes=30)
        due_events = queue.get_due_events(current_time)

        assert len(due_events) == 1

        # 3. Mark event as executed
        due_events[0].status = EventStatus.EXECUTED
        due_events[0].executed_at = current_time

        assert queue.pending_count == 2
        assert queue.executed_count == 1

        # 4. Time advances again
        current_time = now + timedelta(hours=3)
        due_events = queue.get_due_events(current_time)

        assert len(due_events) == 2

    def test_agent_adds_events_during_simulation(self):
        """Test agent adding events to running simulation."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        queue = create_event_queue(
            events=[
                create_simulator_event(scheduled_time=now + timedelta(hours=1)),
            ]
        )

        assert len(queue.events) == 1

        # Agent generates new event
        agent_event = create_simulator_event(
            scheduled_time=now + timedelta(hours=2),
            agent_id="agent-123",
        )
        queue.add_event(agent_event)

        assert len(queue.events) == 2
        assert queue.events[1].agent_id == "agent-123"

    def test_bulk_event_scheduling(self):
        """Test scheduling many events at once."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        queue = create_event_queue()

        # Simulate loading scenario from configuration
        scenario_events = [
            create_simulator_event(
                scheduled_time=now + timedelta(hours=i),
                created_at=now - timedelta(minutes=30),
                modality=["email", "location"][i % 2],
            )
            for i in range(50)
        ]

        queue.add_events(scenario_events)

        assert len(queue.events) == 50
        assert queue.validate() == []  # All valid

    def test_queue_cleanup_after_long_simulation(self):
        """Test cleaning up old events after long simulation."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        # Create events spanning several days
        queue = create_event_queue()
        for day in range(7):
            for hour in range(24):
                event = create_simulator_event(
                    scheduled_time=now + timedelta(days=day, hours=hour),
                    status=EventStatus.EXECUTED,
                    executed_at=now + timedelta(days=day, hours=hour),
                )
                queue.events.append(event)

        initial_count = len(queue.events)
        assert initial_count == 168  # 7 days * 24 hours

        # Clear events older than 3 days
        cutoff = now + timedelta(days=3)
        removed = queue.clear_executed(before=cutoff)

        assert removed == 72  # 3 days * 24 hours
        assert len(queue.events) == 96  # 4 days * 24 hours
