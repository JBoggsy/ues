"""Fixtures for SimulatorEvent."""

from datetime import datetime, timezone, timedelta
from typing import Any

import pytest

from models.event import SimulatorEvent, EventStatus
from tests.fixtures.modalities.email import create_email_input
from tests.fixtures.modalities.location import create_location_input


def create_simulator_event(
    modality: str = "email",
    scheduled_time: datetime | None = None,
    data: Any | None = None,
    created_at: datetime | None = None,
    **kwargs,
) -> SimulatorEvent:
    """Create a SimulatorEvent with sensible defaults.

    Args:
        modality: Which modality this event affects.
        scheduled_time: When event should execute (defaults to now + 1 hour).
        data: The ModalityInput payload (defaults to appropriate input for modality).
        created_at: When event was created (defaults to now or before scheduled_time).
        **kwargs: Additional fields to override.

    Returns:
        SimulatorEvent instance ready for testing.
    """
    now = datetime.now(timezone.utc)
    
    # Set scheduled_time
    if scheduled_time is None:
        scheduled_time = now + timedelta(hours=1)
    
    # Set created_at (ensure it's before scheduled_time)
    if created_at is None:
        # If scheduled_time is in the past, set created_at earlier
        if scheduled_time < now:
            created_at = scheduled_time - timedelta(minutes=30)
        else:
            created_at = now
    
    # Create appropriate data if not provided
    if data is None:
        timestamp = min(scheduled_time, created_at)
        if modality == "email":
            data = create_email_input(timestamp=timestamp)
        elif modality == "location":
            data = create_location_input(timestamp=timestamp)
        else:
            # For other modalities, use a simple input
            data = create_location_input(timestamp=timestamp)
    
    return SimulatorEvent(
        modality=modality,
        scheduled_time=scheduled_time,
        data=data,
        created_at=created_at,
        **kwargs,
    )


# Pre-built example constants
SIMPLE_EVENT = create_simulator_event(
    modality="location",
    data={"latitude": 37.7749, "longitude": -122.4194},
)

EMAIL_EVENT = create_simulator_event(
    modality="email",
    data={
        "from_address": "sender@example.com",
        "to_addresses": ["recipient@example.com"],
        "subject": "Test Email",
        "body_text": "This is a test.",
    },
)

LOCATION_EVENT = create_simulator_event(
    modality="location",
    scheduled_time=datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
    data={
        "latitude": 40.7128,
        "longitude": -74.0060,
        "address": "New York, NY",
    },
)

HIGH_PRIORITY_EVENT = create_simulator_event(
    modality="email",
    priority=10,
    data={"subject": "URGENT: Action Required"},
)

EXECUTED_EVENT = create_simulator_event(
    modality="location",
    status=EventStatus.EXECUTED,
    executed_at=datetime.now(timezone.utc),
)

FAILED_EVENT = create_simulator_event(
    modality="email",
    status=EventStatus.FAILED,
    error_message="Invalid email address",
    executed_at=datetime.now(timezone.utc),
)

AGENT_GENERATED_EVENT = create_simulator_event(
    modality="sms",
    agent_id="agent-001",
    data={"from": "+15551234567", "body": "AI generated message"},
)


# Invalid examples for validation testing
INVALID_EVENTS = {
    "empty_modality": {
        "modality": "",
        "scheduled_time": datetime.now(timezone.utc),
        "data": {},
        "created_at": datetime.now(timezone.utc),
    },
    "scheduled_before_created": {
        "modality": "email",
        "scheduled_time": datetime(2025, 1, 1, tzinfo=timezone.utc),
        "data": {},
        "created_at": datetime(2025, 1, 2, tzinfo=timezone.utc),
    },
}


# JSON fixtures for API testing
EVENT_JSON_EXAMPLES = {
    "simple": {
        "modality": "location",
        "scheduled_time": "2025-01-15T10:00:00Z",
        "data": {"latitude": 37.7749, "longitude": -122.4194},
        "created_at": "2025-01-15T09:00:00Z",
    },
    "with_metadata": {
        "modality": "email",
        "scheduled_time": "2025-01-15T14:30:00Z",
        "data": {"subject": "Meeting"},
        "created_at": "2025-01-15T14:00:00Z",
        "priority": 5,
        "metadata": {"source": "test", "category": "work"},
    },
}


# Pytest fixtures
@pytest.fixture
def simple_event():
    """Provide a simple event for testing."""
    return create_simulator_event()


@pytest.fixture
def location_event():
    """Provide an event with location input."""
    location_input = create_location_input()
    return create_simulator_event(
        modality="location",
        data=location_input,
    )


@pytest.fixture
def email_event():
    """Provide an event with email input."""
    email_input = create_email_input()
    return create_simulator_event(
        modality="email",
        data=email_input,
    )


@pytest.fixture
def high_priority_event():
    """Provide a high priority event for testing."""
    return create_simulator_event(priority=10)


@pytest.fixture
def agent_event():
    """Provide an agent-generated event for testing."""
    return create_simulator_event(agent_id="agent-123")


@pytest.fixture
def past_event():
    """Provide an event scheduled in the past."""
    now = datetime.now(timezone.utc)
    return create_simulator_event(
        scheduled_time=now - timedelta(hours=2),
        created_at=now - timedelta(hours=3),
    )
