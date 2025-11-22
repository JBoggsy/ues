"""Fixtures for Calendar modality."""

from datetime import datetime, timezone, timedelta

from models.modalities.calendar_input import (
    CalendarInput,
    Attendee,
    RecurrenceRule,
    Reminder,
)
from models.modalities.calendar_state import CalendarState


def create_calendar_input(
    operation: str = "create",
    title: str = "Test Event",
    start: datetime | None = None,
    end: datetime | None = None,
    timestamp: datetime | None = None,
    **kwargs,
) -> CalendarInput:
    """Create a CalendarInput with sensible defaults.

    Args:
        operation: Calendar operation type (default: "create").
        title: Event title.
        start: Event start time (defaults to now + 1 hour).
        end: Event end time (defaults to now + 2 hours).
        timestamp: When operation occurred (defaults to now).
        **kwargs: Additional fields to override.

    Returns:
        CalendarInput instance ready for testing.
    """
    now = datetime.now(timezone.utc)
    
    return CalendarInput(
        operation=operation,
        title=title,
        start=start or (now + timedelta(hours=1)),
        end=end or (now + timedelta(hours=2)),
        timestamp=timestamp or now,
        **kwargs,
    )


def create_calendar_state(
    last_updated: datetime | None = None,
    **kwargs,
) -> CalendarState:
    """Create a CalendarState with sensible defaults.

    Args:
        last_updated: When state was last updated (defaults to now).
        **kwargs: Additional fields to override.

    Returns:
        CalendarState instance ready for testing.
    """
    return CalendarState(
        last_updated=last_updated or datetime.now(timezone.utc),
        **kwargs,
    )


# Pre-built event examples
SIMPLE_EVENT = create_calendar_input()

MEETING_EVENT = create_calendar_input(
    title="Team Meeting",
    start=datetime(2025, 1, 16, 14, 0, 0, tzinfo=timezone.utc),
    end=datetime(2025, 1, 16, 15, 0, 0, tzinfo=timezone.utc),
    location="Conference Room A",
    description="Quarterly planning discussion",
    attendees=[
        Attendee(email="alice@company.com", display_name="Alice"),
        Attendee(email="bob@company.com", display_name="Bob"),
        Attendee(email="carol@company.com", display_name="Carol", optional=True),
    ],
)

ONE_ON_ONE = create_calendar_input(
    title="1:1 with Manager",
    start=datetime(2025, 1, 17, 10, 0, 0, tzinfo=timezone.utc),
    end=datetime(2025, 1, 17, 10, 30, 0, tzinfo=timezone.utc),
    location="Office",
    attendees=[
        Attendee(email="manager@company.com", display_name="Manager"),
    ],
    reminders=[
        Reminder(minutes_before=15, type="notification"),
    ],
)

ALL_DAY_EVENT = create_calendar_input(
    title="Conference",
    start=datetime(2025, 2, 15, 0, 0, 0, tzinfo=timezone.utc),
    end=datetime(2025, 2, 16, 0, 0, 0, tzinfo=timezone.utc),
    all_day=True,
    location="Convention Center",
)

RECURRING_DAILY_STANDUP = create_calendar_input(
    title="Daily Standup",
    start=datetime(2025, 1, 20, 9, 0, 0, tzinfo=timezone.utc),
    end=datetime(2025, 1, 20, 9, 15, 0, tzinfo=timezone.utc),
    recurrence=RecurrenceRule(
        frequency="daily",
        interval=1,
        days_of_week=["monday", "tuesday", "wednesday", "thursday", "friday"],
        end_type="count",
        count=20,
    ),
)

RECURRING_WEEKLY_MEETING = create_calendar_input(
    title="Weekly Team Sync",
    start=datetime(2025, 1, 20, 14, 0, 0, tzinfo=timezone.utc),
    end=datetime(2025, 1, 20, 15, 0, 0, tzinfo=timezone.utc),
    recurrence=RecurrenceRule(
        frequency="weekly",
        interval=1,
        days_of_week=["monday"],
        end_type="never",
    ),
    attendees=[
        Attendee(email="team@company.com"),
    ],
)

RECURRING_MONTHLY_REVIEW = create_calendar_input(
    title="Monthly Review",
    start=datetime(2025, 2, 1, 16, 0, 0, tzinfo=timezone.utc),
    end=datetime(2025, 2, 1, 17, 0, 0, tzinfo=timezone.utc),
    recurrence=RecurrenceRule(
        frequency="monthly",
        interval=1,
        day_of_month=1,
        end_type="until",
        end_date=datetime(2025, 12, 31, tzinfo=timezone.utc).date(),
    ),
)

LUNCH_APPOINTMENT = create_calendar_input(
    title="Lunch with Client",
    start=datetime(2025, 1, 18, 12, 0, 0, tzinfo=timezone.utc),
    end=datetime(2025, 1, 18, 13, 30, 0, tzinfo=timezone.utc),
    location="Downtown Restaurant",
    status="confirmed",
    transparency="opaque",
)

TENTATIVE_EVENT = create_calendar_input(
    title="Possible Meeting",
    start=datetime(2025, 1, 19, 15, 0, 0, tzinfo=timezone.utc),
    end=datetime(2025, 1, 19, 16, 0, 0, tzinfo=timezone.utc),
    status="tentative",
)

BIRTHDAY_EVENT = create_calendar_input(
    title="Alice's Birthday",
    start=datetime(2025, 3, 15, 0, 0, 0, tzinfo=timezone.utc),
    end=datetime(2025, 3, 16, 0, 0, 0, tzinfo=timezone.utc),
    all_day=True,
    recurrence=RecurrenceRule(
        frequency="yearly",
        interval=1,
        month_of_year=3,
        day_of_month=15,
        end_type="never",
    ),
)

INTERVIEW_EVENT = create_calendar_input(
    title="Candidate Interview",
    start=datetime(2025, 1, 22, 11, 0, 0, tzinfo=timezone.utc),
    end=datetime(2025, 1, 22, 12, 0, 0, tzinfo=timezone.utc),
    location="Zoom",
    attendees=[
        Attendee(email="candidate@external.com", display_name="Candidate"),
        Attendee(email="hr@company.com", display_name="HR"),
    ],
    reminders=[
        Reminder(minutes_before=30, type="notification"),
        Reminder(minutes_before=60, type="email"),
    ],
)

UPDATE_EVENT = create_calendar_input(
    operation="update",
    event_id="event-12345",
    title="Updated Meeting Title",
    start=datetime(2025, 1, 16, 15, 0, 0, tzinfo=timezone.utc),
    end=datetime(2025, 1, 16, 16, 0, 0, tzinfo=timezone.utc),
)

DELETE_EVENT = create_calendar_input(
    operation="delete",
    event_id="event-67890",
    title="Cancelled Event",
    start=datetime(2025, 1, 17, 10, 0, 0, tzinfo=timezone.utc),
    end=datetime(2025, 1, 17, 11, 0, 0, tzinfo=timezone.utc),
)


# State examples
EMPTY_CALENDAR = create_calendar_state()


# Invalid examples for validation testing
INVALID_CALENDAR_INPUTS = {
    "end_before_start": {
        "operation": "create",
        "title": "Invalid Event",
        "start": datetime(2025, 1, 15, 15, 0, 0, tzinfo=timezone.utc),
        "end": datetime(2025, 1, 15, 14, 0, 0, tzinfo=timezone.utc),
        "timestamp": datetime.now(timezone.utc),
    },
    "bad_email": {
        "operation": "create",
        "title": "Event",
        "start": datetime(2025, 1, 15, 14, 0, 0, tzinfo=timezone.utc),
        "end": datetime(2025, 1, 15, 15, 0, 0, tzinfo=timezone.utc),
        "attendees": [{"email": "not-an-email"}],
        "timestamp": datetime.now(timezone.utc),
    },
}


# JSON fixtures for API testing
CALENDAR_JSON_EXAMPLES = {
    "simple": {
        "modality_type": "calendar",
        "timestamp": "2025-01-15T10:30:00Z",
        "operation": "create",
        "title": "Test Event",
        "start": "2025-01-16T14:00:00Z",
        "end": "2025-01-16T15:00:00Z",
    },
    "with_attendees": {
        "modality_type": "calendar",
        "timestamp": "2025-01-15T14:00:00Z",
        "operation": "create",
        "title": "Team Meeting",
        "start": "2025-01-17T10:00:00Z",
        "end": "2025-01-17T11:00:00Z",
        "location": "Conference Room",
        "attendees": [
            {"email": "alice@company.com", "display_name": "Alice"},
            {"email": "bob@company.com", "display_name": "Bob"},
        ],
    },
}
