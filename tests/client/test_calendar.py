"""Unit tests for the CalendarClient and AsyncCalendarClient.

This module tests the calendar modality sub-client that provides methods for
creating, updating, deleting, and querying calendar events.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from client._calendar import (
    AsyncCalendarClient,
    Attachment,
    Attendee,
    CalendarClient,
    CalendarEvent,
    CalendarQueryResponse,
    CalendarStateResponse,
    RecurrenceRule,
    Reminder,
)
from client.models import ModalityActionResponse


# =============================================================================
# Response Model Tests
# =============================================================================


class TestAttendee:
    """Tests for the Attendee model."""

    def test_instantiation_with_all_fields(self):
        """Test creating an Attendee with all fields."""
        attendee = Attendee(
            email="attendee@example.com",
            display_name="John Doe",
            response_status="accepted",
            optional=False,
            organizer=False,
            comment="Looking forward to it!",
        )
        assert attendee.email == "attendee@example.com"
        assert attendee.display_name == "John Doe"
        assert attendee.response_status == "accepted"

    def test_instantiation_with_defaults(self):
        """Test creating an Attendee with only required fields."""
        attendee = Attendee(email="attendee@example.com")
        assert attendee.display_name is None
        assert attendee.response_status == "needsAction"
        assert attendee.optional is False
        assert attendee.organizer is False


class TestReminder:
    """Tests for the Reminder model."""

    def test_instantiation(self):
        """Test creating a Reminder."""
        reminder = Reminder(method="popup", minutes=15)
        assert reminder.method == "popup"
        assert reminder.minutes == 15

    def test_email_reminder(self):
        """Test creating an email reminder."""
        reminder = Reminder(method="email", minutes=60)
        assert reminder.method == "email"


class TestRecurrenceRule:
    """Tests for the RecurrenceRule model."""

    def test_instantiation_daily(self):
        """Test creating a daily recurrence rule."""
        rule = RecurrenceRule(
            frequency="DAILY",
            interval=1,
            count=10,
        )
        assert rule.frequency == "DAILY"
        assert rule.interval == 1
        assert rule.count == 10

    def test_instantiation_weekly(self):
        """Test creating a weekly recurrence rule."""
        rule = RecurrenceRule(
            frequency="WEEKLY",
            interval=2,
            by_day=["MO", "WE", "FR"],
            until="2025-12-31",
        )
        assert rule.frequency == "WEEKLY"
        assert rule.by_day == ["MO", "WE", "FR"]
        assert rule.until == "2025-12-31"


class TestCalendarEvent:
    """Tests for the CalendarEvent model."""

    def test_instantiation_with_all_fields(self):
        """Test creating a CalendarEvent with all fields."""
        event = CalendarEvent(
            event_id="evt-123",
            calendar_id="primary",
            title="Team Meeting",
            description="Weekly team sync",
            start=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 11, 0, tzinfo=timezone.utc),
            all_day=False,
            timezone="UTC",
            location="Conference Room A",
            status="confirmed",
            organizer="organizer@example.com",
            attendees=[
                Attendee(email="attendee@example.com", response_status="accepted"),
            ],
            recurrence=None,
            reminders=[Reminder(method="popup", minutes=10)],
            color="#4285F4",
            visibility="default",
            transparency="opaque",
            attachments=[],
            conference_link="https://meet.example.com/123",
            created_at=datetime(2025, 1, 14, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 1, 14, 12, 0, tzinfo=timezone.utc),
        )
        assert event.event_id == "evt-123"
        assert event.title == "Team Meeting"
        assert event.location == "Conference Room A"
        assert len(event.attendees) == 1

    def test_instantiation_with_defaults(self):
        """Test creating a CalendarEvent with minimal required fields."""
        event = CalendarEvent(
            event_id="evt-123",
            calendar_id="primary",
            title="Quick Meeting",
            start=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 11, 0, tzinfo=timezone.utc),
        )
        assert event.all_day is False
        assert event.timezone == "UTC"
        assert event.status == "confirmed"
        assert event.visibility == "default"
        assert event.transparency == "opaque"
        assert event.attendees == []
        assert event.reminders == []


class TestCalendarStateResponse:
    """Tests for the CalendarStateResponse model."""

    def test_instantiation(self):
        """Test creating a CalendarStateResponse."""
        response = CalendarStateResponse(
            modality_type="calendar",
            last_updated="2025-01-15T10:00:00+00:00",
            update_count=5,
            default_calendar_id="primary",
            user_timezone="America/New_York",
            calendars={"primary": {"name": "Primary Calendar"}},
            events={"evt-1": {"title": "Meeting"}},
            calendar_count=1,
            event_count=1,
        )
        assert response.modality_type == "calendar"
        assert response.default_calendar_id == "primary"
        assert response.event_count == 1


class TestCalendarQueryResponse:
    """Tests for the CalendarQueryResponse model."""

    def test_instantiation(self):
        """Test creating a CalendarQueryResponse."""
        response = CalendarQueryResponse(
            modality_type="calendar",
            events=[],
            count=0,
            total_count=0,
        )
        assert response.modality_type == "calendar"
        assert response.count == 0


# =============================================================================
# CalendarClient Tests
# =============================================================================


class TestCalendarClientGetState:
    """Tests for CalendarClient.get_state() method."""

    def test_get_state(self):
        """Test getting calendar state."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "modality_type": "calendar",
            "last_updated": "2025-01-15T10:00:00+00:00",
            "update_count": 5,
            "default_calendar_id": "primary",
            "user_timezone": "America/New_York",
            "calendars": {"primary": {"name": "Primary Calendar"}},
            "events": {},
            "calendar_count": 1,
            "event_count": 0,
        }

        client = CalendarClient(mock_http)
        result = client.get_state()

        mock_http.get.assert_called_once_with("/calendar/state", params=None)
        assert isinstance(result, CalendarStateResponse)
        assert result.default_calendar_id == "primary"


class TestCalendarClientQuery:
    """Tests for CalendarClient.query() method."""

    def test_query_no_filters(self):
        """Test querying events with no filters."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "modality_type": "calendar",
            "events": [],
            "count": 0,
            "total_count": 0,
        }

        client = CalendarClient(mock_http)
        result = client.query()

        mock_http.post.assert_called_once_with("/calendar/query", json={}, params=None)
        assert isinstance(result, CalendarQueryResponse)

    def test_query_with_date_range(self):
        """Test querying events with date range."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "modality_type": "calendar",
            "events": [],
            "count": 0,
            "total_count": 0,
        }

        client = CalendarClient(mock_http)
        start = datetime(2025, 1, 15, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 22, 0, 0, tzinfo=timezone.utc)
        result = client.query(start=start, end=end)

        call_args = mock_http.post.call_args
        assert "start" in call_args[1]["json"]
        assert "end" in call_args[1]["json"]

    def test_query_with_filters(self):
        """Test querying events with various filters."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "modality_type": "calendar",
            "events": [],
            "count": 0,
            "total_count": 0,
        }

        client = CalendarClient(mock_http)
        result = client.query(
            calendar_ids=["primary", "work"],
            search="meeting",
            status="confirmed",
            has_attendees=True,
            recurring=False,
            limit=10,
        )

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["calendar_ids"] == ["primary", "work"]
        assert call_args[1]["json"]["search"] == "meeting"
        assert call_args[1]["json"]["status"] == "confirmed"
        assert call_args[1]["json"]["has_attendees"] is True
        assert call_args[1]["json"]["recurring"] is False
        assert call_args[1]["json"]["limit"] == 10

    def test_query_expand_recurring(self):
        """Test querying with expand_recurring option."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "modality_type": "calendar",
            "events": [],
            "count": 0,
            "total_count": 0,
        }

        client = CalendarClient(mock_http)
        result = client.query(expand_recurring=True)

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["expand_recurring"] is True


class TestCalendarClientCreate:
    """Tests for CalendarClient.create() method."""

    def test_create_minimal(self):
        """Test creating an event with minimal parameters."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Event created",
            "modality": "calendar",
        }

        client = CalendarClient(mock_http)
        result = client.create(
            title="Quick Meeting",
            start=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 11, 0, tzinfo=timezone.utc),
        )

        mock_http.post.assert_called_once()
        call_args = mock_http.post.call_args
        assert call_args[0][0] == "/calendar/create"
        assert call_args[1]["json"]["title"] == "Quick Meeting"
        assert call_args[1]["json"]["calendar_id"] == "primary"
        assert call_args[1]["json"]["all_day"] is False
        assert call_args[1]["json"]["timezone"] == "UTC"
        assert isinstance(result, ModalityActionResponse)

    def test_create_with_all_options(self):
        """Test creating an event with all options."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Event created",
            "modality": "calendar",
        }

        client = CalendarClient(mock_http)
        result = client.create(
            title="Team Meeting",
            start=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 11, 0, tzinfo=timezone.utc),
            calendar_id="work",
            description="Weekly sync meeting",
            all_day=False,
            timezone="America/New_York",
            location="Conference Room A",
            status="confirmed",
            organizer="org@example.com",
            attendees=[
                {"email": "attendee@example.com", "response_status": "needsAction"},
            ],
            recurrence={"frequency": "WEEKLY", "interval": 1},
            reminders=[{"method": "popup", "minutes": 15}],
            color="#4285F4",
            visibility="default",
            transparency="opaque",
            conference_link="https://meet.example.com/123",
        )

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["calendar_id"] == "work"
        assert call_args[1]["json"]["description"] == "Weekly sync meeting"
        assert call_args[1]["json"]["location"] == "Conference Room A"
        assert len(call_args[1]["json"]["attendees"]) == 1
        assert call_args[1]["json"]["recurrence"]["frequency"] == "WEEKLY"


class TestCalendarClientUpdate:
    """Tests for CalendarClient.update() method."""

    def test_update_minimal(self):
        """Test updating an event with minimal changes."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Event updated",
            "modality": "calendar",
        }

        client = CalendarClient(mock_http)
        result = client.update(
            event_id="evt-123",
            title="Updated Meeting Title",
        )

        mock_http.post.assert_called_once()
        call_args = mock_http.post.call_args
        assert call_args[0][0] == "/calendar/update"
        assert call_args[1]["json"]["event_id"] == "evt-123"
        assert call_args[1]["json"]["title"] == "Updated Meeting Title"
        assert call_args[1]["json"]["recurrence_scope"] == "this"
        assert isinstance(result, ModalityActionResponse)

    def test_update_recurring_future(self):
        """Test updating a recurring event for future occurrences."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Event updated",
            "modality": "calendar",
        }

        client = CalendarClient(mock_http)
        result = client.update(
            event_id="evt-123",
            recurrence_scope="future",
            location="New Location",
        )

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["recurrence_scope"] == "future"
        assert call_args[1]["json"]["location"] == "New Location"

    def test_update_time(self):
        """Test updating event times."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Event updated",
            "modality": "calendar",
        }

        client = CalendarClient(mock_http)
        new_start = datetime(2025, 1, 16, 14, 0, tzinfo=timezone.utc)
        new_end = datetime(2025, 1, 16, 15, 0, tzinfo=timezone.utc)
        result = client.update(
            event_id="evt-123",
            start=new_start,
            end=new_end,
        )

        call_args = mock_http.post.call_args
        assert "start" in call_args[1]["json"]
        assert "end" in call_args[1]["json"]


class TestCalendarClientDelete:
    """Tests for CalendarClient.delete() method."""

    def test_delete_single(self):
        """Test deleting a single event."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Event deleted",
            "modality": "calendar",
        }

        client = CalendarClient(mock_http)
        result = client.delete(event_id="evt-123")

        mock_http.post.assert_called_once()
        call_args = mock_http.post.call_args
        assert call_args[0][0] == "/calendar/delete"
        assert call_args[1]["json"]["event_id"] == "evt-123"
        assert call_args[1]["json"]["calendar_id"] == "primary"
        assert call_args[1]["json"]["recurrence_scope"] == "this"
        assert isinstance(result, ModalityActionResponse)

    def test_delete_all_recurring(self):
        """Test deleting all occurrences of a recurring event."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Event deleted",
            "modality": "calendar",
        }

        client = CalendarClient(mock_http)
        result = client.delete(
            event_id="evt-123",
            recurrence_scope="all",
        )

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["recurrence_scope"] == "all"


# =============================================================================
# AsyncCalendarClient Tests
# =============================================================================


class TestAsyncCalendarClientGetState:
    """Tests for AsyncCalendarClient.get_state() method."""

    async def test_get_state(self):
        """Test getting calendar state asynchronously."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "modality_type": "calendar",
            "last_updated": "2025-01-15T10:00:00+00:00",
            "update_count": 5,
            "default_calendar_id": "primary",
            "user_timezone": "America/New_York",
            "calendars": {},
            "events": {},
            "calendar_count": 0,
            "event_count": 0,
        }

        client = AsyncCalendarClient(mock_http)
        result = await client.get_state()

        mock_http.get.assert_called_once_with("/calendar/state", params=None)
        assert isinstance(result, CalendarStateResponse)


class TestAsyncCalendarClientQuery:
    """Tests for AsyncCalendarClient.query() method."""

    async def test_query(self):
        """Test querying events asynchronously."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "modality_type": "calendar",
            "events": [],
            "count": 0,
            "total_count": 0,
        }

        client = AsyncCalendarClient(mock_http)
        start = datetime(2025, 1, 15, 0, 0, tzinfo=timezone.utc)
        result = await client.query(start=start)

        mock_http.post.assert_called_once()
        assert isinstance(result, CalendarQueryResponse)


class TestAsyncCalendarClientCreate:
    """Tests for AsyncCalendarClient.create() method."""

    async def test_create(self):
        """Test creating an event asynchronously."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Event created",
            "modality": "calendar",
        }

        client = AsyncCalendarClient(mock_http)
        result = await client.create(
            title="Meeting",
            start=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 11, 0, tzinfo=timezone.utc),
        )

        assert isinstance(result, ModalityActionResponse)


class TestAsyncCalendarClientUpdate:
    """Tests for AsyncCalendarClient.update() method."""

    async def test_update(self):
        """Test updating an event asynchronously."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Event updated",
            "modality": "calendar",
        }

        client = AsyncCalendarClient(mock_http)
        result = await client.update(
            event_id="evt-123",
            title="Updated Title",
        )

        assert isinstance(result, ModalityActionResponse)


class TestAsyncCalendarClientDelete:
    """Tests for AsyncCalendarClient.delete() method."""

    async def test_delete(self):
        """Test deleting an event asynchronously."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Event deleted",
            "modality": "calendar",
        }

        client = AsyncCalendarClient(mock_http)
        result = await client.delete(event_id="evt-123")

        mock_http.post.assert_called_once()
        assert isinstance(result, ModalityActionResponse)
