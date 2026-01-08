"""Simulation orchestration models.

This module contains the SimulationEngine and SimulationLoop classes
that implement the hybrid architecture for simulation orchestration.

See docs/SIMULATION_ENGINE.md for detailed design documentation.
"""

import logging
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Callable, Optional

from pydantic import BaseModel, Field

from models.environment import Environment
from models.event import EventStatus, SimulatorEvent
from models.queue import EventQueue
from models.scenario import Scenario
from models.undo import UndoEntry, UndoStack

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class SimulationEngine(BaseModel):
    """Main orchestrator for UES simulation.
    
    Coordinates time advancement, event execution, state management,
    and API interactions. Delegates auto-advance threading to SimulationLoop.
    
    Responsibilities:
    - Time control operations (advance, set, skip-to-next, pause, resume)
    - Event management (add, execute, query)
    - State access and validation
    - Lifecycle management (start, stop, reset)
    - Mode coordination (manual, event-driven, auto-advance)
    - Undo/redo support for reversing event executions
    - Error handling and logging
    - API request handling
    
    See docs/SIMULATION_ENGINE.md for complete design.
    
    Attributes:
        environment: Complete simulation state container.
        event_queue: Collection of all scheduled events.
        simulation_id: Unique identifier for this simulation instance.
        is_running: Whether simulation is currently active.
        undo_stack: Stack of undo entries for reversing event executions.
    """

    environment: Environment
    event_queue: EventQueue
    simulation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    is_running: bool = False
    undo_stack: UndoStack = Field(default_factory=UndoStack)

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **data):
        """Initialize with private attributes."""
        super().__init__(**data)
        # Initialize private attributes after Pydantic initialization
        self._loop: Optional[SimulationLoop] = None
        self._operation_lock = threading.Lock()
        self._event_executed_callback: Optional[Callable[[SimulatorEvent], None]] = None

    def set_event_callback(
        self, callback: Optional[Callable[[SimulatorEvent], None]]
    ) -> None:
        """Set callback for event execution notifications.
        
        The callback will be invoked for each event after it is executed
        (whether successful or failed). This is used for WebSocket broadcasting.
        
        Args:
            callback: Function to call with the executed event, or None to clear.
        """
        self._event_executed_callback = callback

    # ===== Lifecycle Methods =====

    def start(self, auto_advance: bool = False, time_scale: float = 1.0) -> dict:
        """Start the simulation.
        
        If auto_advance is True, creates and starts SimulationLoop.
        If auto_advance is False, just marks simulation as running.
        
        Args:
            auto_advance: Whether to start auto-advance loop.
            time_scale: Time multiplier for auto-advance mode.
        
        Returns:
            Status dict with simulation_id, current_time, mode.
        
        Raises:
            RuntimeError: If simulation is already running.
        """
        if self.is_running:
            raise RuntimeError("Simulation is already running")

        # Validate before starting
        errors = self.validate()
        if errors:
            raise ValueError(f"Cannot start simulation with validation errors: {errors}")

        self.is_running = True
        
        if auto_advance:
            # Configure time scale
            self.environment.time_state.time_scale = time_scale
            self.environment.time_state.auto_advance = True
            
            # Create and start loop
            self._loop = SimulationLoop(engine=self)
            self._loop.start()
            
            mode = "auto_advance"
        else:
            mode = "manual"

        logger.info(
            f"Simulation {self.simulation_id} started in {mode} mode "
            f"at {self.environment.time_state.current_time}"
        )

        return {
            "simulation_id": self.simulation_id,
            "status": "running",
            "mode": mode,
            "current_time": self.environment.time_state.current_time.isoformat(),
            "time_scale": time_scale if auto_advance else None,
        }

    def stop(self) -> dict:
        """Stop the simulation gracefully.
        
        If SimulationLoop is running, stops it first.
        Finishes executing any in-progress events.
        Returns execution summary.
        
        Returns:
            Summary dict with final_time, events_executed, etc.
        """
        if not self.is_running:
            logger.warning("stop() called but simulation is not running")
            return {
                "simulation_id": self.simulation_id,
                "status": "stopped",
                "final_time": None,
                "total_events": None,
                "events_executed": None,
                "events_failed": None,
            }

        # Stop loop if running
        if self._loop and self._loop.is_running:
            self._loop.stop()
            self._loop = None

        self.is_running = False

        # Get execution summary
        total_events = len(self.event_queue.events)
        executed_events = len(
            [e for e in self.event_queue.events if e.status == EventStatus.EXECUTED]
        )
        failed_events = len(
            [e for e in self.event_queue.events if e.status == EventStatus.FAILED]
        )

        logger.info(
            f"Simulation {self.simulation_id} stopped at "
            f"{self.environment.time_state.current_time}"
        )

        return {
            "simulation_id": self.simulation_id,
            "status": "stopped",
            "final_time": self.environment.time_state.current_time.isoformat(),
            "total_events": total_events,
            "events_executed": executed_events,
            "events_failed": failed_events,
        }

    def reset(self) -> dict[str, Any]:
        """Reset simulation by undoing all executed events.

        This method performs a complete rollback of the simulation:
        1. Undoes ALL events in the undo stack (reversing state changes)
        2. Resets all events to PENDING status
        3. Clears the undo/redo stacks
        4. Stops the simulation if running

        Time is NOT automatically reset - use set_time() or clear() separately
        if you need to reset time.

        Returns:
            Dict with:
                - events_undone: Number of events that were undone (state reversed).
                - events_reset: Number of events reset to PENDING status.
                - undo_errors: List of any errors encountered during undo.
                - was_running: Whether simulation was running before reset.

        Note:
            Unlike undo(), reset() does not stop on errors - it attempts to
            undo as many events as possible and continues to reset event
            statuses even if some undos fail.
        """
        was_running = self.is_running

        # Stop if running
        if self.is_running:
            self.stop()

        # Undo all events in the undo stack
        events_undone = 0
        undo_errors = []

        while self.undo_stack.can_undo:
            entries = self.undo_stack.pop_for_undo(count=1)
            for entry in entries:
                try:
                    # Get the modality state
                    state = self.environment.get_state(entry.modality)
                    # Apply undo
                    state.apply_undo(entry.undo_data)
                    events_undone += 1
                    logger.debug(
                        f"Reset: undid event {entry.event_id} ({entry.modality})"
                    )
                except Exception as e:
                    error_msg = f"Failed to undo event {entry.event_id}: {e}"
                    undo_errors.append(error_msg)
                    logger.warning(error_msg)
                    # Continue with remaining undos

        # Reset all events to pending status
        events_reset = len(self.event_queue.events)
        for event in self.event_queue.events:
            event.status = EventStatus.PENDING
            event.executed_at = None
            event.error_message = None

        # Clear both stacks (undo stack should already be empty, but clear redo too)
        self.undo_stack.clear()

        logger.info(
            f"Simulation {self.simulation_id} reset: "
            f"undid {events_undone} events, reset {events_reset} events to pending"
        )

        return {
            "events_undone": events_undone,
            "events_reset": events_reset,
            "undo_errors": undo_errors,
            "was_running": was_running,
        }

    def clear(self, reset_time_to: Optional[datetime] = None) -> dict:
        """Clear simulation completely, removing all state and events.

        Stops simulation if running, removes all events from the queue,
        clears all modality states to their empty defaults, and optionally
        resets time.

        This is a destructive operation - all simulation data is lost.
        Use this to start completely fresh.

        Args:
            reset_time_to: If provided, reset simulator time to this value.
                          If None, the current time is preserved.

        Returns:
            Summary dict with:
                - events_removed: Number of events removed from queue.
                - modalities_cleared: Number of modality states cleared.
                - time_reset: Whether time was reset (and to what value if so).
        """
        # Stop if running
        if self.is_running:
            self.stop()

        # Clear undo/redo stacks since all state is being cleared
        self.undo_stack.clear()

        # Count and remove all events
        events_removed = len(self.event_queue.events)
        self.event_queue.events.clear()

        # Determine the timestamp to use for cleared states
        if reset_time_to is not None:
            # Directly set current_time to allow backwards time travel during clear
            # (unlike set_time(), which doesn't allow backwards jumps)
            self.environment.time_state.current_time = reset_time_to
            self.environment.time_state.last_wall_time_update = datetime.now(timezone.utc)
            new_timestamp = reset_time_to
        else:
            new_timestamp = self.environment.time_state.current_time

        # Clear all modality states
        modalities_cleared = self.environment.clear_all_states(new_timestamp)

        logger.info(
            f"Simulation {self.simulation_id} cleared: "
            f"{events_removed} events removed, {modalities_cleared} modalities cleared"
        )

        result = {
            "events_removed": events_removed,
            "modalities_cleared": modalities_cleared,
            "time_reset": reset_time_to.isoformat() if reset_time_to else None,
            "current_time": self.environment.time_state.current_time.isoformat(),
        }

        return result

    # ===== Time Control Methods =====

    def advance_time(self, delta: timedelta) -> dict:
        """Manually advance simulator time by specified amount.
        
        This is the manual time control method.
        1. Validates delta (must be positive)
        2. Advances environment.time_state
        3. Gets and executes due events
        4. Returns execution summary
        
        Args:
            delta: Amount of simulator time to advance.
        
        Returns:
            Dict with current_time, events_executed, execution_details.
        
        Raises:
            ValueError: If delta <= 0 or simulation not running.
        """
        if not self.is_running:
            raise ValueError("Cannot advance time: simulation is not running")

        if delta <= timedelta(0):
            raise ValueError(f"Time delta must be positive, got {delta}")

        with self._operation_lock:
            # Advance time
            self.environment.time_state.advance(delta)

            # Execute due events
            executed = self.execute_due_events()

            logger.info(
                f"Advanced time by {delta}, now at "
                f"{self.environment.time_state.current_time}, "
                f"executed {len(executed)} events"
            )

            return {
                "current_time": self.environment.time_state.current_time.isoformat(),
                "time_advanced": str(delta),
                "events_executed": len(executed),
                "execution_details": [
                    {
                        "event_id": e.event_id,
                        "modality": e.modality,
                        "status": e.status.value,
                        "error": e.error_message,
                    }
                    for e in executed
                ],
            }

    def set_time(self, new_time: datetime, execute_skipped: bool = False) -> dict:
        """Jump to specific simulator time.

        Supports both forward and backward time jumps:
        
        **Forward jumps (new_time > current_time)**:
        Events in the skipped range are either executed (if execute_skipped=True)
        or marked as SKIPPED.
        
        **Backward jumps (new_time < current_time)**:
        Events that were executed after the target time are undone and reset
        to PENDING status, allowing them to be re-executed when time advances
        again.

        Args:
            new_time: Target simulator time.
            execute_skipped: If True, execute all skipped events instantly
                           (only applies to forward jumps). If False, mark
                           them as SKIPPED.

        Returns:
            Dict with current_time, previous_time, skipped_events, executed_events,
            and for backward jumps: rolled_back_events.
        """
        if not self.is_running:
            raise ValueError("Cannot set time: simulation is not running")

        current_time = self.environment.time_state.current_time

        with self._operation_lock:
            if new_time < current_time:
                # Backward time jump - undo events and reset to pending
                return self._set_time_backwards(new_time, current_time)
            else:
                # Forward time jump - skip or execute events
                return self._set_time_forwards(
                    new_time, current_time, execute_skipped
                )

    def _set_time_backwards(
        self, new_time: datetime, current_time: datetime
    ) -> dict:
        """Handle backward time jump by undoing events.

        Finds all executed events that occurred after the target time,
        undoes their effects in reverse order, and resets them to PENDING.

        Args:
            new_time: Target time to jump back to.
            current_time: Current simulator time.

        Returns:
            Dict with operation summary.
        """
        # Find executed events that occurred after the target time
        # These need to be undone in reverse chronological order
        events_to_rollback = sorted(
            [
                e
                for e in self.event_queue.events
                if e.status == EventStatus.EXECUTED
                and e.scheduled_time > new_time
            ],
            key=lambda e: e.scheduled_time,
            reverse=True,  # Most recent first
        )

        rolled_back_count = 0

        # We need to find undo entries for these events and apply them
        # Walk through the undo stack to find entries for events to rollback
        for event in events_to_rollback:
            # Find the undo entry for this event in the undo stack
            undo_entry = None
            entry_index = None

            # Search the undo stack for this event's entry
            for i, entry in enumerate(self.undo_stack.undo_entries):
                if entry.event_id == event.event_id:
                    undo_entry = entry
                    entry_index = i
                    break

            if undo_entry is not None:
                try:
                    # Get the modality state and apply undo
                    state = self.environment.get_state(undo_entry.modality)
                    state.apply_undo(undo_entry.undo_data)

                    # Remove from undo stack (don't push to redo - we're resetting)
                    self.undo_stack.undo_entries.pop(entry_index)

                    logger.debug(
                        f"Rolled back event {event.event_id} ({undo_entry.modality})"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to rollback event {event.event_id}: {e}",
                        exc_info=True,
                    )
                    # Continue with other events even if one fails

            # Reset event status to PENDING regardless of whether undo succeeded
            # (the event should be re-executable when time advances again)
            event.status = EventStatus.PENDING
            event.executed_at = None
            event.error_message = None
            rolled_back_count += 1

        # Also reset any SKIPPED events that were in the future
        skipped_reset_count = 0
        for event in self.event_queue.events:
            if (
                event.status == EventStatus.SKIPPED
                and event.scheduled_time > new_time
            ):
                event.status = EventStatus.PENDING
                event.error_message = None
                skipped_reset_count += 1

        # Jump time backwards
        self.environment.time_state.set_time(new_time)

        logger.info(
            f"Jumped time backwards from {current_time} to {new_time}, "
            f"rolled back {rolled_back_count} events, "
            f"reset {skipped_reset_count} skipped events to pending"
        )

        return {
            "current_time": new_time.isoformat(),
            "previous_time": current_time.isoformat(),
            "skipped_events": 0,
            "executed_events": 0,
            "rolled_back_events": rolled_back_count,
            "reset_skipped_events": skipped_reset_count,
        }

    def _set_time_forwards(
        self, new_time: datetime, current_time: datetime, execute_skipped: bool
    ) -> dict:
        """Handle forward time jump by skipping or executing events.

        Args:
            new_time: Target time to jump to.
            current_time: Current simulator time.
            execute_skipped: If True, execute events in the jumped range.

        Returns:
            Dict with operation summary.
        """
        # Find events in skipped range
        skipped_events = [
            e
            for e in self.event_queue.events
            if e.status == EventStatus.PENDING
            and current_time < e.scheduled_time <= new_time
        ]

        if execute_skipped:
            # Execute all skipped events instantly with undo capture
            for event in skipped_events:
                try:
                    undo_entry = event.execute(self.environment, capture_undo=True)
                    if undo_entry is not None:
                        self.undo_stack.push(undo_entry)
                    logger.debug(f"Executed skipped event {event.event_id}")
                except Exception as e:
                    logger.error(
                        f"Error executing skipped event {event.event_id}: {e}"
                    )
            executed_count = len(
                [e for e in skipped_events if e.status == EventStatus.EXECUTED]
            )
        else:
            # Mark as skipped
            for event in skipped_events:
                event.status = EventStatus.SKIPPED
                event.error_message = f"Time jumped from {current_time} to {new_time}"
            executed_count = 0

        # Jump time
        self.environment.time_state.set_time(new_time)

        logger.info(
            f"Jumped time from {current_time} to {new_time}, "
            f"{'executed' if execute_skipped else 'skipped'} {len(skipped_events)} events"
        )

        return {
            "current_time": new_time.isoformat(),
            "previous_time": current_time.isoformat(),
            "skipped_events": len(skipped_events),
            "executed_events": executed_count,
        }

    def skip_to_next_event(self) -> dict:
        """Jump to next scheduled event and execute it.
        
        Implements event-driven time advancement:
        1. Peek at next pending event
        2. Jump time to that event's scheduled_time
        3. Execute all events at that time (may be multiple with same time)
        4. Return execution summary
        
        Returns:
            Dict with current_time, events_executed, next_event_time
            Or {message: "No pending events"} if queue is empty.
        """
        if not self.is_running:
            raise ValueError("Cannot skip to next event: simulation is not running")

        with self._operation_lock:
            # Peek at next event
            next_event = self.event_queue.peek_next()

            if not next_event:
                return {
                    "message": "No pending events",
                    "current_time": self.environment.time_state.current_time.isoformat(),
                }

            # Jump time to that event
            target_time = next_event.scheduled_time
            self.environment.time_state.set_time(target_time)

            # Execute all events at that time
            executed = self.execute_due_events()

            # Check for next event after these
            next_after = self.event_queue.peek_next()

            logger.info(
                f"Skipped to next event at {target_time}, executed {len(executed)} events"
            )

            return {
                "current_time": target_time.isoformat(),
                "events_executed": len(executed),
                "next_event_time": (
                    next_after.scheduled_time.isoformat() if next_after else None
                ),
            }

    def pause(self) -> None:
        """Pause the simulation.
        
        Freezes time advancement (sets environment.time_state.is_paused = True).
        If SimulationLoop is running, it will idle but remain active.
        """
        self.environment.time_state.pause()
        logger.info(f"Simulation {self.simulation_id} paused")

    def resume(self) -> None:
        """Resume simulation from paused state.
        
        Unfreezes time (sets is_paused = False).
        Resets wall_time_anchor to prevent time jump.
        """
        self.environment.time_state.resume()
        logger.info(f"Simulation {self.simulation_id} resumed")

    # ===== Event Management Methods =====

    def add_event(self, event: SimulatorEvent) -> None:
        """Add new event to simulation.
        
        Validates event and adds to queue.
        If event is already due, may execute immediately depending on mode.
        
        Args:
            event: Event to add.
        
        Raises:
            ValueError: If event validation fails.
        """
        # Validate event
        errors = event.validate()
        if errors:
            raise ValueError(f"Invalid event: {errors}")

        # Add to queue
        self.event_queue.add_event(event)

        logger.debug(
            f"Added event {event.event_id} for {event.modality} "
            f"at {event.scheduled_time}"
        )

    def execute_due_events(self) -> list[SimulatorEvent]:
        """Execute all events that are currently due.
        
        Called by:
        - advance_time() after time advances
        - skip_to_next_event() after jumping
        - tick() during auto-advance loop
        
        Captures undo data for each successfully executed event and pushes
        it to the undo stack. Optionally notifies via callback for WebSocket
        broadcasting.
        
        Returns:
            List of executed events (both successful and failed).
        """
        current_time = self.environment.time_state.current_time
        due_events = self.event_queue.get_due_events(current_time)

        executed = []
        for event in due_events:
            try:
                undo_entry = event.execute(self.environment, capture_undo=True)
                executed.append(event)
                
                # Push undo entry to stack if execution succeeded
                if undo_entry is not None:
                    self.undo_stack.push(undo_entry)
                
                logger.debug(
                    f"Executed event {event.event_id} ({event.modality}) "
                    f"status={event.status.value}"
                )
            except Exception as e:
                # Event should have marked itself as FAILED
                executed.append(event)
                logger.error(
                    f"Event {event.event_id} failed during execution: {e}",
                    exc_info=True,
                )
            
            # Notify callback if registered (for WebSocket broadcasting)
            if self._event_executed_callback is not None:
                try:
                    self._event_executed_callback(event)
                except Exception as callback_error:
                    logger.warning(
                        f"Event callback failed for {event.event_id}: {callback_error}"
                    )

        return executed

    def query_events(
        self,
        status: Optional[EventStatus] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        modality: Optional[str] = None,
    ) -> list[SimulatorEvent]:
        """Query events with filters.
        
        Filters events from the queue based on provided criteria.
        
        Args:
            status: Filter by event status.
            start_time: Filter by scheduled_time >= start_time.
            end_time: Filter by scheduled_time <= end_time.
            modality: Filter by modality name.
        
        Returns:
            List of matching events.
        """
        results = self.event_queue.events

        if status is not None:
            results = [e for e in results if e.status == status]

        if start_time is not None:
            results = [e for e in results if e.scheduled_time >= start_time]

        if end_time is not None:
            results = [e for e in results if e.scheduled_time <= end_time]

        if modality is not None:
            results = [e for e in results if e.modality == modality]

        return results

    # ===== Undo/Redo Methods =====

    def undo(self, count: int = 1) -> dict[str, Any]:
        """Undo the most recent event executions.

        Reverses state changes from the most recently executed events
        by applying their undo data. Events are NOT reset to pending
        status - they remain executed but their effects are reversed.

        For each undone event:
        1. Pop entry from undo stack
        2. Get the modality state
        3. Apply undo data to reverse the change
        4. Push entry to redo stack

        Args:
            count: Number of events to undo (default: 1).

        Returns:
            Dict with:
                - undone_count: Number of events actually undone.
                - undone_events: List of event details that were undone.
                - can_undo: Whether more undos are available.
                - can_redo: Whether redos are now available.

        Raises:
            ValueError: If count is not positive.
            RuntimeError: If undo fails due to state inconsistency.
        """
        if count <= 0:
            raise ValueError("count must be positive")

        if not self.undo_stack.can_undo:
            return {
                "undone_count": 0,
                "undone_events": [],
                "can_undo": False,
                "can_redo": self.undo_stack.can_redo,
                "message": "Nothing to undo",
            }

        with self._operation_lock:
            # Pop entries from undo stack
            entries = self.undo_stack.pop_for_undo(count)
            undone_events = []

            for entry in entries:
                try:
                    # Get the modality state
                    state = self.environment.get_state(entry.modality)

                    # Apply undo
                    state.apply_undo(entry.undo_data)

                    # Push to redo stack
                    self.undo_stack.push_to_redo(entry)

                    undone_events.append({
                        "event_id": entry.event_id,
                        "modality": entry.modality,
                        "action": entry.undo_data.get("action"),
                    })

                    logger.info(
                        f"Undid event {entry.event_id} ({entry.modality}): "
                        f"action={entry.undo_data.get('action')}"
                    )

                except Exception as e:
                    # Log error but continue with remaining undos
                    logger.error(
                        f"Failed to undo event {entry.event_id}: {e}",
                        exc_info=True,
                    )
                    # Re-raise to signal failure to caller
                    raise RuntimeError(
                        f"Undo failed for event {entry.event_id}: {e}"
                    ) from e

            return {
                "undone_count": len(undone_events),
                "undone_events": undone_events,
                "can_undo": self.undo_stack.can_undo,
                "can_redo": self.undo_stack.can_redo,
            }

    def redo(self, count: int = 1) -> dict[str, Any]:
        """Redo previously undone event executions.

        Re-applies state changes from events that were previously undone.
        This works by re-executing the original input on the modality state.

        For each redone event:
        1. Pop entry from redo stack
        2. Find the original event in the queue
        3. Get the modality state and capture new undo data
        4. Re-apply the original input
        5. Push new undo entry to undo stack

        Args:
            count: Number of events to redo (default: 1).

        Returns:
            Dict with:
                - redone_count: Number of events actually redone.
                - redone_events: List of event details that were redone.
                - can_undo: Whether undos are now available.
                - can_redo: Whether more redos are available.

        Raises:
            ValueError: If count is not positive.
            RuntimeError: If redo fails due to missing event or state inconsistency.
        """
        if count <= 0:
            raise ValueError("count must be positive")

        if not self.undo_stack.can_redo:
            return {
                "redone_count": 0,
                "redone_events": [],
                "can_undo": self.undo_stack.can_undo,
                "can_redo": False,
                "message": "Nothing to redo",
            }

        with self._operation_lock:
            # Pop entries from redo stack
            entries = self.undo_stack.pop_for_redo(count)
            redone_events = []

            for entry in entries:
                try:
                    # Find the original event
                    original_event = None
                    for event in self.event_queue.events:
                        if event.event_id == entry.event_id:
                            original_event = event
                            break

                    if original_event is None:
                        raise RuntimeError(
                            f"Cannot redo: event {entry.event_id} not found in queue"
                        )

                    # Get the modality state
                    state = self.environment.get_state(entry.modality)

                    # Capture new undo data before re-applying
                    new_undo_data = state.create_undo_data(original_event.data)

                    # Re-apply the original input
                    state.apply_input(original_event.data)

                    # Create new undo entry and add to undo stack
                    # Note: We append directly instead of using push() to preserve
                    # the redo stack - redo is part of the same timeline, not a divergence
                    new_undo_entry = UndoEntry(
                        event_id=entry.event_id,
                        modality=entry.modality,
                        undo_data=new_undo_data,
                        executed_at=self.environment.time_state.current_time,
                    )
                    self.undo_stack.undo_entries.append(new_undo_entry)
                    
                    # Trim if over max_size
                    if (
                        self.undo_stack.max_size is not None
                        and len(self.undo_stack.undo_entries) > self.undo_stack.max_size
                    ):
                        self.undo_stack.undo_entries.pop(0)

                    redone_events.append({
                        "event_id": entry.event_id,
                        "modality": entry.modality,
                        "action": new_undo_data.get("action"),
                    })

                    logger.info(
                        f"Redid event {entry.event_id} ({entry.modality})"
                    )

                except Exception as e:
                    # Log error but continue with remaining redos
                    logger.error(
                        f"Failed to redo event {entry.event_id}: {e}",
                        exc_info=True,
                    )
                    # Re-raise to signal failure to caller
                    raise RuntimeError(
                        f"Redo failed for event {entry.event_id}: {e}"
                    ) from e

            return {
                "redone_count": len(redone_events),
                "redone_events": redone_events,
                "can_undo": self.undo_stack.can_undo,
                "can_redo": self.undo_stack.can_redo,
            }

    # ===== State Access Methods =====

    def get_state(self) -> Environment:
        """Get complete environment state.
        
        Returns reference to environment for direct access.
        Prefer get_snapshot() for serialization.
        
        Returns:
            Environment instance.
        """
        return self.environment

    def get_snapshot(self) -> dict:
        """Get complete state snapshot for API responses.
        
        Includes:
        - Time state
        - All modality states
        - Simulation metadata (id, is_running, etc.)
        - Event queue summary
        - Undo/redo status
        
        Returns:
            Serializable dict snapshot.
        """
        env_snapshot = self.environment.get_snapshot()

        # Add simulation metadata
        return {
            "simulation_id": self.simulation_id,
            "is_running": self.is_running,
            "mode": "auto_advance" if (self._loop and self._loop.is_running) else "manual",
            "environment": env_snapshot,
            "event_queue": {
                "total_events": len(self.event_queue.events),
                "pending_events": len(
                    [e for e in self.event_queue.events if e.status == EventStatus.PENDING]
                ),
                "executed_events": len(
                    [e for e in self.event_queue.events if e.status == EventStatus.EXECUTED]
                ),
                "failed_events": len(
                    [e for e in self.event_queue.events if e.status == EventStatus.FAILED]
                ),
                "next_event": (
                    {
                        "event_id": self.event_queue.peek_next().event_id,
                        "scheduled_time": self.event_queue.peek_next().scheduled_time.isoformat(),
                        "modality": self.event_queue.peek_next().modality,
                    }
                    if self.event_queue.peek_next()
                    else None
                ),
            },
            "undo_redo": {
                "can_undo": self.undo_stack.can_undo,
                "can_redo": self.undo_stack.can_redo,
                "undo_count": self.undo_stack.undo_count,
                "redo_count": self.undo_stack.redo_count,
            },
        }

    def validate(self) -> list[str]:
        """Validate simulation consistency.
        
        Checks:
        - Environment validation (time + modalities)
        - Event queue validation
        - Simulation state consistency
        
        Returns:
            List of validation errors (empty if valid).
        """
        errors = []

        # Validate environment
        env_errors = self.environment.validate()
        errors.extend([f"Environment: {e}" for e in env_errors])

        # Validate event queue
        queue_errors = self.event_queue.validate()
        errors.extend([f"EventQueue: {e}" for e in queue_errors])

        # Check for events referencing non-existent modalities
        available_modalities = self.environment.list_modalities()
        for event in self.event_queue.events:
            if event.status == EventStatus.PENDING and event.modality not in available_modalities:
                errors.append(
                    f"Event {event.event_id} references non-existent modality '{event.modality}'"
                )

        return errors

    # ===== Scenario Export/Load Methods =====

    def export_environment(self) -> dict[str, Any]:
        """Export current environment state for saving.

        Creates a serialized representation of the environment suitable
        for saving to a file or sending over the API. The exported data
        can be later loaded with `load_environment()`.

        Returns:
            Serialized environment dictionary containing:
            - time_state: Serialized SimulatorTime
            - modality_states: Dict of modality_type -> serialized state

        Example:
            >>> env_data = engine.export_environment()
            >>> json.dump(env_data, open("env.json", "w"))
        """
        return self.environment.to_scenario_dict()

    def export_event_queue(self) -> dict[str, Any]:
        """Export current event queue for saving.

        Creates a serialized representation of the event queue suitable
        for saving to a file or sending over the API. The exported data
        can be later loaded with `load_event_queue()`.

        Returns:
            Serialized event queue dictionary containing:
            - events: List of serialized SimulatorEvent dictionaries

        Example:
            >>> events_data = engine.export_event_queue()
            >>> json.dump(events_data, open("events.json", "w"))
        """
        return self.event_queue.to_scenario_dict()

    def export_scenario(
        self,
        author: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Scenario:
        """Export complete scenario with metadata.

        Creates a complete Scenario object containing the environment state,
        event queue, and metadata. This is the most complete export format
        and includes version information for compatibility checking.

        Args:
            author: Optional author name for the scenario metadata.
            description: Optional human-readable description.

        Returns:
            Scenario object ready for serialization with `to_json()`.

        Example:
            >>> scenario = engine.export_scenario(
            ...     author="Test User",
            ...     description="Initial state for regression testing",
            ... )
            >>> with open("scenario.ues-scenario.json", "w") as f:
            ...     f.write(scenario.to_json())
        """
        return Scenario.create(
            environment=self.environment,
            event_queue=self.event_queue,
            author=author,
            description=description,
        )

    def load_environment(
        self,
        data: dict[str, Any],
        historic_event_handling: str = "ignore",
        strict_modalities: bool = False,
    ) -> dict[str, Any]:
        """Load environment state from serialized data.

        Replaces the current environment state with state from the provided
        data. This is typically used to restore a previously saved environment
        or to set up a specific test scenario.

        The undo stack is cleared when loading an environment, as the undo
        history from before the load is no longer relevant.

        Historic events (events scheduled before the new environment time)
        can be handled in different ways based on the `historic_event_handling`
        parameter.

        Args:
            data: Serialized environment dictionary from `export_environment()`
                or `Environment.to_scenario_dict()`.
            historic_event_handling: How to handle existing events scheduled
                before the loaded environment's time:
                - "ignore": Leave them in queue (they will never execute)
                - "delete": Remove them from the queue
                - "apply": Execute them immediately against the loaded state
            strict_modalities: If True, raise ValueError on unknown modality
                types in the data. If False, skip unknown modalities and
                include them in the warnings list.

        Returns:
            Dict with load results:
            - success: True if load succeeded
            - modalities_loaded: List of modality types that were loaded
            - modalities_skipped: List of modality types that were skipped
            - warnings: List of warning messages
            - historic_events_count: Number of historic events found
            - historic_events_action: How historic events were handled

        Raises:
            RuntimeError: If simulation is running (must stop first).
            ValueError: If strict_modalities=True and unknown modality found.
            ValueError: If data is missing required fields.

        Example:
            >>> engine.stop()
            >>> result = engine.load_environment(env_data, strict_modalities=False)
            >>> if result["warnings"]:
            ...     print(f"Loaded with warnings: {result['warnings']}")
        """
        if self.is_running:
            raise RuntimeError(
                "Cannot load environment while simulation is running. "
                "Call stop() first."
            )

        valid_handling_options = ("ignore", "delete", "apply")
        if historic_event_handling not in valid_handling_options:
            raise ValueError(
                f"historic_event_handling must be one of {valid_handling_options}, "
                f"got '{historic_event_handling}'"
            )

        # Deserialize the new environment
        new_environment, warnings = Environment.from_scenario_dict(
            data, strict=strict_modalities
        )

        # Get the new environment time
        new_time = new_environment.time_state.current_time

        # Find historic events (scheduled before new time)
        historic_events = [
            e for e in self.event_queue.events
            if e.status == EventStatus.PENDING and e.scheduled_time < new_time
        ]
        historic_count = len(historic_events)

        # Handle historic events based on option
        if historic_event_handling == "delete":
            # Remove historic events from queue
            for event in historic_events:
                self.event_queue.remove_event(event.event_id)
            if historic_count > 0:
                warnings.append(
                    f"Deleted {historic_count} historic events "
                    f"(scheduled before {new_time.isoformat()})"
                )
        elif historic_event_handling == "apply":
            # Execute historic events against the NEW environment
            # (use the loaded environment, not the old one)
            applied_count = 0
            for event in historic_events:
                try:
                    event.execute(new_environment, capture_undo=False)
                    applied_count += 1
                except Exception as e:
                    warnings.append(
                        f"Failed to apply historic event {event.event_id}: {e}"
                    )
            if applied_count > 0:
                warnings.append(
                    f"Applied {applied_count} historic events to loaded state"
                )
        else:  # "ignore"
            if historic_count > 0:
                warnings.append(
                    f"{historic_count} events scheduled before environment time "
                    f"({new_time.isoformat()}) will be ignored (never execute)"
                )

        # Replace the environment
        self.environment = new_environment

        # Clear undo stack (history no longer relevant)
        self.undo_stack.clear()

        # Build modalities info
        modalities_loaded = list(new_environment.modality_states.keys())
        modalities_skipped = [
            w.replace("Skipped unknown modality type: '", "").rstrip("'")
            for w in warnings
            if w.startswith("Skipped unknown modality type:")
        ]

        logger.info(
            f"Loaded environment with {len(modalities_loaded)} modalities, "
            f"{historic_count} historic events ({historic_event_handling})"
        )

        return {
            "success": True,
            "modalities_loaded": modalities_loaded,
            "modalities_skipped": modalities_skipped,
            "warnings": warnings,
            "historic_events_count": historic_count,
            "historic_events_action": historic_event_handling,
        }

    def load_event_queue(
        self,
        data: dict[str, Any],
        merge: bool = False,
    ) -> dict[str, Any]:
        """Load event queue from serialized data.

        Replaces or merges the current event queue with events from the
        provided data. This is typically used to restore previously saved
        events or to set up test scenarios.

        When merging, the undo stack is preserved. When replacing, the
        undo stack is cleared.

        Args:
            data: Serialized event queue dictionary from `export_event_queue()`
                or `EventQueue.to_scenario_dict()`.
            merge: If True, add loaded events to existing queue.
                If False, replace all events.

        Returns:
            Dict with load results:
            - success: True if load succeeded
            - events_loaded: Number of events loaded
            - events_merged: Number of events added (only when merge=True)
            - previous_events: Number of events before load (when replacing)
            - historic_events_warning: True if any events are before current time
            - historic_event_count: Number of events scheduled before current time

        Raises:
            RuntimeError: If simulation is running (must stop first).
            ValueError: If data is missing required fields.

        Example:
            >>> engine.stop()
            >>> result = engine.load_event_queue(events_data, merge=True)
            >>> print(f"Added {result['events_merged']} events")
        """
        if self.is_running:
            raise RuntimeError(
                "Cannot load event queue while simulation is running. "
                "Call stop() first."
            )

        # Deserialize the new event queue
        new_queue = EventQueue.from_scenario_dict(data, regenerate_ids=True)

        # Get current time for historic event check
        current_time = self.environment.time_state.current_time

        # Count historic events in loaded data
        historic_events = [
            e for e in new_queue.events
            if e.status == EventStatus.PENDING and e.scheduled_time < current_time
        ]
        historic_count = len(historic_events)

        if merge:
            # Merge: add new events to existing queue
            previous_count = len(self.event_queue.events)
            added_count = 0

            for event in new_queue.events:
                try:
                    self.event_queue.add_event(event)
                    added_count += 1
                except ValueError as e:
                    logger.warning(f"Skipped event during merge: {e}")

            logger.info(
                f"Merged {added_count} events into queue "
                f"(had {previous_count}, now {len(self.event_queue.events)})"
            )

            return {
                "success": True,
                "events_loaded": len(new_queue.events),
                "events_merged": added_count,
                "previous_events": previous_count,
                "historic_events_warning": historic_count > 0,
                "historic_event_count": historic_count,
            }
        else:
            # Replace: swap out entire queue
            previous_count = len(self.event_queue.events)
            self.event_queue = new_queue

            # Clear undo stack (history no longer relevant)
            self.undo_stack.clear()

            logger.info(
                f"Replaced event queue: {previous_count} -> {len(new_queue.events)} events"
            )

            return {
                "success": True,
                "events_loaded": len(new_queue.events),
                "events_merged": 0,
                "previous_events": previous_count,
                "historic_events_warning": historic_count > 0,
                "historic_event_count": historic_count,
            }

    def load_scenario(
        self,
        scenario: Scenario,
        strict_modalities: bool = False,
    ) -> dict[str, Any]:
        """Load complete scenario (environment + events).

        Replaces both the environment and event queue with data from
        the provided scenario. This is the most complete load operation
        and is typically used to restore a fully saved state or set up
        regression tests.

        The undo stack is always cleared when loading a scenario.

        Args:
            scenario: Scenario object from `export_scenario()` or loaded
                from a file with `Scenario.from_json()`.
            strict_modalities: If True, raise ValueError on unknown modality
                types. If False, skip unknown modalities with warnings.

        Returns:
            Dict with load results:
            - success: True if load succeeded
            - environment_loaded: True if environment was loaded
            - events_loaded: Number of events loaded
            - modalities_loaded: List of modality types loaded
            - modalities_skipped: List of modality types skipped
            - warnings: List of warning messages
            - scenario_metadata: Summary of loaded scenario metadata

        Raises:
            RuntimeError: If simulation is running (must stop first).
            ValueError: If strict_modalities=True and unknown modality found.

        Example:
            >>> scenario = Scenario.from_json(open("scenario.json").read())
            >>> engine.stop()
            >>> result = engine.load_scenario(scenario)
            >>> print(f"Loaded scenario by {result['scenario_metadata']['author']}")
        """
        if self.is_running:
            raise RuntimeError(
                "Cannot load scenario while simulation is running. "
                "Call stop() first."
            )

        warnings: list[str] = []

        # Check version compatibility
        if not scenario.is_compatible:
            warnings.append(
                f"Scenario was created with UES version {scenario.metadata.ues_version}, "
                f"which may not be fully compatible with current version"
            )

        # Load environment (this also clears undo stack)
        # Use "ignore" for historic events - the scenario's events are the truth
        env_result = self.load_environment(
            scenario.environment,
            historic_event_handling="ignore",
            strict_modalities=strict_modalities,
        )
        warnings.extend(env_result["warnings"])

        # Load event queue (replace, not merge)
        # Note: We regenerate IDs by default via from_scenario_dict
        new_queue = EventQueue.from_scenario_dict(scenario.events, regenerate_ids=True)

        # Count historic events
        current_time = self.environment.time_state.current_time
        historic_events = [
            e for e in new_queue.events
            if e.status == EventStatus.PENDING and e.scheduled_time < current_time
        ]
        if historic_events:
            warnings.append(
                f"{len(historic_events)} events in scenario are scheduled before "
                f"environment time ({current_time.isoformat()}) and will not execute"
            )

        # Replace event queue
        self.event_queue = new_queue

        # Build metadata summary
        metadata_summary = {
            "ues_version": scenario.metadata.ues_version,
            "scenario_version": scenario.metadata.scenario_version,
            "created_at": scenario.metadata.created_at.isoformat(),
            "author": scenario.metadata.author,
            "description": scenario.metadata.description,
        }

        logger.info(
            f"Loaded scenario: {len(env_result['modalities_loaded'])} modalities, "
            f"{len(new_queue.events)} events "
            f"(created {scenario.metadata.created_at.isoformat()})"
        )

        return {
            "success": True,
            "environment_loaded": True,
            "events_loaded": len(new_queue.events),
            "modalities_loaded": env_result["modalities_loaded"],
            "modalities_skipped": env_result["modalities_skipped"],
            "warnings": warnings,
            "scenario_metadata": metadata_summary,
        }

    # ===== Internal/Helper Method =====

    def tick(self) -> None:
        """Execute one simulation tick (called by SimulationLoop).
        
        This is the core auto-advance operation:
        1. Calculate time advancement since last tick
        2. Advance environment.time_state
        3. Execute due events
        4. Log results
        
        Called repeatedly by SimulationLoop in auto-advance mode.
        Should not be called directly by external code.
        """
        with self._operation_lock:
            # Calculate time advancement
            current_wall_time = datetime.now(timezone.utc)
            wall_elapsed = (
                current_wall_time
                - self.environment.time_state.last_wall_time_update
            )

            sim_delta = self.environment.time_state.calculate_advancement(wall_elapsed)

            # Advance time if there's any progression
            if sim_delta > timedelta(0):
                self.environment.time_state.advance(sim_delta)

                # Execute due events
                executed = self.execute_due_events()

                if executed:
                    logger.debug(
                        f"Tick: advanced {sim_delta}, executed {len(executed)} events"
                    )


class SimulationLoop:
    """Threading component for auto-advance mode.
    
    Runs main simulation loop on dedicated thread, calling back to
    SimulationEngine.tick() at regular intervals.
    
    Responsibilities:
    - Thread management (create, start, stop)
    - Main loop execution (continuous tick calls)
    - Timing control (sleep between ticks)
    - Stop signal handling
    - Error isolation (catch tick errors without crashing thread)
    
    Does NOT contain simulation logic - all work delegated to
    SimulationEngine.tick().
    
    See docs/SIMULATION_ENGINE.md for complete design.
    
    Attributes:
        engine: Parent SimulationEngine to call back to.
        tick_interval: Seconds between ticks (default 10ms).
        is_running: Whether loop thread is active.
    """

    def __init__(self, engine: SimulationEngine, tick_interval: float = 0.01) -> None:
        """Initialize simulation loop.
        
        Args:
            engine: Parent SimulationEngine to call back to.
            tick_interval: Seconds between ticks (default 10ms).
        """
        self.engine = engine
        self.tick_interval = tick_interval

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.is_running = False

    def start(self) -> None:
        """Start the simulation loop thread.
        
        Creates new thread running _run_loop().
        
        Raises:
            RuntimeError: If loop is already running.
        """
        if self.is_running:
            raise RuntimeError("Simulation loop is already running")

        self.is_running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        logger.info("SimulationLoop started")

    def stop(self) -> None:
        """Stop the simulation loop gracefully.
        
        Sets stop event, waits for thread to finish current tick.
        """
        if not self.is_running:
            return

        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)

        self.is_running = False
        self._thread = None

        logger.info("SimulationLoop stopped")

    def _run_loop(self) -> None:
        """Main loop that runs on dedicated thread.
        
        Continuously:
        1. Check stop event
        2. Check if paused
        3. Call engine.tick()
        4. Sleep for tick_interval
        """
        while not self._stop_event.is_set():
            # Skip tick if paused, but keep loop running
            if self.engine.environment.time_state.is_paused:
                time.sleep(self.tick_interval)
                continue

            try:
                # Let engine handle all simulation logic
                self.engine.tick()
            except Exception as e:
                # Log but don't crash thread
                logger.error(f"Error during simulation tick: {e}", exc_info=True)
                # Could add circuit breaker here if errors persist

            # Brief sleep to avoid busy loop
            time.sleep(self.tick_interval)