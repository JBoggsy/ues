"""Simulation lifecycle control endpoints.

These endpoints manage the overall simulation lifecycle: starting, stopping,
checking status, resetting, undo/redo operations, and clearing.

All endpoints require authentication via X-API-Key header.
"""

from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ues.api.auth import Permissions, require_permission
from ues.api.broadcast import broadcast_event
from ues.api.dependencies import SimulationEngineDep
from ues.api.websocket import WSEventType
from ues.models.api_key import APIKey
from ues.models.event import EventStatus

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
async def start_simulation(
    request: StartSimulationRequest,
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.SIMULATION_START))],
):
    """Start the simulation.
    
    Initializes and starts the simulation, optionally with auto-advance mode.
    
    Args:
        request: Configuration for starting the simulation.
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        Simulation startup details.
    
    Requires:
        Permission: simulation:start
    
    Raises:
        HTTPException: If simulation is already running or start fails.
    """
    try:
        result = engine.start(
            auto_advance=request.auto_advance,
            time_scale=request.time_scale,
        )
        print("Simulation started:", result)
        
        # Broadcast simulation started event
        await broadcast_event(WSEventType.SIMULATION_STARTED, {
            "simulation_id": result["simulation_id"],
            "mode": "auto" if request.auto_advance else "manual",
            "current_time": result["current_time"],
            "time_scale": result.get("time_scale"),
        })
        
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
async def stop_simulation(
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.SIMULATION_STOP))],
):
    """Stop the simulation gracefully.
    
    Stops the simulation, finishing any in-progress events.
    
    Args:
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        Summary of simulation execution.
    
    Requires:
        Permission: simulation:stop
    """
    try:
        result = engine.stop()
        
        # Broadcast simulation stopped event
        await broadcast_event(WSEventType.SIMULATION_STOPPED, {
            "simulation_id": result["simulation_id"],
            "final_time": result["final_time"],
            "events_executed": result["events_executed"],
            "events_failed": result["events_failed"],
        })
        
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
async def get_simulation_status(
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.SIMULATION_STATUS))],
):
    """Get current simulation status and metrics.
    
    Returns information about the simulation's current state, including
    time, event counts, and execution status.
    
    Args:
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        Current simulation status and statistics.
    
    Requires:
        Permission: simulation:status
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
async def reset_simulation(
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.SIMULATION_RESET))],
):
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
    
    Requires:
        Permission: simulation:reset
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

    # Broadcast simulation reset event
    await broadcast_event(WSEventType.SIMULATION_RESET, {
        "events_undone": result["events_undone"],
        "events_reset": result["events_reset"],
        "undo_errors_count": len(result["undo_errors"]),
    })

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
    _: Annotated[APIKey, Depends(require_permission(Permissions.SIMULATION_CLEAR))],
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
    
    Requires:
        Permission: simulation:clear
    """
    from datetime import datetime

    reset_time_to = None
    if request and request.reset_time_to:
        try:
            reset_time_to = datetime.fromisoformat(
                request.reset_time_to.replace("Z", "+00:00")
            )
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid datetime format for reset_time_to: {e}",
            )

    try:
        result = engine.clear(reset_time_to=reset_time_to)
        
        # Broadcast simulation cleared event
        await broadcast_event(WSEventType.SIMULATION_CLEARED, {
            "events_removed": result["events_removed"],
            "modalities_cleared": result["modalities_cleared"],
            "time_reset": result["time_reset"],
            "current_time": result["current_time"],
        })
        
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
    _: Annotated[APIKey, Depends(require_permission(Permissions.SIMULATION_UNDO))],
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
    
    Requires:
        Permission: simulation:undo
    
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
        
        # Broadcast undo performed event
        await broadcast_event(WSEventType.UNDO_PERFORMED, {
            "undone_count": result["undone_count"],
            "can_undo": result["can_undo"],
            "can_redo": result["can_redo"],
        })
        
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
    _: Annotated[APIKey, Depends(require_permission(Permissions.SIMULATION_REDO))],
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
    
    Requires:
        Permission: simulation:redo
    
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
        
        # Broadcast redo performed event
        await broadcast_event(WSEventType.REDO_PERFORMED, {
            "redone_count": result["redone_count"],
            "can_undo": result["can_undo"],
            "can_redo": result["can_redo"],
        })
        
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


# ===== Hold Management Endpoints =====


class HoldRequest(BaseModel):
    """Request model for acquiring a hold.
    
    Attributes:
        reason: Optional description of why the hold is needed.
        timeout_seconds: Optional timeout in seconds. If None, uses server default.
        agent_id: Optional identifier for the agent acquiring the hold.
    """

    reason: Optional[str] = Field(
        default=None,
        description="Human-readable reason for the hold (e.g., 'Generating LLM response')",
    )
    timeout_seconds: Optional[float] = Field(
        default=None,
        ge=1.0,
        le=3600.0,
        description="Timeout in seconds (1-3600). If None, uses server default (300s).",
    )
    agent_id: Optional[str] = Field(
        default=None,
        description="Optional identifier for the agent acquiring the hold",
    )


class HoldResponse(BaseModel):
    """Response model for hold acquisition.
    
    Attributes:
        hold_id: Unique identifier for the acquired hold.
        reason: The reason provided for the hold.
        timeout_seconds: The effective timeout for this hold.
        acquired_at: ISO timestamp when the hold was acquired.
        expires_at: ISO timestamp when the hold will expire (None if no timeout).
        active_hold_count: Total number of active holds after acquisition.
    """

    hold_id: str
    reason: Optional[str] = None
    timeout_seconds: Optional[float] = None
    acquired_at: str
    expires_at: Optional[str] = None
    active_hold_count: int


class HoldInfo(BaseModel):
    """Information about a single hold.
    
    Attributes:
        hold_id: Unique identifier for the hold.
        reason: The reason provided for the hold.
        timeout_seconds: The timeout for this hold.
        acquired_at: ISO timestamp when the hold was acquired.
        expires_at: ISO timestamp when the hold will expire.
        agent_id: Identifier for the agent that acquired the hold.
    """

    hold_id: str
    reason: Optional[str] = None
    timeout_seconds: Optional[float] = None
    acquired_at: str
    expires_at: Optional[str] = None
    agent_id: Optional[str] = None


class HoldsListResponse(BaseModel):
    """Response model for listing active holds.
    
    Attributes:
        holds: List of active holds.
        active_count: Number of active holds.
    """

    holds: list[HoldInfo]
    active_count: int


class ReleaseHoldResponse(BaseModel):
    """Response model for releasing a hold.
    
    Attributes:
        released: Whether the hold was found and released.
        hold_id: The ID of the hold that was released.
        active_hold_count: Number of holds remaining after release.
    """

    released: bool
    hold_id: str
    active_hold_count: int


@router.post("/hold", response_model=HoldResponse)
async def acquire_hold(
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.SIMULATION_HOLD))],
    request: Optional[HoldRequest] = None,
):
    """Acquire a hold on time advancement.
    
    When a hold is active, time advancement operations (advance, set, skip-to-next)
    will fail with a 409 Conflict error until the hold is released or expires.
    
    This is useful for multi-agent coordination: when an agent needs time to
    process an event (e.g., generating an LLM response), it can acquire a hold
    to prevent other agents from advancing time.
    
    Args:
        engine: The SimulationEngine instance (injected by FastAPI).
        request: Optional request body with hold parameters.
    
    Returns:
        Details of the acquired hold including the hold_id for later release.
    
    Requires:
        Permission: simulation:hold
    """
    # Parse request
    reason = request.reason if request else None
    timeout_seconds = request.timeout_seconds if request else None
    agent_id = request.agent_id if request else None
    
    # Acquire the hold
    hold_id = engine.hold_manager.acquire(
        reason=reason,
        timeout_seconds=timeout_seconds,
        agent_id=agent_id,
    )
    
    # Get the hold details
    hold = engine.hold_manager.get_hold(hold_id)
    
    # Broadcast hold acquired event
    await broadcast_event(WSEventType.HOLD_ACQUIRED, {
        "hold_id": hold_id,
        "reason": reason,
        "timeout_seconds": hold.timeout_seconds if hold else None,
        "agent_id": agent_id,
        "active_hold_count": engine.hold_manager.active_hold_count(),
    })
    
    return HoldResponse(
        hold_id=hold_id,
        reason=reason,
        timeout_seconds=hold.timeout_seconds if hold else None,
        acquired_at=hold.acquired_at.isoformat() if hold else None,
        expires_at=hold.expires_at.isoformat() if hold and hold.expires_at else None,
        active_hold_count=engine.hold_manager.active_hold_count(),
    )


@router.post("/release/{hold_id}", response_model=ReleaseHoldResponse)
async def release_hold(
    hold_id: str,
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.SIMULATION_RELEASE))],
):
    """Release a previously acquired hold.
    
    After release, time advancement operations can proceed (unless other
    holds are still active).
    
    Args:
        hold_id: The ID of the hold to release.
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        Confirmation of whether the hold was released.
    
    Requires:
        Permission: simulation:release
    
    Raises:
        HTTPException: 404 if the hold was not found (may have expired).
    """
    released = engine.hold_manager.release(hold_id)
    
    if released:
        # Broadcast hold released event
        await broadcast_event(WSEventType.HOLD_RELEASED, {
            "hold_id": hold_id,
            "active_hold_count": engine.hold_manager.active_hold_count(),
        })
    
    if not released:
        raise HTTPException(
            status_code=404,
            detail=f"Hold {hold_id} not found. It may have already expired or been released.",
        )
    
    return ReleaseHoldResponse(
        released=released,
        hold_id=hold_id,
        active_hold_count=engine.hold_manager.active_hold_count(),
    )


@router.get("/holds", response_model=HoldsListResponse)
async def list_holds(
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.SIMULATION_HOLDS))],
):
    """List all active holds.
    
    Returns information about all currently active (non-expired) holds.
    
    Args:
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        List of active holds with their details.
    
    Requires:
        Permission: simulation:holds
    """
    holds = engine.hold_manager.list_holds()
    
    return HoldsListResponse(
        holds=[
            HoldInfo(
                hold_id=h.hold_id,
                reason=h.reason,
                timeout_seconds=h.timeout_seconds,
                acquired_at=h.acquired_at.isoformat(),
                expires_at=h.expires_at.isoformat() if h.expires_at else None,
                agent_id=h.agent_id,
            )
            for h in holds
        ],
        active_count=len(holds),
    )