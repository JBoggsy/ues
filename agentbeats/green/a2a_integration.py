"""A2A protocol integration for AgentBeats assessments.

This module provides utilities for integrating with the A2A protocol,
including message serialization, response parsing, and result artifact
production.

## Message Serialization

Green Agent sends Pydantic models to Purple Agent as JSON. This module
provides utilities to serialize these messages correctly:

```python
from agentbeats.green.a2a_integration import serialize_message

message = AssessmentStartMessage(
    ues_url="http://localhost:8000",
    api_key="user-key-123",
    current_time=datetime.now(timezone.utc),
)
json_str = serialize_message(message)
```

## Response Parsing

Purple Agent responses are parsed into the appropriate message type:

```python
from agentbeats.green.a2a_integration import parse_purple_response

response = '{"actions_taken": 3, "notes": "Replied to emails"}'
message = parse_purple_response(response)
# Returns TurnCompleteMessage or EarlyCompletionMessage
```

## Result Artifact Production

After evaluation, produce the final AssessmentResult artifact:

```python
from agentbeats.green.a2a_integration import produce_result_artifact

result = produce_result_artifact(
    session=session,
    reason=AssessmentCompleteReason.SCENARIO_COMPLETE,
    criteria_results=criteria_results,
)
```

## Task Updates Integration

The module provides helpers for emitting task updates at key lifecycle
points, integrating with the existing TaskUpdateEmitter:

```python
from agentbeats.green.a2a_integration import AssessmentUpdateEmitter

emitter = AssessmentUpdateEmitter(task_emitter, assessment_id, context_id)
await emitter.emit_assessment_started(session, scenario_data)
await emitter.emit_turn_started(session)
await emitter.emit_turn_completed(session, turn_result)
await emitter.emit_assessment_complete(session, reason, result)
```
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel

from agentbeats.green.schemas import (
    AssessmentCompleteMessage,
    AssessmentCompleteReason,
    AssessmentResult,
    AssessmentStartMessage,
    AssessmentStatus,
    CriterionResult,
    EarlyCompletionMessage,
    Scores,
    TaskUpdate,
    TaskUpdateType,
    TurnCompleteMessage,
    TurnStartMessage,
)
from agentbeats.green.session import AssessmentSession
from agentbeats.green.updates import (
    TaskUpdateEmitter,
    create_assessment_complete_update,
    create_assessment_started_update,
    create_scenario_loaded_update,
    create_simulation_advanced_update,
    create_turn_completed_update,
    create_turn_started_update,
    task_update_to_a2a_event,
)


# =============================================================================
# Message Serialization
# =============================================================================


def serialize_message(message: BaseModel) -> str:
    """Serialize a Pydantic model for A2A transmission.

    Converts Pydantic models to JSON strings suitable for sending
    via A2A protocol. Handles datetime serialization and timedelta
    conversion to ISO 8601 duration format.

    Args:
        message: A Pydantic model (AssessmentStartMessage, TurnStartMessage, etc.)

    Returns:
        JSON string representation of the message.

    Example:
        >>> msg = TurnStartMessage(
        ...     current_time=datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
        ...     events_processed=3,
        ... )
        >>> json_str = serialize_message(msg)
        >>> print(json_str)
        '{"current_time":"2024-06-15T10:00:00Z","events_processed":3}'
    """
    return message.model_dump_json()


# =============================================================================
# Response Parsing
# =============================================================================


class MessageParseError(Exception):
    """Raised when a Purple agent response cannot be parsed.

    Attributes:
        raw_response: The original response string that failed to parse.
        reason: Description of why parsing failed.
    """

    def __init__(self, raw_response: str, reason: str) -> None:
        self.raw_response = raw_response
        self.reason = reason
        super().__init__(f"Failed to parse Purple response: {reason}")


def parse_purple_response(
    response: str,
) -> TurnCompleteMessage | EarlyCompletionMessage:
    """Parse Purple agent's response into the appropriate message type.

    Distinguishes between TurnCompleteMessage and EarlyCompletionMessage
    based on the presence of certain fields:
    - TurnCompleteMessage: Has `actions_taken` field
    - EarlyCompletionMessage: Has only `reason` field (no `actions_taken`)

    Args:
        response: JSON string response from Purple agent.

    Returns:
        TurnCompleteMessage or EarlyCompletionMessage.

    Raises:
        MessageParseError: If the response cannot be parsed as either message type.

    Example:
        >>> # Parse a turn complete message
        >>> response = '{"actions_taken": 3, "notes": "Replied to emails"}'
        >>> msg = parse_purple_response(response)
        >>> isinstance(msg, TurnCompleteMessage)
        True
        >>> msg.actions_taken
        3

        >>> # Parse an early completion message
        >>> response = '{"reason": "All goals achieved"}'
        >>> msg = parse_purple_response(response)
        >>> isinstance(msg, EarlyCompletionMessage)
        True
    """
    try:
        data = json.loads(response)
    except json.JSONDecodeError as e:
        raise MessageParseError(response, f"Invalid JSON: {e}")

    if not isinstance(data, dict):
        raise MessageParseError(response, f"Expected object, got {type(data).__name__}")

    # Distinguish message types based on fields present
    # TurnCompleteMessage always has actions_taken
    # EarlyCompletionMessage has reason but NOT actions_taken
    if "actions_taken" in data:
        try:
            return TurnCompleteMessage.model_validate(data)
        except Exception as e:
            raise MessageParseError(response, f"Invalid TurnCompleteMessage: {e}")
    elif "reason" in data or len(data) == 0:
        # EarlyCompletionMessage (reason is optional, so empty dict is valid)
        try:
            return EarlyCompletionMessage.model_validate(data)
        except Exception as e:
            raise MessageParseError(response, f"Invalid EarlyCompletionMessage: {e}")
    else:
        raise MessageParseError(
            response,
            "Cannot determine message type: missing 'actions_taken' for "
            "TurnCompleteMessage or 'reason' for EarlyCompletionMessage",
        )


def parse_time_step(time_step: timedelta | str | None) -> timedelta | None:
    """Parse a time step value into a timedelta.

    Handles both timedelta objects and ISO 8601 duration strings.

    Args:
        time_step: Timedelta, ISO 8601 duration string (e.g., "PT1H"), or None.

    Returns:
        Timedelta object or None.

    Example:
        >>> parse_time_step(timedelta(hours=1))
        datetime.timedelta(seconds=3600)
        >>> parse_time_step("PT2H30M")
        datetime.timedelta(seconds=9000)
        >>> parse_time_step(None)
        None
    """
    if time_step is None:
        return None

    if isinstance(time_step, timedelta):
        return time_step

    # Parse ISO 8601 duration string (basic support)
    # Format: PT[nH][nM][nS] (e.g., PT1H30M, PT2H, PT30M)
    if isinstance(time_step, str) and time_step.startswith("PT"):
        try:
            duration_str = time_step[2:]  # Remove "PT" prefix
            hours = 0
            minutes = 0
            seconds = 0

            # Parse hours
            if "H" in duration_str:
                h_idx = duration_str.index("H")
                hours = int(duration_str[:h_idx])
                duration_str = duration_str[h_idx + 1 :]

            # Parse minutes
            if "M" in duration_str:
                m_idx = duration_str.index("M")
                minutes = int(duration_str[:m_idx])
                duration_str = duration_str[m_idx + 1 :]

            # Parse seconds
            if "S" in duration_str:
                s_idx = duration_str.index("S")
                seconds = int(duration_str[:s_idx])

            return timedelta(hours=hours, minutes=minutes, seconds=seconds)
        except (ValueError, IndexError):
            pass

    return None


# =============================================================================
# Turn Result Extraction
# =============================================================================


class TurnResult:
    """Parsed result from Purple agent's turn response.

    This class provides a unified interface for extracting information
    from either TurnCompleteMessage or EarlyCompletionMessage.

    Attributes:
        is_early_completion: True if Purple requested early termination.
        actions_taken: Number of actions taken (0 for early completion).
        notes: Optional notes from Purple (turn complete only).
        time_step: Requested time step (turn complete only).
        early_completion_reason: Reason for early termination (if applicable).
    """

    def __init__(
        self,
        is_early_completion: bool = False,
        actions_taken: int = 0,
        notes: str | None = None,
        time_step: timedelta | None = None,
        early_completion_reason: str | None = None,
    ) -> None:
        self.is_early_completion = is_early_completion
        self.actions_taken = actions_taken
        self.notes = notes
        self.time_step = time_step
        self.early_completion_reason = early_completion_reason

    @classmethod
    def from_message(
        cls,
        message: TurnCompleteMessage | EarlyCompletionMessage,
    ) -> "TurnResult":
        """Create a TurnResult from a parsed message.

        Args:
            message: Parsed TurnCompleteMessage or EarlyCompletionMessage.

        Returns:
            TurnResult with extracted values.
        """
        if isinstance(message, EarlyCompletionMessage):
            return cls(
                is_early_completion=True,
                actions_taken=0,
                early_completion_reason=message.reason,
            )
        else:
            return cls(
                is_early_completion=False,
                actions_taken=message.actions_taken,
                notes=message.notes,
                time_step=message.time_step,
            )

    @classmethod
    def from_response(cls, response: str) -> "TurnResult":
        """Create a TurnResult from a raw response string.

        Convenience method that combines parsing and extraction.

        Args:
            response: Raw JSON response from Purple agent.

        Returns:
            TurnResult with extracted values.

        Raises:
            MessageParseError: If the response cannot be parsed.
        """
        message = parse_purple_response(response)
        return cls.from_message(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for legacy compatibility.

        Returns:
            Dictionary with turn result fields.
        """
        return {
            "early_completion": self.is_early_completion,
            "actions_taken": self.actions_taken,
            "notes": self.notes,
            "time_step": self.time_step,
            "reason": self.early_completion_reason,
        }


# =============================================================================
# Result Artifact Production
# =============================================================================


def reason_to_status(reason: AssessmentCompleteReason) -> AssessmentStatus:
    """Convert completion reason to assessment status.

    Args:
        reason: Why the assessment ended.

    Returns:
        Corresponding AssessmentStatus.
    """
    if reason == AssessmentCompleteReason.TIMEOUT:
        return AssessmentStatus.TIMEOUT
    elif reason == AssessmentCompleteReason.ERROR:
        return AssessmentStatus.ERROR
    else:
        # SCENARIO_COMPLETE and EARLY_COMPLETION both map to COMPLETED
        return AssessmentStatus.COMPLETED


def produce_result_artifact(
    session: AssessmentSession,
    reason: AssessmentCompleteReason,
    criteria_results: list[CriterionResult],
) -> AssessmentResult:
    """Produce the final AssessmentResult artifact.

    Computes scores from criteria results and assembles all assessment
    metadata into the final result artifact.

    Args:
        session: The completed assessment session.
        reason: Why the assessment ended.
        criteria_results: Detailed results from evaluation.

    Returns:
        Complete AssessmentResult artifact.

    Example:
        >>> result = produce_result_artifact(
        ...     session=session,
        ...     reason=AssessmentCompleteReason.SCENARIO_COMPLETE,
        ...     criteria_results=criteria_results,
        ... )
        >>> print(f"Score: {result.scores.overall.percentage}%")
        Score: 85.0%
    """
    # Compute scores from criteria
    scores = Scores.from_criteria(criteria_results)

    # Calculate duration
    duration = (datetime.now(timezone.utc) - session.start_time_wall).total_seconds()

    # Convert action log entries from session format to schema format
    from agentbeats.green.schemas import ActionLogEntry as SchemaActionLogEntry

    action_log_entries = []
    for entry in session.action_log:
        action_log_entries.append(
            SchemaActionLogEntry(
                turn=entry.turn,
                action=f"{entry.modality}.{entry.action_type}",
                timestamp=entry.timestamp,
                parameters=entry.details,
                success=True,  # Actions in log are successful by definition
            )
        )

    return AssessmentResult(
        assessment_id=session.assessment_id,
        scenario_id=session.scenario_id,
        participant=session.participant_url,
        status=reason_to_status(reason),
        duration_seconds=duration,
        turns_taken=session.current_turn,
        actions_taken=session.action_count,
        scores=scores,
        criteria_results=criteria_results,
        action_log=action_log_entries,
    )


# =============================================================================
# Task Updates Integration
# =============================================================================


class AssessmentUpdateEmitter:
    """Emits task updates at key assessment lifecycle points.

    This class wraps TaskUpdateEmitter and provides convenient methods
    for emitting updates at specific assessment events, handling the
    conversion to A2A format when needed.

    Example:
        >>> emitter = AssessmentUpdateEmitter(
        ...     task_emitter=task_emitter,
        ...     assessment_id="assess-123",
        ...     context_id="ctx-456",
        ... )
        >>> await emitter.emit_assessment_started(session, scenario_data)
        >>> await emitter.emit_turn_started(session)
        >>> await emitter.emit_turn_completed(session, turn_result)
        >>> await emitter.emit_assessment_complete(session, reason, result)
    """

    def __init__(
        self,
        task_emitter: TaskUpdateEmitter,
        assessment_id: str,
        context_id: str,
    ) -> None:
        """Initialize the assessment update emitter.

        Args:
            task_emitter: Underlying TaskUpdateEmitter for streaming.
            assessment_id: Unique assessment identifier.
            context_id: A2A context ID for grouping updates.
        """
        self._emitter = task_emitter
        self._assessment_id = assessment_id
        self._context_id = context_id

    async def emit_assessment_started(
        self,
        session: AssessmentSession,
        user_prompt: str,
    ) -> None:
        """Emit assessment started update.

        Args:
            session: The assessment session.
            user_prompt: The user prompt from the scenario.
        """
        update = create_assessment_started_update(
            assessment_id=session.assessment_id,
            scenario_id=session.scenario_id,
            participant=session.participant_url,
            user_prompt=user_prompt,
            verbose_updates=session.verbose_updates,
        )
        await self._emitter.emit(update)

    async def emit_scenario_loaded(
        self,
        session: AssessmentSession,
        initial_state: dict[str, Any],
    ) -> None:
        """Emit scenario loaded update.

        Args:
            session: The assessment session.
            initial_state: Summary of initial state by modality.
        """
        update = create_scenario_loaded_update(
            scenario_id=session.scenario_id,
            initial_state=initial_state,
        )
        await self._emitter.emit(update)

    async def emit_turn_started(
        self,
        session: AssessmentSession,
        current_time: datetime,
    ) -> None:
        """Emit turn started update.

        Args:
            session: The assessment session.
            current_time: Current simulator time.
        """
        update = create_turn_started_update(
            turn=session.current_turn,
            current_time=current_time,
        )
        await self._emitter.emit(update)

    async def emit_turn_completed(
        self,
        session: AssessmentSession,
        turn_result: TurnResult,
    ) -> None:
        """Emit turn completed update.

        Args:
            session: The assessment session.
            turn_result: Parsed result from Purple's response.
        """
        update = create_turn_completed_update(
            turn=session.current_turn,
            actions_taken=turn_result.actions_taken,
            purple_notes=turn_result.notes,
        )
        await self._emitter.emit(update)

    async def emit_simulation_advanced(
        self,
        from_time: datetime,
        to_time: datetime,
        events_processed: int,
    ) -> None:
        """Emit simulation advanced update.

        Args:
            from_time: Simulator time before advancement.
            to_time: Simulator time after advancement.
            events_processed: Number of events that fired.
        """
        update = create_simulation_advanced_update(
            from_time=from_time,
            to_time=to_time,
            events_processed=events_processed,
        )
        await self._emitter.emit(update)

    async def emit_assessment_complete(
        self,
        session: AssessmentSession,
        reason: AssessmentCompleteReason,
        result: AssessmentResult | None = None,
    ) -> None:
        """Emit assessment complete update.

        Args:
            session: The assessment session.
            reason: Why the assessment ended.
            result: Optional final result artifact (includes scores).
        """
        score_dict = None
        if result:
            score_dict = {
                "overall": {
                    "score": result.scores.overall.score,
                    "max_score": result.scores.overall.max_score,
                    "percentage": result.scores.overall.percentage,
                },
            }

        update = create_assessment_complete_update(
            reason=reason.value,
            turns_taken=session.current_turn,
            actions_taken=session.action_count,
            score=score_dict,
        )
        await self._emitter.emit(update)

    def get_a2a_event(self, update: TaskUpdate) -> dict[str, Any]:
        """Convert a task update to A2A event format.

        Useful when directly sending updates via A2A protocol.

        Args:
            update: The task update to convert.

        Returns:
            Dictionary in A2A TaskStatusUpdateEvent format.
        """
        a2a_event = task_update_to_a2a_event(
            update=update,
            task_id=self._assessment_id,
            context_id=self._context_id,
        )
        return a2a_event.model_dump()
