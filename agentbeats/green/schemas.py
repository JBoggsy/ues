"""A2A message schemas for Green-Purple agent communication.

This module defines Pydantic models for all A2A messages exchanged between
the Green Agent (UES benchmark) and Purple Agent (participant being evaluated).

Message Flow:
    1. Green → Purple: AssessmentStartMessage (begin assessment)
    2. Green → Purple: TurnStartMessage (after each time advance)
    3. Purple → Green: TurnCompleteMessage (after taking actions)
    4. Green → Purple: AssessmentCompleteMessage (assessment finished)
    5. Purple → Green: EarlyCompletionMessage (optional early exit)

Results:
    After assessment, Green produces an AssessmentResult artifact containing:
    - Assessment metadata (id, scenario, participant, status, timing)
    - Scores (overall, by dimension, by criterion)
    - Action log (all actions taken by Purple agent)
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, computed_field


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


# =============================================================================
# Results Artifact (Assessment Output)
# =============================================================================


class EvaluationDimension(str, Enum):
    """Fixed evaluation dimensions used across all assessments.

    These five dimensions are consistent across all scenarios. Scenario designers
    control dimension weighting by allocating more or fewer points to criteria
    in each dimension.

    Attributes:
        ACCURACY: Correctness of outputs, information quality, factual accuracy.
        INSTRUCTION_FOLLOWING: Adherence to user instructions, constraints, and procedures.
        EFFICIENCY: Resource usage, minimal unnecessary actions, time management.
        SAFETY: Non-harmful behavior, avoids dangerous/inappropriate content.
        POLITENESS: Tone and manner of interactions, professional communication.
    """

    ACCURACY = "accuracy"
    INSTRUCTION_FOLLOWING = "instruction_following"
    EFFICIENCY = "efficiency"
    SAFETY = "safety"
    POLITENESS = "politeness"


class ScoreSummary(BaseModel):
    """Summary of points earned vs. points possible.

    Used for both overall scores and dimension-level scores.

    Attributes:
        score: Points earned.
        max_score: Maximum points possible.
    """

    score: int = Field(..., ge=0, description="Points earned")
    max_score: int = Field(..., ge=0, description="Maximum points possible")

    @computed_field
    @property
    def percentage(self) -> float:
        """Calculate score as a percentage (0.0 to 100.0)."""
        if self.max_score == 0:
            return 100.0 if self.score == 0 else 0.0
        return round((self.score / self.max_score) * 100, 1)


class CriterionResult(BaseModel):
    """Result for a single evaluation criterion from the scenario rubric.

    Each criterion belongs to exactly one dimension and contributes its
    score to that dimension's total.

    Attributes:
        id: Unique identifier from the rubric (e.g., "hourly_queries").
        name: Human-readable name (e.g., "Hourly Email Queries").
        dimension: Which evaluation dimension this criterion belongs to.
        score: Points earned (0 to max_score).
        max_score: Maximum points possible for this criterion.
        explanation: Justification for the score assigned.
    """

    id: str = Field(..., description="Unique identifier from rubric")
    name: str = Field(..., description="Human-readable criterion name")
    dimension: EvaluationDimension = Field(..., description="Evaluation dimension")
    score: int = Field(..., ge=0, description="Points earned")
    max_score: int = Field(..., ge=0, description="Maximum points possible")
    explanation: str = Field(..., description="Justification for score")


class Scores(BaseModel):
    """Complete scoring breakdown for an assessment.

    Implements pyramid scoring: criteria → dimensions → overall.
    Dimension scores are computed as the sum of criteria scores
    within that dimension. Overall score is the sum of all dimension scores.

    Attributes:
        overall: Total score across all dimensions.
        dimensions: Score breakdown by evaluation dimension.
    """

    overall: ScoreSummary = Field(..., description="Total score across all dimensions")
    dimensions: dict[EvaluationDimension, ScoreSummary] = Field(
        ...,
        description="Score breakdown by evaluation dimension",
    )

    @classmethod
    def from_criteria(cls, criteria_results: list[CriterionResult]) -> "Scores":
        """Compute scores from a list of criterion results.

        Args:
            criteria_results: List of scored criteria from the evaluation.

        Returns:
            Scores object with computed dimension and overall scores.
        """
        # Initialize dimension accumulators
        dimension_scores: dict[EvaluationDimension, dict[str, int]] = {
            dim: {"score": 0, "max_score": 0} for dim in EvaluationDimension
        }

        # Accumulate scores by dimension
        for criterion in criteria_results:
            dimension_scores[criterion.dimension]["score"] += criterion.score
            dimension_scores[criterion.dimension]["max_score"] += criterion.max_score

        # Build dimension summaries
        dimensions = {
            dim: ScoreSummary(score=acc["score"], max_score=acc["max_score"])
            for dim, acc in dimension_scores.items()
        }

        # Compute overall
        total_score = sum(acc["score"] for acc in dimension_scores.values())
        total_max = sum(acc["max_score"] for acc in dimension_scores.values())

        return cls(
            overall=ScoreSummary(score=total_score, max_score=total_max),
            dimensions=dimensions,
        )


class ActionLogEntry(BaseModel):
    """Record of a single action taken by the Purple Agent.

    Captures what the agent did, when, and whether it succeeded.
    Used for debugging, analysis, and potential scoring.

    Attributes:
        turn: Which turn this action occurred in (1-indexed).
        timestamp: Simulator time when the action was taken.
        action: Action identifier (e.g., "email.query", "chat.send").
        parameters: Parameters passed to the action.
        success: Whether the action completed successfully.
    """

    turn: int = Field(..., ge=1, description="Turn number (1-indexed)")
    timestamp: datetime = Field(..., description="Simulator time of action")
    action: str = Field(..., description="Action identifier (e.g., 'email.query')")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters passed to the action",
    )
    success: bool = Field(..., description="Whether action completed successfully")


class AssessmentStatus(str, Enum):
    """Final status of an assessment.

    Attributes:
        COMPLETED: Assessment finished normally (scenario complete or early completion).
        TIMEOUT: Assessment exceeded time limit.
        ERROR: Assessment failed due to an error.
    """

    COMPLETED = "completed"
    TIMEOUT = "timeout"
    ERROR = "error"


class AssessmentResult(BaseModel):
    """Complete results artifact for an assessment.

    This is the primary output of the Green Agent after evaluating a Purple Agent.
    Contains all metadata, scores, and logs needed to understand agent performance.

    Attributes:
        assessment_id: Unique identifier for this assessment run.
        scenario_id: ID of the scenario that was evaluated.
        participant: Identifier for the Purple Agent being evaluated.
        status: Final status of the assessment.
        duration_seconds: Wall-clock time taken for the assessment.
        turns_taken: Number of turns completed.
        actions_taken: Total number of actions the agent performed.
        scores: Complete scoring breakdown (overall, dimensions, criteria implied).
        criteria_results: Detailed results for each rubric criterion.
        action_log: Chronological log of all actions taken.
    """

    assessment_id: str = Field(..., description="Unique assessment identifier")
    scenario_id: str = Field(..., description="Scenario that was evaluated")
    participant: str = Field(..., description="Purple Agent identifier")
    status: AssessmentStatus = Field(..., description="Final assessment status")
    duration_seconds: float = Field(
        ...,
        ge=0,
        description="Wall-clock time for assessment",
    )
    turns_taken: int = Field(..., ge=0, description="Number of turns completed")
    actions_taken: int = Field(..., ge=0, description="Total actions performed")
    scores: Scores = Field(..., description="Complete scoring breakdown")
    criteria_results: list[CriterionResult] = Field(
        ...,
        description="Detailed results for each rubric criterion",
    )
    action_log: list[ActionLogEntry] = Field(
        default_factory=list,
        description="Chronological log of all actions",
    )
