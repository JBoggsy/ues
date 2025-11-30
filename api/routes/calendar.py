"""Calendar endpoints.

Provides REST API for managing calendar events - creating events, updating,
deleting, and querying calendar data.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationError

from api.dependencies import SimulationEngineDep
from api.models import ModalityActionResponse
from api.utils import create_immediate_event
from models.modalities.calendar_input import (
    Attendee,
    AttendeeResponse,
    Attachment,
    CalendarInput,
    EventStatus,
    EventVisibility,
    EventTransparency,
    RecurrenceRule,
    RecurrenceScope,
    Reminder,
)
from models.modalities.calendar_state import CalendarEvent, CalendarState

router = APIRouter(
    prefix="/calendar",
    tags=["calendar"],
)


# Request Models


class CreateCalendarEventRequest(BaseModel):
    """Request to create a new calendar event.

    Args:
        calendar_id: Which calendar to create event in.
        title: Event title.
        description: Event description.
        start: Start datetime.
        end: End datetime.
        all_day: Whether this is an all-day event.
        timezone: Event time zone.
        location: Event location.
        status: Event status.
        organizer: Organizer email address.
        attendees: List of attendees.
        recurrence: Recurrence rule if recurring event.
        recurrence_exceptions: Dates to skip in recurrence.
        reminders: List of reminders.
        color: Event color.
        visibility: Visibility level.
        transparency: Free/busy transparency.
        attachments: File attachments.
        conference_link: Video conference URL.
    """

    calendar_id: str = Field(default="primary", description="Calendar ID")
    title: str = Field(description="Event title")
    description: Optional[str] = Field(default=None, description="Event description")
    start: datetime = Field(description="Start datetime")
    end: datetime = Field(description="End datetime")
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


class UpdateCalendarEventRequest(BaseModel):
    """Request to update an existing calendar event.

    Args:
        event_id: Event to update.
        calendar_id: Calendar containing the event.
        recurrence_scope: For recurring events - which occurrences to affect.
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
    """

    event_id: str = Field(description="Event ID to update")
    calendar_id: str = Field(default="primary", description="Calendar ID")
    recurrence_scope: RecurrenceScope = Field(
        default="this", description="Recurrence scope for updates"
    )
    title: Optional[str] = Field(default=None, description="Event title")
    description: Optional[str] = Field(default=None, description="Event description")
    start: Optional[datetime] = Field(default=None, description="Start datetime")
    end: Optional[datetime] = Field(default=None, description="End datetime")
    all_day: Optional[bool] = Field(default=None, description="Is all-day event")
    timezone: Optional[str] = Field(default=None, description="Event time zone")
    location: Optional[str] = Field(default=None, description="Event location")
    status: Optional[EventStatus] = Field(default=None, description="Event status")
    organizer: Optional[str] = Field(default=None, description="Organizer email")
    attendees: Optional[list[Attendee]] = Field(
        default=None, description="Event attendees"
    )
    recurrence: Optional[RecurrenceRule] = Field(
        default=None, description="Recurrence rule"
    )
    recurrence_exceptions: Optional[list[str]] = Field(
        default=None, description="Exception dates"
    )
    recurrence_id: Optional[str] = Field(
        default=None, description="Which occurrence to modify"
    )
    reminders: Optional[list[Reminder]] = Field(
        default=None, description="Event reminders"
    )
    color: Optional[str] = Field(default=None, description="Event color")
    visibility: Optional[EventVisibility] = Field(
        default=None, description="Visibility level"
    )
    transparency: Optional[EventTransparency] = Field(
        default=None, description="Transparency"
    )
    attachments: Optional[list[Attachment]] = Field(
        default=None, description="Attachments"
    )
    conference_link: Optional[str] = Field(
        default=None, description="Conference URL"
    )


class DeleteCalendarEventRequest(BaseModel):
    """Request to delete a calendar event.

    Args:
        event_id: Event to delete.
        calendar_id: Calendar containing the event.
        recurrence_scope: For recurring events - which occurrences to delete.
        recurrence_id: For recurring events - which occurrence to delete.
    """

    event_id: str = Field(description="Event ID to delete")
    calendar_id: str = Field(default="primary", description="Calendar ID")
    recurrence_scope: RecurrenceScope = Field(
        default="this", description="Recurrence scope for deletion"
    )
    recurrence_id: Optional[str] = Field(
        default=None, description="Which occurrence to delete"
    )


class CalendarQueryRequest(BaseModel):
    """Request to query calendar events.

    Args:
        calendar_ids: Filter by calendar IDs.
        start: Start date/datetime for range.
        end: End date/datetime for range.
        search: Text search in title/description/location.
        status: Filter by event status.
        has_attendees: Filter by attendee presence.
        recurring: Filter by recurring flag.
        expand_recurring: Whether to expand recurring events.
        limit: Maximum number of results.
        offset: Number of results to skip (pagination).
        sort_by: Field to sort by.
        sort_order: Sort order.
    """

    calendar_ids: Optional[list[str]] = Field(
        default=None, description="Filter by calendar IDs"
    )
    start: Optional[datetime] = Field(default=None, description="Range start")
    end: Optional[datetime] = Field(default=None, description="Range end")
    search: Optional[str] = Field(default=None, description="Text search")
    status: Optional[EventStatus] = Field(default=None, description="Status filter")
    has_attendees: Optional[bool] = Field(
        default=None, description="Attendees filter"
    )
    recurring: Optional[bool] = Field(default=None, description="Recurring filter")
    expand_recurring: bool = Field(
        default=False, description="Expand recurring events"
    )
    limit: Optional[int] = Field(default=None, description="Result limit")
    offset: int = Field(default=0, description="Pagination offset")
    sort_by: str = Field(default="start", description="Sort field")
    sort_order: str = Field(default="asc", description="Sort order")


# TODO: Invitation response not implemented in CalendarInput/CalendarState
# These endpoints are planned but need backend implementation first:
# - POST /calendar/accept - Accept calendar invitation
# - POST /calendar/decline - Decline calendar invitation  
# - POST /calendar/tentative - Mark invitation as tentative
#
# Implementation would require:
# 1. Add "respond_to_invitation" operation to CalendarInput
# 2. Add attendee_email and response fields to CalendarInput
# 3. Implement _handle_respond_to_invitation in CalendarState
# 4. The handler would find the event and update the attendee's response status


# Response Models


class CalendarStateResponse(BaseModel):
    """Response model for calendar state.

    Args:
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

    modality_type: str
    last_updated: str
    update_count: int
    default_calendar_id: str
    user_timezone: str
    calendars: dict
    events: dict
    calendar_count: int
    event_count: int


class CalendarQueryResponse(BaseModel):
    """Response model for calendar queries.

    Args:
        modality_type: Always "calendar".
        events: List of CalendarEvent objects matching query.
        count: Number of events returned.
        total_count: Total matching events.
    """

    modality_type: str = "calendar"
    events: list[CalendarEvent]
    count: int
    total_count: int


# Route Handlers


@router.get("/state", response_model=CalendarStateResponse)
async def get_calendar_state(engine: SimulationEngineDep):
    """Get current calendar state.

    Returns a complete snapshot of all calendars and events.

    Args:
        engine: Simulation engine dependency.

    Returns:
        Complete calendar state including all calendars and events.

    Raises:
        HTTPException: If calendar state not found.
    """
    try:
        calendar_state = engine.environment.get_state("calendar")
        if not isinstance(calendar_state, CalendarState):
            raise HTTPException(
                status_code=500, detail="Calendar state not properly initialized"
            )

        snapshot = calendar_state.get_snapshot()
        return CalendarStateResponse(**snapshot)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get calendar state: {str(e)}"
        )


@router.post("/query", response_model=CalendarQueryResponse)
async def query_calendar(request: CalendarQueryRequest, engine: SimulationEngineDep):
    """Query calendar events with filters.

    Allows filtering and searching calendar events by various criteria including
    date range, status, attendees, recurrence, and text search.

    Args:
        request: Query parameters including filters and pagination.
        engine: Simulation engine dependency.

    Returns:
        Matching events with pagination info.

    Raises:
        HTTPException: If query fails.
    """
    try:
        calendar_state = engine.environment.get_state("calendar")
        if not isinstance(calendar_state, CalendarState):
            raise HTTPException(
                status_code=500, detail="Calendar state not properly initialized"
            )

        query_params = {
            "calendar_ids": request.calendar_ids,
            "start": request.start,
            "end": request.end,
            "search": request.search,
            "status": request.status,
            "has_attendees": request.has_attendees,
            "recurring": request.recurring,
            "expand_recurring": request.expand_recurring,
            "limit": request.limit,
            "offset": request.offset,
            "sort_by": request.sort_by,
            "sort_order": request.sort_order,
        }

        results = calendar_state.query(query_params)
        return CalendarQueryResponse(
            events=results["events"],
            count=results["count"],
            total_count=results["total_count"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to query calendar: {str(e)}"
        )


@router.post("/create", response_model=ModalityActionResponse)
async def create_calendar_event(
    request: CreateCalendarEventRequest, engine: SimulationEngineDep
):
    """Create a new calendar event.

    Creates an immediate event that adds a new event to the calendar.

    Args:
        request: Event details including title, times, attendees, etc.
        engine: Simulation engine dependency.

    Returns:
        Action response with event ID and execution status.

    Raises:
        HTTPException: If event creation fails.
    """
    try:
        current_time = engine.environment.time_state.current_time

        # Create calendar input
        calendar_input = CalendarInput(
            operation="create",
            timestamp=current_time,
            calendar_id=request.calendar_id,
            title=request.title,
            description=request.description,
            start=request.start,
            end=request.end,
            all_day=request.all_day,
            timezone=request.timezone,
            location=request.location,
            status=request.status,
            organizer=request.organizer,
            attendees=request.attendees,
            recurrence=request.recurrence,
            recurrence_exceptions=request.recurrence_exceptions,
            reminders=request.reminders,
            color=request.color,
            visibility=request.visibility,
            transparency=request.transparency,
            attachments=request.attachments,
            conference_link=request.conference_link,
        )

        # Validate and auto-generate event_id
        calendar_input.validate_input()

        # Create and execute immediate event
        event = create_immediate_event(
            engine=engine,
            modality="calendar",
            data=calendar_input,
            priority=100,
        )

        return ModalityActionResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            status="executed",
            message=f"Created calendar event: {request.title} (calendar_event_id: {calendar_input.event_id})",
            modality="calendar",
        )
    except ValidationError as e:
        # Pydantic validation failed
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    except ValueError as e:
        # Business logic error (e.g., from validate_input)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create calendar event: {str(e)}"
        )


@router.post("/update", response_model=ModalityActionResponse)
async def update_calendar_event(
    request: UpdateCalendarEventRequest, engine: SimulationEngineDep
):
    """Update an existing calendar event.

    Updates an event with new values. For recurring events, can update single
    occurrence, this and future occurrences, or all occurrences based on
    recurrence_scope.

    Args:
        request: Event ID and updated field values.
        engine: Simulation engine dependency.

    Returns:
        Action response with execution status.

    Raises:
        HTTPException: If update fails.
    """
    try:
        current_time = engine.environment.time_state.current_time

        # Build kwargs only for fields that are set (not None)
        # Required fields for update operation
        input_kwargs = {
            "operation": "update",
            "timestamp": current_time,
            "event_id": request.event_id,
            "calendar_id": request.calendar_id,
            "recurrence_scope": request.recurrence_scope,
        }

        # Optional fields - only include if set
        optional_fields = [
            "title", "description", "start", "end", "all_day", "timezone",
            "location", "status", "organizer", "attendees", "recurrence",
            "recurrence_exceptions", "recurrence_id", "reminders", "color",
            "visibility", "transparency", "attachments", "conference_link",
        ]
        for field in optional_fields:
            value = getattr(request, field)
            if value is not None:
                input_kwargs[field] = value

        # Create calendar input
        calendar_input = CalendarInput(**input_kwargs)

        # Validate
        calendar_input.validate_input()

        # Create and execute immediate event
        event = create_immediate_event(
            engine=engine,
            modality="calendar",
            data=calendar_input,
            priority=100,
        )

        return ModalityActionResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            status="executed",
            message=f"Updated calendar event: {request.event_id}",
            modality="calendar",
        )
    except ValidationError as e:
        # Pydantic validation failed
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    except ValueError as e:
        # Business logic error (e.g., from validate_input)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update calendar event: {str(e)}"
        )


@router.post("/delete", response_model=ModalityActionResponse)
async def delete_calendar_event(
    request: DeleteCalendarEventRequest, engine: SimulationEngineDep
):
    """Delete a calendar event.

    Deletes an event from the calendar. For recurring events, can delete single
    occurrence, this and future occurrences, or all occurrences based on
    recurrence_scope.

    Args:
        request: Event ID and deletion scope.
        engine: Simulation engine dependency.

    Returns:
        Action response with execution status.

    Raises:
        HTTPException: If deletion fails.
    """
    try:
        current_time = engine.environment.time_state.current_time

        # Create calendar input
        calendar_input = CalendarInput(
            operation="delete",
            timestamp=current_time,
            event_id=request.event_id,
            calendar_id=request.calendar_id,
            recurrence_scope=request.recurrence_scope,
            recurrence_id=request.recurrence_id,
        )

        # Validate
        calendar_input.validate_input()

        # Create and execute immediate event
        event = create_immediate_event(
            engine=engine,
            modality="calendar",
            data=calendar_input,
            priority=100,
        )

        return ModalityActionResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            status="executed",
            message=f"Deleted calendar event: {request.event_id}",
            modality="calendar",
        )
    except ValidationError as e:
        # Pydantic validation failed
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    except ValueError as e:
        # Business logic error (e.g., from validate_input)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete calendar event: {str(e)}"
        )
