"""Event management endpoints.

These endpoints allow clients to create, query, and manage simulation events.
"""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationError

from api.broadcast import broadcast_event
from api.dependencies import SimulationEngineDep
from api.websocket import WSEventType
from models.base_input import ModalityInput
from models.event import EventStatus, SimulatorEvent
from models.modalities.calendar_input import CalendarInput
from models.modalities.chat_input import ChatInput
from models.modalities.email_input import EmailInput
from models.modalities.location_input import LocationInput
from models.modalities.sms_input import SMSInput
from models.modalities.time_input import TimeInput
from models.modalities.weather_input import WeatherInput

# Create router for event-related endpoints
router = APIRouter(
    prefix="/events",
    tags=["events"],
)

# Mapping of modality names to their input classes
MODALITY_INPUT_CLASSES: dict[str, type[ModalityInput]] = {
    "email": EmailInput,
    "sms": SMSInput,
    "chat": ChatInput,
    "calendar": CalendarInput,
    "location": LocationInput,
    "weather": WeatherInput,
    "time": TimeInput,
}


def deserialize_modality_input(
    modality: str, data: dict[str, Any], timestamp: datetime
) -> ModalityInput:
    """Deserialize a data dict into the appropriate ModalityInput subclass.
    
    Args:
        modality: The modality type (e.g., "email", "sms").
        data: The raw data dict from the API request.
        timestamp: The timestamp to use for the input (usually event scheduled_time).
    
    Returns:
        A properly typed ModalityInput instance.
    
    Raises:
        HTTPException: If modality is unknown or data is invalid.
    """
    # Get the input class for this modality
    input_class = MODALITY_INPUT_CLASSES.get(modality)
    
    if input_class is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown modality: {modality}. Supported modalities: {', '.join(MODALITY_INPUT_CLASSES.keys())}",
        )
    
    # Add required fields that all ModalityInputs need
    data_with_metadata = {
        **data,
        "modality_type": modality,
        "timestamp": timestamp,
    }
    
    # Deserialize into the proper class
    try:
        return input_class(**data_with_metadata)
    except ValidationError as e:
        # Pydantic validation failed - return helpful error
        raise HTTPException(
            status_code=422,
            detail=f"Invalid data for {modality} modality: {str(e)}",
        )
    except Exception as e:
        # Unexpected error during deserialization
        raise HTTPException(
            status_code=400,
            detail=f"Failed to deserialize {modality} data: {str(e)}",
        )


# Request/Response Models


class CreateEventRequest(BaseModel):
    """Request model for creating a new event.
    
    Attributes:
        scheduled_time: When the event should execute.
        modality: Which modality this event affects.
        data: The ModalityInput payload for this event.
        priority: Optional execution priority (0-100, higher = first).
        metadata: Optional custom metadata.
        agent_id: Optional ID of agent creating this event.
    """

    scheduled_time: datetime
    modality: str
    data: dict[str, Any]
    priority: int = Field(default=50, ge=0, le=100)
    metadata: dict[str, Any] = Field(default_factory=dict)
    agent_id: Optional[str] = None


class ImmediateEventRequest(BaseModel):
    """Request model for submitting an immediate event.
    
    Attributes:
        modality: Which modality this event affects.
        data: The ModalityInput payload for this event.
    """

    modality: str
    data: dict[str, Any]


class EventResponse(BaseModel):
    """Response model for event details.
    
    Attributes:
        event_id: Unique event identifier.
        scheduled_time: When the event is/was scheduled to execute.
        modality: Which modality the event affects.
        status: Current execution status.
        priority: Execution priority.
        created_at: When the event was created.
        executed_at: When the event was executed (if applicable).
        error_message: Error details if execution failed.
        data: The event payload (ModalityInput data).
    """

    event_id: str
    scheduled_time: datetime
    modality: str
    status: str
    priority: int
    created_at: datetime
    data: dict[str, Any] = None
    executed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class EventListResponse(BaseModel):
    """Response model for event listing.
    
    Attributes:
        events: List of event summaries.
        total: Total number of events.
        pending: Count of pending events.
        executed: Count of executed events.
        failed: Count of failed events.
        skipped: Count of skipped events.
    """

    events: list[EventResponse]
    total: int
    pending: int
    executed: int
    failed: int
    skipped: int


class EventSummaryResponse(BaseModel):
    """Response model for event statistics.
    
    Attributes:
        total: Total number of events.
        pending: Count of pending events.
        executed: Count of executed events.
        failed: Count of failed events.
        skipped: Count of skipped events.
        by_modality: Event counts grouped by modality.
        next_event_time: Scheduled time of next pending event.
    """

    total: int
    pending: int
    executed: int
    failed: int
    skipped: int
    by_modality: dict[str, int]
    next_event_time: Optional[datetime] = None


# Batch Event Models


# Maximum number of events allowed in a single batch request
MAX_BATCH_SIZE = 1000


class BatchEventResult(BaseModel):
    """Result for a single event in a batch operation.
    
    Attributes:
        index: Position in the original request array (0-indexed).
        success: Whether the event was created successfully.
        event_id: The created event's ID (None if failed).
        scheduled_time: The event's scheduled time (None if failed).
        error: Error message if validation/creation failed.
    """
    
    index: int
    success: bool
    event_id: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    error: Optional[str] = None


class BatchValidationResult(BaseModel):
    """Result for a single event in validation-only mode.
    
    Attributes:
        index: Position in the original request array (0-indexed).
        valid: Whether the event passed validation.
        error: Error message if validation failed.
    """
    
    index: int
    valid: bool
    error: Optional[str] = None


class BatchCreateEventRequest(BaseModel):
    """Request model for batch event creation.
    
    Attributes:
        events: List of event specifications to create.
        stop_on_first_error: If True, abort entire batch on first error.
        validate_only: If True, validate without creating events.
    """
    
    events: list[CreateEventRequest]
    stop_on_first_error: bool = False
    validate_only: bool = False


class BatchCreateEventResponse(BaseModel):
    """Response model for successful batch event creation.
    
    Attributes:
        total_submitted: Number of events in the request.
        total_created: Number of events successfully created.
        total_failed: Number of events that failed validation.
        events: Per-event results with IDs and errors.
    """
    
    total_submitted: int
    total_created: int
    total_failed: int
    events: list[BatchEventResult]


class BatchValidationResponse(BaseModel):
    """Response model for validation-only batch request.
    
    Attributes:
        total_submitted: Number of events in the request.
        total_valid: Number of events that passed validation.
        total_invalid: Number of events that failed validation.
        events: Per-event validation results.
        validation_only: Always True for this response type.
    """
    
    total_submitted: int
    total_valid: int
    total_invalid: int
    events: list[BatchValidationResult]
    validation_only: bool = True


class BatchErrorResponse(BaseModel):
    """Response model for strict mode batch failure.
    
    Attributes:
        detail: Human-readable error message.
        failed_index: Index of the first failing event.
        events_validated: Number of events validated before failure.
        total_events: Total events in the request.
    """
    
    detail: str
    failed_index: int
    events_validated: int
    total_events: int


# Route Handlers


@router.get("", response_model=EventListResponse)
async def list_events(
    engine: SimulationEngineDep,
    status: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    modality: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
):
    """List events with optional filters.
    
    Query parameters allow filtering by status, time range, and modality.
    
    Args:
        engine: The SimulationEngine instance (injected by FastAPI).
        status: Filter by event status.
        start_time: Filter by scheduled_time >= start_time.
        end_time: Filter by scheduled_time <= end_time.
        modality: Filter by modality type.
        limit: Maximum number of events to return.
        offset: Number of events to skip (for pagination).
    
    Returns:
        List of events matching the filters.
    """
    # Parse status if provided
    event_status = None
    if status:
        try:
            event_status = EventStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status}. Must be one of: pending, executed, failed, skipped, cancelled",
            )
    
    # Query events
    events = engine.query_events(
        status=event_status,
        start_time=start_time,
        end_time=end_time,
        modality=modality,
    )
    
    # Apply pagination
    total = len(events)
    if limit:
        events = events[offset : offset + limit]
    else:
        events = events[offset:]
    
    # Convert to response format
    event_responses = [
        EventResponse(
            event_id=e.event_id,
            scheduled_time=e.scheduled_time,
            modality=e.modality,
            status=e.status.value,
            priority=e.priority,
            created_at=e.created_at,
            executed_at=e.executed_at,
            error_message=e.error_message,
            data=e.data.model_dump(),
        )
        for e in events
    ]
    
    # Count by status
    all_events = engine.event_queue.events
    pending = sum(1 for e in all_events if e.status == EventStatus.PENDING)
    executed = sum(1 for e in all_events if e.status == EventStatus.EXECUTED)
    failed = sum(1 for e in all_events if e.status == EventStatus.FAILED)
    skipped = sum(1 for e in all_events if e.status == EventStatus.SKIPPED)
    
    return EventListResponse(
        events=event_responses,
        total=total,
        pending=pending,
        executed=executed,
        failed=failed,
        skipped=skipped,
    )


@router.post("", response_model=EventResponse)
async def create_event(request: CreateEventRequest, engine: SimulationEngineDep):
    """Create a new scheduled event.
    
    The event will be added to the queue and executed when simulator
    time reaches the scheduled_time.
    
    Args:
        request: Event details including modality and data.
        engine: The SimulationEngine i  nstance (injected by FastAPI).
    
    Returns:
        The created event details.
    
    Raises:
        HTTPException: If event creation fails.
    """
    try:
        # Get current time to use as created_at
        current_time = engine.environment.time_state.current_time
        
        # Validate scheduled time isn't in the past
        if request.scheduled_time < current_time:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot schedule event in the past. Current time: {current_time.isoformat()}, scheduled: {request.scheduled_time.isoformat()}",
            )
        
        # Deserialize the data dict into proper ModalityInput
        modality_input = deserialize_modality_input(
            modality=request.modality,
            data=request.data,
            timestamp=request.scheduled_time,
        )
        
        # Create the event
        event = SimulatorEvent(
            scheduled_time=request.scheduled_time,
            modality=request.modality,
            data=modality_input,
            priority=request.priority,
            created_at=current_time,
            agent_id=request.agent_id,
            metadata=request.metadata,
        )
        
        # Add to simulation
        engine.add_event(event)
        
        # Broadcast event scheduled event
        await broadcast_event(WSEventType.EVENT_SCHEDULED, {
            "event_id": event.event_id,
            "modality": event.modality,
            "scheduled_time": event.scheduled_time.isoformat(),
        })
        
        return EventResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            modality=event.modality,
            status=event.status.value,
            priority=event.priority,
            created_at=event.created_at,
            executed_at=event.executed_at,
            error_message=event.error_message,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create event: {str(e)}",
        )


@router.post("/immediate", response_model=EventResponse)
async def create_immediate_event(request: ImmediateEventRequest, engine: SimulationEngineDep):
    """Submit an event for immediate execution.
    
    This is a convenience endpoint that creates an event scheduled
    at the current simulator time with high priority.
    
    Args:
        request: Event details (modality and data).
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        The created event details.
    
    Raises:
        HTTPException: If event creation fails.
    """
    try:
        current_time = engine.environment.time_state.current_time
        
        # Deserialize the data dict into proper ModalityInput
        modality_input = deserialize_modality_input(
            modality=request.modality,
            data=request.data,
            timestamp=current_time,
        )
        
        # Create event at current time with high priority
        event = SimulatorEvent(
            scheduled_time=current_time,
            modality=request.modality,
            data=modality_input,
            priority=100,  # High priority for immediate execution
            created_at=current_time,
        )
        
        # Add to simulation
        engine.add_event(event)
        
        # Broadcast event scheduled event
        await broadcast_event(WSEventType.EVENT_SCHEDULED, {
            "event_id": event.event_id,
            "modality": event.modality,
            "scheduled_time": event.scheduled_time.isoformat(),
        })
        
        return EventResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            modality=event.modality,
            status=event.status.value,
            priority=event.priority,
            created_at=event.created_at,
            executed_at=event.executed_at,
            error_message=event.error_message,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create immediate event: {str(e)}",
        )


@router.post("/batch")
async def create_batch_events(
    request: BatchCreateEventRequest,
    engine: SimulationEngineDep,
):
    """Create multiple events in a single batch operation.
    
    This endpoint enables efficient bulk event scheduling, reducing network
    overhead when creating many events. Events are validated before creation,
    and the response includes per-event success/failure information.
    
    Behavior modes:
    - Default: Create all valid events, report failures (HTTP 207 if mixed)
    - stop_on_first_error=True: Abort on first failure, create nothing (HTTP 400)
    - validate_only=True: Validate without creating, return validation results
    
    Args:
        request: Batch request with events and options.
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        BatchCreateEventResponse (201/207) or BatchValidationResponse (200)
        or raises HTTPException (400) for strict mode failures.
    
    Raises:
        HTTPException 400: Batch too large, empty batch, or strict mode failure.
        HTTPException 422: Request structure invalid.
    """
    from fastapi.responses import JSONResponse
    
    # Enforce batch size limit
    if len(request.events) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Batch size {len(request.events)} exceeds maximum of {MAX_BATCH_SIZE}",
        )
    
    if len(request.events) == 0:
        raise HTTPException(
            status_code=400,
            detail="Batch must contain at least one event",
        )
    
    current_time = engine.environment.time_state.current_time
    
    # Phase 1: Validate all events and prepare SimulatorEvent objects
    validation_results: list[tuple[int, Optional[SimulatorEvent], Optional[str]]] = []
    
    for idx, event_request in enumerate(request.events):
        error: Optional[str] = None
        event: Optional[SimulatorEvent] = None
        
        try:
            # Check scheduled time is not in the past
            if event_request.scheduled_time < current_time:
                error = (
                    f"Cannot schedule event in the past. "
                    f"Current time: {current_time.isoformat()}, "
                    f"scheduled: {event_request.scheduled_time.isoformat()}"
                )
            else:
                # Deserialize and validate the modality input
                modality_input = deserialize_modality_input(
                    modality=event_request.modality,
                    data=event_request.data,
                    timestamp=event_request.scheduled_time,
                )
                
                # Create the event object
                event = SimulatorEvent(
                    scheduled_time=event_request.scheduled_time,
                    modality=event_request.modality,
                    data=modality_input,
                    priority=event_request.priority,
                    created_at=current_time,
                    agent_id=event_request.agent_id,
                    metadata=event_request.metadata,
                )
        except HTTPException as e:
            error = e.detail
        except ValidationError as e:
            error = f"Invalid data: {str(e)}"
        except Exception as e:
            error = f"Validation error: {str(e)}"
        
        validation_results.append((idx, event, error))
        
        # In strict mode, abort on first error
        if request.stop_on_first_error and error is not None:
            raise HTTPException(
                status_code=400,
                detail=BatchErrorResponse(
                    detail=f"Batch validation failed at index {idx}: {error}",
                    failed_index=idx,
                    events_validated=idx + 1,
                    total_events=len(request.events),
                ).model_dump(),
            )
    
    # Phase 2: Handle validate_only mode
    if request.validate_only:
        validation_response_events = [
            BatchValidationResult(
                index=idx,
                valid=error is None,
                error=error,
            )
            for idx, _, error in validation_results
        ]
        
        total_valid = sum(1 for r in validation_response_events if r.valid)
        
        return BatchValidationResponse(
            total_submitted=len(request.events),
            total_valid=total_valid,
            total_invalid=len(request.events) - total_valid,
            events=validation_response_events,
        )
    
    # Phase 3: Create valid events
    valid_events = [event for _, event, error in validation_results if event is not None]
    
    if valid_events:
        engine.event_queue.add_events(valid_events)
        
        # Broadcast batch scheduled event
        await broadcast_event(WSEventType.BATCH_EVENTS_SCHEDULED, {
            "count": len(valid_events),
            "event_ids": [e.event_id for e in valid_events],
            "modalities": list(set(e.modality for e in valid_events)),
        })
    
    # Phase 4: Build response
    response_events = [
        BatchEventResult(
            index=idx,
            success=event is not None,
            event_id=event.event_id if event else None,
            scheduled_time=event.scheduled_time if event else None,
            error=error,
        )
        for idx, event, error in validation_results
    ]
    
    total_created = len(valid_events)
    total_failed = len(request.events) - total_created
    
    response = BatchCreateEventResponse(
        total_submitted=len(request.events),
        total_created=total_created,
        total_failed=total_failed,
        events=response_events,
    )
    
    # Return 201 if all succeeded, 207 if mixed results
    if total_failed == 0:
        return JSONResponse(status_code=201, content=response.model_dump(mode="json"))
    else:
        return JSONResponse(status_code=207, content=response.model_dump(mode="json"))


@router.get("/next", response_model=EventResponse)
async def peek_next_event(engine: SimulationEngineDep):
    """Peek at the next pending event without executing it.
    
    Returns the next event that will be executed when time advances.
    
    Args:
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        Next pending event details.
    
    Raises:
        HTTPException: If no pending events exist.
    """
    next_event = engine.event_queue.peek_next()
    
    if not next_event:
        raise HTTPException(
            status_code=404,
            detail="No pending events",
        )
    
    return EventResponse(
        event_id=next_event.event_id,
        scheduled_time=next_event.scheduled_time,
        modality=next_event.modality,
        status=next_event.status.value,
        priority=next_event.priority,
        created_at=next_event.created_at,
        executed_at=next_event.executed_at,
        error_message=next_event.error_message,
    )


@router.get("/summary", response_model=EventSummaryResponse)
async def get_event_summary(engine: SimulationEngineDep):
    """Get event execution statistics.
    
    Provides counts and statistics about events in the simulation.
    
    Args:
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        Event summary statistics.
    """
    all_events = engine.event_queue.events
    
    # Count by status
    total = len(all_events)
    pending = sum(1 for e in all_events if e.status == EventStatus.PENDING)
    executed = sum(1 for e in all_events if e.status == EventStatus.EXECUTED)
    failed = sum(1 for e in all_events if e.status == EventStatus.FAILED)
    skipped = sum(1 for e in all_events if e.status == EventStatus.SKIPPED)
    
    # Count by modality
    by_modality: dict[str, int] = {}
    for event in all_events:
        by_modality[event.modality] = by_modality.get(event.modality, 0) + 1
    
    # Get next event time
    next_event = engine.event_queue.peek_next()
    next_event_time = next_event.scheduled_time if next_event else None
    
    return EventSummaryResponse(
        total=total,
        pending=pending,
        executed=executed,
        failed=failed,
        skipped=skipped,
        by_modality=by_modality,
        next_event_time=next_event_time,
    )


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: str, engine: SimulationEngineDep):
    """Get details for a specific event.
    
    Args:
        event_id: The unique event identifier.
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        Full event details including the event data payload.
    
    Raises:
        HTTPException: If event is not found.
    """
    # Search for event in queue
    event = None
    for e in engine.event_queue.events:
        if e.event_id == event_id:
            event = e
            break
    
    if not event:
        raise HTTPException(
            status_code=404,
            detail=f"Event {event_id} not found",
        )
    
    # Serialize the event data if it exists
    event_data = None
    if event.data is not None:
        if hasattr(event.data, 'model_dump'):
            event_data = event.data.model_dump()
        elif isinstance(event.data, dict):
            event_data = event.data
    
    return EventResponse(
        event_id=event.event_id,
        scheduled_time=event.scheduled_time,
        modality=event.modality,
        status=event.status.value,
        priority=event.priority,
        created_at=event.created_at,
        executed_at=event.executed_at,
        error_message=event.error_message,
        data=event_data,
    )


@router.delete("/{event_id}")
async def cancel_event(event_id: str, engine: SimulationEngineDep):
    """Cancel a pending event.
    
    Only pending events can be cancelled. Executed or failed events
    cannot be cancelled.
    
    Args:
        event_id: The unique event identifier.
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        Confirmation of cancellation.
    
    Raises:
        HTTPException: If event not found or cannot be cancelled.
    """
    # Find the event
    event = None
    for e in engine.event_queue.events:
        if e.event_id == event_id:
            event = e
            break
    
    if not event:
        raise HTTPException(
            status_code=404,
            detail=f"Event {event_id} not found",
        )
    
    # Check if can be cancelled
    if event.status != EventStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel event with status {event.status.value}. Only pending events can be cancelled.",
        )
    
    # Cancel the event
    event.status = EventStatus.CANCELLED
    
    # Broadcast event cancelled event
    await broadcast_event(WSEventType.EVENT_CANCELLED, {
        "event_id": event_id,
    })
    
    return {
        "cancelled": True,
        "event_id": event_id,
    }
