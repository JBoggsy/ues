"""A2A message schemas for Green-Purple agent communication.

This module defines Pydantic models for all A2A messages exchanged between
the Green Agent (UES benchmark) and Purple Agent (participant being evaluated).

Message Flow:
    1. Green → Purple: AssessmentStartMessage (begin assessment)
    2. Green → Purple: TurnStartMessage (after each time advance)
    3. Purple → Green: TurnCompleteMessage (after taking actions)
    4. Green → Purple: AssessmentCompleteMessage (assessment finished)
    5. Purple → Green: EarlyCompletionMessage (optional early exit)
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# =============================================================================
# Initial State Summary
# =============================================================================


class ModalityCounts(BaseModel):
    """Summary counts for a single modality.

    Attributes:
        total: Total number of items in this modality.
        unread: Number of unread items (for email, sms, chat).
        events_today: Number of events scheduled for today (for calendar).
    """

    total: int = Field(..., ge=0, description="Total number of items")
    unread: int | None = Field(
        default=None,
        ge=0,
        description="Number of unread items (email, sms, chat)",
    )
    events_today: int | None = Field(
        default=None,
        ge=0,
        description="Number of events scheduled for today (calendar)",
    )


class InitialStateSummary(BaseModel):
    """Summary of the initial environment state by modality.

    Provides high-level counts so Purple Agent knows what to expect.
    Agent should query UES API for full details.

    Attributes:
        email: Email modality counts (total, unread).
        calendar: Calendar modality counts (total, events_today).
        sms: SMS modality counts (total, unread).
        chat: Chat modality counts (total, unread).
    """

    email: ModalityCounts | None = Field(default=None, description="Email state summary")
    calendar: ModalityCounts | None = Field(default=None, description="Calendar state summary")
    sms: ModalityCounts | None = Field(default=None, description="SMS state summary")
    chat: ModalityCounts | None = Field(default=None, description="Chat state summary")


# =============================================================================
# Green → Purple Messages
# =============================================================================

# Fixed instructions sent to Purple Agent in every assessment.
# Directs them to check the chat modality for user-provided scenario instructions.
DEFAULT_ASSESSMENT_INSTRUCTIONS: str = (
    "You are a personal assistant AI being evaluated on your ability to help a user. "
    "Your instructions for this assessment have been provided by the user via the chat modality. "
    "Query the chat state (GET /chat/state) to find the most recent message from the user "
    "and follow the instructions provided there. The message will contain your goals, "
    "constraints, and any other relevant context for this assessment."
)


class AssessmentStartMessage(BaseModel):
    """Message sent from Green to Purple to begin an assessment.

    Contains all information Purple Agent needs to connect to UES
    and begin the assessment. The actual scenario instructions (goals,
    constraints, context) are delivered via the chat modality - the agent
    should query /chat/state to find the user's instructions.

    Attributes:
        ues_url: Base URL of the UES REST API.
        api_key: User-level API key for UES authentication.
        assessment_instructions: Fixed instructions telling agent to check chat for user prompt.
        current_time: Current simulator time at assessment start.
        initial_state_summary: Counts of items in each modality.
    """

    ues_url: str = Field(
        ...,
        description="Base URL of the UES REST API",
        examples=["http://localhost:8000"],
    )
    api_key: str = Field(
        ...,
        description="User-level API key for UES authentication",
    )
    assessment_instructions: str = Field(
        default=DEFAULT_ASSESSMENT_INSTRUCTIONS,
        description="Fixed instructions directing agent to check chat modality for user prompt",
    )
    current_time: datetime = Field(
        ...,
        description="Current simulator time at assessment start",
    )
    initial_state_summary: InitialStateSummary = Field(
        ...,
        description="Summary counts of items in each modality",
    )


class TurnStartMessage(BaseModel):
    """Message sent from Green to Purple at the start of each turn.

    Notifies Purple that time has advanced and events may have occurred.
    Purple should query UES state to see what changed.

    Attributes:
        current_time: Current simulator time after advancement.
        events_processed: Number of scheduled events that fired during time advance.
    """

    current_time: datetime = Field(
        ...,
        description="Current simulator time after advancement",
    )
    events_processed: int = Field(
        ...,
        ge=0,
        description="Number of scheduled events that fired during time advance",
    )


class AssessmentCompleteReason(str, Enum):
    """Reasons why an assessment ended."""

    SCENARIO_COMPLETE = "scenario_complete"
    EARLY_COMPLETION = "early_completion"
    TIMEOUT = "timeout"
    ERROR = "error"


class AssessmentCompleteMessage(BaseModel):
    """Message sent from Green to Purple when the assessment ends.

    Attributes:
        reason: Why the assessment ended.
        message: Optional human-readable explanation.
    """

    reason: AssessmentCompleteReason = Field(
        ...,
        description="Reason for assessment completion",
    )
    message: str | None = Field(
        default=None,
        description="Optional human-readable explanation",
    )


# =============================================================================
# Purple → Green Messages
# =============================================================================


class TurnCompleteMessage(BaseModel):
    """Message sent from Purple to Green after completing a turn.

    Signals that Purple has finished taking actions and is ready
    for time to advance.

    Attributes:
        actions_taken: Number of actions the agent performed this turn.
        notes: Optional reasoning or comments (logged, may affect scoring).
        time_step: How much to advance simulator time (ISO 8601 duration).
    """

    actions_taken: int = Field(
        ...,
        ge=0,
        description="Number of actions the agent performed this turn",
    )
    notes: str | None = Field(
        default=None,
        description="Optional reasoning or comments for logging and potential scoring",
        examples=["Replied to 2 urgent emails, archived 1 spam thread"],
    )
    time_step: timedelta | None = Field(
        default=None,
        description="How much to advance simulator time; if omitted, Green uses default",
        examples=[timedelta(hours=1), timedelta(minutes=30)],
    )


class EarlyCompletionMessage(BaseModel):
    """Message sent from Purple to Green to signal early completion.

    Purple Agent can send this when it believes all goals are achieved
    before the scenario naturally ends.

    Attributes:
        reason: Optional explanation for early completion.
    """

    reason: str | None = Field(
        default=None,
        description="Optional explanation for early completion",
        examples=["All goals achieved - inbox empty, all urgent emails replied"],
    )


# =============================================================================
# Message Type Literals (for type discrimination)
# =============================================================================

# Type aliases for message discrimination in handlers
GreenToPurpleMessage = AssessmentStartMessage | TurnStartMessage | AssessmentCompleteMessage
PurpleToGreenMessage = TurnCompleteMessage | EarlyCompletionMessage


# =============================================================================
# Task Updates (Streaming Logs)
# =============================================================================


class TaskUpdateType(str, Enum):
    """Types of task updates emitted during assessment.

    These are log events streamed to the AgentBeats platform for observability.
    Prefixed with 'LOG_' to distinguish from A2A messages (e.g., LOG_TURN_STARTED
    is a log event, whereas TurnStartMessage is the actual A2A message).

    Attributes:
        LOG_ASSESSMENT_STARTED: Assessment has begun.
        LOG_SCENARIO_LOADED: Scenario imported into UES.
        LOG_TURN_STARTED: New turn began (after sending turn_start to Purple).
        LOG_TURN_COMPLETED: Turn finished (after receiving turn_complete from Purple).
        LOG_SIMULATION_ADVANCED: Simulation time progressed.
        LOG_ASSESSMENT_COMPLETE: Assessment ended.
    """

    LOG_ASSESSMENT_STARTED = "log_assessment_started"
    LOG_SCENARIO_LOADED = "log_scenario_loaded"
    LOG_TURN_STARTED = "log_turn_started"
    LOG_TURN_COMPLETED = "log_turn_completed"
    LOG_SIMULATION_ADVANCED = "log_simulation_advanced"
    LOG_ASSESSMENT_COMPLETE = "log_assessment_complete"


class TaskUpdate(BaseModel):
    """A task update emitted during assessment execution.

    Task updates are streamed to the AgentBeats platform for real-time
    observability. They allow operators, evaluators, and spectators to
    watch the assessment unfold.

    Attributes:
        type: The category of update (log event type).
        timestamp: When this update was generated (wall-clock time).
        message: Human-readable description of what happened.
        details: Structured data specific to the update type.

    Example:
        >>> update = TaskUpdate(
        ...     type=TaskUpdateType.LOG_TURN_COMPLETED,
        ...     timestamp=datetime.now(timezone.utc),
        ...     message="Turn 3 completed",
        ...     details={"turn": 3, "actions_taken": 2},
        ... )
    """

    type: TaskUpdateType = Field(
        ...,
        description="The category of task update (log event type)",
    )
    timestamp: datetime = Field(
        ...,
        description="When this update was generated (wall-clock time)",
    )
    message: str = Field(
        ...,
        description="Human-readable description of what happened",
    )
    details: dict[str, object] | None = Field(
        default=None,
        description="Structured data specific to the update type",
    )
