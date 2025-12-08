"""Simulation lifecycle control endpoints.

These endpoints manage the overall simulation lifecycle: starting, stopping,
checking status, resetting, undo/redo operations, and clearing.
"""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import SimulationEngineDep
from models.event import EventStatus

# Create router for simulation control endpoints
router = APIRouter(
    prefix="/simulation",
    tags=["simulation"],
)


# Request/Response Models


class StartSimulationRequest(BaseModel):
    """Request model for starting simulation.
    
    Attributes:
        auto_advance: Enable automatic time advancement.
        time_scale: Time multiplier for auto-advance mode.
    """

    auto_advance: bool = Field(default=False)
    time_scale: float = Field(default=1.0, gt=0)


class StartSimulationResponse(BaseModel):
    """Response model for simulation start.
    
    Attributes:
        simulation_id: Unique identifier for this simulation.
        status: Current simulation status.
        current_time: Current simulator time.
        auto_advance: Whether auto-advance is enabled.
        time_scale: Time multiplier (if auto-advance enabled).
    """

    simulation_id: str
    status: str
    current_time: str
    auto_advance: bool
    time_scale: Optional[float] = None


class StopSimulationResponse(BaseModel):
    """Response model for simulation stop.
    
    Attributes:
        simulation_id: Unique identifier for this simulation.
        status: Current simulation status.
        final_time: Simulator time when stopped (None if wasn't running).
        total_events: Total number of events (None if wasn't running).
        events_executed: Number of executed events (None if wasn't running).
        events_failed: Number of failed events (None if wasn't running).
    """

    simulation_id: str
    status: str
    final_time: Optional[str] = None
    total_events: Optional[int] = None
    events_executed: Optional[int] = None
    events_failed: Optional[int] = None


class SimulationStatusResponse(BaseModel):
    """Response model for simulation status.
    
    Attributes:
        is_running: Whether simulation is currently active.
        current_time: Current simulator time.
        is_paused: Whether time advancement is paused.
        auto_advance: Whether auto-advance mode is enabled.
        time_scale: Current time multiplier.
        pending_events: Count of pending events.
        executed_events: Count of executed events.
        failed_events: Count of failed events.
        next_event_time: Scheduled time of next pending event.
    """

    is_running: bool
    current_time: str
    is_paused: bool
    auto_advance: bool
    time_scale: float
    pending_events: int
    executed_events: int
    failed_events: int
    next_event_time: Optional[str] = None


class ResetSimulationResponse(BaseModel):
    """Response model for simulation reset.

    Attributes:
        status: Confirmation status ("reset").
        message: Description of what was reset.
        cleared_events: Number of events reset to PENDING status.
        events_undone: Number of events whose state changes were reversed.
        undo_errors: List of any errors encountered during undo.
    """

    status: str
    message: str
    cleared_events: int
    events_undone: int = 0
    undo_errors: list[str] = []


# Route Handlers


@router.post("/start", response_model=StartSimulationResponse)
async def start_simulation(request: StartSimulationRequest, engine: SimulationEngineDep):
    """Start the simulation.
    
    Initializes and starts the simulation, optionally with auto-advance mode.
    
    Args:
        request: Configuration for starting the simulation.
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        Simulation startup details.
    
    Raises:
        HTTPException: If simulation is already running or start fails.
    """
    try:
        result = engine.start(
            auto_advance=request.auto_advance,
            time_scale=request.time_scale,
        )
        print("Simulation started:", result)
        
        return StartSimulationResponse(
            simulation_id=result["simulation_id"],
            status=result["status"],
            current_time=result["current_time"],
            auto_advance=request.auto_advance,
            time_scale=result.get("time_scale"),
        )
    except RuntimeError as e:
        # Simulation already running
        raise HTTPException(
            status_code=409,
            detail=str(e),
        )
    except ValueError as e:
        # Validation errors
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start simulation: {str(e)}",
        )


@router.post("/stop", response_model=StopSimulationResponse)
async def stop_simulation(engine: SimulationEngineDep):
    """Stop the simulation gracefully.
    
    Stops the simulation, finishing any in-progress events.
    
    Args:
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        Summary of simulation execution.
    """
    try:
        result = engine.stop()
        
        return StopSimulationResponse(
            simulation_id=result["simulation_id"],
            status=result["status"],
            final_time=result["final_time"],
            total_events=result["total_events"],
            events_executed=result["events_executed"],
            events_failed=result["events_failed"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop simulation: {str(e)}",
        )


@router.get("/status", response_model=SimulationStatusResponse)
async def get_simulation_status(engine: SimulationEngineDep):
    """Get current simulation status and metrics.
    
    Returns information about the simulation's current state, including
    time, event counts, and execution status.
    
    Args:
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        Current simulation status and statistics.
    """    
    time_state = engine.environment.time_state
    all_events = engine.event_queue.events
    auto_advance = time_state.auto_advance
    
    # Count events by status
    pending = sum(1 for e in all_events if e.status == EventStatus.PENDING)
    executed = sum(1 for e in all_events if e.status == EventStatus.EXECUTED)
    failed = sum(1 for e in all_events if e.status == EventStatus.FAILED)
    
    # Get next event time
    next_event = engine.event_queue.peek_next()
    next_event_time = next_event.scheduled_time.isoformat() if next_event else None
    
    return SimulationStatusResponse(
        is_running=engine.is_running,
        current_time=time_state.current_time.isoformat(),
        is_paused=time_state.is_paused,
        auto_advance=auto_advance,
        time_scale=time_state.time_scale,
        pending_events=pending,
        executed_events=executed,
        failed_events=failed,
        next_event_time=next_event_time,
    )


@router.post("/reset", response_model=ResetSimulationResponse)
async def reset_simulation(engine: SimulationEngineDep):
    """Reset simulation by undoing all executed events.

    This endpoint performs a complete rollback of the simulation:
    1. Undoes ALL events in the undo stack (reversing state changes)
    2. Resets all events to PENDING status (preserving them for replay)
    3. Clears the undo/redo stacks
    4. Stops the simulation if running

    Time is NOT automatically reset - use POST /simulator/time/set or
    POST /simulation/clear separately if you need to reset time.

    Use this endpoint when you want to "replay" a simulation scenario
    from the beginning, with all state changes reversed.

    For a complete wipe (removing all events and clearing all state),
    use POST /simulation/clear instead.

    Args:
        engine: The SimulationEngine instance (injected by FastAPI).

    Returns:
        ResetSimulationResponse with:
        - status: "reset"
        - message: Description of what was reset
        - cleared_events: Number of events reset to PENDING
        - events_undone: Number of events whose state changes were reversed
        - undo_errors: List of any errors encountered during undo
    """
    result = engine.reset()

    # Build descriptive message
    if result["events_undone"] > 0:
        message = (
            f"Reset complete: reversed {result['events_undone']} state changes, "
            f"reset {result['events_reset']} events to pending status."
        )
    else:
        message = f"Reset complete: {result['events_reset']} events reset to pending status."

    if result["undo_errors"]:
        message += f" Warning: {len(result['undo_errors'])} undo errors occurred."

    return ResetSimulationResponse(
        status="reset",
        message=message,
        cleared_events=result["events_reset"],
        events_undone=result["events_undone"],
        undo_errors=result["undo_errors"],
    )


class ClearSimulationRequest(BaseModel):
    """Request model for clearing simulation.
    
    Attributes:
        reset_time_to: Optional ISO-format datetime to reset time to.
                      If not provided, current time is preserved.
    """

    reset_time_to: Optional[str] = Field(
        default=None,
        description="ISO-format datetime to reset time to (optional)",
    )


class ClearSimulationResponse(BaseModel):
    """Response model for simulation clear.
    
    Attributes:
        status: Confirmation status.
        events_removed: Number of events removed from queue.
        modalities_cleared: Number of modality states cleared.
        time_reset: The time that was set (if reset_time_to was provided).
        current_time: Current simulator time after clearing.
    """

    status: str
    events_removed: int
    modalities_cleared: int
    time_reset: Optional[str] = None
    current_time: str


class UndoRedoEventDetail(BaseModel):
    """Details of a single undone or redone event.
    
    Attributes:
        event_id: ID of the event that was undone/redone.
        modality: The modality type of the event.
        action: The action that was undone/redone (e.g., "receive", "send").
    """

    event_id: str
    modality: str
    action: Optional[str] = None


class UndoRequest(BaseModel):
    """Request model for undo operation.
    
    Attributes:
        count: Number of events to undo (default: 1).
    """

    count: int = Field(default=1, ge=1, le=100)


class UndoResponse(BaseModel):
    """Response model for undo operation.
    
    Attributes:
        undone_count: Number of events actually undone.
        undone_events: Details of each undone event.
        can_undo: Whether more undos are available.
        can_redo: Whether redos are now available.
        message: Optional message (e.g., when nothing to undo).
    """

    undone_count: int
    undone_events: list[UndoRedoEventDetail]
    can_undo: bool
    can_redo: bool
    message: Optional[str] = None


class RedoRequest(BaseModel):
    """Request model for redo operation.
    
    Attributes:
        count: Number of events to redo (default: 1).
    """

    count: int = Field(default=1, ge=1, le=100)


class RedoResponse(BaseModel):
    """Response model for redo operation.
    
    Attributes:
        redone_count: Number of events actually redone.
        redone_events: Details of each redone event.
        can_undo: Whether undos are now available.
        can_redo: Whether more redos are available.
        message: Optional message (e.g., when nothing to redo).
    """

    redone_count: int
    redone_events: list[UndoRedoEventDetail]
    can_undo: bool
    can_redo: bool
    message: Optional[str] = None


@router.post("/clear", response_model=ClearSimulationResponse)
async def clear_simulation(
    engine: SimulationEngineDep,
    request: Optional[ClearSimulationRequest] = None,
):
    """Clear simulation completely.
    
    Removes all events from the queue, clears all modality states to their
    empty defaults, and optionally resets time. This is a destructive operation
    that removes all simulation data.
    
    Use this to start completely fresh without any prior state.
    
    Args:
        engine: The SimulationEngine instance (injected by FastAPI).
        request: Optional request body with reset_time_to parameter.
    
    Returns:
        Summary of what was cleared.
    """
    from datetime import datetime

    reset_time_to = None
    if request and request.reset_time_to:
        try:
            reset_time_to = datetime.fromisoformat(request.reset_time_to)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid datetime format for reset_time_to: {e}",
            )

    try:
        result = engine.clear(reset_time_to=reset_time_to)
        
        return ClearSimulationResponse(
            status="cleared",
            events_removed=result["events_removed"],
            modalities_cleared=result["modalities_cleared"],
            time_reset=result["time_reset"],
            current_time=result["current_time"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear simulation: {str(e)}",
        )


@router.post("/undo", response_model=UndoResponse)
async def undo_simulation(
    engine: SimulationEngineDep,
    request: Optional[UndoRequest] = None,
):
    """Undo previously executed events.
    
    Reverses the effects of the most recently executed events. Each undo
    restores the modality state to what it was before the event was applied.
    Undone events are moved to the redo stack.
    
    Args:
        engine: The SimulationEngine instance (injected by FastAPI).
        request: Optional request body with count parameter (default: 1).
    
    Returns:
        Details of what was undone and current undo/redo availability.
    
    Raises:
        HTTPException: If simulation is not running or undo fails.
    """
    if not engine.is_running:
        raise HTTPException(
            status_code=409,
            detail="Simulation is not running. Start simulation first.",
        )

    count = request.count if request else 1

    try:
        result = engine.undo(count=count)
        
        # Convert event details to response model
        undone_events = [
            UndoRedoEventDetail(
                event_id=e["event_id"],
                modality=e["modality"],
                action=e.get("action"),
            )
            for e in result.get("undone_events", [])
        ]
        
        return UndoResponse(
            undone_count=result["undone_count"],
            undone_events=undone_events,
            can_undo=result["can_undo"],
            can_redo=result["can_redo"],
            message=result.get("message"),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Undo failed: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during undo: {str(e)}",
        )


@router.post("/redo", response_model=RedoResponse)
async def redo_simulation(
    engine: SimulationEngineDep,
    request: Optional[RedoRequest] = None,
):
    """Redo previously undone events.
    
    Re-applies the effects of events that were previously undone. Each redo
    re-executes the original input on the modality state and moves the
    entry back to the undo stack.
    
    Args:
        engine: The SimulationEngine instance (injected by FastAPI).
        request: Optional request body with count parameter (default: 1).
    
    Returns:
        Details of what was redone and current undo/redo availability.
    
    Raises:
        HTTPException: If simulation is not running or redo fails.
    """
    if not engine.is_running:
        raise HTTPException(
            status_code=409,
            detail="Simulation is not running. Start simulation first.",
        )

    count = request.count if request else 1

    try:
        result = engine.redo(count=count)
        
        # Convert event details to response model
        redone_events = [
            UndoRedoEventDetail(
                event_id=e["event_id"],
                modality=e["modality"],
                action=e.get("action"),
            )
            for e in result.get("redone_events", [])
        ]
        
        return RedoResponse(
            redone_count=result["redone_count"],
            redone_events=redone_events,
            can_undo=result["can_undo"],
            can_redo=result["can_redo"],
            message=result.get("message"),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Redo failed: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during redo: {str(e)}",
        )