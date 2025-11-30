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
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field

from models.environment import Environment
from models.event import EventStatus, SimulatorEvent
from models.queue import EventQueue

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
    - Error handling and logging
    - API request handling
    
    See docs/SIMULATION_ENGINE.md for complete design.
    
    Attributes:
        environment: Complete simulation state container.
        event_queue: Collection of all scheduled events.
        simulation_id: Unique identifier for this simulation instance.
        is_running: Whether simulation is currently active.
    """

    environment: Environment
    event_queue: EventQueue
    simulation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    is_running: bool = False

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

    def reset(self) -> int:
        """Reset simulation to initial state.
        
        Stops simulation if running.
        Resets all events to pending status (preserves events for replay).
        
        Note: Time and environment states are NOT reset by this method.
        Events are preserved but their execution state is cleared, allowing
        the same simulation scenario to be replayed.
        
        Returns:
            Number of events that were reset.
        """        
        # Stop if running
        if self.is_running:
            self.stop()

        # Count events for return value
        event_count = len(self.event_queue.events)
        
        # Reset all events to pending status
        for event in self.event_queue.events:
            event.status = EventStatus.PENDING
            event.executed_at = None
            event.error_message = None

        logger.info(f"Simulation {self.simulation_id} reset, reset {event_count} events to pending")
        
        return event_count

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
                # Execute all skipped events instantly
                for event in skipped_events:
                    try:
                        event.execute(self.environment)
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
        
        Returns:
            List of executed events (both successful and failed).
        """
        current_time = self.environment.time_state.current_time
        due_events = self.event_queue.get_due_events(current_time)

        executed = []
        for event in due_events:
            try:
                event.execute(self.environment)
                executed.append(event)
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