"""Assessment session management for AgentBeats Green Agent.

This module provides the AssessmentSession class which acts as a state container
for a running assessment, storing all context needed for the turn loop, action
tracking, and final evaluation.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, Field


class ActionLogEntry(BaseModel):
    """Record of a single action taken by the Purple agent.
    
    Actions are derived from events created with the Purple agent's API key.
    
    Attributes:
        turn: The turn number when this action was taken.
        event_id: The event ID in the UES event queue.
        modality: The modality affected (email, sms, calendar, etc.).
        action_type: The specific action (send, receive, create, etc.).
        timestamp: When the action was taken (simulator time).
        summary: Human-readable description of the action.
        details: Full event data for detailed analysis.
    """
    
    turn: int = Field(..., ge=1, description="Turn number when action was taken")
    event_id: str = Field(..., description="Event ID in UES event queue")
    modality: str = Field(..., description="Modality affected by this action")
    action_type: str = Field(..., description="Type of action taken")
    timestamp: datetime = Field(..., description="Simulator time when action occurred")
    summary: str = Field(..., description="Human-readable action summary")
    details: dict[str, Any] | None = Field(
        default=None, description="Full event data for analysis"
    )


@dataclass
class AssessmentSession:
    """State container for a running assessment.
    
    This class holds all the context needed during an assessment, including:
    - Identity information (assessment ID, scenario ID, participant URL)
    - API keys for proctor (Green) and user (Purple) access levels
    - Turn tracking and timing state
    - Action log of all Purple agent actions
    - Configuration options
    
    The session is created during setup and passed through the turn loop,
    accumulating state as the assessment progresses.
    
    Attributes:
        assessment_id: Unique identifier for this assessment run.
        scenario_id: ID of the scenario being evaluated.
        participant_url: A2A URL of the Purple agent being assessed.
        proctor_key: Proctor-level API key for Green agent (time control, resets).
        user_key: User-level API key for Purple agent (limited permissions).
        purple_agent_id: Agent ID used for event attribution queries.
        current_turn: Current turn number (1-indexed).
        start_time_wall: Wall-clock time when assessment started.
        last_turn_end_time: Simulator time at end of last turn (for action queries).
        action_log: List of all actions taken by Purple agent.
        total_actions: Running count of total actions reported by Purple.
        verbose_updates: Whether to emit detailed progress updates.
        seed: Random seed for reproducibility (affects response generators).
        default_time_step: Default time advance between turns.
        turn_timeout_seconds: Maximum seconds to wait for Purple's turn_complete.
    """
    
    # Identity
    assessment_id: str
    scenario_id: str
    participant_url: str
    
    # API Keys
    proctor_key: str
    user_key: str
    purple_agent_id: str
    
    # Turn State
    current_turn: int = 0
    start_time_wall: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_turn_end_time: datetime | None = None
    
    # Action Tracking
    action_log: list[ActionLogEntry] = field(default_factory=list)
    total_actions: int = 0
    
    # Configuration
    verbose_updates: bool = True
    seed: int | None = None
    default_time_step: timedelta = field(
        default_factory=lambda: timedelta(hours=1)
    )
    turn_timeout_seconds: float = 300.0
    
    def record_action(self, entry: ActionLogEntry) -> None:
        """Add an action to the log.
        
        Args:
            entry: The action log entry to record.
        """
        self.action_log.append(entry)
    
    def record_actions(self, entries: list[ActionLogEntry]) -> None:
        """Add multiple actions to the log.
        
        Args:
            entries: List of action log entries to record.
        """
        self.action_log.extend(entries)
    
    def increment_turn(self) -> int:
        """Advance to the next turn and return the new turn number.
        
        Returns:
            The new current turn number.
        """
        self.current_turn += 1
        return self.current_turn
    
    def update_turn_end_time(self, simulator_time: datetime) -> None:
        """Update the last turn end time for action tracking.
        
        Args:
            simulator_time: The simulator time at end of turn.
        """
        self.last_turn_end_time = simulator_time
    
    @property
    def elapsed_wall_time(self) -> timedelta:
        """Calculate elapsed wall-clock time since assessment start.
        
        Returns:
            Timedelta of elapsed time.
        """
        return datetime.now(timezone.utc) - self.start_time_wall
    
    @property
    def action_count(self) -> int:
        """Get the number of recorded actions.
        
        Returns:
            Number of entries in the action log.
        """
        return len(self.action_log)
