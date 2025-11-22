"""Fixtures for EventQueue."""

from datetime import datetime, timezone, timedelta

import pytest

from models.queue import EventQueue
from models.event import SimulatorEvent, EventStatus
from tests.fixtures.core.events import create_simulator_event


def create_event_queue(
    events: list[SimulatorEvent] | None = None,
) -> EventQueue:
    """Create an EventQueue with optional events.

    Args:
        events: List of events to populate queue with (default: empty).

    Returns:
        EventQueue instance ready for testing.
    """
    return EventQueue(events=events or [])


# Pre-built example constants
EMPTY_QUEUE = create_event_queue()

QUEUE_WITH_EVENTS = create_event_queue(
    events=[
        create_simulator_event(
            modality="email",
            scheduled_time=datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        ),
        create_simulator_event(
            modality="location",
            scheduled_time=datetime(2025, 1, 15, 11, 0, 0, tzinfo=timezone.utc),
        ),
        create_simulator_event(
            modality="sms",
            scheduled_time=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        ),
    ]
)

QUEUE_WITH_MIXED_STATUS = create_event_queue(
    events=[
        create_simulator_event(
            modality="email",
            scheduled_time=datetime(2025, 1, 15, 9, 0, 0, tzinfo=timezone.utc),
            status=EventStatus.EXECUTED,
            executed_at=datetime(2025, 1, 15, 9, 0, 1, tzinfo=timezone.utc),
        ),
        create_simulator_event(
            modality="location",
            scheduled_time=datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            status=EventStatus.PENDING,
        ),
        create_simulator_event(
            modality="sms",
            scheduled_time=datetime(2025, 1, 15, 11, 0, 0, tzinfo=timezone.utc),
            status=EventStatus.FAILED,
            error_message="Network error",
            executed_at=datetime(2025, 1, 15, 11, 0, 2, tzinfo=timezone.utc),
        ),
    ]
)

QUEUE_WITH_PRIORITIES = create_event_queue(
    events=[
        create_simulator_event(
            modality="email",
            scheduled_time=datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            priority=10,
        ),
        create_simulator_event(
            modality="sms",
            scheduled_time=datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            priority=5,
        ),
        create_simulator_event(
            modality="location",
            scheduled_time=datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            priority=1,
        ),
    ]
)


# Pytest fixtures
@pytest.fixture
def empty_queue():
    """Provide an empty event queue for testing."""
    return create_event_queue()


@pytest.fixture
def queue_with_events():
    """Provide a queue with several pending events."""
    now = datetime.now(timezone.utc)
    return create_event_queue(
        events=[
            create_simulator_event(scheduled_time=now + timedelta(hours=1)),
            create_simulator_event(scheduled_time=now + timedelta(hours=2)),
            create_simulator_event(scheduled_time=now + timedelta(hours=3)),
        ]
    )


@pytest.fixture
def queue_with_mixed_status():
    """Provide a queue with events in different statuses."""
    now = datetime.now(timezone.utc)
    return create_event_queue(
        events=[
            create_simulator_event(
                scheduled_time=now - timedelta(hours=2),
                status=EventStatus.EXECUTED,
                executed_at=now - timedelta(hours=2),
            ),
            create_simulator_event(
                scheduled_time=now + timedelta(hours=1),
                status=EventStatus.PENDING,
            ),
            create_simulator_event(
                scheduled_time=now - timedelta(hours=1),
                status=EventStatus.FAILED,
                error_message="Test error",
                executed_at=now - timedelta(hours=1),
            ),
        ]
    )


@pytest.fixture
def queue_with_priorities():
    """Provide a queue with events at same time but different priorities."""
    now = datetime.now(timezone.utc)
    same_time = now + timedelta(hours=1)
    return create_event_queue(
        events=[
            create_simulator_event(scheduled_time=same_time, priority=10),
            create_simulator_event(scheduled_time=same_time, priority=5),
            create_simulator_event(scheduled_time=same_time, priority=1),
        ]
    )
