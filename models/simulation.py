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
from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, Field

from models.environment import Environment
from models.event import EventStatus, SimulatorEvent
from models.queue import EventQueue
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
        
        Handles events in skipped range based on execute_skipped flag.
        
        Args:
            new_time: Target simulator time.
            execute_skipped: If True, execute all skipped events instantly.
                           If False, mark them as SKIPPED.
        
        Returns:
            Dict with current_time, skipped_events, executed_events.
        
        Raises:
            ValueError: If new_time is in the past.
        """
        if not self.is_running:
            raise ValueError("Cannot set time: simulation is not running")

        current_time = self.environment.time_state.current_time

        if new_time < current_time:
            raise ValueError(
                f"Cannot travel backwards in time: "
                f"current={current_time}, target={new_time}"
            )

        with self._operation_lock:
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
        it to the undo stack.
        
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