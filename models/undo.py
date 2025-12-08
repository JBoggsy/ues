"""Undo/Redo infrastructure models.

This module provides models for tracking and reversing event executions:
- UndoEntry: Captures the data needed to undo a single event execution
- UndoStack: Manages a stack of undo entries with redo capability

The undo system uses a "Hybrid Targeted Memento" pattern where each modality
captures minimal data before an input is applied. For additive operations,
only IDs are stored. For destructive operations, full objects are captured.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class UndoEntry(BaseModel):
    """Captures the data needed to undo a single event execution.

    An UndoEntry is created when a SimulatorEvent is executed successfully.
    It stores the minimal data needed to reverse the state change caused
    by that event.

    The undo_data dict is modality-specific and always includes:
    - "action": The type of undo operation (e.g., "remove_location", "restore_previous")
    - "state_previous_update_count": The modality state's update_count before execution
    - "state_previous_last_updated": The modality state's last_updated before execution

    Additional fields depend on the modality and operation type:
    - Additive operations store minimal IDs for removal
    - Destructive operations store full objects for restoration

    Args:
        event_id: Unique identifier of the event that was executed.
        modality: Which modality the event affected (e.g., "email", "weather").
        undo_data: Dictionary containing operation-specific undo data.
        executed_at: When the event was executed (simulator time).

    Examples:
        # Undo entry for adding a new weather location
        UndoEntry(
            event_id="event-123",
            modality="weather",
            undo_data={
                "action": "remove_location",
                "location_key": "40.71,-74.01",
                "state_previous_update_count": 5,
                "state_previous_last_updated": "2025-01-15T10:30:00+00:00"
            },
            executed_at=datetime(2025, 1, 15, 10, 30, tzinfo=timezone.utc)
        )

        # Undo entry for deleting an email
        UndoEntry(
            event_id="event-456",
            modality="email",
            undo_data={
                "action": "restore_email",
                "email": {... full email object ...},
                "original_folder": "inbox",
                "state_previous_update_count": 10,
                "state_previous_last_updated": "2025-01-15T11:00:00+00:00"
            },
            executed_at=datetime(2025, 1, 15, 11, 0, tzinfo=timezone.utc)
        )
    """

    event_id: str = Field(description="Unique identifier of the event that was executed")
    modality: str = Field(description="Which modality the event affected")
    undo_data: dict[str, Any] = Field(
        description="Dictionary containing operation-specific undo data"
    )
    executed_at: datetime = Field(description="When the event was executed (simulator time)")

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, v: str) -> str:
        """Validate that event_id is non-empty.

        Args:
            v: The event_id value.

        Returns:
            The validated event_id.

        Raises:
            ValueError: If event_id is empty or whitespace.
        """
        if not v or not v.strip():
            raise ValueError("event_id cannot be empty")
        return v

    @field_validator("modality")
    @classmethod
    def validate_modality(cls, v: str) -> str:
        """Validate that modality is non-empty.

        Args:
            v: The modality value.

        Returns:
            The validated modality.

        Raises:
            ValueError: If modality is empty or whitespace.
        """
        if not v or not v.strip():
            raise ValueError("modality cannot be empty")
        return v

    @field_validator("undo_data")
    @classmethod
    def validate_undo_data(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate that undo_data contains required fields.

        All undo_data dicts must contain:
        - "action": The undo action type
        - "state_previous_update_count": Previous update count
        - "state_previous_last_updated": Previous last_updated timestamp

        Args:
            v: The undo_data dictionary.

        Returns:
            The validated undo_data dictionary.

        Raises:
            ValueError: If required fields are missing.
        """
        if "action" not in v:
            raise ValueError("undo_data must contain 'action' field")
        if "state_previous_update_count" not in v:
            raise ValueError("undo_data must contain 'state_previous_update_count' field")
        if "state_previous_last_updated" not in v:
            raise ValueError("undo_data must contain 'state_previous_last_updated' field")
        return v

    def to_dict(self) -> dict[str, Any]:
        """Convert this undo entry to a dictionary.

        Returns:
            Dictionary representation suitable for serialization.
        """
        return {
            "event_id": self.event_id,
            "modality": self.modality,
            "undo_data": self.undo_data,
            "executed_at": self.executed_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UndoEntry":
        """Create an UndoEntry from a dictionary.

        Args:
            data: Dictionary containing undo entry data.

        Returns:
            New UndoEntry instance.
        """
        return cls(
            event_id=data["event_id"],
            modality=data["modality"],
            undo_data=data["undo_data"],
            executed_at=datetime.fromisoformat(data["executed_at"]),
        )


class UndoStack(BaseModel):
    """Manages a stack of undo entries with redo capability.

    The UndoStack provides a standard undo/redo mechanism:
    - When an event is executed, push() adds an UndoEntry to the undo stack
    - When undo() is called, entries are moved from undo to redo stack
    - When redo() is called, entries are moved from redo to undo stack
    - Any new push() clears the redo stack (new timeline divergence)

    The stack has an optional maximum size. When exceeded, oldest entries
    are discarded to make room for new ones.

    Args:
        undo_entries: Stack of entries available for undo (most recent at end).
        redo_entries: Stack of entries available for redo (most recent at end).
        max_size: Maximum number of entries to keep (None = unlimited).

    Examples:
        # Create stack with max 100 entries
        stack = UndoStack(max_size=100)

        # Push entry after event execution
        stack.push(undo_entry)

        # Undo last 3 operations
        undone = stack.pop_for_undo(count=3)
        # ... apply undo to each entry ...
        for entry in undone:
            state.apply_undo(entry.undo_data)
            stack.push_to_redo(entry)

        # Redo last operation
        redone = stack.pop_for_redo(count=1)
        # ... re-apply the event ...
    """

    undo_entries: list[UndoEntry] = Field(
        default_factory=list,
        description="Stack of entries available for undo (most recent at end)",
    )
    redo_entries: list[UndoEntry] = Field(
        default_factory=list,
        description="Stack of entries available for redo (most recent at end)",
    )
    max_size: Optional[int] = Field(
        default=None,
        description="Maximum number of entries to keep (None = unlimited)",
    )

    @field_validator("max_size")
    @classmethod
    def validate_max_size(cls, v: Optional[int]) -> Optional[int]:
        """Validate that max_size is positive if provided.

        Args:
            v: The max_size value.

        Returns:
            The validated max_size.

        Raises:
            ValueError: If max_size is not positive.
        """
        if v is not None and v <= 0:
            raise ValueError("max_size must be positive")
        return v

    @model_validator(mode="after")
    def trim_entries_to_max_size(self) -> "UndoStack":
        """Trim entries if they exceed max_size.

        This ensures the stack respects max_size even if initialized
        with too many entries.

        Returns:
            The validated UndoStack.
        """
        if self.max_size is not None:
            if len(self.undo_entries) > self.max_size:
                # Keep most recent entries
                self.undo_entries = self.undo_entries[-self.max_size :]
            if len(self.redo_entries) > self.max_size:
                # Keep most recent entries
                self.redo_entries = self.redo_entries[-self.max_size :]
        return self

    @property
    def can_undo(self) -> bool:
        """Check if there are entries available for undo.

        Returns:
            True if at least one entry is available for undo.
        """
        return len(self.undo_entries) > 0

    @property
    def can_redo(self) -> bool:
        """Check if there are entries available for redo.

        Returns:
            True if at least one entry is available for redo.
        """
        return len(self.redo_entries) > 0

    @property
    def undo_count(self) -> int:
        """Get the number of entries available for undo.

        Returns:
            Number of entries in the undo stack.
        """
        return len(self.undo_entries)

    @property
    def redo_count(self) -> int:
        """Get the number of entries available for redo.

        Returns:
            Number of entries in the redo stack.
        """
        return len(self.redo_entries)

    def push(self, entry: UndoEntry) -> Optional[UndoEntry]:
        """Push an undo entry after an event is executed.

        Adds the entry to the undo stack and clears the redo stack
        (since we're creating a new timeline). If max_size is set and
        the stack is full, the oldest entry is removed and returned.

        Args:
            entry: The UndoEntry to add.

        Returns:
            The removed oldest entry if max_size was exceeded, None otherwise.
        """
        # Clear redo stack - we're creating a new timeline
        self.redo_entries.clear()

        # Add new entry
        self.undo_entries.append(entry)

        # Trim if over max_size
        removed = None
        if self.max_size is not None and len(self.undo_entries) > self.max_size:
            removed = self.undo_entries.pop(0)

        return removed

    def pop_for_undo(self, count: int = 1) -> list[UndoEntry]:
        """Pop entries from the undo stack for undoing.

        Removes and returns the most recent entries from the undo stack.
        The entries should be applied in the order returned (most recent first).
        After applying each undo, call push_to_redo() to enable redo.

        Args:
            count: Number of entries to pop (default: 1).

        Returns:
            List of UndoEntry objects, most recent first.
            May be shorter than requested if stack has fewer entries.

        Raises:
            ValueError: If count is not positive.
        """
        if count <= 0:
            raise ValueError("count must be positive")

        entries = []
        for _ in range(min(count, len(self.undo_entries))):
            entries.append(self.undo_entries.pop())

        return entries

    def push_to_redo(self, entry: UndoEntry) -> None:
        """Push an entry to the redo stack after undoing.

        Called after successfully applying an undo operation.
        This enables the operation to be redone later.

        Note: If max_size is set and redo stack is full, oldest redo
        entry is discarded.

        Args:
            entry: The UndoEntry that was just undone.
        """
        self.redo_entries.append(entry)

        # Trim if over max_size
        if self.max_size is not None and len(self.redo_entries) > self.max_size:
            self.redo_entries.pop(0)

    def pop_for_redo(self, count: int = 1) -> list[UndoEntry]:
        """Pop entries from the redo stack for redoing.

        Removes and returns the most recent entries from the redo stack.
        The entries should be re-executed in the order returned (most recent first,
        which means reverse chronological order of original execution).

        After re-executing each event, the execution will push new undo entries.

        Args:
            count: Number of entries to pop (default: 1).

        Returns:
            List of UndoEntry objects, most recent first (reverse execution order).
            May be shorter than requested if stack has fewer entries.

        Raises:
            ValueError: If count is not positive.
        """
        if count <= 0:
            raise ValueError("count must be positive")

        entries = []
        for _ in range(min(count, len(self.redo_entries))):
            entries.append(self.redo_entries.pop())

        return entries

    def clear(self) -> None:
        """Clear both undo and redo stacks.

        Used when resetting the simulation or starting fresh.
        """
        self.undo_entries.clear()
        self.redo_entries.clear()

    def clear_redo(self) -> None:
        """Clear only the redo stack.

        Called implicitly when push() is used, but can be called
        explicitly if needed.
        """
        self.redo_entries.clear()

    def peek_undo(self, count: int = 1) -> list[UndoEntry]:
        """Peek at the most recent undo entries without removing them.

        Args:
            count: Number of entries to peek (default: 1).

        Returns:
            List of UndoEntry objects, most recent first.
            May be shorter than requested if stack has fewer entries.

        Raises:
            ValueError: If count is not positive.
        """
        if count <= 0:
            raise ValueError("count must be positive")

        # Return most recent first
        return list(reversed(self.undo_entries[-count:]))

    def peek_redo(self, count: int = 1) -> list[UndoEntry]:
        """Peek at the most recent redo entries without removing them.

        Args:
            count: Number of entries to peek (default: 1).

        Returns:
            List of UndoEntry objects, most recent first.
            May be shorter than requested if stack has fewer entries.

        Raises:
            ValueError: If count is not positive.
        """
        if count <= 0:
            raise ValueError("count must be positive")

        # Return most recent first
        return list(reversed(self.redo_entries[-count:]))

    def get_undo_summary(self) -> list[dict[str, Any]]:
        """Get a summary of entries available for undo.

        Returns:
            List of dicts with event_id, modality, and action for each entry.
            Ordered most recent first.
        """
        return [
            {
                "event_id": entry.event_id,
                "modality": entry.modality,
                "action": entry.undo_data.get("action"),
                "executed_at": entry.executed_at.isoformat(),
            }
            for entry in reversed(self.undo_entries)
        ]

    def get_redo_summary(self) -> list[dict[str, Any]]:
        """Get a summary of entries available for redo.

        Returns:
            List of dicts with event_id, modality, and action for each entry.
            Ordered most recent first (next to be redone first).
        """
        return [
            {
                "event_id": entry.event_id,
                "modality": entry.modality,
                "action": entry.undo_data.get("action"),
                "executed_at": entry.executed_at.isoformat(),
            }
            for entry in reversed(self.redo_entries)
        ]

    def to_dict(self) -> dict[str, Any]:
        """Convert this undo stack to a dictionary.

        Returns:
            Dictionary representation suitable for serialization.
        """
        return {
            "undo_entries": [entry.to_dict() for entry in self.undo_entries],
            "redo_entries": [entry.to_dict() for entry in self.redo_entries],
            "max_size": self.max_size,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UndoStack":
        """Create an UndoStack from a dictionary.

        Args:
            data: Dictionary containing undo stack data.

        Returns:
            New UndoStack instance.
        """
        return cls(
            undo_entries=[UndoEntry.from_dict(e) for e in data.get("undo_entries", [])],
            redo_entries=[UndoEntry.from_dict(e) for e in data.get("redo_entries", [])],
            max_size=data.get("max_size"),
        )
