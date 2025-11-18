"""Calendar input model."""

from datetime import date, datetime
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from models.base_input import ModalityInput


CalendarOperation = Literal["create", "update", "delete"]
RecurrenceScope = Literal["this", "this_and_future", "all"]
AttendeeResponse = Literal["accepted", "declined", "tentative", "needs-action"]
EventStatus = Literal["confirmed", "tentative", "cancelled"]
EventVisibility = Literal["public", "private", "default"]
EventTransparency = Literal["opaque", "transparent"]
ReminderType = Literal["notification", "email", "both"]
RecurrenceFrequency = Literal["daily", "weekly", "monthly", "yearly"]
RecurrenceEndType = Literal["never", "until", "count"]
DayOfWeek = Literal[
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
]


class Attendee(BaseModel):
    """Represents an event attendee.

    Args:
        email: Attendee email address.
        display_name: Optional attendee display name.
        optional: Whether attendance is optional (default: False).
        response: Attendee's response status.
        comment: Optional response comment.
    """

    email: str = Field(description="Attendee email address")
    display_name: Optional[str] = Field(
        default=None, description="Attendee display name"
    )
    optional: bool = Field(default=False, description="Is attendance optional")
    response: AttendeeResponse = Field(
        default="needs-action", description="Attendee response status"
    )
    comment: Optional[str] = Field(default=None, description="Response comment")

    @field_validator("email")
    @classmethod
    def validate_email(cls, email: str) -> str:
        """Validate email format.

        Args:
            email: Email address to validate.

        Returns:
            The validated email address.

        Raises:
            ValueError: If email format is invalid.
        """
        if "@" not in email or "." not in email.split("@")[1]:
            raise ValueError(f"Invalid email format: {email}")
        return email.lower()

    def to_dict(self) -> dict:
        """Convert attendee to dictionary.

        Returns:
            Dictionary representation of this attendee.
        """
        result = {
            "email": self.email,
            "optional": self.optional,
            "response": self.response,
        }
        if self.display_name:
            result["display_name"] = self.display_name
        if self.comment:
            result["comment"] = self.comment
        return result


class RecurrenceRule(BaseModel):
    """Represents a recurrence rule for repeating events.

    Args:
        frequency: How often event repeats (daily, weekly, monthly, yearly).
        interval: Repeat every N periods (default: 1).
        days_of_week: For weekly - which days to repeat on.
        day_of_month: For monthly - which day of month (1-31).
        month_of_year: For yearly - which month (1-12).
        end_type: How recurrence ends (never, until date, or after count).
        end_date: End date if end_type is "until".
        count: Number of occurrences if end_type is "count".
    """

    frequency: RecurrenceFrequency = Field(description="Recurrence frequency")
    interval: int = Field(default=1, ge=1, description="Repeat every N periods")
    days_of_week: Optional[list[DayOfWeek]] = Field(
        default=None, description="Days for weekly recurrence"
    )
    day_of_month: Optional[int] = Field(
        default=None, ge=1, le=31, description="Day for monthly recurrence"
    )
    month_of_year: Optional[int] = Field(
        default=None, ge=1, le=12, description="Month for yearly recurrence"
    )
    end_type: RecurrenceEndType = Field(
        default="never", description="How recurrence ends"
    )
    end_date: Optional[date] = Field(
        default=None, description="End date for 'until' type"
    )
    count: Optional[int] = Field(
        default=None, ge=1, description="Occurrence count for 'count' type"
    )

    @field_validator("days_of_week")
    @classmethod
    def validate_days_of_week(cls, days: Optional[list[DayOfWeek]]) -> Optional[list[DayOfWeek]]:
        """Ensure days_of_week has no duplicates.

        Args:
            days: List of days of the week.

        Returns:
            The validated list of days.

        Raises:
            ValueError: If there are duplicate days.
        """
        if days and len(days) != len(set(days)):
            raise ValueError("days_of_week must not contain duplicates")
        return days

    def to_dict(self) -> dict:
        """Convert recurrence rule to dictionary.

        Returns:
            Dictionary representation of this rule.
        """
        result = {
            "frequency": self.frequency,
            "interval": self.interval,
            "end_type": self.end_type,
        }
        if self.days_of_week:
            result["days_of_week"] = self.days_of_week
        if self.day_of_month:
            result["day_of_month"] = self.day_of_month
        if self.month_of_year:
            result["month_of_year"] = self.month_of_year
        if self.end_date:
            result["end_date"] = self.end_date.isoformat()
        if self.count:
            result["count"] = self.count
        return result


class Reminder(BaseModel):
    """Represents an event reminder.

    Args:
        minutes_before: Minutes before event to trigger reminder.
        type: Type of reminder (notification, email, or both).
    """

    minutes_before: int = Field(ge=0, description="Minutes before event")
    type: ReminderType = Field(default="notification", description="Reminder type")

    def to_dict(self) -> dict:
        """Convert reminder to dictionary.

        Returns:
            Dictionary representation of this reminder.
        """
        return {
            "minutes_before": self.minutes_before,
            "type": self.type,
        }


class Attachment(BaseModel):
    """Represents an event attachment.

    Args:
        filename: Name of the attached file.
        size: File size in bytes.
        mime_type: MIME type of the file.
        url: Optional URL to the attachment.
        data: Optional inline attachment data.
        attachment_id: Unique identifier (auto-generated).
    """

    filename: str = Field(description="Filename")
    size: int = Field(ge=0, description="File size in bytes")
    mime_type: str = Field(description="MIME type")
    url: Optional[str] = Field(default=None, description="URL to attachment")
    data: Optional[str] = Field(default=None, description="Inline attachment data")
    attachment_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique identifier"
    )

    def to_dict(self) -> dict:
        """Convert attachment to dictionary.

        Returns:
            Dictionary representation of this attachment.
        """
        result = {
            "filename": self.filename,
            "size": self.size,
            "mime_type": self.mime_type,
            "attachment_id": self.attachment_id,
        }
        if self.url:
            result["url"] = self.url
        if self.data:
            result["data"] = self.data
        return result


class CalendarInput(ModalityInput):
    """Input for calendar operations (create, update, delete).

    Represents different types of calendar events and operations. Uses an
    operation-based design where different attributes are required depending
    on the operation type.

    Args:
        modality_type: Always "calendar" for this input type.
        timestamp: When operation occurred (simulator time).
        input_id: Unique input identifier (auto-generated).
        operation: Type of calendar operation to perform.
        event_id: Event identifier (auto-generated for create, required for update/delete).
        calendar_id: Which calendar this event belongs to.
        recurrence_scope: For recurring events - which occurrences to affect.
        title: Event title (required for create).
        description: Event description.
        start: Start datetime (required for create).
        end: End datetime (required for create).
        all_day: Whether this is an all-day event.
        timezone: Event time zone.
        location: Event location.
        status: Event status.
        organizer: Organizer email address.
        attendees: List of attendees.
        recurrence: Recurrence rule if recurring event.
        recurrence_exceptions: Dates to skip in recurrence.
        recurrence_id: For modified occurrences - which occurrence.
        reminders: List of reminders.
        color: Event color.
        visibility: Visibility level.
        transparency: Free/busy transparency.
        attachments: File attachments.
        conference_link: Video conference URL.
    """

    modality_type: str = Field(default="calendar", frozen=True)
    operation: CalendarOperation = Field(description="Calendar operation type")
    event_id: Optional[str] = Field(
        default=None, description="Event ID (auto-generated for create)"
    )
    calendar_id: str = Field(default="primary", description="Calendar ID")
    recurrence_scope: RecurrenceScope = Field(
        default="this", description="Recurrence scope for updates/deletes"
    )
    title: Optional[str] = Field(default=None, description="Event title")
    description: Optional[str] = Field(default=None, description="Event description")
    start: Optional[datetime] = Field(default=None, description="Start datetime")
    end: Optional[datetime] = Field(default=None, description="End datetime")
    all_day: bool = Field(default=False, description="Is all-day event")
    timezone: str = Field(default="UTC", description="Event time zone")
    location: Optional[str] = Field(default=None, description="Event location")
    status: EventStatus = Field(default="confirmed", description="Event status")
    organizer: Optional[str] = Field(default=None, description="Organizer email")
    attendees: Optional[list[Attendee]] = Field(
        default=None, description="Event attendees"
    )
    recurrence: Optional[RecurrenceRule] = Field(
        default=None, description="Recurrence rule"
    )
    recurrence_exceptions: Optional[list[str]] = Field(
        default=None, description="Exception dates (YYYY-MM-DD)"
    )
    recurrence_id: Optional[str] = Field(
        default=None, description="Which occurrence to modify"
    )
    reminders: Optional[list[Reminder]] = Field(
        default=None, description="Event reminders"
    )
    color: Optional[str] = Field(default=None, description="Event color")
    visibility: EventVisibility = Field(
        default="default", description="Visibility level"
    )
    transparency: EventTransparency = Field(
        default="opaque", description="Free/busy transparency"
    )
    attachments: Optional[list[Attachment]] = Field(
        default=None, description="File attachments"
    )
    conference_link: Optional[str] = Field(
        default=None, description="Video conference URL"
    )

    def validate_input(self) -> None:
        """Validate calendar input constraints.

        Raises:
            ValueError: If validation fails.
        """
        self._validate_operation_requirements()
        self._validate_time_logic()
        self._validate_recurrence_consistency()
        self._validate_organizer_email()

    def _validate_operation_requirements(self) -> None:
        """Validate required fields for each operation type.

        Raises:
            ValueError: If required fields are missing.
        """
        if self.operation == "create":
            if not self.title:
                raise ValueError("title is required for create operation")
            if not self.start:
                raise ValueError("start is required for create operation")
            if not self.end:
                raise ValueError("end is required for create operation")
            if not self.event_id:
                self.event_id = str(uuid4())
        elif self.operation in ["update", "delete"]:
            if not self.event_id:
                raise ValueError(f"event_id is required for {self.operation} operation")

    def _validate_time_logic(self) -> None:
        """Validate time-related constraints.

        Raises:
            ValueError: If time logic is invalid.
        """
        if self.start and self.end:
            if self.end <= self.start:
                raise ValueError("end time must be after start time")

        if self.recurrence and self.recurrence.end_type == "until":
            if not self.recurrence.end_date:
                raise ValueError("end_date required when end_type is 'until'")
            if self.start and self.recurrence.end_date < self.start.date():
                raise ValueError("recurrence end_date must be after start date")

        if self.recurrence and self.recurrence.end_type == "count":
            if not self.recurrence.count:
                raise ValueError("count required when end_type is 'count'")

    def _validate_recurrence_consistency(self) -> None:
        """Validate recurrence rule consistency.

        Raises:
            ValueError: If recurrence rule is inconsistent.
        """
        if not self.recurrence:
            return

        if self.recurrence.frequency == "weekly" and not self.recurrence.days_of_week:
            raise ValueError("days_of_week required for weekly recurrence")

        if self.recurrence.frequency == "monthly" and not self.recurrence.day_of_month:
            raise ValueError("day_of_month required for monthly recurrence")

        if self.recurrence.frequency == "yearly":
            if not self.recurrence.month_of_year:
                raise ValueError("month_of_year required for yearly recurrence")
            if not self.recurrence.day_of_month:
                raise ValueError("day_of_month required for yearly recurrence")

    def _validate_organizer_email(self) -> None:
        """Validate organizer email format if present.

        Raises:
            ValueError: If email format is invalid.
        """
        if self.organizer:
            if "@" not in self.organizer or "." not in self.organizer.split("@")[1]:
                raise ValueError(f"Invalid organizer email format: {self.organizer}")

    def get_affected_entities(self) -> list[str]:
        """Return list of entity IDs affected by this input.

        Returns:
            List containing calendar_id and event_id.
        """
        entities = [self.calendar_id]
        if self.event_id:
            entities.append(self.event_id)
        return entities

    def get_summary(self) -> str:
        """Generate human-readable summary of this input.

        Returns:
            Summary string describing the operation.
        """
        if self.operation == "create":
            start_str = self.start.strftime("%Y-%m-%d %H:%M") if self.start else "?"
            return f"Create event: {self.title} on {start_str}"
        elif self.operation == "update":
            updates = []
            if self.title:
                updates.append(f"title='{self.title}'")
            if self.start:
                updates.append(f"start={self.start.strftime('%Y-%m-%d %H:%M')}")
            update_str = ", ".join(updates) if updates else "fields"
            return f"Update event {self.event_id}: {update_str}"
        else:
            return f"Delete event {self.event_id} ({self.recurrence_scope})"

    def should_merge_with(self, other: ModalityInput) -> bool:
        """Check if this input should merge with another.

        Args:
            other: Another input to potentially merge with.

        Returns:
            Always False - calendar operations don't merge.
        """
        return False
