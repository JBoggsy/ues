"""Calendar modality sub-client for the UES API.

This module provides CalendarClient and AsyncCalendarClient for interacting with
the calendar modality endpoints (/calendar/*).

This is an internal module. Import from `client` instead.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field

from client._base import AsyncBaseClient, BaseClient
from client.models import ModalityActionResponse

if TYPE_CHECKING:
    from client._http import AsyncHTTPClient, HTTPClient


# Type aliases for calendar fields
EventStatus = Literal["confirmed", "tentative", "cancelled"]
EventVisibility = Literal["default", "public", "private", "confidential"]
EventTransparency = Literal["opaque", "transparent"]
RecurrenceScope = Literal["this", "future", "all"]
AttendeeResponse = Literal["accepted", "declined", "tentative", "needsAction"]


# Response models for calendar endpoints


class Attendee(BaseModel):
    """Represents a calendar event attendee.
    
    Attributes:
        email: Attendee's email address.
        display_name: Optional display name.
        response_status: Response status (accepted, declined, tentative, needsAction).
        optional: Whether attendance is optional.
        organizer: Whether this attendee is the organizer.
        self_: Whether this is the current user.
        comment: Optional response comment.
    """

    email: str
    display_name: str | None = None
    response_status: AttendeeResponse = "needsAction"
    optional: bool = False
    organizer: bool = False
    self_: bool = Field(default=False, alias="self")
    comment: str | None = None


class Reminder(BaseModel):
    """Represents an event reminder.
    
    Attributes:
        method: Reminder method ("email", "popup", "sms").
        minutes: Minutes before event to trigger reminder.
    """

    method: Literal["email", "popup", "sms"]
    minutes: int


class Attachment(BaseModel):
    """Represents a calendar event attachment.
    
    Attributes:
        file_url: URL to the file.
        title: Display title.
        mime_type: MIME type of the file.
        icon_link: Optional icon URL.
        file_id: Optional file ID (for cloud storage).
    """

    file_url: str
    title: str
    mime_type: str | None = None
    icon_link: str | None = None
    file_id: str | None = None


class RecurrenceRule(BaseModel):
    """Represents a recurrence rule for repeating events.
    
    Attributes:
        frequency: Recurrence frequency (DAILY, WEEKLY, MONTHLY, YEARLY).
        interval: Interval between recurrences (default 1).
        count: Number of occurrences (if not using until).
        until: End date for recurrence (if not using count).
        by_day: Days of week for weekly recurrence (MO, TU, WE, TH, FR, SA, SU).
        by_month_day: Days of month for monthly recurrence (1-31, or -1 for last).
        by_month: Months for yearly recurrence (1-12).
        by_set_pos: Position within set for complex rules.
    """

    frequency: Literal["DAILY", "WEEKLY", "MONTHLY", "YEARLY"]
    interval: int = 1
    count: int | None = None
    until: str | None = None
    by_day: list[str] | None = None
    by_month_day: list[int] | None = None
    by_month: list[int] | None = None
    by_set_pos: list[int] | None = None


class CalendarEvent(BaseModel):
    """Represents a calendar event.
    
    Attributes:
        event_id: Unique event identifier.
        calendar_id: Calendar this event belongs to.
        title: Event title.
        description: Event description.
        start: Start datetime.
        end: End datetime.
        all_day: Whether this is an all-day event.
        timezone: Event time zone.
        location: Event location.
        status: Event status (confirmed, tentative, cancelled).
        organizer: Organizer email address.
        attendees: List of attendees.
        recurrence: Recurrence rule if recurring.
        recurrence_id: For recurring events, ID of specific occurrence.
        recurring_event_id: For recurring events, ID of the master event.
        reminders: List of reminders.
        color: Event color.
        visibility: Visibility level.
        transparency: Free/busy transparency.
        attachments: File attachments.
        conference_link: Video conference URL.
        created_at: When event was created.
        updated_at: When event was last updated.
    """

    event_id: str
    calendar_id: str
    title: str
    description: str | None = None
    start: datetime
    end: datetime
    all_day: bool = False
    timezone: str = "UTC"
    location: str | None = None
    status: EventStatus = "confirmed"
    organizer: str | None = None
    attendees: list[Attendee] = Field(default_factory=list)
    recurrence: RecurrenceRule | None = None
    recurrence_id: str | None = None
    recurring_event_id: str | None = None
    reminders: list[Reminder] = Field(default_factory=list)
    color: str | None = None
    visibility: EventVisibility = "default"
    transparency: EventTransparency = "opaque"
    attachments: list[Attachment] = Field(default_factory=list)
    conference_link: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CalendarStateResponse(BaseModel):
    """Response model for calendar state endpoint.
    
    Attributes:
        modality_type: Always "calendar".
        last_updated: When state was last modified.
        update_count: Number of operations applied.
        default_calendar_id: ID of default calendar.
        user_timezone: User's default time zone.
        calendars: Dict of calendar objects.
        events: Dict of event objects.
        calendar_count: Number of calendars.
        event_count: Number of events.
    """

    modality_type: str = "calendar"
    last_updated: str
    update_count: int
    default_calendar_id: str
    user_timezone: str
    calendars: dict[str, Any]
    events: dict[str, Any]
    calendar_count: int
    event_count: int


class CalendarQueryResponse(BaseModel):
    """Response model for calendar query endpoint.
    
    Attributes:
        modality_type: Always "calendar".
        events: List of CalendarEvent objects matching query.
        count: Number of events returned.
        total_count: Total matching events.
    """

    modality_type: str = "calendar"
    events: list[CalendarEvent]
    count: int
    total_count: int


# Synchronous CalendarClient


class CalendarClient(BaseClient):
    """Synchronous client for calendar modality endpoints (/calendar/*).
    
    This client provides methods for creating, updating, deleting, and
    querying calendar events. Supports recurring events, attendees,
    reminders, and all standard calendar features.
    
    Example:
        with UESClient() as client:
            # Create an event
            client.calendar.create(
                title="Team Meeting",
                start=datetime(2025, 1, 15, 10, 0),
                end=datetime(2025, 1, 15, 11, 0),
                location="Conference Room A",
            )
            
            # Get calendar state
            state = client.calendar.get_state()
            print(f"Total events: {state.event_count}")
            
            # Query upcoming events
            upcoming = client.calendar.query(
                start=datetime.now(),
                end=datetime.now() + timedelta(days=7),
            )
            print(f"Found {upcoming.total_count} upcoming events")
    """

    _BASE_PATH = "/calendar"

    def get_state(self) -> CalendarStateResponse:
        """Get the current calendar state.
        
        Returns a complete snapshot of all calendars and events.
        
        Returns:
            Complete calendar state including all calendars and events.
        
        Raises:
            APIError: If the request fails.
        """
        data = self._get(f"{self._BASE_PATH}/state")
        return CalendarStateResponse(**data)

    def query(
        self,
        calendar_ids: list[str] | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        search: str | None = None,
        status: EventStatus | None = None,
        has_attendees: bool | None = None,
        recurring: bool | None = None,
        expand_recurring: bool = False,
        limit: int | None = None,
        offset: int = 0,
        sort_by: str = "start",
        sort_order: Literal["asc", "desc"] = "asc",
    ) -> CalendarQueryResponse:
        """Query calendar events with filters.
        
        Allows filtering and searching calendar events by various criteria
        including date range, status, attendees, recurrence, and text search.
        
        Args:
            calendar_ids: Filter by calendar IDs.
            start: Start date/datetime for range filter.
            end: End date/datetime for range filter.
            search: Text search in title/description/location.
            status: Filter by event status (confirmed, tentative, cancelled).
            has_attendees: Filter by attendee presence.
            recurring: Filter by recurring flag.
            expand_recurring: Whether to expand recurring events into instances.
            limit: Maximum number of results to return.
            offset: Number of results to skip (for pagination).
            sort_by: Field to sort by (default: "start").
            sort_order: Sort direction ("asc" or "desc").
        
        Returns:
            Matching events with pagination info.
        
        Raises:
            ValidationError: If query parameters are invalid.
            APIError: If the request fails.
        """
        # Build the request body, excluding None values
        request_data: dict[str, Any] = {}
        
        if calendar_ids is not None:
            request_data["calendar_ids"] = calendar_ids
        if start is not None:
            request_data["start"] = start.isoformat()
        if end is not None:
            request_data["end"] = end.isoformat()
        if search is not None:
            request_data["search"] = search
        if status is not None:
            request_data["status"] = status
        if has_attendees is not None:
            request_data["has_attendees"] = has_attendees
        if recurring is not None:
            request_data["recurring"] = recurring
        if expand_recurring:
            request_data["expand_recurring"] = expand_recurring
        if limit is not None:
            request_data["limit"] = limit
        if offset != 0:
            request_data["offset"] = offset
        if sort_by != "start":
            request_data["sort_by"] = sort_by
        if sort_order != "asc":
            request_data["sort_order"] = sort_order
        
        data = self._post(f"{self._BASE_PATH}/query", json=request_data)
        return CalendarQueryResponse(**data)

    def create(
        self,
        title: str,
        start: datetime,
        end: datetime,
        calendar_id: str = "primary",
        description: str | None = None,
        all_day: bool = False,
        timezone: str = "UTC",
        location: str | None = None,
        status: EventStatus = "confirmed",
        organizer: str | None = None,
        attendees: list[dict[str, Any]] | None = None,
        recurrence: dict[str, Any] | None = None,
        recurrence_exceptions: list[str] | None = None,
        reminders: list[dict[str, Any]] | None = None,
        color: str | None = None,
        visibility: EventVisibility = "default",
        transparency: EventTransparency = "opaque",
        attachments: list[dict[str, Any]] | None = None,
        conference_link: str | None = None,
    ) -> ModalityActionResponse:
        """Create a new calendar event.
        
        Creates an immediate event that adds a new event to the calendar.
        
        Args:
            title: Event title.
            start: Start datetime.
            end: End datetime.
            calendar_id: Which calendar to create event in (default: "primary").
            description: Event description.
            all_day: Whether this is an all-day event.
            timezone: Event time zone (default: "UTC").
            location: Event location.
            status: Event status (default: "confirmed").
            organizer: Organizer email address.
            attendees: List of attendees (each dict with 'email' and optional fields).
            recurrence: Recurrence rule (dict with 'frequency' and optional fields).
            recurrence_exceptions: Dates to skip in recurrence (YYYY-MM-DD format).
            reminders: List of reminders (each dict with 'method' and 'minutes').
            color: Event color.
            visibility: Visibility level (default: "default").
            transparency: Free/busy transparency (default: "opaque").
            attachments: File attachments.
            conference_link: Video conference URL.
        
        Returns:
            Action response with event ID and execution status.
        
        Raises:
            ValidationError: If request parameters are invalid.
            APIError: If the request fails.
        """
        request_data: dict[str, Any] = {
            "title": title,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "calendar_id": calendar_id,
            "all_day": all_day,
            "timezone": timezone,
            "status": status,
            "visibility": visibility,
            "transparency": transparency,
        }
        
        if description is not None:
            request_data["description"] = description
        if location is not None:
            request_data["location"] = location
        if organizer is not None:
            request_data["organizer"] = organizer
        if attendees is not None:
            request_data["attendees"] = attendees
        if recurrence is not None:
            request_data["recurrence"] = recurrence
        if recurrence_exceptions is not None:
            request_data["recurrence_exceptions"] = recurrence_exceptions
        if reminders is not None:
            request_data["reminders"] = reminders
        if color is not None:
            request_data["color"] = color
        if attachments is not None:
            request_data["attachments"] = attachments
        if conference_link is not None:
            request_data["conference_link"] = conference_link
        
        data = self._post(f"{self._BASE_PATH}/create", json=request_data)
        return ModalityActionResponse(**data)

    def update(
        self,
        event_id: str,
        calendar_id: str = "primary",
        recurrence_scope: RecurrenceScope = "this",
        title: str | None = None,
        description: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        all_day: bool | None = None,
        timezone: str | None = None,
        location: str | None = None,
        status: EventStatus | None = None,
        organizer: str | None = None,
        attendees: list[dict[str, Any]] | None = None,
        recurrence: dict[str, Any] | None = None,
        recurrence_exceptions: list[str] | None = None,
        recurrence_id: str | None = None,
        reminders: list[dict[str, Any]] | None = None,
        color: str | None = None,
        visibility: EventVisibility | None = None,
        transparency: EventTransparency | None = None,
        attachments: list[dict[str, Any]] | None = None,
        conference_link: str | None = None,
    ) -> ModalityActionResponse:
        """Update an existing calendar event.
        
        Updates an event with new values. For recurring events, can update single
        occurrence, this and future occurrences, or all occurrences based on
        recurrence_scope.
        
        Args:
            event_id: Event ID to update.
            calendar_id: Calendar containing the event (default: "primary").
            recurrence_scope: For recurring events - which occurrences to affect
                ("this", "future", or "all").
            title: Updated event title.
            description: Updated event description.
            start: Updated start datetime.
            end: Updated end datetime.
            all_day: Updated all-day flag.
            timezone: Updated time zone.
            location: Updated event location.
            status: Updated event status.
            organizer: Updated organizer email.
            attendees: Updated attendees list.
            recurrence: Updated recurrence rule.
            recurrence_exceptions: Updated exception dates.
            recurrence_id: For recurring events - which occurrence to modify.
            reminders: Updated reminders.
            color: Updated event color.
            visibility: Updated visibility level.
            transparency: Updated transparency.
            attachments: Updated attachments.
            conference_link: Updated conference URL.
        
        Returns:
            Action response with execution status.
        
        Raises:
            ValidationError: If request parameters are invalid.
            APIError: If the request fails.
        """
        request_data: dict[str, Any] = {
            "event_id": event_id,
            "calendar_id": calendar_id,
            "recurrence_scope": recurrence_scope,
        }
        
        if title is not None:
            request_data["title"] = title
        if description is not None:
            request_data["description"] = description
        if start is not None:
            request_data["start"] = start.isoformat()
        if end is not None:
            request_data["end"] = end.isoformat()
        if all_day is not None:
            request_data["all_day"] = all_day
        if timezone is not None:
            request_data["timezone"] = timezone
        if location is not None:
            request_data["location"] = location
        if status is not None:
            request_data["status"] = status
        if organizer is not None:
            request_data["organizer"] = organizer
        if attendees is not None:
            request_data["attendees"] = attendees
        if recurrence is not None:
            request_data["recurrence"] = recurrence
        if recurrence_exceptions is not None:
            request_data["recurrence_exceptions"] = recurrence_exceptions
        if recurrence_id is not None:
            request_data["recurrence_id"] = recurrence_id
        if reminders is not None:
            request_data["reminders"] = reminders
        if color is not None:
            request_data["color"] = color
        if visibility is not None:
            request_data["visibility"] = visibility
        if transparency is not None:
            request_data["transparency"] = transparency
        if attachments is not None:
            request_data["attachments"] = attachments
        if conference_link is not None:
            request_data["conference_link"] = conference_link
        
        data = self._post(f"{self._BASE_PATH}/update", json=request_data)
        return ModalityActionResponse(**data)

    def delete(
        self,
        event_id: str,
        calendar_id: str = "primary",
        recurrence_scope: RecurrenceScope = "this",
        recurrence_id: str | None = None,
    ) -> ModalityActionResponse:
        """Delete a calendar event.
        
        Deletes an event from the calendar. For recurring events, can delete single
        occurrence, this and future occurrences, or all occurrences based on
        recurrence_scope.
        
        Args:
            event_id: Event ID to delete.
            calendar_id: Calendar containing the event (default: "primary").
            recurrence_scope: For recurring events - which occurrences to delete
                ("this", "future", or "all").
            recurrence_id: For recurring events - which occurrence to delete.
        
        Returns:
            Action response with execution status.
        
        Raises:
            ValidationError: If request parameters are invalid.
            APIError: If the request fails.
        """
        request_data: dict[str, Any] = {
            "event_id": event_id,
            "calendar_id": calendar_id,
            "recurrence_scope": recurrence_scope,
        }
        
        if recurrence_id is not None:
            request_data["recurrence_id"] = recurrence_id
        
        data = self._post(f"{self._BASE_PATH}/delete", json=request_data)
        return ModalityActionResponse(**data)


# Asynchronous AsyncCalendarClient


class AsyncCalendarClient(AsyncBaseClient):
    """Asynchronous client for calendar modality endpoints (/calendar/*).
    
    This client provides async methods for creating, updating, deleting, and
    querying calendar events. Supports recurring events, attendees,
    reminders, and all standard calendar features.
    
    Example:
        async with AsyncUESClient() as client:
            # Create an event
            await client.calendar.create(
                title="Team Meeting",
                start=datetime(2025, 1, 15, 10, 0),
                end=datetime(2025, 1, 15, 11, 0),
                location="Conference Room A",
            )
            
            # Get calendar state
            state = await client.calendar.get_state()
            print(f"Total events: {state.event_count}")
            
            # Query upcoming events
            upcoming = await client.calendar.query(
                start=datetime.now(),
                end=datetime.now() + timedelta(days=7),
            )
            print(f"Found {upcoming.total_count} upcoming events")
    """

    _BASE_PATH = "/calendar"

    async def get_state(self) -> CalendarStateResponse:
        """Get the current calendar state.
        
        Returns a complete snapshot of all calendars and events.
        
        Returns:
            Complete calendar state including all calendars and events.
        
        Raises:
            APIError: If the request fails.
        """
        data = await self._get(f"{self._BASE_PATH}/state")
        return CalendarStateResponse(**data)

    async def query(
        self,
        calendar_ids: list[str] | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        search: str | None = None,
        status: EventStatus | None = None,
        has_attendees: bool | None = None,
        recurring: bool | None = None,
        expand_recurring: bool = False,
        limit: int | None = None,
        offset: int = 0,
        sort_by: str = "start",
        sort_order: Literal["asc", "desc"] = "asc",
    ) -> CalendarQueryResponse:
        """Query calendar events with filters.
        
        Allows filtering and searching calendar events by various criteria
        including date range, status, attendees, recurrence, and text search.
        
        Args:
            calendar_ids: Filter by calendar IDs.
            start: Start date/datetime for range filter.
            end: End date/datetime for range filter.
            search: Text search in title/description/location.
            status: Filter by event status (confirmed, tentative, cancelled).
            has_attendees: Filter by attendee presence.
            recurring: Filter by recurring flag.
            expand_recurring: Whether to expand recurring events into instances.
            limit: Maximum number of results to return.
            offset: Number of results to skip (for pagination).
            sort_by: Field to sort by (default: "start").
            sort_order: Sort direction ("asc" or "desc").
        
        Returns:
            Matching events with pagination info.
        
        Raises:
            ValidationError: If query parameters are invalid.
            APIError: If the request fails.
        """
        # Build the request body, excluding None values
        request_data: dict[str, Any] = {}
        
        if calendar_ids is not None:
            request_data["calendar_ids"] = calendar_ids
        if start is not None:
            request_data["start"] = start.isoformat()
        if end is not None:
            request_data["end"] = end.isoformat()
        if search is not None:
            request_data["search"] = search
        if status is not None:
            request_data["status"] = status
        if has_attendees is not None:
            request_data["has_attendees"] = has_attendees
        if recurring is not None:
            request_data["recurring"] = recurring
        if expand_recurring:
            request_data["expand_recurring"] = expand_recurring
        if limit is not None:
            request_data["limit"] = limit
        if offset != 0:
            request_data["offset"] = offset
        if sort_by != "start":
            request_data["sort_by"] = sort_by
        if sort_order != "asc":
            request_data["sort_order"] = sort_order
        
        data = await self._post(f"{self._BASE_PATH}/query", json=request_data)
        return CalendarQueryResponse(**data)

    async def create(
        self,
        title: str,
        start: datetime,
        end: datetime,
        calendar_id: str = "primary",
        description: str | None = None,
        all_day: bool = False,
        timezone: str = "UTC",
        location: str | None = None,
        status: EventStatus = "confirmed",
        organizer: str | None = None,
        attendees: list[dict[str, Any]] | None = None,
        recurrence: dict[str, Any] | None = None,
        recurrence_exceptions: list[str] | None = None,
        reminders: list[dict[str, Any]] | None = None,
        color: str | None = None,
        visibility: EventVisibility = "default",
        transparency: EventTransparency = "opaque",
        attachments: list[dict[str, Any]] | None = None,
        conference_link: str | None = None,
    ) -> ModalityActionResponse:
        """Create a new calendar event.
        
        Creates an immediate event that adds a new event to the calendar.
        
        Args:
            title: Event title.
            start: Start datetime.
            end: End datetime.
            calendar_id: Which calendar to create event in (default: "primary").
            description: Event description.
            all_day: Whether this is an all-day event.
            timezone: Event time zone (default: "UTC").
            location: Event location.
            status: Event status (default: "confirmed").
            organizer: Organizer email address.
            attendees: List of attendees (each dict with 'email' and optional fields).
            recurrence: Recurrence rule (dict with 'frequency' and optional fields).
            recurrence_exceptions: Dates to skip in recurrence (YYYY-MM-DD format).
            reminders: List of reminders (each dict with 'method' and 'minutes').
            color: Event color.
            visibility: Visibility level (default: "default").
            transparency: Free/busy transparency (default: "opaque").
            attachments: File attachments.
            conference_link: Video conference URL.
        
        Returns:
            Action response with event ID and execution status.
        
        Raises:
            ValidationError: If request parameters are invalid.
            APIError: If the request fails.
        """
        request_data: dict[str, Any] = {
            "title": title,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "calendar_id": calendar_id,
            "all_day": all_day,
            "timezone": timezone,
            "status": status,
            "visibility": visibility,
            "transparency": transparency,
        }
        
        if description is not None:
            request_data["description"] = description
        if location is not None:
            request_data["location"] = location
        if organizer is not None:
            request_data["organizer"] = organizer
        if attendees is not None:
            request_data["attendees"] = attendees
        if recurrence is not None:
            request_data["recurrence"] = recurrence
        if recurrence_exceptions is not None:
            request_data["recurrence_exceptions"] = recurrence_exceptions
        if reminders is not None:
            request_data["reminders"] = reminders
        if color is not None:
            request_data["color"] = color
        if attachments is not None:
            request_data["attachments"] = attachments
        if conference_link is not None:
            request_data["conference_link"] = conference_link
        
        data = await self._post(f"{self._BASE_PATH}/create", json=request_data)
        return ModalityActionResponse(**data)

    async def update(
        self,
        event_id: str,
        calendar_id: str = "primary",
        recurrence_scope: RecurrenceScope = "this",
        title: str | None = None,
        description: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        all_day: bool | None = None,
        timezone: str | None = None,
        location: str | None = None,
        status: EventStatus | None = None,
        organizer: str | None = None,
        attendees: list[dict[str, Any]] | None = None,
        recurrence: dict[str, Any] | None = None,
        recurrence_exceptions: list[str] | None = None,
        recurrence_id: str | None = None,
        reminders: list[dict[str, Any]] | None = None,
        color: str | None = None,
        visibility: EventVisibility | None = None,
        transparency: EventTransparency | None = None,
        attachments: list[dict[str, Any]] | None = None,
        conference_link: str | None = None,
    ) -> ModalityActionResponse:
        """Update an existing calendar event.
        
        Updates an event with new values. For recurring events, can update single
        occurrence, this and future occurrences, or all occurrences based on
        recurrence_scope.
        
        Args:
            event_id: Event ID to update.
            calendar_id: Calendar containing the event (default: "primary").
            recurrence_scope: For recurring events - which occurrences to affect
                ("this", "future", or "all").
            title: Updated event title.
            description: Updated event description.
            start: Updated start datetime.
            end: Updated end datetime.
            all_day: Updated all-day flag.
            timezone: Updated time zone.
            location: Updated event location.
            status: Updated event status.
            organizer: Updated organizer email.
            attendees: Updated attendees list.
            recurrence: Updated recurrence rule.
            recurrence_exceptions: Updated exception dates.
            recurrence_id: For recurring events - which occurrence to modify.
            reminders: Updated reminders.
            color: Updated event color.
            visibility: Updated visibility level.
            transparency: Updated transparency.
            attachments: Updated attachments.
            conference_link: Updated conference URL.
        
        Returns:
            Action response with execution status.
        
        Raises:
            ValidationError: If request parameters are invalid.
            APIError: If the request fails.
        """
        request_data: dict[str, Any] = {
            "event_id": event_id,
            "calendar_id": calendar_id,
            "recurrence_scope": recurrence_scope,
        }
        
        if title is not None:
            request_data["title"] = title
        if description is not None:
            request_data["description"] = description
        if start is not None:
            request_data["start"] = start.isoformat()
        if end is not None:
            request_data["end"] = end.isoformat()
        if all_day is not None:
            request_data["all_day"] = all_day
        if timezone is not None:
            request_data["timezone"] = timezone
        if location is not None:
            request_data["location"] = location
        if status is not None:
            request_data["status"] = status
        if organizer is not None:
            request_data["organizer"] = organizer
        if attendees is not None:
            request_data["attendees"] = attendees
        if recurrence is not None:
            request_data["recurrence"] = recurrence
        if recurrence_exceptions is not None:
            request_data["recurrence_exceptions"] = recurrence_exceptions
        if recurrence_id is not None:
            request_data["recurrence_id"] = recurrence_id
        if reminders is not None:
            request_data["reminders"] = reminders
        if color is not None:
            request_data["color"] = color
        if visibility is not None:
            request_data["visibility"] = visibility
        if transparency is not None:
            request_data["transparency"] = transparency
        if attachments is not None:
            request_data["attachments"] = attachments
        if conference_link is not None:
            request_data["conference_link"] = conference_link
        
        data = await self._post(f"{self._BASE_PATH}/update", json=request_data)
        return ModalityActionResponse(**data)

    async def delete(
        self,
        event_id: str,
        calendar_id: str = "primary",
        recurrence_scope: RecurrenceScope = "this",
        recurrence_id: str | None = None,
    ) -> ModalityActionResponse:
        """Delete a calendar event.
        
        Deletes an event from the calendar. For recurring events, can delete single
        occurrence, this and future occurrences, or all occurrences based on
        recurrence_scope.
        
        Args:
            event_id: Event ID to delete.
            calendar_id: Calendar containing the event (default: "primary").
            recurrence_scope: For recurring events - which occurrences to delete
                ("this", "future", or "all").
            recurrence_id: For recurring events - which occurrence to delete.
        
        Returns:
            Action response with execution status.
        
        Raises:
            ValidationError: If request parameters are invalid.
            APIError: If the request fails.
        """
        request_data: dict[str, Any] = {
            "event_id": event_id,
            "calendar_id": calendar_id,
            "recurrence_scope": recurrence_scope,
        }
        
        if recurrence_id is not None:
            request_data["recurrence_id"] = recurrence_id
        
        data = await self._post(f"{self._BASE_PATH}/delete", json=request_data)
        return ModalityActionResponse(**data)
