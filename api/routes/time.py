"""Time control endpoints for the simulator.

These endpoints allow clients to query and manipulate the simulator's time state.
"""

from datetime import datetime
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import SimulationEngineDep
from models.simulation import SimulationEngine


# Create a router - this is like a mini FastAPI app for time-related routes
router = APIRouter(
    prefix="/simulator/time",
    tags=["time"],  # Groups endpoints in the auto-generated docs
)


# Request/Response Models
# These define the shape of data going in and out of your endpoints


class TimeStateResponse(BaseModel):
    """Response model for current time state.
    
    Attributes:
        current_time: The current simulator time.
        time_scale: Multiplier for time progression (1.0 = real-time).
        is_paused: Whether time progression is paused.
        auto_advance: Whether time advances automatically.
    """
    
    current_time: datetime
    time_scale: float
    is_paused: bool
    auto_advance: bool


class AdvanceTimeRequest(BaseModel):
    """Request model for advancing time by a duration.
    
    Attributes:
        seconds: Number of simulator seconds to advance.
    """
    
    seconds: float = Field(
        ...,
        gt=0,
        description="Number of seconds to advance (must be positive)",
    )


class SetTimeRequest(BaseModel):
    """Request model for jumping to a specific time.
    
    Attributes:
        target_time: The simulator time to jump to.
    """
    
    target_time: datetime = Field(
        ...,
        description="The target simulator time (must be timezone-aware)",
    )


# Route Handlers
# Each function below handles one API endpoint


@router.get("/", response_model=TimeStateResponse)
async def get_time_state(engine: SimulationEngineDep):
    """Get the current simulator time state.
    
    This endpoint returns information about the simulator's current time,
    time scale, and whether automatic time advancement is enabled.
    
    Args:
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        Current time state including time, scale, pause status, and auto-advance.
    """
    time_state = engine.environment.time_state
    
    return TimeStateResponse(
        current_time=time_state.current_time,
        time_scale=time_state.time_scale,
        is_paused=time_state.is_paused,
        auto_advance=time_state.auto_advance,
    )


@router.post("/advance", response_model=TimeStateResponse)
async def advance_time(request: AdvanceTimeRequest, engine: SimulationEngineDep):
    """Advance simulator time by a specified duration.
    
    This moves the simulator forward by the specified number of seconds,
    processing any events that occur during that interval.
    
    Args:
        request: Contains the number of seconds to advance.
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        Updated time state after advancing.
    
    Raises:
        HTTPException: If time advancement fails.
    """
    try:
        engine.advance_time(delta=timedelta(seconds=request.seconds))
        time_state = engine.environment.time_state
        
        return TimeStateResponse(
            current_time=time_state.current_time,
            time_scale=time_state.time_scale,
            is_paused=time_state.is_paused,
            auto_advance=time_state.auto_advance,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to advance time: {str(e)}",
        )


class SetTimeResponse(BaseModel):
    """Response model for set_time endpoint.
    
    Attributes:
        current_time: The new current simulator time.
        previous_time: The time before the jump.
        skipped_events: Number of events that were skipped.
        executed_events: Number of events that were executed (if execute_skipped=True).
    """
    
    current_time: datetime
    previous_time: datetime
    skipped_events: int
    executed_events: int


class SkipToNextResponse(BaseModel):
    """Response model for skip_to_next endpoint.
    
    Attributes:
        current_time: The new current simulator time.
        events_executed: Number of events executed at the target time.
        next_event_time: Time of the next pending event, or None if no more events.
    """
    
    current_time: datetime
    events_executed: int
    next_event_time: Optional[datetime] = None


class SetScaleRequest(BaseModel):
    """Request model for setting time scale.
    
    Attributes:
        scale: Time multiplier (must be > 0).
    """
    
    scale: float = Field(
        ...,
        gt=0,
        description="Time multiplier (1.0 = real-time, >1.0 = fast-forward, <1.0 = slow-motion)",
    )


@router.post("/set", response_model=SetTimeResponse)
async def set_time(request: SetTimeRequest, engine: SimulationEngineDep):
    """Jump to a specific simulator time.
    
    This instantly moves the simulator to the target time. You can choose
    whether to execute or skip events in the jumped interval.
    
    Args:
        request: Contains the target time to jump to.
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        Summary of the time jump operation.
    
    Raises:
        HTTPException: If the target time is invalid or in the past.
    """
    try:
        result = engine.set_time(new_time=request.target_time, execute_skipped=False)
        
        return SetTimeResponse(
            current_time=datetime.fromisoformat(result["current_time"]),
            previous_time=datetime.fromisoformat(result["previous_time"]),
            skipped_events=result["skipped_events"],
            executed_events=result["executed_events"],
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set time: {str(e)}",
        )


@router.post("/skip-to-next", response_model=SkipToNextResponse)
async def skip_to_next_event(engine: SimulationEngineDep):
    """Jump directly to the next scheduled event time.
    
    This is event-driven time advancement - jumps to the next event
    and executes all events scheduled at that time.
    
    Args:
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        Summary of the skip operation including events executed.
    
    Raises:
        HTTPException: If there are no pending events or operation fails.
    """
    try:
        result = engine.skip_to_next_event()
        
        # Check if no pending events
        if "message" in result:
            raise HTTPException(
                status_code=404,
                detail=result["message"],
            )
        
        return SkipToNextResponse(
            current_time=datetime.fromisoformat(result["current_time"]),
            events_executed=result["events_executed"],
            next_event_time=(
                datetime.fromisoformat(result["next_event_time"])
                if result["next_event_time"]
                else None
            ),
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
            detail=f"Failed to skip to next event: {str(e)}",
        )


@router.post("/set-scale", response_model=TimeStateResponse)
async def set_time_scale(request: SetScaleRequest, engine: SimulationEngineDep):
    """Change the time multiplier for auto-advance mode.
    
    Controls how fast simulator time progresses relative to wall-clock time.
    
    Args:
        request: Contains the new time scale.
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        Updated time state with new scale.
    """
    try:
        # Update time scale
        engine.environment.time_state.time_scale = request.scale
        
        time_state = engine.environment.time_state
        
        return TimeStateResponse(
            current_time=time_state.current_time,
            time_scale=time_state.time_scale,
            is_paused=time_state.is_paused,
            auto_advance=time_state.auto_advance,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set time scale: {str(e)}",
        )


@router.post("/pause")
async def pause_time(engine: SimulationEngineDep):
    """Pause automatic time advancement.
    
    Stops the simulation loop if auto-advance is enabled. Has no effect
    if the simulator is already paused.
    
    Args:
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        A confirmation message with the current pause state.
    """
    engine.pause()
    
    return {
        "message": "Time paused",
        "is_paused": engine.environment.time_state.is_paused,
    }


@router.post("/resume")
async def resume_time(engine: SimulationEngineDep):
    """Resume automatic time advancement.
    
    Restarts the simulation loop if it was paused. Has no effect if
    the simulator is already running.
    
    Args:
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        A confirmation message with the current pause state.
    """
    engine.resume()
    
    return {
        "message": "Time resumed",
        "is_paused": engine.environment.time_state.is_paused,
    }
