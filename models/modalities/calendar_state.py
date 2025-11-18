"""Calendar state model."""

from datetime import date, datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

from pydantic import Field

from models.base_input import ModalityInput
from models.base_state import ModalityState
from models.modalities.calendar_input import (
    Attachment,
    Attendee,
    CalendarInput,
    RecurrenceRule,
    Reminder,
)


class Calendar:
    """Represents a calendar container for events.

    Args:
        calendar_id: Unique calendar identifier.
        name: Calendar display name.
        color: Calendar color (hex code).
        visible: Whether calendar is currently shown.
        created_at: When calendar was created.
        updated_at: When calendar was last modified.
        event_ids: Set of event IDs in this calendar.
        default_reminders: Default reminder settings for new events.
    """

    def __init__(
        self,
        calendar_id: str,
        name: str,
        color: str = "#4285f4",
        visible: bool = True,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        event_ids: Optional[set[str]] = None,
        default_reminders: Optional[list[Reminder]] = None,
    ):
        """Initialize a calendar.

        Args:
            calendar_id: Unique identifier.
            name: Display name.
            color: Calendar color.
            visible: Visibility flag.
            created_at: Creation timestamp.
            updated_at: Last update timestamp.
            event_ids: Set of event IDs.
            default_reminders: Default reminders.
        """
        self.calendar_id = calendar_id
        self.name = name
        self.color = color
        self.visible = visible
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.event_ids = event_ids or set()
        self.default_reminders = default_reminders or []

    def to_dict(self) -> dict[str, Any]:
        """Convert calendar to dictionary.

        Returns:
            Dictionary representation of this calendar.
        """
        return {
            "calendar_id": self.calendar_id,
            "name": self.name,
            "color": self.color,
            "visible": self.visible,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "event_count": len(self.event_ids),
            "default_reminders": [r.to_dict() for r in self.default_reminders],
        }


class CalendarEvent:
    """Represents a calendar event with all metadata.

    Args:
        event_id: Unique event identifier.
        calendar_id: Which calendar this belongs to.
        title: Event title.
        start: Start datetime.
        end: End datetime.
        all_day: All-day event flag.
        timezone: Event time zone.
        description: Event description.
        location: Event location.
        status: Event status.
        organizer: Organizer email.
        attendees: List of attendees.
        recurrence: Recurrence rule.
        recurrence_exceptions: Set of skipped dates.
        recurrence_id: If modified occurrence, which one.
        parent_event_id: If modified occurrence, link to parent.
        reminders: List of reminders.
        color: Event color override.
        visibility: Visibility level.
        transparency: Free/busy transparency.
        attachments: List of attachments.
        conference_link: Video conference URL.
        created_at: When event was created.
        updated_at: When event was last modified.
        deleted_at: If deleted, when.
    """

    def __init__(
        self,
        event_id: str,
        calendar_id: str,
        title: str,
        start: datetime,
        end: datetime,
        all_day: bool = False,
        timezone: str = "UTC",
        description: Optional[str] = None,
        location: Optional[str] = None,
        status: str = "confirmed",
        organizer: Optional[str] = None,
        attendees: Optional[list[Attendee]] = None,
        recurrence: Optional[RecurrenceRule] = None,
        recurrence_exceptions: Optional[set[str]] = None,
        recurrence_id: Optional[str] = None,
        parent_event_id: Optional[str] = None,
        reminders: Optional[list[Reminder]] = None,
        color: Optional[str] = None,
        visibility: str = "default",
        transparency: str = "opaque",
        attachments: Optional[list[Attachment]] = None,
        conference_link: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        deleted_at: Optional[datetime] = None,
    ):
        """Initialize a calendar event.

        Args:
            event_id: Unique identifier.
            calendar_id: Parent calendar ID.
            title: Event title.
            start: Start datetime.
            end: End datetime.
            all_day: All-day flag.
            timezone: Event timezone.
            description: Description text.
            location: Location text.
            status: Event status.
            organizer: Organizer email.
            attendees: Attendee list.
            recurrence: Recurrence rule.
            recurrence_exceptions: Exception dates.
            recurrence_id: Occurrence identifier.
            parent_event_id: Parent event link.
            reminders: Reminder list.
            color: Event color.
            visibility: Visibility level.
            transparency: Transparency setting.
            attachments: Attachment list.
            conference_link: Conference URL.
            created_at: Creation timestamp.
            updated_at: Update timestamp.
            deleted_at: Deletion timestamp.
        """
        self.event_id = event_id
        self.calendar_id = calendar_id
        self.title = title
        self.start = start
        self.end = end
        self.all_day = all_day
        self.timezone = timezone
        self.description = description
        self.location = location
        self.status = status
        self.organizer = organizer
        self.attendees = attendees or []
        self.recurrence = recurrence
        self.recurrence_exceptions = recurrence_exceptions or set()
        self.recurrence_id = recurrence_id
        self.parent_event_id = parent_event_id
        self.reminders = reminders or []
        self.color = color
        self.visibility = visibility
        self.transparency = transparency
        self.attachments = attachments or []
        self.conference_link = conference_link
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.deleted_at = deleted_at

    def is_recurring(self) -> bool:
        """Check if this event has a recurrence rule.

        Returns:
            True if event is recurring.
        """
        return self.recurrence is not None

    def is_modified_occurrence(self) -> bool:
        """Check if this is a modified occurrence of a recurring event.

        Returns:
            True if this is a modified occurrence.
        """
        return self.parent_event_id is not None

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary.

        Returns:
            Dictionary representation of this event.
        """
        result = {
            "event_id": self.event_id,
            "calendar_id": self.calendar_id,
            "title": self.title,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "all_day": self.all_day,
            "timezone": self.timezone,
            "status": self.status,
            "visibility": self.visibility,
            "transparency": self.transparency,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_recurring": self.is_recurring(),
            "has_attendees": len(self.attendees) > 0,
            "has_attachments": len(self.attachments) > 0,
        }

        if self.description:
            result["description"] = self.description
        if self.location:
            result["location"] = self.location
        if self.organizer:
            result["organizer"] = self.organizer
        if self.attendees:
            result["attendees"] = [a.to_dict() for a in self.attendees]
        if self.recurrence:
            result["recurrence"] = self.recurrence.to_dict()
        if self.recurrence_exceptions:
            result["recurrence_exceptions"] = sorted(list(self.recurrence_exceptions))
        if self.recurrence_id:
            result["recurrence_id"] = self.recurrence_id
        if self.parent_event_id:
            result["parent_event_id"] = self.parent_event_id
        if self.reminders:
            result["reminders"] = [r.to_dict() for r in self.reminders]
        if self.color:
            result["color"] = self.color
        if self.attachments:
            result["attachments"] = [a.to_dict() for a in self.attachments]
        if self.conference_link:
            result["conference_link"] = self.conference_link
        if self.deleted_at:
            result["deleted_at"] = self.deleted_at.isoformat()

        return result


class CalendarState(ModalityState):
    """Current calendar state tracking all calendars and events.

    Args:
        modality_type: Always "calendar".
        last_updated: When state was last modified.
        update_count: Number of operations applied.
        calendars: Dict mapping calendar_id to Calendar objects.
        events: Dict mapping event_id to CalendarEvent objects.
        default_calendar_id: ID of default calendar.
        user_timezone: User's default time zone.
    """

    model_config = {"arbitrary_types_allowed": True}

    modality_type: str = Field(default="calendar", frozen=True)
    last_updated: datetime = Field(
        default_factory=datetime.utcnow, description="Last update time"
    )
    update_count: int = Field(default=0, description="Number of updates")
    calendars: dict[str, Calendar] = Field(
        default_factory=dict, description="Calendar objects by ID"
    )
    events: dict[str, CalendarEvent] = Field(
        default_factory=dict, description="Event objects by ID"
    )
    default_calendar_id: str = Field(
        default="primary", description="Default calendar ID"
    )
    user_timezone: str = Field(default="UTC", description="User's time zone")

    def model_post_init(self, __context: Any) -> None:
        """Initialize state with default primary calendar if empty.

        Args:
            __context: Pydantic context (unused).
        """
        if not self.calendars:
            self.calendars["primary"] = Calendar(
                calendar_id="primary",
                name="Personal",
                color="#4285f4",
            )

    def apply_input(self, input_data: ModalityInput) -> None:
        """Apply a calendar input to update state.

        Args:
            input_data: CalendarInput to process.

        Raises:
            TypeError: If input_data is not a CalendarInput.
            ValueError: If operation is invalid.
        """
        if not isinstance(input_data, CalendarInput):
            raise TypeError(f"Expected CalendarInput, got {type(input_data)}")

        if input_data.operation == "create":
            self._handle_create(input_data)
        elif input_data.operation == "update":
            self._handle_update(input_data)
        elif input_data.operation == "delete":
            self._handle_delete(input_data)
        else:
            raise ValueError(f"Unknown operation: {input_data.operation}")

        self.last_updated = input_data.timestamp
        self.update_count += 1

    def _handle_create(self, input_data: CalendarInput) -> None:
        """Handle event creation.

        Args:
            input_data: CalendarInput with create operation.
        """
        if input_data.calendar_id not in self.calendars:
            self.calendars[input_data.calendar_id] = Calendar(
                calendar_id=input_data.calendar_id,
                name=input_data.calendar_id.title(),
            )

        event = CalendarEvent(
            event_id=input_data.event_id,
            calendar_id=input_data.calendar_id,
            title=input_data.title,
            start=input_data.start,
            end=input_data.end,
            all_day=input_data.all_day,
            timezone=input_data.timezone,
            description=input_data.description,
            location=input_data.location,
            status=input_data.status,
            organizer=input_data.organizer,
            attendees=input_data.attendees,
            recurrence=input_data.recurrence,
            reminders=input_data.reminders,
            color=input_data.color,
            visibility=input_data.visibility,
            transparency=input_data.transparency,
            attachments=input_data.attachments,
            conference_link=input_data.conference_link,
            created_at=input_data.timestamp,
            updated_at=input_data.timestamp,
        )

        self.events[event.event_id] = event
        self.calendars[input_data.calendar_id].event_ids.add(event.event_id)
        self.calendars[input_data.calendar_id].updated_at = input_data.timestamp

    def _handle_update(self, input_data: CalendarInput) -> None:
        """Handle event update.

        Args:
            input_data: CalendarInput with update operation.

        Raises:
            ValueError: If event not found.
        """
        if input_data.event_id not in self.events:
            raise ValueError(f"Event {input_data.event_id} not found")

        event = self.events[input_data.event_id]

        if event.is_recurring() and input_data.recurrence_scope != "this":
            self._handle_recurring_update(event, input_data)
        else:
            self._apply_updates_to_event(event, input_data)

        event.updated_at = input_data.timestamp

    def _handle_recurring_update(
        self, event: CalendarEvent, input_data: CalendarInput
    ) -> None:
        """Handle update to recurring event with scope.

        Args:
            event: The recurring event to update.
            input_data: Update input with recurrence_scope.
        """
        if input_data.recurrence_scope == "all":
            self._apply_updates_to_event(event, input_data)
        elif input_data.recurrence_scope == "this_and_future":
            self._split_recurring_event(event, input_data)
        elif input_data.recurrence_scope == "this" and input_data.recurrence_id:
            self._create_modified_occurrence(event, input_data)

    def _apply_updates_to_event(
        self, event: CalendarEvent, input_data: CalendarInput
    ) -> None:
        """Apply field updates to an event.

        Args:
            event: Event to update.
            input_data: Input containing updates.
        """
        if input_data.title is not None:
            event.title = input_data.title
        if input_data.description is not None:
            event.description = input_data.description
        if input_data.start is not None:
            event.start = input_data.start
        if input_data.end is not None:
            event.end = input_data.end
        if input_data.location is not None:
            event.location = input_data.location
        if input_data.status is not None:
            event.status = input_data.status
        if input_data.organizer is not None:
            event.organizer = input_data.organizer
        if input_data.attendees is not None:
            event.attendees = input_data.attendees
        if input_data.reminders is not None:
            event.reminders = input_data.reminders
        if input_data.color is not None:
            event.color = input_data.color
        if input_data.visibility is not None:
            event.visibility = input_data.visibility
        if input_data.transparency is not None:
            event.transparency = input_data.transparency
        if input_data.attachments is not None:
            event.attachments = input_data.attachments
        if input_data.conference_link is not None:
            event.conference_link = input_data.conference_link
        if input_data.recurrence_exceptions is not None:
            event.recurrence_exceptions.update(input_data.recurrence_exceptions)

    def _split_recurring_event(
        self, event: CalendarEvent, input_data: CalendarInput
    ) -> None:
        """Split recurring event at a date (this_and_future).

        Args:
            event: Original recurring event.
            input_data: Update input with recurrence_id indicating split point.
        """
        if not input_data.recurrence_id:
            return

        split_date = date.fromisoformat(input_data.recurrence_id)
        event.recurrence_exceptions.add(input_data.recurrence_id)

        if event.recurrence and event.recurrence.end_type == "until":
            event.recurrence.end_date = split_date - timedelta(days=1)

        new_event_id = str(uuid4())
        new_event = CalendarEvent(
            event_id=new_event_id,
            calendar_id=event.calendar_id,
            title=input_data.title or event.title,
            start=input_data.start or event.start,
            end=input_data.end or event.end,
            all_day=event.all_day,
            timezone=event.timezone,
            description=input_data.description or event.description,
            location=input_data.location or event.location,
            status=input_data.status or event.status,
            organizer=input_data.organizer or event.organizer,
            attendees=input_data.attendees or event.attendees,
            recurrence=event.recurrence,
            reminders=input_data.reminders or event.reminders,
            color=input_data.color or event.color,
            visibility=input_data.visibility or event.visibility,
            transparency=input_data.transparency or event.transparency,
            attachments=input_data.attachments or event.attachments,
            conference_link=input_data.conference_link or event.conference_link,
            created_at=input_data.timestamp,
            updated_at=input_data.timestamp,
        )

        self.events[new_event_id] = new_event
        self.calendars[event.calendar_id].event_ids.add(new_event_id)

    def _create_modified_occurrence(
        self, parent_event: CalendarEvent, input_data: CalendarInput
    ) -> None:
        """Create a modified occurrence of a recurring event.

        Args:
            parent_event: The parent recurring event.
            input_data: Update input with modifications.
        """
        if not input_data.recurrence_id:
            return

        parent_event.recurrence_exceptions.add(input_data.recurrence_id)

        modified_event_id = str(uuid4())
        modified_event = CalendarEvent(
            event_id=modified_event_id,
            calendar_id=parent_event.calendar_id,
            title=input_data.title or parent_event.title,
            start=input_data.start or parent_event.start,
            end=input_data.end or parent_event.end,
            all_day=parent_event.all_day,
            timezone=parent_event.timezone,
            description=input_data.description or parent_event.description,
            location=input_data.location or parent_event.location,
            status=input_data.status or parent_event.status,
            organizer=input_data.organizer or parent_event.organizer,
            attendees=input_data.attendees or parent_event.attendees,
            recurrence=None,
            recurrence_id=input_data.recurrence_id,
            parent_event_id=parent_event.event_id,
            reminders=input_data.reminders or parent_event.reminders,
            color=input_data.color or parent_event.color,
            visibility=input_data.visibility or parent_event.visibility,
            transparency=input_data.transparency or parent_event.transparency,
            attachments=input_data.attachments or parent_event.attachments,
            conference_link=input_data.conference_link or parent_event.conference_link,
            created_at=input_data.timestamp,
            updated_at=input_data.timestamp,
        )

        self.events[modified_event_id] = modified_event
        self.calendars[parent_event.calendar_id].event_ids.add(modified_event_id)

    def _handle_delete(self, input_data: CalendarInput) -> None:
        """Handle event deletion.

        Args:
            input_data: CalendarInput with delete operation.

        Raises:
            ValueError: If event not found.
        """
        if input_data.event_id not in self.events:
            raise ValueError(f"Event {input_data.event_id} not found")

        event = self.events[input_data.event_id]

        if event.is_recurring() and input_data.recurrence_scope != "all":
            if input_data.recurrence_scope == "this" and input_data.recurrence_id:
                event.recurrence_exceptions.add(input_data.recurrence_id)
            elif input_data.recurrence_scope == "this_and_future":
                self._split_recurring_event(event, input_data)
        else:
            self.calendars[event.calendar_id].event_ids.discard(event.event_id)
            del self.events[event.event_id]

    def get_snapshot(self) -> dict[str, Any]:
        """Get complete state snapshot.

        Returns:
            Dictionary containing all calendars and events.
        """
        return {
            "modality_type": self.modality_type,
            "last_updated": self.last_updated.isoformat(),
            "update_count": self.update_count,
            "default_calendar_id": self.default_calendar_id,
            "user_timezone": self.user_timezone,
            "calendars": {
                cid: cal.to_dict() for cid, cal in self.calendars.items()
            },
            "events": {eid: evt.to_dict() for eid, evt in self.events.items()},
            "calendar_count": len(self.calendars),
            "event_count": len(self.events),
        }

    def validate_state(self) -> None:
        """Validate state consistency.

        Raises:
            ValueError: If state is invalid.
        """
        for event_id, event in self.events.items():
            if event.calendar_id not in self.calendars:
                raise ValueError(
                    f"Event {event_id} references missing calendar {event.calendar_id}"
                )

            if event.end <= event.start:
                raise ValueError(
                    f"Event {event_id} has invalid time range: {event.start} to {event.end}"
                )

            if event.parent_event_id and event.parent_event_id not in self.events:
                raise ValueError(
                    f"Modified occurrence {event_id} references missing parent {event.parent_event_id}"
                )

        for calendar_id, calendar in self.calendars.items():
            for event_id in calendar.event_ids:
                if event_id not in self.events:
                    raise ValueError(
                        f"Calendar {calendar_id} references missing event {event_id}"
                    )

    def query(self, query_params: dict[str, Any]) -> dict[str, Any]:
        """Query events with filters.

        Args:
            query_params: Query parameters including:
                - calendar_ids: List of calendar IDs to filter.
                - start: Start date/datetime for range.
                - end: End date/datetime for range.
                - search: Text search in title/description/location.
                - status: Filter by status.
                - has_attendees: Filter by attendee presence.
                - recurring: Filter by recurring flag.
                - expand_recurring: Whether to expand recurring events.
                - limit: Maximum number of results.

        Returns:
            Dictionary with matching events.
        """
        calendar_ids = query_params.get("calendar_ids")
        start_date = query_params.get("start")
        end_date = query_params.get("end")
        search_text = query_params.get("search", "").lower()
        status_filter = query_params.get("status")
        has_attendees_filter = query_params.get("has_attendees")
        recurring_filter = query_params.get("recurring")
        expand_recurring = query_params.get("expand_recurring", False)
        limit = query_params.get("limit")

        matching_events = []

        for event in self.events.values():
            if not self._event_matches_filters(
                event,
                calendar_ids,
                status_filter,
                has_attendees_filter,
                recurring_filter,
                search_text,
            ):
                continue

            if expand_recurring and event.is_recurring() and start_date and end_date:
                occurrences = self._expand_recurrence(event, start_date, end_date)
                matching_events.extend(occurrences)
            else:
                if self._event_in_date_range(event, start_date, end_date):
                    matching_events.append(event.to_dict())

        matching_events.sort(key=lambda e: e["start"])

        if limit:
            matching_events = matching_events[:limit]

        return {
            "events": matching_events,
            "count": len(matching_events),
        }

    def _event_matches_filters(
        self,
        event: CalendarEvent,
        calendar_ids: Optional[list[str]],
        status_filter: Optional[str],
        has_attendees_filter: Optional[bool],
        recurring_filter: Optional[bool],
        search_text: str,
    ) -> bool:
        """Check if event matches query filters.

        Args:
            event: Event to check.
            calendar_ids: Calendar ID filter.
            status_filter: Status filter.
            has_attendees_filter: Attendees filter.
            recurring_filter: Recurring filter.
            search_text: Search text.

        Returns:
            True if event matches all filters.
        """
        if calendar_ids and event.calendar_id not in calendar_ids:
            return False

        if status_filter and event.status != status_filter:
            return False

        if has_attendees_filter is not None:
            if has_attendees_filter and not event.attendees:
                return False
            if not has_attendees_filter and event.attendees:
                return False

        if recurring_filter is not None:
            if recurring_filter and not event.is_recurring():
                return False
            if not recurring_filter and event.is_recurring():
                return False

        if search_text:
            searchable = (
                f"{event.title} {event.description or ''} {event.location or ''}"
            ).lower()
            if search_text not in searchable:
                return False

        return True

    def _event_in_date_range(
        self,
        event: CalendarEvent,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> bool:
        """Check if event falls within date range.

        Args:
            event: Event to check.
            start_date: Range start.
            end_date: Range end.

        Returns:
            True if event is in range.
        """
        if start_date and event.end < start_date:
            return False
        if end_date and event.start > end_date:
            return False
        return True

    def _expand_recurrence(
        self, event: CalendarEvent, start_date: datetime, end_date: datetime
    ) -> list[dict[str, Any]]:
        """Expand recurring event into individual occurrences.

        Args:
            event: Recurring event to expand.
            start_date: Start of range.
            end_date: End of range.

        Returns:
            List of occurrence dictionaries.
        """
        if not event.recurrence:
            return []

        occurrences = []
        current_date = max(event.start.date(), start_date.date())
        end_limit = end_date.date()

        if event.recurrence.end_type == "until" and event.recurrence.end_date:
            end_limit = min(end_limit, event.recurrence.end_date)

        count = 0
        max_count = event.recurrence.count if event.recurrence.end_type == "count" else None

        while current_date <= end_limit:
            if max_count and count >= max_count:
                break

            date_str = current_date.isoformat()

            if date_str not in event.recurrence_exceptions:
                occurrence_start = datetime.combine(
                    current_date, event.start.time()
                )
                occurrence_end = datetime.combine(
                    current_date, event.end.time()
                )

                occurrence_dict = event.to_dict()
                occurrence_dict["start"] = occurrence_start.isoformat()
                occurrence_dict["end"] = occurrence_end.isoformat()
                occurrence_dict["occurrence_date"] = date_str

                occurrences.append(occurrence_dict)
                count += 1

            current_date = self._get_next_occurrence_date(event, current_date)

            if current_date > end_limit:
                break

        return occurrences

    def _get_next_occurrence_date(
        self, event: CalendarEvent, current_date: date
    ) -> date:
        """Calculate next occurrence date for recurring event.

        Args:
            event: The recurring event.
            current_date: Current occurrence date.

        Returns:
            Next occurrence date.
        """
        if not event.recurrence:
            return current_date

        frequency = event.recurrence.frequency
        interval = event.recurrence.interval

        if frequency == "daily":
            return current_date + timedelta(days=interval)
        elif frequency == "weekly":
            return current_date + timedelta(weeks=interval)
        elif frequency == "monthly":
            next_month = current_date.month + interval
            next_year = current_date.year + (next_month - 1) // 12
            next_month = ((next_month - 1) % 12) + 1
            day = min(current_date.day, 28)
            return date(next_year, next_month, day)
        elif frequency == "yearly":
            return date(current_date.year + interval, current_date.month, current_date.day)
        else:
            return current_date + timedelta(days=1)

    def get_calendar(self, calendar_id: str) -> Optional[Calendar]:
        """Get calendar by ID.

        Args:
            calendar_id: Calendar identifier.

        Returns:
            Calendar object or None if not found.
        """
        return self.calendars.get(calendar_id)

    def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        """Get event by ID.

        Args:
            event_id: Event identifier.

        Returns:
            CalendarEvent object or None if not found.
        """
        return self.events.get(event_id)

    def create_calendar(
        self, calendar_id: str, name: str, color: str = "#4285f4"
    ) -> Calendar:
        """Create a new calendar.

        Args:
            calendar_id: Calendar identifier.
            name: Calendar display name.
            color: Calendar color.

        Returns:
            Created Calendar object.
        """
        calendar = Calendar(calendar_id=calendar_id, name=name, color=color)
        self.calendars[calendar_id] = calendar
        return calendar

    def delete_calendar(self, calendar_id: str) -> None:
        """Delete a calendar and all its events.

        Args:
            calendar_id: Calendar to delete.

        Raises:
            ValueError: If calendar not found or is default calendar.
        """
        if calendar_id not in self.calendars:
            raise ValueError(f"Calendar {calendar_id} not found")

        if calendar_id == self.default_calendar_id:
            raise ValueError("Cannot delete default calendar")

        calendar = self.calendars[calendar_id]
        for event_id in list(calendar.event_ids):
            if event_id in self.events:
                del self.events[event_id]

        del self.calendars[calendar_id]
