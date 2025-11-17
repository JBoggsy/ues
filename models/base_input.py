"""Base class for all modality input models."""

from abc import abstractmethod
from datetime import datetime
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ModalityInput(BaseModel):
    """Base class for all event payloads.

    Each subclass defines the structure of data that events carry (e.g., EmailInput, TextInput).
    Used in SimulatorEvent.data field and includes modality-specific validation logic.

    Inputs represent what changes when an event occurs. They are immutable value objects
    that describe state mutations.

    Args:
        modality_type: Identifies which modality this input affects (e.g., "email", "location").
        timestamp: When this input logically occurred (simulator time).
        input_id: Unique identifier for this specific input.
    """

    modality_type: str = Field(
        description="Identifies which modality this input affects"
    )
    timestamp: datetime = Field(
        description="When this input logically occurred (simulator time)"
    )
    input_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this specific input",
    )

    @abstractmethod
    def validate_input(self) -> None:
        """Perform modality-specific validation beyond Pydantic field validation.

        This method should check complex cross-field or semantic constraints that
        can't be expressed in Pydantic field validators.

        Examples:
            - EmailInput: Validate email address formats, check attachment sizes
            - LocationInput: Ensure lat/long within valid ranges
            - CalendarEventInput: Verify start_time < end_time

        Raises:
            ValueError: If validation fails with descriptive message.
        """
        pass

    @abstractmethod
    def get_affected_entities(self) -> list[str]:
        """Return list of entity IDs affected by this input.

        This allows the system to track which entities are modified by which events,
        useful for conflict detection, dependency tracking, and query optimization.

        Examples:
            - EmailInput: Returns [thread_id] or generates one if new thread
            - TextInput: Returns [conversation_id]
            - CalendarEventInput: Returns [event_id]

        Returns:
            List of string identifiers for entities this input affects.
        """
        pass

    @abstractmethod
    def get_summary(self) -> str:
        """Return human-readable one-line summary of this input.

        Essential for debugging, logging, and UI display. Users need to quickly
        understand what an event does.

        Examples:
            - EmailInput: "Email from john@example.com: 'Meeting Tomorrow'"
            - LocationInput: "Moved to 123 Main St, Springfield"
            - TextInput: "Text from (555) 123-4567: 'Running late'"

        Returns:
            Brief, human-readable description for logging/UI display.
        """
        pass

    def should_merge_with(self, other: "ModalityInput") -> bool:
        """Determine if this input should be merged with another input.

        Prevents duplicate or redundant inputs from cluttering the simulation.
        Subclasses opt-in to merging behavior by overriding this method.

        Examples:
            - LocationInput: Merge if timestamps are within 1 second (position updates)
            - WeatherInput: Merge if timestamps are within 5 minutes (redundant updates)

        Args:
            other: Another input of the same type.

        Returns:
            True if inputs should be merged, False otherwise.
        """
        return False
