"""Task update streaming for AgentBeats platform observability.

This module provides the infrastructure for emitting task updates during
assessment execution. Task updates are streamed to the AgentBeats platform
to provide real-time visibility into assessment progress.

Task updates are distinct from A2A messages:
- A2A messages: Coordination between Green and Purple agents
- Task updates: Observability logs sent to the platform

Example:
    >>> emitter = TaskUpdateEmitter()
    >>> await emitter.emit(TaskUpdate(
    ...     type=TaskUpdateType.LOG_TURN_STARTED,
    ...     timestamp=datetime.now(timezone.utc),
    ...     message="Turn 1 started",
    ...     details={"turn": 1, "current_time": "2026-01-22T09:00:00Z"},
    ... ))
    >>> 
    >>> # Consume updates elsewhere
    >>> async for update in emitter.stream():
    ...     print(update.message)
"""

import asyncio
from datetime import datetime, timezone
from typing import AsyncIterator

from pydantic import BaseModel, Field

from agentbeats.green.schemas import TaskUpdate, TaskUpdateType


class TaskUpdateEmitter:
    """Emits task updates for streaming to the AgentBeats platform.

    Uses an async queue to decouple update production from consumption.
    Updates can be emitted from the assessment loop and consumed by
    an SSE streaming endpoint or A2A task handler.

    Attributes:
        verbose: If False, only emit start/complete and error updates.

    Example:
        >>> emitter = TaskUpdateEmitter(verbose=True)
        >>> 
        >>> # Producer side (in assessment loop)
        >>> await emitter.emit(TaskUpdate(...))
        >>> 
        >>> # Consumer side (in SSE handler)
        >>> async for update in emitter.stream():
        ...     yield format_sse(update)
    """

    def __init__(self, verbose: bool = True) -> None:
        """Initialize the emitter.

        Args:
            verbose: If True, emit all update types. If False, only emit
                LOG_ASSESSMENT_STARTED, LOG_ASSESSMENT_COMPLETE, and errors.
        """
        self._queue: asyncio.Queue[TaskUpdate | None] = asyncio.Queue()
        self._verbose = verbose
        self._closed = False

    @property
    def verbose(self) -> bool:
        """Whether verbose updates are enabled."""
        return self._verbose

    async def emit(self, update: TaskUpdate) -> None:
        """Emit a task update.

        If verbose mode is disabled, only assessment_started, assessment_complete,
        and error-related updates are emitted; others are silently dropped.

        Args:
            update: The task update to emit.

        Raises:
            RuntimeError: If the emitter has been closed.
        """
        if self._closed:
            raise RuntimeError("Cannot emit to a closed TaskUpdateEmitter")

        # Filter non-verbose updates
        if not self._verbose:
            allowed_types = {
                TaskUpdateType.LOG_ASSESSMENT_STARTED,
                TaskUpdateType.LOG_ASSESSMENT_COMPLETE,
            }
            if update.type not in allowed_types:
                return

        await self._queue.put(update)

    async def stream(self) -> AsyncIterator[TaskUpdate]:
        """Async iterator for consuming emitted updates.

        Yields updates as they are emitted. Stops when the emitter is closed
        via the close() method.

        Yields:
            TaskUpdate instances as they are emitted.

        Example:
            >>> async for update in emitter.stream():
            ...     print(f"[{update.type.value}] {update.message}")
        """
        while True:
            update = await self._queue.get()
            if update is None:
                # Sentinel value indicates stream is closed
                break
            yield update

    async def close(self) -> None:
        """Close the emitter, signaling no more updates will be sent.

        After calling close(), the stream() iterator will complete and
        any further emit() calls will raise RuntimeError.
        """
        self._closed = True
        await self._queue.put(None)  # Sentinel to stop stream()

    def is_closed(self) -> bool:
        """Check if the emitter has been closed."""
        return self._closed


# =============================================================================
# Helper Functions for Creating Task Updates
# =============================================================================


def create_assessment_started_update(
    assessment_id: str,
    scenario_id: str,
    participant: str,
    verbose_updates: bool = True,
) -> TaskUpdate:
    """Create a LOG_ASSESSMENT_STARTED task update.

    Args:
        assessment_id: Unique identifier for this assessment.
        scenario_id: ID of the scenario being run.
        participant: Name/ID of the participant agent.
        verbose_updates: Whether verbose mode is enabled.

    Returns:
        A TaskUpdate with type LOG_ASSESSMENT_STARTED.
    """
    return TaskUpdate(
        type=TaskUpdateType.LOG_ASSESSMENT_STARTED,
        timestamp=datetime.now(timezone.utc),
        message=f"Assessment started for scenario '{scenario_id}'",
        details={
            "assessment_id": assessment_id,
            "scenario_id": scenario_id,
            "participant": participant,
            "verbose_updates": verbose_updates,
        },
    )


def create_scenario_loaded_update(
    scenario_id: str,
    initial_state: dict[str, object],
) -> TaskUpdate:
    """Create a LOG_SCENARIO_LOADED task update.

    Args:
        scenario_id: ID of the loaded scenario.
        initial_state: Summary of initial state by modality.

    Returns:
        A TaskUpdate with type LOG_SCENARIO_LOADED.
    """
    return TaskUpdate(
        type=TaskUpdateType.LOG_SCENARIO_LOADED,
        timestamp=datetime.now(timezone.utc),
        message=f"Scenario '{scenario_id}' loaded successfully",
        details={
            "scenario_id": scenario_id,
            "initial_state": initial_state,
        },
    )


def create_turn_started_update(
    turn: int,
    current_time: datetime,
) -> TaskUpdate:
    """Create a LOG_TURN_STARTED task update.

    Args:
        turn: Turn number (1-indexed).
        current_time: Current simulator time.

    Returns:
        A TaskUpdate with type LOG_TURN_STARTED.
    """
    return TaskUpdate(
        type=TaskUpdateType.LOG_TURN_STARTED,
        timestamp=datetime.now(timezone.utc),
        message=f"Turn {turn} started at {current_time.isoformat()}",
        details={
            "turn": turn,
            "current_time": current_time.isoformat(),
        },
    )


def create_turn_completed_update(
    turn: int,
    actions_taken: int,
    purple_notes: str | None = None,
) -> TaskUpdate:
    """Create a LOG_TURN_COMPLETED task update.

    Args:
        turn: Turn number (1-indexed).
        actions_taken: Number of actions taken by Purple this turn.
        purple_notes: Optional notes from Purple's turn_complete message.

    Returns:
        A TaskUpdate with type LOG_TURN_COMPLETED.
    """
    details: dict[str, object] = {
        "turn": turn,
        "actions_taken": actions_taken,
    }
    if purple_notes is not None:
        details["purple_notes"] = purple_notes

    return TaskUpdate(
        type=TaskUpdateType.LOG_TURN_COMPLETED,
        timestamp=datetime.now(timezone.utc),
        message=f"Turn {turn} completed ({actions_taken} actions)",
        details=details,
    )


def create_simulation_advanced_update(
    from_time: datetime,
    to_time: datetime,
    events_processed: int,
) -> TaskUpdate:
    """Create a LOG_SIMULATION_ADVANCED task update.

    Args:
        from_time: Simulator time before advancement.
        to_time: Simulator time after advancement.
        events_processed: Number of events that fired during the advance.

    Returns:
        A TaskUpdate with type LOG_SIMULATION_ADVANCED.
    """
    return TaskUpdate(
        type=TaskUpdateType.LOG_SIMULATION_ADVANCED,
        timestamp=datetime.now(timezone.utc),
        message=f"Simulation advanced to {to_time.isoformat()} ({events_processed} events)",
        details={
            "from_time": from_time.isoformat(),
            "to_time": to_time.isoformat(),
            "events_processed": events_processed,
        },
    )


def create_assessment_complete_update(
    reason: str,
    turns_taken: int,
    actions_taken: int,
    score: dict[str, object] | None = None,
) -> TaskUpdate:
    """Create a LOG_ASSESSMENT_COMPLETE task update.

    Args:
        reason: Why the assessment ended (scenario_complete, early_completion, etc.).
        turns_taken: Total number of turns in the assessment.
        actions_taken: Total number of actions taken by Purple.
        score: Optional scoring summary.

    Returns:
        A TaskUpdate with type LOG_ASSESSMENT_COMPLETE.
    """
    details: dict[str, object] = {
        "reason": reason,
        "turns_taken": turns_taken,
        "actions_taken": actions_taken,
    }
    if score is not None:
        details["score"] = score

    return TaskUpdate(
        type=TaskUpdateType.LOG_ASSESSMENT_COMPLETE,
        timestamp=datetime.now(timezone.utc),
        message=f"Assessment complete: {reason}",
        details=details,
    )


# =============================================================================
# A2A SDK Integration
# =============================================================================


class A2ATaskStatusUpdate(BaseModel):
    """Simplified A2A TaskStatusUpdateEvent for serialization.

    This model mirrors the A2A protocol's TaskStatusUpdateEvent structure
    for conversion purposes. When the actual A2A SDK is used, this can be
    replaced with the SDK's native types.

    Attributes:
        task_id: The assessment task ID.
        context_id: Grouping context for related updates.
        state: Current task state (working, completed, failed, etc.).
        message: Human-readable status message.
        timestamp: When this status was recorded.
        final: True if this is the last event.
        metadata: Custom data including UES update type and details.
    """

    task_id: str = Field(..., description="The assessment task ID")
    context_id: str = Field(..., description="Grouping context")
    state: str = Field(
        ...,
        description="Task state: submitted, working, completed, failed, cancelled, input_required",
    )
    message: str = Field(..., description="Human-readable status message")
    timestamp: datetime = Field(..., description="When this status was recorded")
    final: bool = Field(default=False, description="True if this is the last event")
    metadata: dict[str, object] = Field(
        default_factory=dict,
        description="Custom data including UES update type",
    )


def task_update_to_a2a_event(
    update: TaskUpdate,
    task_id: str,
    context_id: str,
) -> A2ATaskStatusUpdate:
    """Convert a UES TaskUpdate to A2A TaskStatusUpdateEvent format.

    Maps UES update types to appropriate A2A task states:
    - LOG_ASSESSMENT_COMPLETE → completed (final=True)
    - LOG_TURN_STARTED → input_required (waiting for Purple)
    - All others → working

    Args:
        update: The UES TaskUpdate to convert.
        task_id: The A2A task ID for this assessment.
        context_id: The A2A context ID for grouping related updates.

    Returns:
        An A2ATaskStatusUpdate ready for serialization.
    """
    # Determine A2A state based on update type
    if update.type == TaskUpdateType.LOG_ASSESSMENT_COMPLETE:
        state = "completed"
        final = True
    elif update.type == TaskUpdateType.LOG_TURN_STARTED:
        # Waiting for Purple Agent's response
        state = "input_required"
        final = False
    else:
        state = "working"
        final = False

    # Build metadata with UES-specific information
    metadata: dict[str, object] = {"ues_update_type": update.type.value}
    if update.details:
        metadata.update(update.details)

    return A2ATaskStatusUpdate(
        task_id=task_id,
        context_id=context_id,
        state=state,
        message=update.message,
        timestamp=update.timestamp,
        final=final,
        metadata=metadata,
    )
