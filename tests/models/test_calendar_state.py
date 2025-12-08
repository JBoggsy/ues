"""Unit tests for calendar state modality.

This module tests both general ModalityState behavior and calendar-specific features.
"""

from datetime import datetime, date, timezone, timedelta

import pytest

from models.modalities.calendar_input import (
    Attendee,
    CalendarInput,
    RecurrenceRule,
    Reminder,
)
from models.modalities.calendar_state import Calendar, CalendarEvent, CalendarState


class TestCalendarStateInstantiation:
    """Test instantiation patterns for CalendarState.

    GENERAL PATTERN: All ModalityState subclasses should instantiate with last_updated.
    """

    def test_minimal_instantiation(self):
        """GENERAL PATTERN: Verify CalendarState instantiates with minimal required fields."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        assert state.last_updated == datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        assert state.modality_type == "calendar"
        assert len(state.events) == 0
        assert len(state.calendars) == 1  # Primary calendar auto-created
        assert "primary" in state.calendars

    def test_default_primary_calendar(self):
        """MODALITY-SPECIFIC: Verify primary calendar is auto-created."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        assert "primary" in state.calendars
        primary = state.calendars["primary"]
        assert primary.calendar_id == "primary"
        assert primary.name == "Personal"
        assert primary.color == "#4285f4"
        assert primary.visible is True

    def test_default_values(self):
        """GENERAL PATTERN: Verify default values are set correctly."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        assert state.update_count == 0
        assert state.default_calendar_id == "primary"
        assert state.user_timezone == "UTC"


class TestCalendarHelperClass:
    """Test Calendar helper class.

    MODALITY-SPECIFIC: Calendar container for events.
    """

    def test_calendar_minimal(self):
        """Verify Calendar instantiates with minimal fields."""
        cal = Calendar(calendar_id="work", name="Work Calendar")

        assert cal.calendar_id == "work"
        assert cal.name == "Work Calendar"
        assert cal.color == "#4285f4"
        assert cal.visible is True
        assert len(cal.event_ids) == 0

    def test_calendar_full(self):
        """Verify Calendar with all fields."""
        cal = Calendar(
            calendar_id="personal",
            name="Personal",
            color="#FF5733",
            visible=False,
            event_ids={"event-1", "event-2"},
        )

        assert cal.color == "#FF5733"
        assert cal.visible is False
        assert len(cal.event_ids) == 2

    def test_calendar_to_dict(self):
        """Verify Calendar serialization."""
        cal = Calendar(calendar_id="work", name="Work", event_ids={"event-1"})

        result = cal.model_dump(mode="json")
        assert result["calendar_id"] == "work"
        assert result["name"] == "Work"
        assert cal.event_count == 1


class TestCalendarEventHelperClass:
    """Test CalendarEvent helper class.

    MODALITY-SPECIFIC: Event with full metadata.
    """

    def test_event_minimal(self):
        """Verify CalendarEvent instantiates with minimal fields."""
        event = CalendarEvent(
            event_id="event-123",
            calendar_id="primary",
            title="Test Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )

        assert event.event_id == "event-123"
        assert event.calendar_id == "primary"
        assert event.title == "Test Event"
        assert event.all_day is False
        assert event.status == "confirmed"

    def test_event_is_recurring(self):
        """MODALITY-SPECIFIC: Verify is_recurring detection."""
        event_normal = CalendarEvent(
            event_id="event-1",
            calendar_id="primary",
            title="Normal Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        assert event_normal.is_recurring() is False

        event_recurring = CalendarEvent(
            event_id="event-2",
            calendar_id="primary",
            title="Recurring Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
            recurrence=RecurrenceRule(frequency="weekly", days_of_week=["monday"], end_type="never"),
        )
        assert event_recurring.is_recurring() is True

    def test_event_is_modified_occurrence(self):
        """MODALITY-SPECIFIC: Verify modified occurrence detection."""
        event_normal = CalendarEvent(
            event_id="event-1",
            calendar_id="primary",
            title="Normal Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        assert event_normal.is_modified_occurrence() is False

        event_modified = CalendarEvent(
            event_id="event-2",
            calendar_id="primary",
            title="Modified Occurrence",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
            parent_event_id="event-parent",
            recurrence_id="2025-01-15",
        )
        assert event_modified.is_modified_occurrence() is True

    def test_event_to_dict(self):
        """Verify CalendarEvent serialization."""
        event = CalendarEvent(
            event_id="event-123",
            calendar_id="primary",
            title="Meeting",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
            location="Office",
            attendees=[Attendee(email="alice@example.com")],
        )

        result = event.model_dump(mode="json")
        assert result["event_id"] == "event-123"
        assert result["title"] == "Meeting"
        assert result["location"] == "Office"
        assert event.has_attendees is True
        assert len(event.attendees) == 1


class TestCalendarStateApplyInput:
    """Test CalendarState.apply_input method.

    GENERAL PATTERN: Test state modification via input application.
    """

    def test_apply_create_event(self):
        """MODALITY-SPECIFIC: Verify creating an event."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        input_data = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="Team Meeting",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        input_data.validate_input()

        state.apply_input(input_data)

        assert len(state.events) == 1
        assert state.update_count == 1
        assert state.last_updated == datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc)

        event_id = input_data.event_id
        assert event_id in state.events
        event = state.events[event_id]
        assert event.title == "Team Meeting"
        assert event.calendar_id == "primary"

    def test_apply_create_to_new_calendar(self):
        """MODALITY-SPECIFIC: Creating event in non-existent calendar creates it."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        input_data = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            calendar_id="work",
            title="Work Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        input_data.validate_input()

        state.apply_input(input_data)

        assert "work" in state.calendars
        assert state.calendars["work"].name == "Work"

    def test_apply_update_event(self):
        """MODALITY-SPECIFIC: Verify updating an event."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        # Create event first
        create_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="Original Title",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        create_input.validate_input()
        state.apply_input(create_input)
        event_id = create_input.event_id

        # Update event
        update_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
            operation="update",
            event_id=event_id,
            title="Updated Title",
            start=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 16, 0, tzinfo=timezone.utc),
        )

        state.apply_input(update_input)

        event = state.events[event_id]
        assert event.title == "Updated Title"
        assert event.start == datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc)
        assert state.update_count == 2

    def test_apply_update_nonexistent_event_raises(self):
        """MODALITY-SPECIFIC: Updating non-existent event raises error."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        update_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="update",
            event_id="nonexistent",
            title="Updated",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )

        with pytest.raises(ValueError, match="Event nonexistent not found"):
            state.apply_input(update_input)

    def test_apply_delete_event(self):
        """MODALITY-SPECIFIC: Verify deleting an event."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        # Create event first
        create_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="To Delete",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        create_input.validate_input()
        state.apply_input(create_input)
        event_id = create_input.event_id

        # Delete event
        delete_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
            operation="delete",
            event_id=event_id,
            recurrence_scope="all",
            title="To Delete",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )

        state.apply_input(delete_input)

        assert event_id not in state.events
        assert event_id not in state.calendars["primary"].event_ids

    def test_apply_delete_recurring_event_single_occurrence(self):
        """MODALITY-SPECIFIC: Deleting single occurrence adds exception."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        # Create recurring event
        create_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="Weekly Meeting",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
            recurrence=RecurrenceRule(
                frequency="weekly",
                days_of_week=["monday"],
                end_type="count",
                count=10,
            ),
        )
        create_input.validate_input()
        state.apply_input(create_input)
        event_id = create_input.event_id

        # Delete single occurrence
        delete_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
            operation="delete",
            event_id=event_id,
            recurrence_scope="this",
            recurrence_id="2025-01-22",
            title="Weekly Meeting",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )

        state.apply_input(delete_input)

        # Event still exists but has exception
        assert event_id in state.events
        event = state.events[event_id]
        assert "2025-01-22" in event.recurrence_exceptions

    def test_apply_input_with_attendees(self):
        """MODALITY-SPECIFIC: Create event with attendees."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        attendees = [
            Attendee(email="alice@example.com", display_name="Alice"),
            Attendee(email="bob@example.com", optional=True),
        ]

        input_data = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="Team Meeting",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
            organizer="organizer@example.com",
            attendees=attendees,
        )
        input_data.validate_input()

        state.apply_input(input_data)

        event = state.events[input_data.event_id]
        assert len(event.attendees) == 2
        assert event.organizer == "organizer@example.com"

    def test_apply_invalid_input_type_raises(self):
        """GENERAL PATTERN: Applying wrong input type raises error."""
        from models.modalities.email_input import EmailInput

        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        wrong_input = EmailInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="receive",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            subject="Test",
            body_text="Test",
        )

        with pytest.raises(TypeError):
            state.apply_input(wrong_input)


class TestCalendarStateGetSnapshot:
    """Test CalendarState.get_snapshot method.

    GENERAL PATTERN: Test state snapshot generation.
    """

    def test_get_snapshot_empty(self):
        """GENERAL PATTERN: Verify snapshot of empty state."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        snapshot = state.get_snapshot()

        assert snapshot["modality_type"] == "calendar"
        assert snapshot["last_updated"] == "2025-01-01T12:00:00+00:00"
        assert snapshot["update_count"] == 0
        assert snapshot["calendar_count"] == 1
        assert snapshot["event_count"] == 0
        assert "calendars" in snapshot
        assert "events" in snapshot

    def test_get_snapshot_with_events(self):
        """MODALITY-SPECIFIC: Verify snapshot includes events."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        # Add events
        for i in range(3):
            input_data = CalendarInput(
                timestamp=datetime(2025, 1, 1, 13 + i, 0, tzinfo=timezone.utc),
                operation="create",
                title=f"Event {i}",
                start=datetime(2025, 1, 15 + i, 14, 0, tzinfo=timezone.utc),
                end=datetime(2025, 1, 15 + i, 15, 0, tzinfo=timezone.utc),
            )
            input_data.validate_input()
            state.apply_input(input_data)

        snapshot = state.get_snapshot()

        assert snapshot["event_count"] == 3
        assert len(snapshot["events"]) == 3


class TestCalendarStateValidateState:
    """Test CalendarState.validate_state method.

    GENERAL PATTERN: Test state consistency validation.
    """

    def test_validate_empty_state(self):
        """GENERAL PATTERN: Empty state is valid."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        errors = state.validate_state()
        assert errors == []

    def test_validate_state_with_events(self):
        """MODALITY-SPECIFIC: Valid state passes validation."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        input_data = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="Test Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        input_data.validate_input()
        state.apply_input(input_data)

        errors = state.validate_state()
        assert errors == []

    def test_validate_event_calendar_mismatch(self):
        """MODALITY-SPECIFIC: Event referencing missing calendar fails validation."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        # Manually create invalid state
        event = CalendarEvent(
            event_id="event-123",
            calendar_id="nonexistent",
            title="Orphan Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        state.events["event-123"] = event

        errors = state.validate_state()
        assert len(errors) > 0
        assert any("references missing calendar" in err for err in errors)

    def test_validate_invalid_time_range(self):
        """MODALITY-SPECIFIC: Event with end before start fails validation."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        # Manually create invalid event
        event = CalendarEvent(
            event_id="event-123",
            calendar_id="primary",
            title="Invalid Event",
            start=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
        )
        state.events["event-123"] = event
        state.calendars["primary"].event_ids.add("event-123")

        errors = state.validate_state()
        assert len(errors) > 0
        assert any("invalid time range" in err for err in errors)


class TestCalendarStateQuery:
    """Test CalendarState.query method.

    MODALITY-SPECIFIC: Test event querying and filtering.
    """

    def test_query_all_events(self):
        """MODALITY-SPECIFIC: Query all events."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        # Add events
        for i in range(3):
            input_data = CalendarInput(
                timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
                operation="create",
                title=f"Event {i}",
                start=datetime(2025, 1, 15 + i, 14, 0, tzinfo=timezone.utc),
                end=datetime(2025, 1, 15 + i, 15, 0, tzinfo=timezone.utc),
            )
            input_data.validate_input()
            state.apply_input(input_data)

        result = state.query({})

        assert result["count"] == 3
        assert len(result["events"]) == 3

    def test_query_by_calendar_id(self):
        """MODALITY-SPECIFIC: Query events from specific calendar."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        # Add events to different calendars
        for cal_id in ["primary", "work"]:
            input_data = CalendarInput(
                timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
                operation="create",
                calendar_id=cal_id,
                title=f"{cal_id} Event",
                start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
                end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
            )
            input_data.validate_input()
            state.apply_input(input_data)

        result = state.query({"calendar_ids": ["work"]})

        assert result["count"] == 1
        assert result["events"][0].calendar_id == "work"

    def test_query_by_date_range(self):
        """MODALITY-SPECIFIC: Query events within date range."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        # Add events on different dates
        for i in range(5):
            input_data = CalendarInput(
                timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
                operation="create",
                title=f"Event {i}",
                start=datetime(2025, 1, 10 + i, 14, 0, tzinfo=timezone.utc),
                end=datetime(2025, 1, 10 + i, 15, 0, tzinfo=timezone.utc),
            )
            input_data.validate_input()
            state.apply_input(input_data)

        # Query for events between Jan 12-13
        result = state.query({
            "start": datetime(2025, 1, 12, 0, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 1, 13, 23, 59, tzinfo=timezone.utc),
        })

        assert result["count"] == 2

    def test_query_by_search_text(self):
        """MODALITY-SPECIFIC: Query events by text search."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        # Add events with different titles
        titles = ["Team Meeting", "Client Call", "Team Standup"]
        for title in titles:
            input_data = CalendarInput(
                timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
                operation="create",
                title=title,
                start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
                end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
            )
            input_data.validate_input()
            state.apply_input(input_data)

        result = state.query({"search": "team"})

        assert result["count"] == 2
        titles_found = [e.title for e in result["events"]]
        assert "Team Meeting" in titles_found
        assert "Team Standup" in titles_found

    def test_query_by_status(self):
        """MODALITY-SPECIFIC: Query events by status."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        # Add events with different statuses
        for status in ["confirmed", "tentative", "cancelled"]:
            input_data = CalendarInput(
                timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
                operation="create",
                title=f"{status} Event",
                start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
                end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
                status=status,
            )
            input_data.validate_input()
            state.apply_input(input_data)

        result = state.query({"status": "confirmed"})

        assert result["count"] == 1
        assert result["events"][0].status == "confirmed"

    def test_query_by_has_attendees(self):
        """MODALITY-SPECIFIC: Query events with/without attendees."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        # Event with attendees
        input_with = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="Meeting",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
            attendees=[Attendee(email="alice@example.com")],
        )
        input_with.validate_input()
        state.apply_input(input_with)

        # Event without attendees
        input_without = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="Solo Work",
            start=datetime(2025, 1, 16, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 16, 15, 0, tzinfo=timezone.utc),
        )
        input_without.validate_input()
        state.apply_input(input_without)

        result_with = state.query({"has_attendees": True})
        assert result_with["count"] == 1
        assert result_with["events"][0].title == "Meeting"

        result_without = state.query({"has_attendees": False})
        assert result_without["count"] == 1
        assert result_without["events"][0].title == "Solo Work"

    def test_query_by_recurring(self):
        """MODALITY-SPECIFIC: Query recurring vs non-recurring events."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        # Recurring event
        input_recurring = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="Weekly Meeting",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
            recurrence=RecurrenceRule(
                frequency="weekly",
                days_of_week=["monday"],
                end_type="never",
            ),
        )
        input_recurring.validate_input()
        state.apply_input(input_recurring)

        # Non-recurring event
        input_normal = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="One-time Event",
            start=datetime(2025, 1, 16, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 16, 15, 0, tzinfo=timezone.utc),
        )
        input_normal.validate_input()
        state.apply_input(input_normal)

        result_recurring = state.query({"recurring": True})
        assert result_recurring["count"] == 1
        assert result_recurring["events"][0].title == "Weekly Meeting"

        result_normal = state.query({"recurring": False})
        assert result_normal["count"] == 1
        assert result_normal["events"][0].title == "One-time Event"

    def test_query_with_limit(self):
        """MODALITY-SPECIFIC: Query with result limit."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        # Add 10 events
        for i in range(10):
            input_data = CalendarInput(
                timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
                operation="create",
                title=f"Event {i}",
                start=datetime(2025, 1, 15 + i, 14, 0, tzinfo=timezone.utc),
                end=datetime(2025, 1, 15 + i, 15, 0, tzinfo=timezone.utc),
            )
            input_data.validate_input()
            state.apply_input(input_data)

        result = state.query({"limit": 5})

        assert result["count"] == 5
        assert len(result["events"]) == 5

    def test_query_expand_recurring_events(self):
        """MODALITY-SPECIFIC: Query with recurring event expansion."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        # Create daily recurring event
        input_data = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="Daily Standup",
            start=datetime(2025, 1, 15, 9, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 9, 15, tzinfo=timezone.utc),
            recurrence=RecurrenceRule(
                frequency="daily",
                interval=1,
                end_type="count",
                count=5,
            ),
        )
        input_data.validate_input()
        state.apply_input(input_data)

        # Query with expansion
        result = state.query({
            "start": datetime(2025, 1, 15, 0, 0, tzinfo=timezone.utc),
            "end": datetime(2025, 1, 20, 0, 0, tzinfo=timezone.utc),
            "expand_recurring": True,
        })

        # Should get 5 occurrences (Jan 15-19)
        assert result["count"] == 5


class TestCalendarStateHelperMethods:
    """Test CalendarState helper methods.

    MODALITY-SPECIFIC: Calendar and event management methods.
    """

    def test_get_calendar(self):
        """MODALITY-SPECIFIC: Retrieve calendar by ID."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        cal = state.get_calendar("primary")
        assert cal is not None
        assert cal.calendar_id == "primary"

        missing = state.get_calendar("nonexistent")
        assert missing is None

    def test_get_event(self):
        """MODALITY-SPECIFIC: Retrieve event by ID."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        input_data = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="Test Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        input_data.validate_input()
        state.apply_input(input_data)

        event = state.get_event(input_data.event_id)
        assert event is not None
        assert event.title == "Test Event"

        missing = state.get_event("nonexistent")
        assert missing is None

    def test_create_calendar(self):
        """MODALITY-SPECIFIC: Create new calendar."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        cal = state.create_calendar("work", "Work Calendar", "#FF5733")

        assert cal.calendar_id == "work"
        assert cal.name == "Work Calendar"
        assert cal.color == "#FF5733"
        assert "work" in state.calendars

    def test_delete_calendar(self):
        """MODALITY-SPECIFIC: Delete calendar and its events."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        # Create calendar with event
        state.create_calendar("work", "Work")
        input_data = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            calendar_id="work",
            title="Work Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        input_data.validate_input()
        state.apply_input(input_data)

        # Delete calendar
        state.delete_calendar("work")

        assert "work" not in state.calendars
        assert len(state.events) == 0

    def test_delete_calendar_nonexistent_raises(self):
        """MODALITY-SPECIFIC: Deleting non-existent calendar raises error."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        with pytest.raises(ValueError, match="Calendar nonexistent not found"):
            state.delete_calendar("nonexistent")

    def test_delete_default_calendar_raises(self):
        """MODALITY-SPECIFIC: Deleting default calendar raises error."""
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        with pytest.raises(ValueError, match="Cannot delete default calendar"):
            state.delete_calendar("primary")


class TestCalendarStateSerialization:
    """Test CalendarState serialization.

    GENERAL PATTERN: Verify state can be serialized and deserialized.
    """

    def test_empty_state_serialization(self):
        """GENERAL PATTERN: Verify empty state serializes."""
        original = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        dumped = original.model_dump()
        restored = CalendarState.model_validate(dumped)

        assert restored.last_updated == original.last_updated
        assert restored.modality_type == original.modality_type
        assert len(restored.calendars) == len(original.calendars)

    def test_populated_state_serialization(self):
        """GENERAL PATTERN: Verify populated state persists correctly."""
        original = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )

        # Add events
        for i in range(3):
            input_data = CalendarInput(
                timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
                operation="create",
                title=f"Event {i}",
                start=datetime(2025, 1, 15 + i, 14, 0, tzinfo=timezone.utc),
                end=datetime(2025, 1, 15 + i, 15, 0, tzinfo=timezone.utc),
            )
            input_data.validate_input()
            original.apply_input(input_data)

        dumped = original.model_dump()
        restored = CalendarState.model_validate(dumped)

        assert len(restored.events) == len(original.events)
        assert restored.update_count == original.update_count


class TestCalendarStateFromFixtures:
    """Test using pre-built calendar state fixtures.

    GENERAL PATTERN: Verify fixtures work correctly.
    """

    def test_create_calendar_state_fixture(self):
        """Verify create_calendar_state factory function."""
        from tests.fixtures.modalities.calendar import create_calendar_state

        state = create_calendar_state()

        assert state.modality_type == "calendar"
        assert state.last_updated is not None
        assert "primary" in state.calendars


class TestCalendarStateCreateUndoData:
    """Test CalendarState.create_undo_data() method.
    
    GENERAL PATTERN: All ModalityState subclasses must implement create_undo_data()
    to capture minimal data needed to reverse an apply_input() operation.
    
    CALENDAR-SPECIFIC: Handles create, update, and delete operations with
    special handling for recurring events (scope-based updates/deletions).
    """

    def test_create_undo_data_for_create_event(self):
        """Test create_undo_data for creating a new event.
        
        CALENDAR-SPECIFIC: Only needs event_id to remove on undo.
        """
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        create_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="Test Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        create_input.validate_input()
        
        undo_data = state.create_undo_data(create_input)
        
        assert undo_data["action"] == "remove_event"
        assert undo_data["event_id"] == create_input.event_id
        assert undo_data["calendar_id"] == "primary"
        assert undo_data["was_new_calendar"] is False

    def test_create_undo_data_for_create_event_new_calendar(self):
        """Test create_undo_data when creating event in a new calendar.
        
        CALENDAR-SPECIFIC: Tracks that calendar was also created as side effect.
        """
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        create_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            calendar_id="work",
            title="Work Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        create_input.validate_input()
        
        undo_data = state.create_undo_data(create_input)
        
        assert undo_data["action"] == "remove_event"
        assert undo_data["calendar_id"] == "work"
        assert undo_data["was_new_calendar"] is True

    def test_create_undo_data_for_update_simple(self):
        """Test create_undo_data for simple update (non-recurring).
        
        CALENDAR-SPECIFIC: Stores full previous event state.
        """
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        # First create an event
        create_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="Original Title",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        create_input.validate_input()
        state.apply_input(create_input)
        
        # Create update input
        update_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
            operation="update",
            event_id=create_input.event_id,
            title="Updated Title",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        
        undo_data = state.create_undo_data(update_input)
        
        assert undo_data["action"] == "restore_event"
        assert undo_data["event_id"] == create_input.event_id
        assert undo_data["previous_event"]["title"] == "Original Title"

    def test_create_undo_data_for_update_nonexistent(self):
        """Test create_undo_data for updating non-existent event.
        
        CALENDAR-SPECIFIC: Returns noop action.
        """
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        update_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
            operation="update",
            event_id="nonexistent-event",
            title="Updated Title",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        
        undo_data = state.create_undo_data(update_input)
        
        assert undo_data["action"] == "noop"

    def test_create_undo_data_for_update_recurring_all(self):
        """Test create_undo_data for updating all occurrences of recurring event.
        
        CALENDAR-SPECIFIC: Simple restore_event action for all-scope updates.
        """
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        # Create recurring event
        create_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="Daily Standup",
            start=datetime(2025, 1, 15, 9, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 9, 30, tzinfo=timezone.utc),
            recurrence=RecurrenceRule(
                frequency="daily",
                interval=1,
                end_type="count",
                count=10,
            ),
        )
        create_input.validate_input()
        state.apply_input(create_input)
        
        # Update all occurrences
        update_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
            operation="update",
            event_id=create_input.event_id,
            title="Updated Standup",
            start=datetime(2025, 1, 15, 9, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 9, 30, tzinfo=timezone.utc),
            recurrence_scope="all",
        )
        
        undo_data = state.create_undo_data(update_input)
        
        assert undo_data["action"] == "restore_event"
        assert undo_data["previous_event"]["title"] == "Daily Standup"

    def test_create_undo_data_for_update_recurring_this_and_future(self):
        """Test create_undo_data for updating this and future occurrences.
        
        CALENDAR-SPECIFIC: Tracks previous event IDs to find split event.
        """
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        # Create recurring event (weekly needs days_of_week)
        create_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="Weekly Meeting",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
            recurrence=RecurrenceRule(
                frequency="weekly",
                interval=1,
                days_of_week=["wednesday"],
                end_type="never",
            ),
        )
        create_input.validate_input()
        state.apply_input(create_input)
        
        # Update this and future
        update_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
            operation="update",
            event_id=create_input.event_id,
            title="Updated Meeting",
            start=datetime(2025, 1, 22, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 22, 15, 0, tzinfo=timezone.utc),
            recurrence_scope="this_and_future",
            recurrence_id="2025-01-22",
        )
        
        undo_data = state.create_undo_data(update_input)
        
        assert undo_data["action"] == "restore_event_remove_split"
        assert "previous_event_ids" in undo_data
        assert undo_data["previous_event"]["title"] == "Weekly Meeting"

    def test_create_undo_data_for_update_single_occurrence(self):
        """Test create_undo_data for modifying single occurrence.
        
        CALENDAR-SPECIFIC: Tracks previous event IDs to find modified occurrence.
        """
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        # Create recurring event
        create_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="Daily Standup",
            start=datetime(2025, 1, 15, 9, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 9, 30, tzinfo=timezone.utc),
            recurrence=RecurrenceRule(
                frequency="daily",
                interval=1,
                end_type="count",
                count=10,
            ),
        )
        create_input.validate_input()
        state.apply_input(create_input)
        
        # Modify single occurrence
        update_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
            operation="update",
            event_id=create_input.event_id,
            title="Special Standup",
            start=datetime(2025, 1, 17, 10, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 17, 10, 30, tzinfo=timezone.utc),
            recurrence_scope="this",
            recurrence_id="2025-01-17",
        )
        
        undo_data = state.create_undo_data(update_input)
        
        assert undo_data["action"] == "restore_event_remove_occurrence"
        assert undo_data["recurrence_id"] == "2025-01-17"
        assert "previous_event_ids" in undo_data

    def test_create_undo_data_for_delete(self):
        """Test create_undo_data for deleting an event.
        
        CALENDAR-SPECIFIC: Stores full event for restoration.
        """
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        # Create event
        create_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="Event to Delete",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        create_input.validate_input()
        state.apply_input(create_input)
        
        # Delete event
        delete_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
            operation="delete",
            event_id=create_input.event_id,
            title="",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        
        undo_data = state.create_undo_data(delete_input)
        
        assert undo_data["action"] == "restore_deleted_event"
        assert undo_data["deleted_event"]["title"] == "Event to Delete"

    def test_create_undo_data_for_delete_nonexistent(self):
        """Test create_undo_data for deleting non-existent event.
        
        CALENDAR-SPECIFIC: Returns noop action.
        """
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        delete_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
            operation="delete",
            event_id="nonexistent",
            title="",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        
        undo_data = state.create_undo_data(delete_input)
        
        assert undo_data["action"] == "noop"

    def test_create_undo_data_for_delete_single_occurrence(self):
        """Test create_undo_data for deleting single occurrence of recurring event.
        
        CALENDAR-SPECIFIC: Captures exception date to remove.
        """
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        # Create recurring event
        create_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="Daily Standup",
            start=datetime(2025, 1, 15, 9, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 9, 30, tzinfo=timezone.utc),
            recurrence=RecurrenceRule(
                frequency="daily",
                interval=1,
                end_type="count",
                count=10,
            ),
        )
        create_input.validate_input()
        state.apply_input(create_input)
        
        # Delete single occurrence
        delete_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
            operation="delete",
            event_id=create_input.event_id,
            title="",
            start=datetime(2025, 1, 15, 9, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 9, 30, tzinfo=timezone.utc),
            recurrence_scope="this",
            recurrence_id="2025-01-17",
        )
        
        undo_data = state.create_undo_data(delete_input)
        
        assert undo_data["action"] == "remove_exception"
        assert undo_data["recurrence_id"] == "2025-01-17"

    def test_create_undo_data_captures_state_metadata(self):
        """Test that create_undo_data captures state-level metadata.
        
        GENERAL PATTERN: Undo data should include state-level update_count and last_updated.
        """
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        # Apply one event
        create_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="First Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        create_input.validate_input()
        state.apply_input(create_input)
        
        original_update_count = state.update_count
        
        # Create second event
        second_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
            operation="create",
            title="Second Event",
            start=datetime(2025, 1, 16, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 16, 15, 0, tzinfo=timezone.utc),
        )
        second_input.validate_input()
        
        undo_data = state.create_undo_data(second_input)
        
        assert "state_previous_update_count" in undo_data
        assert "state_previous_last_updated" in undo_data
        assert undo_data["state_previous_update_count"] == original_update_count

    def test_create_undo_data_raises_for_invalid_input_type(self):
        """Test that create_undo_data raises for non-CalendarInput.
        
        GENERAL PATTERN: All modalities should validate input type.
        """
        from models.modalities.location_input import LocationInput
        
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        invalid_input = LocationInput(
            latitude=40.0,
            longitude=-74.0,
            timestamp=datetime.now(timezone.utc),
        )
        
        with pytest.raises(ValueError, match="CalendarInput"):
            state.create_undo_data(invalid_input)

    def test_create_undo_data_does_not_modify_state(self):
        """Test that create_undo_data does not modify state.
        
        GENERAL PATTERN: create_undo_data should be read-only.
        """
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        create_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="Test Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        create_input.validate_input()
        state.apply_input(create_input)
        
        original_update_count = state.update_count
        original_event_count = len(state.events)
        
        # Create another input and get undo data (shouldn't modify state)
        another_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
            operation="create",
            title="Another Event",
            start=datetime(2025, 1, 16, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 16, 15, 0, tzinfo=timezone.utc),
        )
        another_input.validate_input()
        state.create_undo_data(another_input)
        
        assert state.update_count == original_update_count
        assert len(state.events) == original_event_count


class TestCalendarStateApplyUndo:
    """Test CalendarState.apply_undo() method.
    
    GENERAL PATTERN: All ModalityState subclasses must implement apply_undo()
    to reverse a previous apply_input() operation using undo data.
    
    CALENDAR-SPECIFIC: Handles removing created events, restoring deleted events,
    undoing recurring event modifications, and handling split events.
    """

    def test_apply_undo_removes_created_event(self):
        """Test that apply_undo removes a created event.
        
        CALENDAR-SPECIFIC: remove_event action deletes the event from state.
        """
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        create_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="Test Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        create_input.validate_input()
        
        undo_data = state.create_undo_data(create_input)
        state.apply_input(create_input)
        
        assert len(state.events) == 1
        
        state.apply_undo(undo_data)
        
        assert len(state.events) == 0

    def test_apply_undo_removes_new_calendar(self):
        """Test that apply_undo removes calendar created as side effect.
        
        CALENDAR-SPECIFIC: When event creation created a new calendar, undo removes it.
        """
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        create_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            calendar_id="work",
            title="Work Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        create_input.validate_input()
        
        undo_data = state.create_undo_data(create_input)
        state.apply_input(create_input)
        
        assert "work" in state.calendars
        
        state.apply_undo(undo_data)
        
        assert "work" not in state.calendars

    def test_apply_undo_restores_updated_event(self):
        """Test that apply_undo restores event after update.
        
        CALENDAR-SPECIFIC: restore_event action restores previous event state.
        """
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        # Create event
        create_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="Original Title",
            location="Room A",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        create_input.validate_input()
        state.apply_input(create_input)
        
        # Update event
        update_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
            operation="update",
            event_id=create_input.event_id,
            title="Updated Title",
            location="Room B",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        
        undo_data = state.create_undo_data(update_input)
        state.apply_input(update_input)
        
        assert state.events[create_input.event_id].title == "Updated Title"
        assert state.events[create_input.event_id].location == "Room B"
        
        state.apply_undo(undo_data)
        
        assert state.events[create_input.event_id].title == "Original Title"
        assert state.events[create_input.event_id].location == "Room A"

    def test_apply_undo_restores_deleted_event(self):
        """Test that apply_undo restores a deleted event.
        
        CALENDAR-SPECIFIC: restore_deleted_event action brings back the event.
        """
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        # Create event
        create_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="Event to Delete",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        create_input.validate_input()
        state.apply_input(create_input)
        
        event_id = create_input.event_id
        
        # Delete event
        delete_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
            operation="delete",
            event_id=event_id,
            title="",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        
        undo_data = state.create_undo_data(delete_input)
        state.apply_input(delete_input)
        
        assert event_id not in state.events
        
        state.apply_undo(undo_data)
        
        assert event_id in state.events
        assert state.events[event_id].title == "Event to Delete"

    def test_apply_undo_removes_exception_date(self):
        """Test that apply_undo removes exception date for single occurrence delete.
        
        CALENDAR-SPECIFIC: remove_exception action removes the exception.
        """
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        # Create recurring event
        create_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="Daily Standup",
            start=datetime(2025, 1, 15, 9, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 9, 30, tzinfo=timezone.utc),
            recurrence=RecurrenceRule(
                frequency="daily",
                interval=1,
                end_type="count",
                count=10,
            ),
        )
        create_input.validate_input()
        state.apply_input(create_input)
        
        event_id = create_input.event_id
        
        # Delete single occurrence
        delete_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
            operation="delete",
            event_id=event_id,
            title="",
            start=datetime(2025, 1, 17, 9, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 17, 9, 30, tzinfo=timezone.utc),
            recurrence_scope="this",
            recurrence_id="2025-01-17",
        )
        
        undo_data = state.create_undo_data(delete_input)
        state.apply_input(delete_input)
        
        assert "2025-01-17" in state.events[event_id].recurrence_exceptions
        
        state.apply_undo(undo_data)
        
        assert "2025-01-17" not in state.events[event_id].recurrence_exceptions

    def test_apply_undo_restores_state_metadata(self):
        """Test that apply_undo restores state-level metadata.
        
        GENERAL PATTERN: State-level update_count and last_updated are restored.
        """
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        # Create event
        create_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="Test Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        create_input.validate_input()
        state.apply_input(create_input)
        
        original_update_count = state.update_count
        original_last_updated = state.last_updated
        
        # Create another event
        second_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
            operation="create",
            title="Second Event",
            start=datetime(2025, 1, 16, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 16, 15, 0, tzinfo=timezone.utc),
        )
        second_input.validate_input()
        
        undo_data = state.create_undo_data(second_input)
        state.apply_input(second_input)
        
        state.apply_undo(undo_data)
        
        assert state.update_count == original_update_count
        assert state.last_updated == original_last_updated

    def test_apply_undo_noop(self):
        """Test that apply_undo handles noop action correctly.
        
        GENERAL PATTERN: Noop only restores metadata.
        """
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        # Create event
        create_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="Test Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        create_input.validate_input()
        state.apply_input(create_input)
        
        original_update_count = state.update_count
        
        # Update nonexistent event (will be noop)
        update_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
            operation="update",
            event_id="nonexistent",
            title="Updated",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        
        undo_data = state.create_undo_data(update_input)
        
        # Manually increment to simulate the operation (would fail normally)
        state.update_count += 1
        state.last_updated = update_input.timestamp
        
        state.apply_undo(undo_data)
        
        assert state.update_count == original_update_count
        assert len(state.events) == 1

    def test_apply_undo_raises_for_missing_action(self):
        """Test that apply_undo raises for undo_data without action.
        
        GENERAL PATTERN: Undo data must have an action field.
        """
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        with pytest.raises(ValueError, match="action"):
            state.apply_undo({"event_id": "test"})

    def test_apply_undo_raises_for_missing_event_id(self):
        """Test that apply_undo raises for remove_event without event_id.
        
        GENERAL PATTERN: remove_event action needs event_id.
        """
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        with pytest.raises(ValueError, match="event_id"):
            state.apply_undo({
                "action": "remove_event",
                "calendar_id": "primary",
                "state_previous_update_count": 0,
                "state_previous_last_updated": datetime.now(timezone.utc).isoformat(),
            })

    def test_apply_undo_raises_for_unknown_action(self):
        """Test that apply_undo raises for unknown action.
        
        GENERAL PATTERN: Only valid actions should be accepted.
        """
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        with pytest.raises(ValueError, match="Unknown undo action"):
            state.apply_undo({
                "action": "invalid_action",
                "state_previous_update_count": 0,
                "state_previous_last_updated": datetime.now(timezone.utc).isoformat(),
            })

    def test_apply_undo_raises_for_event_not_found(self):
        """Test that apply_undo raises when event to remove doesn't exist.
        
        GENERAL PATTERN: Cannot undo if state is inconsistent.
        """
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        with pytest.raises(RuntimeError, match="not found"):
            state.apply_undo({
                "action": "remove_event",
                "event_id": "nonexistent",
                "calendar_id": "primary",
                "was_new_calendar": False,
                "state_previous_update_count": 0,
                "state_previous_last_updated": datetime.now(timezone.utc).isoformat(),
            })

    def test_undo_full_cycle_create_event(self):
        """Test complete undo cycle for creating an event.
        
        INTEGRATION: create_undo_data -> apply_input -> apply_undo should be idempotent.
        """
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        original_snapshot = state.get_snapshot()
        
        create_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="Test Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        create_input.validate_input()
        
        undo_data = state.create_undo_data(create_input)
        state.apply_input(create_input)
        state.apply_undo(undo_data)
        
        restored_snapshot = state.get_snapshot()
        assert restored_snapshot["event_count"] == original_snapshot["event_count"]
        assert restored_snapshot["update_count"] == original_snapshot["update_count"]

    def test_undo_full_cycle_update_event(self):
        """Test complete undo cycle for updating an event.
        
        INTEGRATION: create_undo_data -> apply_input -> apply_undo should be idempotent.
        """
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        # Create event
        create_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="Original",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        create_input.validate_input()
        state.apply_input(create_input)
        
        original_snapshot = state.get_snapshot()
        original_title = state.events[create_input.event_id].title
        
        # Update event
        update_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
            operation="update",
            event_id=create_input.event_id,
            title="Updated",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        
        undo_data = state.create_undo_data(update_input)
        state.apply_input(update_input)
        state.apply_undo(undo_data)
        
        assert state.events[create_input.event_id].title == original_title
        assert state.update_count == original_snapshot["update_count"]

    def test_undo_full_cycle_delete_event(self):
        """Test complete undo cycle for deleting an event.
        
        INTEGRATION: create_undo_data -> apply_input -> apply_undo should be idempotent.
        """
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        # Create event
        create_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="Event to Delete",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        create_input.validate_input()
        state.apply_input(create_input)
        
        original_snapshot = state.get_snapshot()
        
        # Delete event
        delete_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
            operation="delete",
            event_id=create_input.event_id,
            title="",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        
        undo_data = state.create_undo_data(delete_input)
        state.apply_input(delete_input)
        state.apply_undo(undo_data)
        
        restored_snapshot = state.get_snapshot()
        assert restored_snapshot["event_count"] == original_snapshot["event_count"]
        assert restored_snapshot["update_count"] == original_snapshot["update_count"]

    def test_multiple_undo_operations(self):
        """Test multiple sequential undo operations.
        
        INTEGRATION: Multiple undos should work correctly in sequence.
        """
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        undo_stack = []
        
        # Create multiple events
        for i in range(5):
            create_input = CalendarInput(
                timestamp=datetime(2025, 1, 1, 13 + i, 0, tzinfo=timezone.utc),
                operation="create",
                title=f"Event {i}",
                start=datetime(2025, 1, 15 + i, 14, 0, tzinfo=timezone.utc),
                end=datetime(2025, 1, 15 + i, 15, 0, tzinfo=timezone.utc),
            )
            create_input.validate_input()
            
            undo_data = state.create_undo_data(create_input)
            undo_stack.append(undo_data)
            state.apply_input(create_input)
        
        assert len(state.events) == 5
        assert state.update_count == 5
        
        # Undo all in reverse
        for undo_data in reversed(undo_stack):
            state.apply_undo(undo_data)
        
        assert len(state.events) == 0
        assert state.update_count == 0

    def test_undo_mixed_operations(self):
        """Test undoing a mix of create, update, and delete operations.
        
        INTEGRATION: Different operation types should undo correctly.
        """
        state = CalendarState(
            last_updated=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        
        undo_stack = []
        
        # Create event
        create_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="Original",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        create_input.validate_input()
        undo_data = state.create_undo_data(create_input)
        undo_stack.append(undo_data)
        state.apply_input(create_input)
        
        # Update event
        update_input = CalendarInput(
            timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
            operation="update",
            event_id=create_input.event_id,
            title="Updated",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        undo_data = state.create_undo_data(update_input)
        undo_stack.append(undo_data)
        state.apply_input(update_input)
        
        assert state.events[create_input.event_id].title == "Updated"
        
        # Undo update - should restore to "Original"
        state.apply_undo(undo_stack.pop())
        assert state.events[create_input.event_id].title == "Original"
        
        # Undo create - should remove event
        state.apply_undo(undo_stack.pop())
        assert len(state.events) == 0
