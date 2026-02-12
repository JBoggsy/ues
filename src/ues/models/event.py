"""Simulator event model."""

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

if TYPE_CHECKING:
    from ues.models.base_input import ModalityInput
    from ues.models.environment import Environment
    from ues.models.undo import UndoEntry


class EventStatus(str, Enum):
    """Status of a simulator event."""

    PENDING = "pending"
    EXECUTING = "executing"
    EXECUTED = "executed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class SimulatorEvent(BaseModel):
    """Represents a scheduled action in the simulation timeline.

    Events occur at specific simulator times and carry ModalityInput
    payloads that modify corresponding ModalityState instances.

    Events are self-contained actions that know how to execute themselves
    by applying their input payload to the appropriate modality state.

    Args:
        event_id: Unique identifier for this event.
        scheduled_time: When this event should execute (simulator time).
        modality: Which modality this event affects (e.g., "email", "location").
        data: The ModalityInput payload for this event.
        status: Current execution state of the event.
        created_at: When this event was created (simulator time).
        executed_at: When this event was actually executed (simulator time).
        agent_id: Optional ID of the agent that generated this event.
        priority: Secondary ordering for events at same scheduled_time (higher = first).
        error_message: Error details if status is FAILED.
        metadata: Flexible additional data for extensibility.
    """

    event_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this event",
    )
    scheduled_time: datetime = Field(
        description="When this event should execute (simulator time)"
    )
    modality: str = Field(description="Which modality this event affects")
    data: Any = Field(
        description="The ModalityInput payload for this event"
    )  # Type: ModalityInput, but using Any to avoid circular import issues
    status: EventStatus = Field(
        default=EventStatus.PENDING, description="Current execution state"
    )
    created_at: datetime = Field(description="When this event was created")
    executed_at: Optional[datetime] = Field(
        default=None, description="When this event was actually executed"
    )
    agent_id: Optional[str] = Field(
        default=None, description="ID of agent that generated this event"
    )
    priority: int = Field(
        default=0,
        description="Secondary ordering for events at same time (higher = first)",
    )
    error_message: Optional[str] = Field(
        default=None, description="Error details if status is FAILED"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Flexible additional data"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True, use_enum_values=False)

    @field_validator("scheduled_time", "created_at", "executed_at", mode="before")
    @classmethod
    def validate_timezone_aware(cls, v: datetime | str | None) -> datetime | None:
        """Ensure datetime is timezone-aware, converting naive to UTC if needed."""
        if v is None:
            return None
        if isinstance(v, str):
            v = datetime.fromisoformat(v.replace("Z", "+00:00"))
        if isinstance(v, datetime) and v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v

    @model_validator(mode="before")
    @classmethod
    def deserialize_data_field(cls, values: Any) -> Any:
        """Convert data field from dict to appropriate ModalityInput subclass.

        When deserializing from JSON/dict (e.g., from scenario files), the data
        field will be a plain dict containing a 'modality_type' key. This validator
        uses the registry to instantiate the correct ModalityInput subclass.

        If data is already a ModalityInput instance (normal construction),
        or if it's a dict without 'modality_type' (legacy/test usage),
        this validator passes it through unchanged.

        Args:
            values: The raw input values (dict when deserializing).

        Returns:
            The values with data converted to ModalityInput if needed.
        """
        # Only process dict inputs (deserialization case)
        if not isinstance(values, dict):
            return values

        data = values.get("data")

        # If data is not a dict, nothing to do
        if not isinstance(data, dict):
            return values

        # Only attempt deserialization if data has modality_type field
        # This distinguishes scenario deserialization from legacy/test dict usage
        modality_type = data.get("modality_type")
        if not modality_type:
            return values

        # Import here to avoid circular import at module level
        from ues.models.registry import get_modality_input_class, is_modality_input_registered

        if not is_modality_input_registered(modality_type):
            # Unknown modality - let validation handle the error later
            return values

        # Get the appropriate input class and instantiate
        input_class = get_modality_input_class(modality_type)
        values["data"] = input_class.model_validate(data)

        # Ensure event modality matches data modality_type
        if "modality" not in values or not values["modality"]:
            values["modality"] = modality_type

        return values

    def execute(
        self, environment: "Environment", capture_undo: bool = True
    ) -> Optional["UndoEntry"]:
        """Execute this event by applying its input to the appropriate state.

        This is the core execution method that:
        1. Validates the input
        2. Looks up the correct state from environment
        3. Optionally captures undo data before applying
        4. Applies the input to the state
        5. Updates event status and timing
        6. Returns undo entry if capture_undo is True
        7. Handles errors gracefully

        Args:
            environment: The environment containing modality states.
            capture_undo: Whether to capture undo data (default True).

        Returns:
            UndoEntry if capture_undo is True and execution succeeded, None otherwise.

        Raises:
            ValueError: If modality doesn't exist or input is invalid.
            RuntimeError: If event is already executed or in wrong state.
        """
        # Import here to avoid circular import
        from ues.models.undo import UndoEntry

        if self.status != EventStatus.PENDING:
            raise RuntimeError(
                f"Cannot execute event {self.event_id} with status {self.status}"
            )

        self.status = EventStatus.EXECUTING
        undo_entry: Optional[UndoEntry] = None

        try:
            # Validate input
            self.data.validate_input()

            # Get state
            state = environment.get_state(self.modality)

            # Capture undo data BEFORE applying input
            undo_data: Optional[dict[str, Any]] = None
            if capture_undo:
                undo_data = state.create_undo_data(self.data)

            # Apply input
            state.apply_input(self.data, environment)

            # Success
            self.status = EventStatus.EXECUTED
            self.executed_at = environment.time_state.current_time

            # Create undo entry if we captured undo data
            if undo_data is not None:
                undo_entry = UndoEntry(
                    event_id=self.event_id,
                    modality=self.modality,
                    undo_data=undo_data,
                    executed_at=self.executed_at,
                )

        except Exception as e:
            # Failure - don't re-raise, simulation continues
            self.status = EventStatus.FAILED
            self.error_message = f"{type(e).__name__}: {str(e)}"
            self.executed_at = environment.time_state.current_time

        return undo_entry

    def can_execute(self, current_time: datetime) -> bool:
        """Check if this event is eligible for execution.

        An event can execute if:
        - Status is PENDING
        - scheduled_time <= current_time
        - Input is valid

        Args:
            current_time: Current simulator time.

        Returns:
            True if event can be executed, False otherwise.
        """
        if self.status != EventStatus.PENDING:
            return False

        if self.scheduled_time > current_time:
            return False

        # Check if input is valid
        try:
            self.data.validate_input()
            return True
        except Exception:
            return False

    def validate(self) -> list[str]:
        """Validate event consistency and return any issues.

        Checks:
        - scheduled_time is not in distant past (vs created_at)
        - modality is non-empty and valid format
        - data is compatible with modality
        - status is valid for event age

        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []

        # Check modality is non-empty
        if not self.modality or not self.modality.strip():
            errors.append("Modality cannot be empty")

        # Check scheduled_time vs created_at
        if self.scheduled_time < self.created_at:
            errors.append(
                f"scheduled_time ({self.scheduled_time}) is before created_at ({self.created_at})"
            )

        # Check data modality matches event modality
        if hasattr(self.data, "modality_type") and self.data.modality_type != self.modality:
            errors.append(
                f"Data modality_type ({self.data.modality_type}) doesn't match event modality ({self.modality})"
            )

        # Validate input data
        try:
            self.data.validate_input()
        except Exception as e:
            errors.append(f"Invalid input data: {e}")

        # Check status consistency
        if self.status in (EventStatus.EXECUTED, EventStatus.FAILED) and self.executed_at is None:
            errors.append(f"Event has status {self.status} but executed_at is None")

        if self.status == EventStatus.FAILED and not self.error_message:
            errors.append("Event has status FAILED but no error_message")

        return errors

    def get_summary(self) -> str:
        """Return human-readable summary of this event.

        Format: "[{scheduled_time}] {modality}: {data.get_summary()}"

        Example: "[2024-03-15 14:30] email: Email from boss@company.com: 'Q1 Report Due'"

        Returns:
            Brief description for logging and UI display.
        """
        time_str = self.scheduled_time.strftime("%Y-%m-%d %H:%M:%S")
        data_summary = self.data.get_summary()
        return f"[{time_str}] {self.modality}: {data_summary}"

    def skip(self, reason: str) -> None:
        """Mark this event as skipped without executing it.

        Used when:
        - Simulation jumps past scheduled_time
        - Event is invalidated by previous events
        - User manually skips event

        Args:
            reason: Why this event was skipped.
        """
        if self.status != EventStatus.PENDING:
            raise RuntimeError(
                f"Cannot skip event {self.event_id} with status {self.status}"
            )

        self.status = EventStatus.SKIPPED
        self.metadata["skip_reason"] = reason

    def cancel(self, reason: str) -> None:
        """Cancel this event before execution.

        Only works if status is PENDING. Once executed, cannot be undone.

        Args:
            reason: Why this event was cancelled.

        Raises:
            RuntimeError: If event is already executed.
        """
        if self.status == EventStatus.EXECUTED:
            raise RuntimeError(
                f"Cannot cancel executed event {self.event_id}"
            )

        if self.status in (EventStatus.EXECUTING, EventStatus.FAILED):
            raise RuntimeError(
                f"Cannot cancel event {self.event_id} with status {self.status}"
            )

        self.status = EventStatus.CANCELLED
        self.metadata["cancel_reason"] = reason

    def get_dependencies(self) -> list[str]:
        """Return list of entity IDs this event depends on.

        Used for:
        - Detecting conflicts (multiple events affecting same entity)
        - Ordering events with dependencies
        - Query optimization

        Delegates to data.get_affected_entities()

        Returns:
            List of entity IDs this event affects.
        """
        return self.data.get_affected_entities()