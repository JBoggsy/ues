"""Event management endpoints.

These endpoints allow clients to create, query, and manage simulation events.
"""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import SimulationEngineDep
from models.event import EventStatus, SimulatorEvent

# Create router for event-related endpoints
router = APIRouter(
    prefix="/events",
    tags=["events"],
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
    """

    event_id: str
    scheduled_time: datetime
    modality: str
    status: str
    priority: int
    created_at: datetime
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
        engine: The SimulationEngine instance (injected by FastAPI).
    
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
        
        # Import modality-specific input classes to construct proper data
        # For now, we'll just pass the data dict as-is
        # TODO: Implement proper ModalityInput deserialization
        
        # Create the event
        event = SimulatorEvent(
            scheduled_time=request.scheduled_time,
            modality=request.modality,
            data=request.data,
            priority=request.priority,
            created_at=current_time,
            agent_id=request.agent_id,
            metadata=request.metadata,
        )
        
        # Add to simulation
        engine.add_event(event)
        
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
        
        # Create event at current time with high priority
        event = SimulatorEvent(
            scheduled_time=current_time,
            modality=request.modality,
            data=request.data,
            priority=100,  # High priority for immediate execution
            created_at=current_time,
        )
        
        # Add to simulation
        engine.add_event(event)
        
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


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: str, engine: SimulationEngineDep):
    """Get details for a specific event.
    
    Args:
        event_id: The unique event identifier.
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        Full event details.
    
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
    
    return {
        "cancelled": True,
        "event_id": event_id,
    }


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
