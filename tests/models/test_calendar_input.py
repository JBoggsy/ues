"""Unit tests for calendar input modality.

This module tests both general ModalityInput behavior and calendar-specific features.
"""

from datetime import datetime, date, timezone

import pytest

from models.modalities.calendar_input import (
    Attendee,
    Attachment,
    CalendarInput,
    RecurrenceRule,
    Reminder,
)


class TestCalendarInputInstantiation:
    """Test instantiation patterns for CalendarInput.

    GENERAL PATTERN: All ModalityInput subclasses should instantiate with timestamp
    and modality parameters.
    """

    def test_minimal_create_instantiation(self):
        """GENERAL PATTERN: Verify CalendarInput instantiates with minimal required fields."""
        event = CalendarInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="create",
            title="Test Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )

        assert event.timestamp == datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        assert event.modality_type == "calendar"
        assert event.operation == "create"
        assert event.title == "Test Event"
        assert event.start == datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc)
        assert event.end == datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc)

    def test_update_instantiation(self):
        """MODALITY-SPECIFIC: Verify update operation with event_id."""
        event = CalendarInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="update",
            event_id="event-123",
            title="Updated Event",
            start=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 16, 0, tzinfo=timezone.utc),
        )

        assert event.operation == "update"
        assert event.event_id == "event-123"
        assert event.title == "Updated Event"

    def test_delete_instantiation(self):
        """MODALITY-SPECIFIC: Verify delete operation with event_id."""
        event = CalendarInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="delete",
            event_id="event-123",
            title="Deleted Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )

        assert event.operation == "delete"
        assert event.event_id == "event-123"

    def test_full_instantiation(self):
        """Verify CalendarInput instantiates with all optional fields."""
        attendees = [
            Attendee(email="alice@example.com", display_name="Alice"),
            Attendee(email="bob@example.com", optional=True),
        ]
        reminders = [
            Reminder(minutes_before=15, type="notification"),
            Reminder(minutes_before=60, type="email"),
        ]
        attachments = [
            Attachment(filename="agenda.pdf", size=102400, mime_type="application/pdf"),
        ]
        recurrence = RecurrenceRule(
            frequency="weekly",
            interval=1,
            days_of_week=["monday", "wednesday"],
            end_type="count",
            count=10,
        )

        event = CalendarInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="create",
            calendar_id="work",
            title="Team Meeting",
            description="Weekly sync meeting",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
            location="Conference Room A",
            timezone="America/New_York",
            status="confirmed",
            organizer="organizer@example.com",
            attendees=attendees,
            recurrence=recurrence,
            reminders=reminders,
            color="#FF5733",
            visibility="public",
            transparency="opaque",
            attachments=attachments,
            conference_link="https://meet.example.com/abc-defg",
        )

        assert event.calendar_id == "work"
        assert event.description == "Weekly sync meeting"
        assert event.location == "Conference Room A"
        assert event.timezone == "America/New_York"
        assert event.organizer == "organizer@example.com"
        assert len(event.attendees) == 2
        assert event.attendees[0].display_name == "Alice"
        assert event.recurrence.frequency == "weekly"
        assert len(event.reminders) == 2
        assert event.color == "#FF5733"
        assert len(event.attachments) == 1

    def test_default_values(self):
        """GENERAL PATTERN: Verify CalendarInput applies correct defaults."""
        event = CalendarInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="create",
            title="Test",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )

        assert event.calendar_id == "primary"
        assert event.recurrence_scope == "this"
        assert event.all_day is False
        assert event.timezone == "UTC"
        assert event.status == "confirmed"
        assert event.visibility == "default"
        assert event.transparency == "opaque"
        assert event.description is None
        assert event.attendees is None
        assert event.recurrence is None

    def test_all_day_event(self):
        """MODALITY-SPECIFIC: Verify all-day event creation."""
        event = CalendarInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="create",
            title="Vacation",
            start=datetime(2025, 7, 1, 0, 0, tzinfo=timezone.utc),
            end=datetime(2025, 7, 8, 0, 0, tzinfo=timezone.utc),
            all_day=True,
        )

        assert event.all_day is True
        assert event.start.hour == 0
        assert event.start.minute == 0


class TestAttendeeModel:
    """Test Attendee Pydantic helper class.

    MODALITY-SPECIFIC: Attendee validation and serialization.
    """

    def test_attendee_minimal(self):
        """Verify Attendee instantiates with minimal fields."""
        attendee = Attendee(email="alice@example.com")

        assert attendee.email == "alice@example.com"
        assert attendee.display_name is None
        assert attendee.optional is False
        assert attendee.response == "needs-action"
        assert attendee.comment is None

    def test_attendee_full(self):
        """Verify Attendee with all fields."""
        attendee = Attendee(
            email="bob@example.com",
            display_name="Bob Smith",
            optional=True,
            response="accepted",
            comment="Looking forward to it!",
        )

        assert attendee.email == "bob@example.com"
        assert attendee.display_name == "Bob Smith"
        assert attendee.optional is True
        assert attendee.response == "accepted"
        assert attendee.comment == "Looking forward to it!"

    def test_attendee_email_validation(self):
        """MODALITY-SPECIFIC: Verify email validation."""
        with pytest.raises(ValueError, match="Invalid email format"):
            Attendee(email="not-an-email")

        with pytest.raises(ValueError, match="Invalid email format"):
            Attendee(email="missing-at-sign.com")

    def test_attendee_email_normalization(self):
        """MODALITY-SPECIFIC: Verify email is lowercased."""
        attendee = Attendee(email="Alice@EXAMPLE.COM")
        assert attendee.email == "alice@example.com"

    def test_attendee_to_dict(self):
        """Verify Attendee serialization to dict."""
        attendee = Attendee(
            email="alice@example.com",
            display_name="Alice",
            response="accepted",
        )

        result = attendee.to_dict()
        assert result["email"] == "alice@example.com"
        assert result["display_name"] == "Alice"
        assert result["optional"] is False
        assert result["response"] == "accepted"


class TestRecurrenceRuleModel:
    """Test RecurrenceRule Pydantic helper class.

    MODALITY-SPECIFIC: Recurrence rule validation and patterns.
    """

    def test_recurrence_daily(self):
        """MODALITY-SPECIFIC: Verify daily recurrence rule."""
        rule = RecurrenceRule(frequency="daily", interval=1, end_type="count", count=30)

        assert rule.frequency == "daily"
        assert rule.interval == 1
        assert rule.end_type == "count"
        assert rule.count == 30

    def test_recurrence_weekly(self):
        """MODALITY-SPECIFIC: Verify weekly recurrence with days."""
        rule = RecurrenceRule(
            frequency="weekly",
            interval=1,
            days_of_week=["monday", "wednesday", "friday"],
            end_type="never",
        )

        assert rule.frequency == "weekly"
        assert rule.days_of_week == ["monday", "wednesday", "friday"]
        assert rule.end_type == "never"

    def test_recurrence_monthly(self):
        """MODALITY-SPECIFIC: Verify monthly recurrence."""
        rule = RecurrenceRule(
            frequency="monthly",
            interval=1,
            day_of_month=15,
            end_type="until",
            end_date=date(2025, 12, 31),
        )

        assert rule.frequency == "monthly"
        assert rule.day_of_month == 15
        assert rule.end_date == date(2025, 12, 31)

    def test_recurrence_yearly(self):
        """MODALITY-SPECIFIC: Verify yearly recurrence."""
        rule = RecurrenceRule(
            frequency="yearly",
            interval=1,
            month_of_year=3,
            day_of_month=15,
            end_type="never",
        )

        assert rule.frequency == "yearly"
        assert rule.month_of_year == 3
        assert rule.day_of_month == 15

    def test_recurrence_duplicate_days_validation(self):
        """MODALITY-SPECIFIC: Verify days_of_week prevents duplicates."""
        with pytest.raises(ValueError, match="must not contain duplicates"):
            RecurrenceRule(
                frequency="weekly",
                days_of_week=["monday", "monday", "tuesday"],
                end_type="never",
            )

    def test_recurrence_to_dict(self):
        """Verify RecurrenceRule serialization."""
        rule = RecurrenceRule(
            frequency="weekly",
            interval=2,
            days_of_week=["tuesday", "thursday"],
            end_type="count",
            count=20,
        )

        result = rule.to_dict()
        assert result["frequency"] == "weekly"
        assert result["interval"] == 2
        assert result["days_of_week"] == ["tuesday", "thursday"]
        assert result["end_type"] == "count"
        assert result["count"] == 20


class TestReminderModel:
    """Test Reminder Pydantic helper class.

    MODALITY-SPECIFIC: Reminder validation.
    """

    def test_reminder_notification(self):
        """Verify notification reminder."""
        reminder = Reminder(minutes_before=15, type="notification")

        assert reminder.minutes_before == 15
        assert reminder.type == "notification"

    def test_reminder_email(self):
        """Verify email reminder."""
        reminder = Reminder(minutes_before=60, type="email")

        assert reminder.minutes_before == 60
        assert reminder.type == "email"

    def test_reminder_both(self):
        """Verify combined reminder."""
        reminder = Reminder(minutes_before=30, type="both")

        assert reminder.type == "both"

    def test_reminder_default_type(self):
        """Verify default reminder type."""
        reminder = Reminder(minutes_before=10)

        assert reminder.type == "notification"


class TestAttachmentModel:
    """Test Attachment Pydantic helper class.

    MODALITY-SPECIFIC: Attachment metadata handling.
    """

    def test_attachment_with_url(self):
        """Verify attachment with URL reference."""
        attachment = Attachment(
            filename="document.pdf",
            size=204800,
            mime_type="application/pdf",
            url="https://example.com/files/document.pdf",
        )

        assert attachment.filename == "document.pdf"
        assert attachment.size == 204800
        assert attachment.mime_type == "application/pdf"
        assert attachment.url == "https://example.com/files/document.pdf"
        assert attachment.attachment_id is not None

    def test_attachment_with_data(self):
        """Verify attachment with inline data."""
        attachment = Attachment(
            filename="image.png",
            size=51200,
            mime_type="image/png",
            data="base64encodeddata...",
        )

        assert attachment.filename == "image.png"
        assert attachment.data == "base64encodeddata..."

    def test_attachment_id_generation(self):
        """Verify attachment_id is auto-generated."""
        attachment1 = Attachment(filename="file1.txt", size=100, mime_type="text/plain")
        attachment2 = Attachment(filename="file2.txt", size=200, mime_type="text/plain")

        assert attachment1.attachment_id != attachment2.attachment_id


class TestCalendarInputValidation:
    """Test CalendarInput validation logic.

    MODALITY-SPECIFIC: Calendar-specific validation constraints.
    """

    def test_validate_create_requires_title(self):
        """MODALITY-SPECIFIC: Create operation requires title."""
        event = CalendarInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="create",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )

        with pytest.raises(ValueError, match="title is required"):
            event.validate_input()

    def test_validate_create_requires_start(self):
        """MODALITY-SPECIFIC: Create operation requires start time."""
        event = CalendarInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="create",
            title="Test Event",
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )

        with pytest.raises(ValueError, match="start is required"):
            event.validate_input()

    def test_validate_create_requires_end(self):
        """MODALITY-SPECIFIC: Create operation requires end time."""
        event = CalendarInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="create",
            title="Test Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
        )

        with pytest.raises(ValueError, match="end is required"):
            event.validate_input()

    def test_validate_create_generates_event_id(self):
        """MODALITY-SPECIFIC: Create operation auto-generates event_id."""
        event = CalendarInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="create",
            title="Test Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )

        assert event.event_id is None
        event.validate_input()
        assert event.event_id is not None

    def test_validate_update_requires_event_id(self):
        """MODALITY-SPECIFIC: Update operation requires event_id."""
        event = CalendarInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="update",
            title="Updated",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )

        with pytest.raises(ValueError, match="event_id is required"):
            event.validate_input()

    def test_validate_delete_requires_event_id(self):
        """MODALITY-SPECIFIC: Delete operation requires event_id."""
        event = CalendarInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="delete",
            title="Deleted",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )

        with pytest.raises(ValueError, match="event_id is required"):
            event.validate_input()

    def test_validate_end_after_start(self):
        """MODALITY-SPECIFIC: End time must be after start time."""
        event = CalendarInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="create",
            title="Test Event",
            start=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
        )

        with pytest.raises(ValueError, match="end time must be after start time"):
            event.validate_input()

    def test_validate_weekly_requires_days(self):
        """MODALITY-SPECIFIC: Weekly recurrence requires days_of_week."""
        event = CalendarInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="create",
            title="Test Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
            recurrence=RecurrenceRule(frequency="weekly", end_type="never"),
        )

        with pytest.raises(ValueError, match="days_of_week required"):
            event.validate_input()

    def test_validate_monthly_requires_day(self):
        """MODALITY-SPECIFIC: Monthly recurrence requires day_of_month."""
        event = CalendarInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="create",
            title="Test Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
            recurrence=RecurrenceRule(frequency="monthly", end_type="never"),
        )

        with pytest.raises(ValueError, match="day_of_month required"):
            event.validate_input()

    def test_validate_yearly_requires_month_and_day(self):
        """MODALITY-SPECIFIC: Yearly recurrence requires month_of_year and day_of_month."""
        event = CalendarInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="create",
            title="Test Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
            recurrence=RecurrenceRule(frequency="yearly", day_of_month=15, end_type="never"),
        )

        with pytest.raises(ValueError, match="month_of_year required"):
            event.validate_input()

    def test_validate_until_requires_end_date(self):
        """MODALITY-SPECIFIC: Recurrence end_type 'until' requires end_date."""
        event = CalendarInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="create",
            title="Test Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
            recurrence=RecurrenceRule(
                frequency="daily",
                end_type="until",
            ),
        )

        with pytest.raises(ValueError, match="end_date required"):
            event.validate_input()

    def test_validate_count_requires_count(self):
        """MODALITY-SPECIFIC: Recurrence end_type 'count' requires count value."""
        event = CalendarInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="create",
            title="Test Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
            recurrence=RecurrenceRule(
                frequency="daily",
                end_type="count",
            ),
        )

        with pytest.raises(ValueError, match="count required"):
            event.validate_input()

    def test_validate_organizer_email_format(self):
        """MODALITY-SPECIFIC: Organizer email must be valid format."""
        event = CalendarInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="create",
            title="Test Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
            organizer="not-an-email",
        )

        with pytest.raises(ValueError, match="Invalid organizer email format"):
            event.validate_input()


class TestCalendarInputMethods:
    """Test CalendarInput methods.

    GENERAL PATTERN: Test interface methods defined by ModalityInput.
    """

    def test_get_affected_entities(self):
        """GENERAL PATTERN: Verify affected entities are returned."""
        event = CalendarInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="update",
            event_id="event-123",
            calendar_id="work",
            title="Test",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )

        entities = event.get_affected_entities()
        assert "work" in entities
        assert "event-123" in entities

    def test_get_summary_create(self):
        """GENERAL PATTERN: Verify summary for create operation."""
        event = CalendarInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="create",
            title="Team Meeting",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )

        summary = event.get_summary()
        assert "Create event" in summary
        assert "Team Meeting" in summary
        assert "2025-01-15" in summary

    def test_get_summary_update(self):
        """GENERAL PATTERN: Verify summary for update operation."""
        event = CalendarInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="update",
            event_id="event-123",
            title="Updated Title",
            start=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 16, 0, tzinfo=timezone.utc),
        )

        summary = event.get_summary()
        assert "Update event" in summary
        assert "event-123" in summary

    def test_get_summary_delete(self):
        """GENERAL PATTERN: Verify summary for delete operation."""
        event = CalendarInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="delete",
            event_id="event-123",
            recurrence_scope="all",
            title="Deleted",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )

        summary = event.get_summary()
        assert "Delete event" in summary
        assert "event-123" in summary
        assert "all" in summary

    def test_should_merge_with(self):
        """GENERAL PATTERN: Calendar inputs don't merge."""
        event1 = CalendarInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="create",
            title="Event 1",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )
        event2 = CalendarInput(
            timestamp=datetime(2025, 1, 1, 13, 0, tzinfo=timezone.utc),
            operation="create",
            title="Event 2",
            start=datetime(2025, 1, 16, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 16, 15, 0, tzinfo=timezone.utc),
        )

        assert event1.should_merge_with(event2) is False


class TestCalendarInputSerialization:
    """Test CalendarInput serialization.

    GENERAL PATTERN: Verify input can be serialized and deserialized.
    """

    def test_simple_serialization(self):
        """GENERAL PATTERN: Verify input serializes and deserializes."""
        original = CalendarInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="create",
            title="Test Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
        )

        dumped = original.model_dump()
        restored = CalendarInput.model_validate(dumped)

        assert restored.timestamp == original.timestamp
        assert restored.operation == original.operation
        assert restored.title == original.title
        assert restored.start == original.start
        assert restored.end == original.end

    def test_complex_serialization(self):
        """Verify complex input with nested objects serializes."""
        original = CalendarInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="create",
            title="Complex Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
            attendees=[
                Attendee(email="alice@example.com", display_name="Alice"),
            ],
            recurrence=RecurrenceRule(
                frequency="weekly",
                days_of_week=["monday"],
                end_type="count",
                count=10,
            ),
            reminders=[Reminder(minutes_before=15)],
        )

        dumped = original.model_dump()
        restored = CalendarInput.model_validate(dumped)

        assert len(restored.attendees) == 1
        assert restored.attendees[0].email == "alice@example.com"
        assert restored.recurrence.frequency == "weekly"
        assert len(restored.reminders) == 1


class TestCalendarInputEdgeCases:
    """Test CalendarInput edge cases.

    GENERAL PATTERN: Test boundary conditions and edge cases.
    """

    def test_same_start_and_end_invalid(self):
        """MODALITY-SPECIFIC: Events with same start and end times are invalid."""
        event = CalendarInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="create",
            title="Zero Duration Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
        )

        with pytest.raises(ValueError, match="end time must be after start time"):
            event.validate_input()

    def test_multiple_attendees(self):
        """MODALITY-SPECIFIC: Event can have many attendees."""
        attendees = [
            Attendee(email=f"user{i}@example.com") for i in range(50)
        ]

        event = CalendarInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="create",
            title="Large Meeting",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
            attendees=attendees,
        )

        assert len(event.attendees) == 50

    def test_multiple_reminders(self):
        """MODALITY-SPECIFIC: Event can have multiple reminders."""
        reminders = [
            Reminder(minutes_before=1),
            Reminder(minutes_before=15),
            Reminder(minutes_before=60),
            Reminder(minutes_before=1440),  # 1 day
        ]

        event = CalendarInput(
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            operation="create",
            title="Important Event",
            start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
            end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
            reminders=reminders,
        )

        assert len(event.reminders) == 4

    def test_recurrence_scope_values(self):
        """MODALITY-SPECIFIC: Test all recurrence scope options."""
        for scope in ["this", "this_and_future", "all"]:
            event = CalendarInput(
                timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
                operation="update",
                event_id="event-123",
                recurrence_scope=scope,
                title="Test",
                start=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
                end=datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc),
            )
            assert event.recurrence_scope == scope


class TestCalendarInputFromFixtures:
    """Test using pre-built calendar fixtures.

    GENERAL PATTERN: Verify fixtures work correctly.
    """

    def test_create_calendar_input_fixture(self):
        """Verify create_calendar_input factory function."""
        from tests.fixtures.modalities.calendar import create_calendar_input

        event = create_calendar_input(
            title="Custom Event",
            operation="create",
        )

        assert event.modality_type == "calendar"
        assert event.title == "Custom Event"
        assert event.operation == "create"
        assert event.start is not None
        assert event.end is not None

    def test_simple_event_fixture(self):
        """Verify SIMPLE_EVENT fixture."""
        from tests.fixtures.modalities.calendar import SIMPLE_EVENT

        assert SIMPLE_EVENT.operation == "create"
        assert SIMPLE_EVENT.title == "Test Event"

    def test_meeting_event_fixture(self):
        """Verify MEETING_EVENT fixture with attendees."""
        from tests.fixtures.modalities.calendar import MEETING_EVENT

        assert MEETING_EVENT.title == "Team Meeting"
        assert len(MEETING_EVENT.attendees) == 3
        assert MEETING_EVENT.location == "Conference Room A"

    def test_recurring_daily_standup_fixture(self):
        """Verify RECURRING_DAILY_STANDUP fixture."""
        from tests.fixtures.modalities.calendar import RECURRING_DAILY_STANDUP

        assert RECURRING_DAILY_STANDUP.recurrence is not None
        assert RECURRING_DAILY_STANDUP.recurrence.frequency == "daily"
        assert RECURRING_DAILY_STANDUP.recurrence.end_type == "count"
