"""Time control sub-client for the UES API.

This module provides TimeClient and AsyncTimeClient for interacting with
the simulator time control endpoints (/simulator/time/*).

This is an internal module. Import from `client` instead.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from client._base import AsyncBaseClient, BaseClient

if TYPE_CHECKING:
    from client._http import AsyncHTTPClient, HTTPClient


# Response models for time endpoints


class EventExecutionDetail(BaseModel):
    """Details about a single event that was executed.
    
    Attributes:
        event_id: Unique identifier of the event.
        modality: The modality type (email, sms, etc.).
        status: Execution status (executed, failed, etc.).
        error: Error message if the event failed, None otherwise.
    """

    event_id: str
    modality: str
    status: str
    error: str | None = None


class TimeStateResponse(BaseModel):
    """Response model for current time state.
    
    Attributes:
        current_time: The current simulator time.
        time_scale: Multiplier for time progression (1.0 = real-time).
        is_paused: Whether time progression is paused.
        auto_advance: Whether time advances automatically.
        mode: The current time control mode ("manual", "auto", or "paused").
    """

    current_time: datetime
    time_scale: float
    is_paused: bool
    auto_advance: bool
    mode: str


class AdvanceTimeResponse(BaseModel):
    """Response model for advance_time endpoint.
    
    Attributes:
        previous_time: The simulator time before advancement.
        current_time: The new current simulator time after advancement.
        time_advanced: String representation of the time delta that was advanced.
        events_executed: Number of events that were successfully executed.
        events_failed: Number of events that failed during execution.
        execution_details: Details about each event that was executed.
    """

    previous_time: datetime
    current_time: datetime
    time_advanced: str
    events_executed: int
    events_failed: int
    execution_details: list[EventExecutionDetail]


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
        previous_time: The simulator time before the skip.
        current_time: The new current simulator time.
        events_executed: Number of events executed at the target time.
        next_event_time: Time of the next pending event, or None if no more events.
    """

    previous_time: datetime
    current_time: datetime
    events_executed: int
    next_event_time: datetime | None = None


class PauseResumeResponse(BaseModel):
    """Response model for pause/resume endpoints.
    
    Attributes:
        message: Confirmation message.
        current_time: The current simulator time.
        is_paused: Whether time is currently paused.
    """

    message: str
    current_time: datetime
    is_paused: bool


# Synchronous TimeClient


class TimeClient(BaseClient):
    """Synchronous client for time control endpoints (/simulator/time/*).
    
    This client provides methods for querying and manipulating the simulator's
    time state, including advancing time, jumping to specific times, and
    controlling time scale.
    
    Example:
        with UESClient() as client:
            # Get current time state
            state = client.time.get_state()
            print(f"Current time: {state.current_time}")
            
            # Advance time by 1 hour
            result = client.time.advance(seconds=3600)
            print(f"Executed {result.events_executed} events")
            
            # Jump to next event
            result = client.time.skip_to_next()
            print(f"Skipped to {result.current_time}")
    """

    _BASE_PATH = "/simulator/time"

    def get_state(self) -> TimeStateResponse:
        """Get the current simulator time state.
        
        Returns information about the simulator's current time, time scale,
        and whether automatic time advancement is enabled.
        
        Returns:
            Current time state including time, scale, pause status, 
            auto-advance, and mode.
        
        Raises:
            APIError: If the request fails.
        """
        data = self._get(self._BASE_PATH)
        return TimeStateResponse(**data)

    def advance(self, seconds: float) -> AdvanceTimeResponse:
        """Advance simulator time by a specified duration.
        
        This moves the simulator forward by the specified number of seconds,
        processing any events that occur during that interval.
        
        Args:
            seconds: Number of seconds to advance (must be positive).
        
        Returns:
            Summary of advancement including previous time, current time, 
            and executed events.
        
        Raises:
            ValidationError: If seconds is not positive.
            APIError: If the request fails.
        """
        data = self._post(f"{self._BASE_PATH}/advance", json={"seconds": seconds})
        return AdvanceTimeResponse(**data)

    def set(self, target_time: datetime) -> SetTimeResponse:
        """Jump to a specific simulator time.
        
        This instantly moves the simulator to the target time. Events in
        the jumped interval are skipped (not executed).
        
        Args:
            target_time: The simulator time to jump to.
        
        Returns:
            Summary of the time jump operation.
        
        Raises:
            ValidationError: If the target time is invalid.
            APIError: If the target time is in the past or request fails.
        """
        # Convert datetime to ISO format for JSON serialization
        data = self._post(
            f"{self._BASE_PATH}/set",
            json={"target_time": target_time.isoformat()},
        )
        return SetTimeResponse(**data)

    def skip_to_next(self) -> SkipToNextResponse:
        """Jump directly to the next scheduled event time.
        
        This is event-driven time advancement - jumps to the next event
        and executes all events scheduled at that time.
        
        Returns:
            Summary of the skip operation including previous time 
            and events executed.
        
        Raises:
            NotFoundError: If there are no pending events.
            APIError: If the operation fails.
        """
        data = self._post(f"{self._BASE_PATH}/skip-to-next")
        return SkipToNextResponse(**data)

    def pause(self) -> PauseResumeResponse:
        """Pause automatic time advancement.
        
        Stops the simulation loop if auto-advance is enabled. Has no effect
        if the simulator is already paused.
        
        Returns:
            Confirmation with current time and pause state.
        
        Raises:
            APIError: If the request fails.
        """
        data = self._post(f"{self._BASE_PATH}/pause")
        return PauseResumeResponse(**data)

    def resume(self) -> PauseResumeResponse:
        """Resume automatic time advancement.
        
        Restarts the simulation loop if it was paused. Has no effect if
        the simulator is already running.
        
        Returns:
            Confirmation with current time and pause state.
        
        Raises:
            APIError: If the request fails.
        """
        data = self._post(f"{self._BASE_PATH}/resume")
        return PauseResumeResponse(**data)

    def set_scale(self, scale: float) -> TimeStateResponse:
        """Change the time multiplier for auto-advance mode.
        
        Controls how fast simulator time progresses relative to wall-clock time.
        
        Args:
            scale: Time multiplier (1.0 = real-time, >1.0 = fast-forward,
                <1.0 = slow-motion). Must be positive.
        
        Returns:
            Updated time state with new scale.
        
        Raises:
            ValidationError: If scale is not positive.
            APIError: If the request fails.
        """
        data = self._post(f"{self._BASE_PATH}/set-scale", json={"scale": scale})
        return TimeStateResponse(**data)


# Asynchronous AsyncTimeClient


class AsyncTimeClient(AsyncBaseClient):
    """Asynchronous client for time control endpoints (/simulator/time/*).
    
    This client provides async methods for querying and manipulating the 
    simulator's time state, including advancing time, jumping to specific 
    times, and controlling time scale.
    
    Example:
        async with AsyncUESClient() as client:
            # Get current time state
            state = await client.time.get_state()
            print(f"Current time: {state.current_time}")
            
            # Advance time by 1 hour
            result = await client.time.advance(seconds=3600)
            print(f"Executed {result.events_executed} events")
            
            # Jump to next event
            result = await client.time.skip_to_next()
            print(f"Skipped to {result.current_time}")
    """

    _BASE_PATH = "/simulator/time"

    async def get_state(self) -> TimeStateResponse:
        """Get the current simulator time state.
        
        Returns information about the simulator's current time, time scale,
        and whether automatic time advancement is enabled.
        
        Returns:
            Current time state including time, scale, pause status, 
            auto-advance, and mode.
        
        Raises:
            APIError: If the request fails.
        """
        data = await self._get(self._BASE_PATH)
        return TimeStateResponse(**data)

    async def advance(self, seconds: float) -> AdvanceTimeResponse:
        """Advance simulator time by a specified duration.
        
        This moves the simulator forward by the specified number of seconds,
        processing any events that occur during that interval.
        
        Args:
            seconds: Number of seconds to advance (must be positive).
        
        Returns:
            Summary of advancement including previous time, current time, 
            and executed events.
        
        Raises:
            ValidationError: If seconds is not positive.
            APIError: If the request fails.
        """
        data = await self._post(f"{self._BASE_PATH}/advance", json={"seconds": seconds})
        return AdvanceTimeResponse(**data)

    async def set(self, target_time: datetime) -> SetTimeResponse:
        """Jump to a specific simulator time.
        
        This instantly moves the simulator to the target time. Events in
        the jumped interval are skipped (not executed).
        
        Args:
            target_time: The simulator time to jump to.
        
        Returns:
            Summary of the time jump operation.
        
        Raises:
            ValidationError: If the target time is invalid.
            APIError: If the target time is in the past or request fails.
        """
        # Convert datetime to ISO format for JSON serialization
        data = await self._post(
            f"{self._BASE_PATH}/set",
            json={"target_time": target_time.isoformat()},
        )
        return SetTimeResponse(**data)

    async def skip_to_next(self) -> SkipToNextResponse:
        """Jump directly to the next scheduled event time.
        
        This is event-driven time advancement - jumps to the next event
        and executes all events scheduled at that time.
        
        Returns:
            Summary of the skip operation including previous time 
            and events executed.
        
        Raises:
            NotFoundError: If there are no pending events.
            APIError: If the operation fails.
        """
        data = await self._post(f"{self._BASE_PATH}/skip-to-next")
        return SkipToNextResponse(**data)

    async def pause(self) -> PauseResumeResponse:
        """Pause automatic time advancement.
        
        Stops the simulation loop if auto-advance is enabled. Has no effect
        if the simulator is already paused.
        
        Returns:
            Confirmation with current time and pause state.
        
        Raises:
            APIError: If the request fails.
        """
        data = await self._post(f"{self._BASE_PATH}/pause")
        return PauseResumeResponse(**data)

    async def resume(self) -> PauseResumeResponse:
        """Resume automatic time advancement.
        
        Restarts the simulation loop if it was paused. Has no effect if
        the simulator is already running.
        
        Returns:
            Confirmation with current time and pause state.
        
        Raises:
            APIError: If the request fails.
        """
        data = await self._post(f"{self._BASE_PATH}/resume")
        return PauseResumeResponse(**data)

    async def set_scale(self, scale: float) -> TimeStateResponse:
        """Change the time multiplier for auto-advance mode.
        
        Controls how fast simulator time progresses relative to wall-clock time.
        
        Args:
            scale: Time multiplier (1.0 = real-time, >1.0 = fast-forward,
                <1.0 = slow-motion). Must be positive.
        
        Returns:
            Updated time state with new scale.
        
        Raises:
            ValidationError: If scale is not positive.
            APIError: If the request fails.
        """
        data = await self._post(f"{self._BASE_PATH}/set-scale", json={"scale": scale})
        return TimeStateResponse(**data)
