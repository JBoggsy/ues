"""Simulation lifecycle control endpoints.

These endpoints manage the overall simulation lifecycle: starting, stopping,
checking status, and resetting.
"""

from typing import Optional

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
        status: Confirmation status.
        message: Description of what was reset.
        cleared_events: Number of event records cleared.
    """

    status: str
    message: str
    cleared_events: int


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
    """Reset simulation to initial state.
    
    Clears executed events and resets the environment. The simulation
    will be stopped if it's currently running.
    
    Args:
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        Confirmation of reset operation.
    """
    try:
        # Count events before reset
        events_before = len(engine.event_queue.events)
        
        # Reset the simulation
        engine.reset()
        
        return ResetSimulationResponse(
            status="reset",
            message="Simulation reset to initial state",
            cleared_events=events_before,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset simulation: {str(e)}",
        )
