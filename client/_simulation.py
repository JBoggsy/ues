"""Simulation control sub-client for the UES API.

This module provides SimulationClient and AsyncSimulationClient for interacting
with the simulation lifecycle endpoints (/simulation/*).

This is an internal module. Import from `client` instead.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from client._base import AsyncBaseClient, BaseClient

if TYPE_CHECKING:
    from client._http import AsyncHTTPClient, HTTPClient


# Response models for simulation endpoints


class UndoRedoEventDetail(BaseModel):
    """Details of a single undone or redone event.
    
    Attributes:
        event_id: ID of the event that was undone/redone.
        modality: The modality type of the event.
        action: The action that was undone/redone (e.g., "receive", "send").
    """

    event_id: str
    modality: str
    action: str | None = None


class StartSimulationResponse(BaseModel):
    """Response model for simulation start.
    
    Attributes:
        simulation_id: Unique identifier for this simulation.
        status: Current simulation status.
        current_time: Current simulator time (ISO format string).
        auto_advance: Whether auto-advance is enabled.
        time_scale: Time multiplier (if auto-advance enabled).
    """

    simulation_id: str
    status: str
    current_time: str
    auto_advance: bool
    time_scale: float | None = None


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
    final_time: str | None = None
    total_events: int | None = None
    events_executed: int | None = None
    events_failed: int | None = None


class SimulationStatusResponse(BaseModel):
    """Response model for simulation status.
    
    Attributes:
        is_running: Whether simulation is currently active.
        current_time: Current simulator time (ISO format string).
        is_paused: Whether time advancement is paused.
        auto_advance: Whether auto-advance mode is enabled.
        time_scale: Current time multiplier.
        pending_events: Count of pending events.
        executed_events: Count of executed events.
        failed_events: Count of failed events.
        next_event_time: Scheduled time of next pending event (ISO format).
    """

    is_running: bool
    current_time: str
    is_paused: bool
    auto_advance: bool
    time_scale: float
    pending_events: int
    executed_events: int
    failed_events: int
    next_event_time: str | None = None


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
    undo_errors: list[str] = Field(default_factory=list)


class ClearSimulationResponse(BaseModel):
    """Response model for simulation clear.
    
    Attributes:
        status: Confirmation status ("cleared").
        events_removed: Number of events removed from queue.
        modalities_cleared: Number of modality states cleared.
        time_reset: The time that was set (if reset_time_to was provided).
        current_time: Current simulator time after clearing.
    """

    status: str
    events_removed: int
    modalities_cleared: int
    time_reset: str | None = None
    current_time: str


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
    message: str | None = None


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
    message: str | None = None


# Synchronous SimulationClient


class SimulationClient(BaseClient):
    """Synchronous client for simulation control endpoints (/simulation/*).
    
    This client provides methods for managing the simulation lifecycle:
    starting, stopping, resetting, clearing, and undo/redo operations.
    
    Example:
        with UESClient() as client:
            # Start the simulation
            result = client.simulation.start(auto_advance=True, time_scale=10.0)
            print(f"Started simulation {result.simulation_id}")
            
            # Check status
            status = client.simulation.status()
            print(f"Pending events: {status.pending_events}")
            
            # Stop when done
            result = client.simulation.stop()
            print(f"Executed {result.events_executed} events")
    """

    _BASE_PATH = "/simulation"

    def start(
        self,
        auto_advance: bool = False,
        time_scale: float = 1.0,
    ) -> StartSimulationResponse:
        """Start the simulation.
        
        Initializes and starts the simulation, optionally with auto-advance mode.
        
        Args:
            auto_advance: Enable automatic time advancement. When True, simulator
                time advances automatically based on wall-clock time.
            time_scale: Time multiplier for auto-advance mode (1.0 = real-time,
                >1.0 = fast-forward, <1.0 = slow-motion). Must be positive.
        
        Returns:
            Simulation startup details including simulation_id and current_time.
        
        Raises:
            ConflictError: If simulation is already running.
            ValidationError: If time_scale is not positive.
            APIError: If the request fails.
        """
        data = self._post(
            f"{self._BASE_PATH}/start",
            json={"auto_advance": auto_advance, "time_scale": time_scale},
        )
        return StartSimulationResponse(**data)

    def stop(self) -> StopSimulationResponse:
        """Stop the simulation gracefully.
        
        Stops the simulation, finishing any in-progress events.
        
        Returns:
            Summary of simulation execution including final_time and event counts.
        
        Raises:
            APIError: If the request fails.
        """
        data = self._post(f"{self._BASE_PATH}/stop")
        return StopSimulationResponse(**data)

    def status(self) -> SimulationStatusResponse:
        """Get current simulation status and metrics.
        
        Returns information about the simulation's current state, including
        time, event counts, and execution status.
        
        Returns:
            Current simulation status and statistics.
        
        Raises:
            APIError: If the request fails.
        """
        data = self._get(f"{self._BASE_PATH}/status")
        return SimulationStatusResponse(**data)

    def reset(self) -> ResetSimulationResponse:
        """Reset simulation by undoing all executed events.
        
        This performs a complete rollback of the simulation:
        1. Undoes ALL events in the undo stack (reversing state changes)
        2. Resets all events to PENDING status (preserving them for replay)
        3. Clears the undo/redo stacks
        4. Stops the simulation if running
        
        Time is NOT automatically reset - use client.time.set() or
        client.simulation.clear() separately if you need to reset time.
        
        Use this when you want to "replay" a simulation scenario from
        the beginning, with all state changes reversed.
        
        Returns:
            Summary of what was reset including cleared_events and events_undone.
        
        Raises:
            APIError: If the request fails.
        """
        data = self._post(f"{self._BASE_PATH}/reset")
        return ResetSimulationResponse(**data)

    def clear(self, reset_time_to: datetime | None = None) -> ClearSimulationResponse:
        """Clear simulation completely.
        
        Removes all events from the queue, clears all modality states to their
        empty defaults, and optionally resets time. This is a destructive
        operation that removes all simulation data.
        
        Use this to start completely fresh without any prior state.
        
        Args:
            reset_time_to: Optional datetime to reset simulator time to.
                If not provided, current time is preserved.
        
        Returns:
            Summary of what was cleared including events_removed and 
            modalities_cleared.
        
        Raises:
            ValidationError: If reset_time_to format is invalid.
            APIError: If the request fails.
        """
        json_body = None
        if reset_time_to is not None:
            json_body = {"reset_time_to": reset_time_to.isoformat()}
        
        data = self._post(f"{self._BASE_PATH}/clear", json=json_body)
        return ClearSimulationResponse(**data)

    def undo(self, count: int = 1) -> UndoResponse:
        """Undo previously executed events.
        
        Reverses the effects of the most recently executed events. Each undo
        restores the modality state to what it was before the event was applied.
        Undone events are moved to the redo stack.
        
        Args:
            count: Number of events to undo (default: 1, max: 100).
        
        Returns:
            Details of what was undone and current undo/redo availability.
        
        Raises:
            ConflictError: If simulation is not running.
            ValidationError: If count is out of range.
            APIError: If the undo operation fails.
        """
        json_body = {"count": count} if count != 1 else None
        data = self._post(f"{self._BASE_PATH}/undo", json=json_body)
        return UndoResponse(**data)

    def redo(self, count: int = 1) -> RedoResponse:
        """Redo previously undone events.
        
        Re-applies the effects of events that were previously undone. Each redo
        re-executes the original input on the modality state and moves the
        entry back to the undo stack.
        
        Args:
            count: Number of events to redo (default: 1, max: 100).
        
        Returns:
            Details of what was redone and current undo/redo availability.
        
        Raises:
            ConflictError: If simulation is not running.
            ValidationError: If count is out of range.
            APIError: If the redo operation fails.
        """
        json_body = {"count": count} if count != 1 else None
        data = self._post(f"{self._BASE_PATH}/redo", json=json_body)
        return RedoResponse(**data)


# Asynchronous AsyncSimulationClient


class AsyncSimulationClient(AsyncBaseClient):
    """Asynchronous client for simulation control endpoints (/simulation/*).
    
    This client provides async methods for managing the simulation lifecycle:
    starting, stopping, resetting, clearing, and undo/redo operations.
    
    Example:
        async with AsyncUESClient() as client:
            # Start the simulation
            result = await client.simulation.start(auto_advance=True, time_scale=10.0)
            print(f"Started simulation {result.simulation_id}")
            
            # Check status
            status = await client.simulation.status()
            print(f"Pending events: {status.pending_events}")
            
            # Stop when done
            result = await client.simulation.stop()
            print(f"Executed {result.events_executed} events")
    """

    _BASE_PATH = "/simulation"

    async def start(
        self,
        auto_advance: bool = False,
        time_scale: float = 1.0,
    ) -> StartSimulationResponse:
        """Start the simulation.
        
        Initializes and starts the simulation, optionally with auto-advance mode.
        
        Args:
            auto_advance: Enable automatic time advancement. When True, simulator
                time advances automatically based on wall-clock time.
            time_scale: Time multiplier for auto-advance mode (1.0 = real-time,
                >1.0 = fast-forward, <1.0 = slow-motion). Must be positive.
        
        Returns:
            Simulation startup details including simulation_id and current_time.
        
        Raises:
            ConflictError: If simulation is already running.
            ValidationError: If time_scale is not positive.
            APIError: If the request fails.
        """
        data = await self._post(
            f"{self._BASE_PATH}/start",
            json={"auto_advance": auto_advance, "time_scale": time_scale},
        )
        return StartSimulationResponse(**data)

    async def stop(self) -> StopSimulationResponse:
        """Stop the simulation gracefully.
        
        Stops the simulation, finishing any in-progress events.
        
        Returns:
            Summary of simulation execution including final_time and event counts.
        
        Raises:
            APIError: If the request fails.
        """
        data = await self._post(f"{self._BASE_PATH}/stop")
        return StopSimulationResponse(**data)

    async def status(self) -> SimulationStatusResponse:
        """Get current simulation status and metrics.
        
        Returns information about the simulation's current state, including
        time, event counts, and execution status.
        
        Returns:
            Current simulation status and statistics.
        
        Raises:
            APIError: If the request fails.
        """
        data = await self._get(f"{self._BASE_PATH}/status")
        return SimulationStatusResponse(**data)

    async def reset(self) -> ResetSimulationResponse:
        """Reset simulation by undoing all executed events.
        
        This performs a complete rollback of the simulation:
        1. Undoes ALL events in the undo stack (reversing state changes)
        2. Resets all events to PENDING status (preserving them for replay)
        3. Clears the undo/redo stacks
        4. Stops the simulation if running
        
        Time is NOT automatically reset - use client.time.set() or
        client.simulation.clear() separately if you need to reset time.
        
        Use this when you want to "replay" a simulation scenario from
        the beginning, with all state changes reversed.
        
        Returns:
            Summary of what was reset including cleared_events and events_undone.
        
        Raises:
            APIError: If the request fails.
        """
        data = await self._post(f"{self._BASE_PATH}/reset")
        return ResetSimulationResponse(**data)

    async def clear(
        self, reset_time_to: datetime | None = None
    ) -> ClearSimulationResponse:
        """Clear simulation completely.
        
        Removes all events from the queue, clears all modality states to their
        empty defaults, and optionally resets time. This is a destructive
        operation that removes all simulation data.
        
        Use this to start completely fresh without any prior state.
        
        Args:
            reset_time_to: Optional datetime to reset simulator time to.
                If not provided, current time is preserved.
        
        Returns:
            Summary of what was cleared including events_removed and 
            modalities_cleared.
        
        Raises:
            ValidationError: If reset_time_to format is invalid.
            APIError: If the request fails.
        """
        json_body = None
        if reset_time_to is not None:
            json_body = {"reset_time_to": reset_time_to.isoformat()}
        
        data = await self._post(f"{self._BASE_PATH}/clear", json=json_body)
        return ClearSimulationResponse(**data)

    async def undo(self, count: int = 1) -> UndoResponse:
        """Undo previously executed events.
        
        Reverses the effects of the most recently executed events. Each undo
        restores the modality state to what it was before the event was applied.
        Undone events are moved to the redo stack.
        
        Args:
            count: Number of events to undo (default: 1, max: 100).
        
        Returns:
            Details of what was undone and current undo/redo availability.
        
        Raises:
            ConflictError: If simulation is not running.
            ValidationError: If count is out of range.
            APIError: If the undo operation fails.
        """
        json_body = {"count": count} if count != 1 else None
        data = await self._post(f"{self._BASE_PATH}/undo", json=json_body)
        return UndoResponse(**data)

    async def redo(self, count: int = 1) -> RedoResponse:
        """Redo previously undone events.
        
        Re-applies the effects of events that were previously undone. Each redo
        re-executes the original input on the modality state and moves the
        entry back to the undo stack.
        
        Args:
            count: Number of events to redo (default: 1, max: 100).
        
        Returns:
            Details of what was redone and current undo/redo availability.
        
        Raises:
            ConflictError: If simulation is not running.
            ValidationError: If count is out of range.
            APIError: If the redo operation fails.
        """
        json_body = {"count": count} if count != 1 else None
        data = await self._post(f"{self._BASE_PATH}/redo", json=json_body)
        return RedoResponse(**data)
