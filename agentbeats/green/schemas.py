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
# Scenario Description
# =============================================================================


class ScenarioDescription(BaseModel):
    """Description of the assessment scenario provided to the Purple Agent.

    Attributes:
        description: Natural language overview of the scenario context.
        goals: List of specific, measurable objectives the agent should achieve.
        constraints: Optional rules or restrictions the agent must follow.
    """

    description: str = Field(
        ...,
        description="Natural language overview of the scenario context",
        examples=["You are a personal assistant managing a busy professional's inbox..."],
    )
    goals: list[str] = Field(
        ...,
        description="Specific measurable objectives the agent should achieve",
        examples=[["Reply to urgent emails", "Archive completed threads"]],
    )
    constraints: list[str] | None = Field(
        default=None,
        description="Optional rules or restrictions the agent must follow",
        examples=[["Do not delete any emails", "Do not send emails to external domains"]],
    )


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


class AssessmentStartMessage(BaseModel):
    """Message sent from Green to Purple to begin an assessment.

    Contains all information Purple Agent needs to connect to UES
    and understand the assessment objectives.

    Attributes:
        ues_url: Base URL of the UES REST API.
        api_key: User-level API key for UES authentication.
        scenario: Description of goals and constraints.
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
    scenario: ScenarioDescription = Field(
        ...,
        description="Scenario description with goals and constraints",
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
