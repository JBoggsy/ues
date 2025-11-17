"""Event queue model."""

import bisect
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from models.event import EventStatus, SimulatorEvent


class EventQueue(BaseModel):
    """Manages ordered queue of scheduled events.

    Maintains events sorted by scheduled_time and provides methods
    to retrieve due events based on current simulator time.

    The queue serves as both an active event scheduler and a historical
    event log. Executed events remain in the queue for debugging and
    analysis unless explicitly cleared.

    Args:
        events: All events in the queue (pending, executed, failed, etc.).
    """

    events: list[SimulatorEvent] = Field(
        default_factory=list,
        description="All events in the queue, sorted by scheduled_time",
    )

    class Config:
        arbitrary_types_allowed = True

    @property
    def next_event_time(self) -> Optional[datetime]:
        """Timestamp of the next pending event, or None if queue is empty.

        Returns:
            Next pending event's scheduled_time, or None.
        """
        next_event = self.peek_next()
        return next_event.scheduled_time if next_event else None

    @property
    def pending_count(self) -> int:
        """Number of pending events in the queue.

        Returns:
            Count of events with PENDING status.
        """
        return sum(1 for e in self.events if e.status == EventStatus.PENDING)

    @property
    def executed_count(self) -> int:
        """Number of executed events in the queue.

        Returns:
            Count of events with EXECUTED status.
        """
        return sum(1 for e in self.events if e.status == EventStatus.EXECUTED)

    def add_event(self, event: SimulatorEvent) -> None:
        """Add an event to the queue maintaining sorted order.

        Uses bisect to insert in O(n) time (O(log n) search + O(n) insert).
        For bulk inserts, prefer add_events() which sorts once.

        Args:
            event: Event to add.

        Raises:
            ValueError: If event with same event_id already exists.
        """
        # Check for duplicate ID
        if any(e.event_id == event.event_id for e in self.events):
            raise ValueError(f"Event {event.event_id} already exists in queue")

        # Validate event
        errors = event.validate()
        if errors:
            raise ValueError(f"Invalid event: {errors}")

        # Find insertion point using binary search
        insert_index = self._find_insert_index(event)

        # Insert at correct position
        self.events.insert(insert_index, event)

    def add_events(self, events: list[SimulatorEvent]) -> None:
        """Add multiple events to the queue efficiently.

        Merges new events with existing ones and sorts once in O(n log n).
        More efficient than calling add_event() repeatedly.

        Args:
            events: List of events to add.

        Raises:
            ValueError: If any event_id conflicts with existing events.
        """
        # Check for duplicates within new events
        new_ids = [e.event_id for e in events]
        if len(new_ids) != len(set(new_ids)):
            raise ValueError("Duplicate event_ids in new events")

        # Check for conflicts with existing events
        existing_ids = {e.event_id for e in self.events}
        conflicts = existing_ids.intersection(new_ids)
        if conflicts:
            raise ValueError(f"Event IDs already exist in queue: {conflicts}")

        # Validate all new events
        for event in events:
            errors = event.validate()
            if errors:
                raise ValueError(f"Invalid event {event.event_id}: {errors}")

        # Add and sort all at once
        self.events.extend(events)
        self._sort_events()

    def get_due_events(self, current_time: datetime) -> list[SimulatorEvent]:
        """Get all pending events with scheduled_time <= current_time.

        Returns events in execution order (by scheduled_time, then priority).
        Does NOT modify event status - that's the simulation engine's job.

        Args:
            current_time: Current simulator time.

        Returns:
            List of events ready for execution (may be empty).
        """
        due_events = [
            e
            for e in self.events
            if e.status == EventStatus.PENDING and e.scheduled_time <= current_time
        ]
        return due_events

    def peek_next(self) -> Optional[SimulatorEvent]:
        """Get the next pending event without removing it.

        Returns:
            Next pending event, or None if no pending events.
        """
        for event in self.events:
            if event.status == EventStatus.PENDING:
                return event
        return None

    def get_events_by_status(self, status: EventStatus) -> list[SimulatorEvent]:
        """Get all events with a specific status.

        Args:
            status: Status to filter by.

        Returns:
            List of events with matching status.
        """
        return [e for e in self.events if e.status == status]

    def get_events_in_range(
        self,
        start: datetime,
        end: datetime,
        status_filter: Optional[EventStatus] = None,
    ) -> list[SimulatorEvent]:
        """Get events scheduled within a time range.

        Efficient binary search since events are sorted by time.

        Args:
            start: Start of time range (inclusive).
            end: End of time range (inclusive).
            status_filter: Optional status to filter by.

        Returns:
            Events in the specified time range.
        """
        # Find start index using binary search
        start_index = bisect.bisect_left(
            self.events, start, key=lambda e: e.scheduled_time
        )

        # Find end index using binary search
        end_index = bisect.bisect_right(
            self.events, end, key=lambda e: e.scheduled_time
        )

        # Get events in range
        events_in_range = self.events[start_index:end_index]

        # Apply status filter if provided
        if status_filter is not None:
            events_in_range = [e for e in events_in_range if e.status == status_filter]

        return events_in_range

    def remove_event(self, event_id: str) -> SimulatorEvent:
        """Remove an event from the queue.

        Primarily used for cancelling pending events.
        Executed events typically stay in queue for history.

        Args:
            event_id: ID of event to remove.

        Returns:
            The removed event.

        Raises:
            KeyError: If event_id not found.
        """
        for i, event in enumerate(self.events):
            if event.event_id == event_id:
                return self.events.pop(i)

        raise KeyError(f"Event {event_id} not found in queue")

    def clear_executed(self, before: Optional[datetime] = None) -> int:
        """Remove executed/failed events from queue to save memory.

        Args:
            before: Only remove events executed before this time (None = all).

        Returns:
            Number of events removed.
        """
        initial_count = len(self.events)

        if before is None:
            # Remove all executed/failed events
            self.events = [
                e
                for e in self.events
                if e.status not in (EventStatus.EXECUTED, EventStatus.FAILED)
            ]
        else:
            # Remove executed/failed events before specified time
            self.events = [
                e
                for e in self.events
                if not (
                    e.status in (EventStatus.EXECUTED, EventStatus.FAILED)
                    and e.executed_at is not None
                    and e.executed_at < before
                )
            ]

        return initial_count - len(self.events)

    def validate(self) -> list[str]:
        """Validate queue consistency.

        Checks:
        - Events are properly sorted
        - No duplicate event_ids
        - All events are valid (call event.validate())
        - Status counts match actual events

        Returns:
            List of validation errors (empty if valid).
        """
        errors = []

        # Check for duplicate IDs
        event_ids = [e.event_id for e in self.events]
        if len(event_ids) != len(set(event_ids)):
            duplicates = {eid for eid in event_ids if event_ids.count(eid) > 1}
            errors.append(f"Duplicate event IDs found: {duplicates}")

        # Check sorting
        for i in range(len(self.events) - 1):
            curr = self.events[i]
            next_event = self.events[i + 1]

            if curr.scheduled_time > next_event.scheduled_time:
                errors.append(
                    f"Events not sorted: event {i} ({curr.scheduled_time}) "
                    f"is after event {i+1} ({next_event.scheduled_time})"
                )
            elif curr.scheduled_time == next_event.scheduled_time:
                # Check priority ordering (higher priority first)
                if curr.priority < next_event.priority:
                    errors.append(
                        f"Events at same time not sorted by priority: "
                        f"event {i} (priority {curr.priority}) "
                        f"is before event {i+1} (priority {next_event.priority})"
                    )

        # Validate each event
        for i, event in enumerate(self.events):
            event_errors = event.validate()
            if event_errors:
                errors.append(f"Event {i} ({event.event_id}): {event_errors}")

        return errors

    def _sort_events(self) -> None:
        """Sort events by (scheduled_time, -priority, created_at).

        Called after bulk insertions or modifications.
        Negative priority so higher priority executes first.
        """
        self.events.sort(
            key=lambda e: (e.scheduled_time, -e.priority, e.created_at)
        )

    def _find_insert_index(self, event: SimulatorEvent) -> int:
        """Find correct insertion index using binary search.

        Returns index where event should be inserted to maintain sort order.

        Args:
            event: Event to find insertion point for.

        Returns:
            Index where event should be inserted.
        """
        # Custom comparison key matching _sort_events
        class EventKey:
            def __init__(self, scheduled_time: datetime, priority: int, created_at: datetime):
                self.scheduled_time = scheduled_time
                self.priority = priority
                self.created_at = created_at

            def __lt__(self, other):
                if self.scheduled_time != other.scheduled_time:
                    return self.scheduled_time < other.scheduled_time
                if self.priority != other.priority:
                    return self.priority > other.priority  # Higher priority first
                return self.created_at < other.created_at

        event_key = EventKey(event.scheduled_time, event.priority, event.created_at)
        existing_keys = [
            EventKey(e.scheduled_time, e.priority, e.created_at) for e in self.events
        ]

        return bisect.bisect_right(existing_keys, event_key)
