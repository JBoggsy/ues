"""Unit tests for UndoEntry and UndoStack models.

This module tests undo infrastructure including:
- UndoEntry: Captures undo data for a single event execution
- UndoStack: Manages undo/redo stacks with capacity limits

Tests follow patterns established in other model tests:
- General patterns: instantiation, validation, serialization
- Specific patterns: stack operations, capacity handling, redo workflow
"""

from datetime import datetime, timezone, timedelta

import pytest

from models.undo import UndoEntry, UndoStack


# =============================================================================
# Helper Functions
# =============================================================================


def create_undo_entry(
    event_id: str = "event-123",
    modality: str = "weather",
    action: str = "remove_location",
    executed_at: datetime | None = None,
    **extra_undo_data,
) -> UndoEntry:
    """Create an UndoEntry with sensible defaults for testing.

    Args:
        event_id: Event ID for the entry.
        modality: Modality name.
        action: Undo action type.
        executed_at: Execution timestamp.
        **extra_undo_data: Additional fields for undo_data dict.

    Returns:
        New UndoEntry instance.
    """
    if executed_at is None:
        executed_at = datetime(2025, 1, 15, 10, 30, tzinfo=timezone.utc)

    undo_data = {
        "action": action,
        "state_previous_update_count": 5,
        "state_previous_last_updated": "2025-01-15T10:00:00+00:00",
        **extra_undo_data,
    }

    return UndoEntry(
        event_id=event_id,
        modality=modality,
        undo_data=undo_data,
        executed_at=executed_at,
    )


# =============================================================================
# UndoEntry Tests
# =============================================================================


class TestUndoEntryInstantiation:
    """Test instantiation patterns for UndoEntry.

    GENERAL PATTERN: All UndoEntry instances should require
    event_id, modality, undo_data (with required fields), and executed_at.
    """

    def test_minimal_valid_instantiation(self):
        """Verify UndoEntry instantiates with minimal valid data."""
        entry = UndoEntry(
            event_id="event-123",
            modality="weather",
            undo_data={
                "action": "remove_location",
                "state_previous_update_count": 0,
                "state_previous_last_updated": "2025-01-15T10:00:00+00:00",
            },
            executed_at=datetime(2025, 1, 15, 10, 30, tzinfo=timezone.utc),
        )

        assert entry.event_id == "event-123"
        assert entry.modality == "weather"
        assert entry.undo_data["action"] == "remove_location"
        assert entry.executed_at == datetime(2025, 1, 15, 10, 30, tzinfo=timezone.utc)

    def test_instantiation_with_complex_undo_data(self):
        """Verify UndoEntry handles complex undo_data with nested objects."""
        entry = UndoEntry(
            event_id="event-456",
            modality="email",
            undo_data={
                "action": "restore_email",
                "state_previous_update_count": 10,
                "state_previous_last_updated": "2025-01-15T11:00:00+00:00",
                "email": {
                    "email_id": "email-789",
                    "subject": "Test email",
                    "body": "Hello world",
                    "from_address": "sender@example.com",
                },
                "original_folder": "inbox",
            },
            executed_at=datetime(2025, 1, 15, 11, 0, tzinfo=timezone.utc),
        )

        assert entry.undo_data["email"]["email_id"] == "email-789"
        assert entry.undo_data["original_folder"] == "inbox"

    def test_instantiation_preserves_all_undo_data_fields(self):
        """Verify UndoEntry preserves all fields in undo_data."""
        custom_data = {
            "action": "restore_previous",
            "state_previous_update_count": 5,
            "state_previous_last_updated": "2025-01-15T10:00:00+00:00",
            "location_key": "40.71,-74.01",
            "previous_report": {"temperature": 72, "conditions": "sunny"},
            "removed_history_entry": {"timestamp": "2025-01-14T10:00:00+00:00"},
        }

        entry = UndoEntry(
            event_id="event-123",
            modality="weather",
            undo_data=custom_data,
            executed_at=datetime.now(timezone.utc),
        )

        assert entry.undo_data == custom_data


class TestUndoEntryValidation:
    """Test validation for UndoEntry fields.

    ENTRY-SPECIFIC: Tests validation rules for required fields.
    """

    def test_empty_event_id_raises(self):
        """Verify empty event_id raises ValueError."""
        with pytest.raises(ValueError, match="event_id cannot be empty"):
            UndoEntry(
                event_id="",
                modality="weather",
                undo_data={
                    "action": "test",
                    "state_previous_update_count": 0,
                    "state_previous_last_updated": "2025-01-15T10:00:00+00:00",
                },
                executed_at=datetime.now(timezone.utc),
            )

    def test_whitespace_event_id_raises(self):
        """Verify whitespace-only event_id raises ValueError."""
        with pytest.raises(ValueError, match="event_id cannot be empty"):
            UndoEntry(
                event_id="   ",
                modality="weather",
                undo_data={
                    "action": "test",
                    "state_previous_update_count": 0,
                    "state_previous_last_updated": "2025-01-15T10:00:00+00:00",
                },
                executed_at=datetime.now(timezone.utc),
            )

    def test_empty_modality_raises(self):
        """Verify empty modality raises ValueError."""
        with pytest.raises(ValueError, match="modality cannot be empty"):
            UndoEntry(
                event_id="event-123",
                modality="",
                undo_data={
                    "action": "test",
                    "state_previous_update_count": 0,
                    "state_previous_last_updated": "2025-01-15T10:00:00+00:00",
                },
                executed_at=datetime.now(timezone.utc),
            )

    def test_whitespace_modality_raises(self):
        """Verify whitespace-only modality raises ValueError."""
        with pytest.raises(ValueError, match="modality cannot be empty"):
            UndoEntry(
                event_id="event-123",
                modality="   ",
                undo_data={
                    "action": "test",
                    "state_previous_update_count": 0,
                    "state_previous_last_updated": "2025-01-15T10:00:00+00:00",
                },
                executed_at=datetime.now(timezone.utc),
            )

    def test_undo_data_missing_action_raises(self):
        """Verify undo_data without 'action' raises ValueError."""
        with pytest.raises(ValueError, match="must contain 'action' field"):
            UndoEntry(
                event_id="event-123",
                modality="weather",
                undo_data={
                    "state_previous_update_count": 0,
                    "state_previous_last_updated": "2025-01-15T10:00:00+00:00",
                },
                executed_at=datetime.now(timezone.utc),
            )

    def test_undo_data_missing_update_count_raises(self):
        """Verify undo_data without 'state_previous_update_count' raises ValueError."""
        with pytest.raises(ValueError, match="must contain 'state_previous_update_count' field"):
            UndoEntry(
                event_id="event-123",
                modality="weather",
                undo_data={
                    "action": "test",
                    "state_previous_last_updated": "2025-01-15T10:00:00+00:00",
                },
                executed_at=datetime.now(timezone.utc),
            )

    def test_undo_data_missing_last_updated_raises(self):
        """Verify undo_data without 'state_previous_last_updated' raises ValueError."""
        with pytest.raises(ValueError, match="must contain 'state_previous_last_updated' field"):
            UndoEntry(
                event_id="event-123",
                modality="weather",
                undo_data={
                    "action": "test",
                    "state_previous_update_count": 0,
                },
                executed_at=datetime.now(timezone.utc),
            )


class TestUndoEntrySerialization:
    """Test serialization for UndoEntry.

    GENERAL PATTERN: All entries should be serializable and deserializable.
    """

    def test_to_dict_includes_all_fields(self):
        """Verify to_dict() includes all entry fields."""
        executed_at = datetime(2025, 1, 15, 10, 30, tzinfo=timezone.utc)
        entry = create_undo_entry(
            event_id="event-123",
            modality="weather",
            action="remove_location",
            executed_at=executed_at,
            location_key="40.71,-74.01",
        )

        result = entry.to_dict()

        assert result["event_id"] == "event-123"
        assert result["modality"] == "weather"
        assert result["undo_data"]["action"] == "remove_location"
        assert result["undo_data"]["location_key"] == "40.71,-74.01"
        assert result["executed_at"] == "2025-01-15T10:30:00+00:00"

    def test_from_dict_round_trip(self):
        """Verify from_dict() recreates identical entry."""
        original = create_undo_entry(
            event_id="event-456",
            modality="email",
            action="restore_email",
            email={"email_id": "email-789"},
        )

        serialized = original.to_dict()
        restored = UndoEntry.from_dict(serialized)

        assert restored.event_id == original.event_id
        assert restored.modality == original.modality
        assert restored.undo_data == original.undo_data
        assert restored.executed_at == original.executed_at


# =============================================================================
# UndoStack Tests
# =============================================================================


class TestUndoStackInstantiation:
    """Test instantiation patterns for UndoStack.

    GENERAL PATTERN: All UndoStack instances should support creation
    with empty or populated stacks.
    """

    def test_minimal_instantiation(self):
        """Verify UndoStack instantiates as empty stack."""
        stack = UndoStack()

        assert stack.undo_entries == []
        assert stack.redo_entries == []
        assert stack.max_size is None
        assert not stack.can_undo
        assert not stack.can_redo
        assert stack.undo_count == 0
        assert stack.redo_count == 0

    def test_instantiation_with_max_size(self):
        """Verify UndoStack respects max_size."""
        stack = UndoStack(max_size=100)

        assert stack.max_size == 100

    def test_instantiation_with_entries(self):
        """Verify UndoStack instantiates with provided entries."""
        entries = [
            create_undo_entry(event_id="event-1"),
            create_undo_entry(event_id="event-2"),
        ]

        stack = UndoStack(undo_entries=entries)

        assert len(stack.undo_entries) == 2
        assert stack.can_undo
        assert stack.undo_count == 2

    def test_instantiation_trims_to_max_size(self):
        """Verify UndoStack trims entries if over max_size on init."""
        entries = [
            create_undo_entry(event_id=f"event-{i}")
            for i in range(5)
        ]

        stack = UndoStack(undo_entries=entries, max_size=3)

        # Should keep most recent 3 (events 2, 3, 4)
        assert len(stack.undo_entries) == 3
        assert stack.undo_entries[0].event_id == "event-2"
        assert stack.undo_entries[2].event_id == "event-4"


class TestUndoStackValidation:
    """Test validation for UndoStack fields.

    STACK-SPECIFIC: Tests validation rules for max_size.
    """

    def test_zero_max_size_raises(self):
        """Verify max_size of 0 raises ValueError."""
        with pytest.raises(ValueError, match="max_size must be positive"):
            UndoStack(max_size=0)

    def test_negative_max_size_raises(self):
        """Verify negative max_size raises ValueError."""
        with pytest.raises(ValueError, match="max_size must be positive"):
            UndoStack(max_size=-5)


class TestUndoStackPush:
    """Test push operations for UndoStack.

    STACK-SPECIFIC: Tests adding entries to the undo stack.
    """

    def test_push_adds_to_undo_stack(self):
        """Verify push() adds entry to undo stack."""
        stack = UndoStack()
        entry = create_undo_entry(event_id="event-1")

        stack.push(entry)

        assert len(stack.undo_entries) == 1
        assert stack.undo_entries[0].event_id == "event-1"
        assert stack.can_undo

    def test_push_clears_redo_stack(self):
        """Verify push() clears the redo stack."""
        stack = UndoStack(redo_entries=[create_undo_entry(event_id="redo-1")])
        assert stack.can_redo

        entry = create_undo_entry(event_id="new-1")
        stack.push(entry)

        assert not stack.can_redo
        assert stack.redo_count == 0

    def test_push_respects_max_size(self):
        """Verify push() removes oldest entry when at max_size."""
        stack = UndoStack(max_size=3)
        for i in range(3):
            stack.push(create_undo_entry(event_id=f"event-{i}"))

        assert len(stack.undo_entries) == 3
        assert stack.undo_entries[0].event_id == "event-0"

        # Push one more - should remove event-0
        removed = stack.push(create_undo_entry(event_id="event-3"))

        assert len(stack.undo_entries) == 3
        assert removed is not None
        assert removed.event_id == "event-0"
        assert stack.undo_entries[0].event_id == "event-1"
        assert stack.undo_entries[2].event_id == "event-3"

    def test_push_returns_none_when_not_at_capacity(self):
        """Verify push() returns None when not at capacity."""
        stack = UndoStack(max_size=10)
        entry = create_undo_entry(event_id="event-1")

        removed = stack.push(entry)

        assert removed is None

    def test_push_order_is_preserved(self):
        """Verify entries are stored in push order (oldest first)."""
        stack = UndoStack()

        for i in range(5):
            stack.push(create_undo_entry(event_id=f"event-{i}"))

        assert stack.undo_entries[0].event_id == "event-0"
        assert stack.undo_entries[4].event_id == "event-4"


class TestUndoStackPopForUndo:
    """Test pop_for_undo operations for UndoStack.

    STACK-SPECIFIC: Tests removing entries for undo application.
    """

    def test_pop_for_undo_returns_most_recent_first(self):
        """Verify pop_for_undo() returns most recent entry first."""
        stack = UndoStack()
        for i in range(5):
            stack.push(create_undo_entry(event_id=f"event-{i}"))

        entries = stack.pop_for_undo(count=2)

        assert len(entries) == 2
        assert entries[0].event_id == "event-4"  # Most recent
        assert entries[1].event_id == "event-3"

    def test_pop_for_undo_removes_from_stack(self):
        """Verify pop_for_undo() removes entries from stack."""
        stack = UndoStack()
        for i in range(5):
            stack.push(create_undo_entry(event_id=f"event-{i}"))

        stack.pop_for_undo(count=2)

        assert len(stack.undo_entries) == 3
        assert stack.undo_entries[-1].event_id == "event-2"

    def test_pop_for_undo_returns_available_if_fewer_than_requested(self):
        """Verify pop_for_undo() returns available entries if less than count."""
        stack = UndoStack()
        stack.push(create_undo_entry(event_id="event-1"))
        stack.push(create_undo_entry(event_id="event-2"))

        entries = stack.pop_for_undo(count=5)

        assert len(entries) == 2
        assert stack.undo_count == 0

    def test_pop_for_undo_empty_stack_returns_empty_list(self):
        """Verify pop_for_undo() returns empty list for empty stack."""
        stack = UndoStack()

        entries = stack.pop_for_undo(count=1)

        assert entries == []

    def test_pop_for_undo_zero_count_raises(self):
        """Verify pop_for_undo() with count=0 raises ValueError."""
        stack = UndoStack()

        with pytest.raises(ValueError, match="count must be positive"):
            stack.pop_for_undo(count=0)

    def test_pop_for_undo_negative_count_raises(self):
        """Verify pop_for_undo() with negative count raises ValueError."""
        stack = UndoStack()

        with pytest.raises(ValueError, match="count must be positive"):
            stack.pop_for_undo(count=-1)


class TestUndoStackRedo:
    """Test redo operations for UndoStack.

    STACK-SPECIFIC: Tests redo workflow (push_to_redo, pop_for_redo).
    """

    def test_push_to_redo_adds_to_redo_stack(self):
        """Verify push_to_redo() adds entry to redo stack."""
        stack = UndoStack()
        entry = create_undo_entry(event_id="event-1")

        stack.push_to_redo(entry)

        assert len(stack.redo_entries) == 1
        assert stack.redo_entries[0].event_id == "event-1"
        assert stack.can_redo

    def test_push_to_redo_respects_max_size(self):
        """Verify push_to_redo() respects max_size."""
        stack = UndoStack(max_size=3)
        for i in range(3):
            stack.push_to_redo(create_undo_entry(event_id=f"event-{i}"))

        # Push one more - should remove oldest
        stack.push_to_redo(create_undo_entry(event_id="event-3"))

        assert len(stack.redo_entries) == 3
        assert stack.redo_entries[0].event_id == "event-1"
        assert stack.redo_entries[2].event_id == "event-3"

    def test_pop_for_redo_returns_most_recent_first(self):
        """Verify pop_for_redo() returns most recent entry first."""
        stack = UndoStack()
        for i in range(3):
            stack.push_to_redo(create_undo_entry(event_id=f"event-{i}"))

        entries = stack.pop_for_redo(count=2)

        assert len(entries) == 2
        assert entries[0].event_id == "event-2"  # Most recent
        assert entries[1].event_id == "event-1"

    def test_pop_for_redo_removes_from_stack(self):
        """Verify pop_for_redo() removes entries from stack."""
        stack = UndoStack()
        for i in range(3):
            stack.push_to_redo(create_undo_entry(event_id=f"event-{i}"))

        stack.pop_for_redo(count=2)

        assert len(stack.redo_entries) == 1
        assert stack.redo_entries[0].event_id == "event-0"

    def test_pop_for_redo_empty_stack_returns_empty_list(self):
        """Verify pop_for_redo() returns empty list for empty stack."""
        stack = UndoStack()

        entries = stack.pop_for_redo(count=1)

        assert entries == []

    def test_pop_for_redo_zero_count_raises(self):
        """Verify pop_for_redo() with count=0 raises ValueError."""
        stack = UndoStack()

        with pytest.raises(ValueError, match="count must be positive"):
            stack.pop_for_redo(count=0)


class TestUndoStackWorkflow:
    """Test complete undo/redo workflow scenarios.

    INTEGRATION-STYLE: Tests realistic usage patterns.
    """

    def test_basic_undo_redo_cycle(self):
        """Verify basic undo then redo cycle works correctly."""
        stack = UndoStack()

        # Simulate 3 event executions
        for i in range(3):
            stack.push(create_undo_entry(event_id=f"event-{i}"))

        assert stack.undo_count == 3
        assert stack.redo_count == 0

        # Undo 2 operations
        undone = stack.pop_for_undo(count=2)
        for entry in undone:
            stack.push_to_redo(entry)

        assert stack.undo_count == 1
        assert stack.redo_count == 2

        # Redo 1 operation - gets most recent redo (last one we undone)
        # We undid event-2 first, then event-1, so event-1 is most recent in redo stack
        redone = stack.pop_for_redo(count=1)

        assert stack.undo_count == 1  # Unchanged (would be incremented on re-execute)
        assert stack.redo_count == 1
        assert redone[0].event_id == "event-1"  # Most recent redo (last undone)

    def test_push_after_undo_clears_redo(self):
        """Verify new push after undo clears redo stack (new timeline)."""
        stack = UndoStack()

        # Push 3 events
        for i in range(3):
            stack.push(create_undo_entry(event_id=f"event-{i}"))

        # Undo 2 events
        undone = stack.pop_for_undo(count=2)
        for entry in undone:
            stack.push_to_redo(entry)

        assert stack.redo_count == 2

        # Push new event (creates new timeline)
        stack.push(create_undo_entry(event_id="new-event"))

        assert stack.undo_count == 2  # event-0 + new-event
        assert stack.redo_count == 0  # Redo cleared

    def test_multiple_undo_operations(self):
        """Verify multiple sequential undos work correctly."""
        stack = UndoStack()

        # Push 5 events
        for i in range(5):
            stack.push(create_undo_entry(event_id=f"event-{i}"))

        # Undo one at a time
        for i in range(5):
            entries = stack.pop_for_undo(count=1)
            assert len(entries) == 1
            assert entries[0].event_id == f"event-{4 - i}"
            stack.push_to_redo(entries[0])

        assert stack.undo_count == 0
        assert stack.redo_count == 5


class TestUndoStackClear:
    """Test clear operations for UndoStack.

    STACK-SPECIFIC: Tests clearing stacks.
    """

    def test_clear_empties_both_stacks(self):
        """Verify clear() empties both undo and redo stacks."""
        stack = UndoStack()
        for i in range(3):
            stack.push(create_undo_entry(event_id=f"event-{i}"))
        stack.push_to_redo(create_undo_entry(event_id="redo-1"))

        assert stack.can_undo
        assert stack.can_redo

        stack.clear()

        assert not stack.can_undo
        assert not stack.can_redo
        assert stack.undo_count == 0
        assert stack.redo_count == 0

    def test_clear_redo_only_clears_redo(self):
        """Verify clear_redo() only clears redo stack."""
        stack = UndoStack()
        stack.push(create_undo_entry(event_id="event-1"))
        stack.push_to_redo(create_undo_entry(event_id="redo-1"))

        stack.clear_redo()

        assert stack.can_undo
        assert not stack.can_redo


class TestUndoStackPeek:
    """Test peek operations for UndoStack.

    STACK-SPECIFIC: Tests viewing without removing entries.
    """

    def test_peek_undo_returns_most_recent_first(self):
        """Verify peek_undo() returns most recent entries first."""
        stack = UndoStack()
        for i in range(5):
            stack.push(create_undo_entry(event_id=f"event-{i}"))

        entries = stack.peek_undo(count=3)

        assert len(entries) == 3
        assert entries[0].event_id == "event-4"  # Most recent
        assert entries[1].event_id == "event-3"
        assert entries[2].event_id == "event-2"

    def test_peek_undo_does_not_remove(self):
        """Verify peek_undo() does not remove entries."""
        stack = UndoStack()
        for i in range(3):
            stack.push(create_undo_entry(event_id=f"event-{i}"))

        stack.peek_undo(count=2)

        assert stack.undo_count == 3  # Unchanged

    def test_peek_undo_returns_available_if_fewer_than_requested(self):
        """Verify peek_undo() returns available entries if less than count."""
        stack = UndoStack()
        stack.push(create_undo_entry(event_id="event-1"))

        entries = stack.peek_undo(count=5)

        assert len(entries) == 1

    def test_peek_undo_zero_count_raises(self):
        """Verify peek_undo() with count=0 raises ValueError."""
        stack = UndoStack()

        with pytest.raises(ValueError, match="count must be positive"):
            stack.peek_undo(count=0)

    def test_peek_redo_returns_most_recent_first(self):
        """Verify peek_redo() returns most recent entries first."""
        stack = UndoStack()
        for i in range(3):
            stack.push_to_redo(create_undo_entry(event_id=f"event-{i}"))

        entries = stack.peek_redo(count=2)

        assert len(entries) == 2
        assert entries[0].event_id == "event-2"  # Most recent
        assert entries[1].event_id == "event-1"

    def test_peek_redo_zero_count_raises(self):
        """Verify peek_redo() with count=0 raises ValueError."""
        stack = UndoStack()

        with pytest.raises(ValueError, match="count must be positive"):
            stack.peek_redo(count=0)


class TestUndoStackSummary:
    """Test summary methods for UndoStack.

    STACK-SPECIFIC: Tests summary generation for UI/API use.
    """

    def test_get_undo_summary_returns_correct_format(self):
        """Verify get_undo_summary() returns expected format."""
        stack = UndoStack()
        executed_at = datetime(2025, 1, 15, 10, 30, tzinfo=timezone.utc)
        stack.push(create_undo_entry(
            event_id="event-1",
            modality="weather",
            action="remove_location",
            executed_at=executed_at,
        ))

        summary = stack.get_undo_summary()

        assert len(summary) == 1
        assert summary[0]["event_id"] == "event-1"
        assert summary[0]["modality"] == "weather"
        assert summary[0]["action"] == "remove_location"
        assert summary[0]["executed_at"] == "2025-01-15T10:30:00+00:00"

    def test_get_undo_summary_most_recent_first(self):
        """Verify get_undo_summary() returns most recent first."""
        stack = UndoStack()
        for i in range(3):
            stack.push(create_undo_entry(event_id=f"event-{i}"))

        summary = stack.get_undo_summary()

        assert summary[0]["event_id"] == "event-2"  # Most recent
        assert summary[2]["event_id"] == "event-0"  # Oldest

    def test_get_redo_summary_returns_correct_format(self):
        """Verify get_redo_summary() returns expected format."""
        stack = UndoStack()
        stack.push_to_redo(create_undo_entry(
            event_id="redo-1",
            modality="email",
            action="restore_email",
        ))

        summary = stack.get_redo_summary()

        assert len(summary) == 1
        assert summary[0]["event_id"] == "redo-1"
        assert summary[0]["modality"] == "email"
        assert summary[0]["action"] == "restore_email"

    def test_empty_stack_summaries_return_empty_lists(self):
        """Verify summaries return empty lists for empty stacks."""
        stack = UndoStack()

        assert stack.get_undo_summary() == []
        assert stack.get_redo_summary() == []


class TestUndoStackSerialization:
    """Test serialization for UndoStack.

    GENERAL PATTERN: All stacks should be serializable and deserializable.
    """

    def test_to_dict_includes_all_fields(self):
        """Verify to_dict() includes all stack fields."""
        stack = UndoStack(max_size=50)
        stack.push(create_undo_entry(event_id="event-1"))
        stack.push_to_redo(create_undo_entry(event_id="redo-1"))

        result = stack.to_dict()

        assert "undo_entries" in result
        assert "redo_entries" in result
        assert result["max_size"] == 50
        assert len(result["undo_entries"]) == 1
        assert len(result["redo_entries"]) == 1

    def test_from_dict_round_trip(self):
        """Verify from_dict() recreates identical stack."""
        original = UndoStack(max_size=100)
        original.push(create_undo_entry(event_id="event-1", modality="weather"))
        original.push(create_undo_entry(event_id="event-2", modality="email"))
        original.push_to_redo(create_undo_entry(event_id="redo-1", modality="chat"))

        serialized = original.to_dict()
        restored = UndoStack.from_dict(serialized)

        assert restored.max_size == original.max_size
        assert restored.undo_count == original.undo_count
        assert restored.redo_count == original.redo_count
        assert restored.undo_entries[0].event_id == "event-1"
        assert restored.undo_entries[1].event_id == "event-2"
        assert restored.redo_entries[0].event_id == "redo-1"

    def test_from_dict_handles_empty_stacks(self):
        """Verify from_dict() handles missing/empty entries."""
        data = {"max_size": 25}

        stack = UndoStack.from_dict(data)

        assert stack.max_size == 25
        assert stack.undo_count == 0
        assert stack.redo_count == 0

    def test_from_dict_handles_no_max_size(self):
        """Verify from_dict() handles missing max_size."""
        data = {
            "undo_entries": [],
            "redo_entries": [],
        }

        stack = UndoStack.from_dict(data)

        assert stack.max_size is None


class TestUndoStackCapacity:
    """Test capacity handling for UndoStack.

    STACK-SPECIFIC: Tests max_size enforcement scenarios.
    """

    def test_unlimited_stack_grows_indefinitely(self):
        """Verify stack with no max_size grows without limit."""
        stack = UndoStack()

        for i in range(1000):
            stack.push(create_undo_entry(event_id=f"event-{i}"))

        assert stack.undo_count == 1000

    def test_max_size_one_keeps_only_latest(self):
        """Verify max_size=1 keeps only the latest entry."""
        stack = UndoStack(max_size=1)

        for i in range(5):
            stack.push(create_undo_entry(event_id=f"event-{i}"))

        assert stack.undo_count == 1
        assert stack.undo_entries[0].event_id == "event-4"

    def test_redo_stack_also_respects_max_size(self):
        """Verify redo stack respects max_size."""
        stack = UndoStack(max_size=2)

        for i in range(5):
            stack.push_to_redo(create_undo_entry(event_id=f"redo-{i}"))

        assert stack.redo_count == 2
        assert stack.redo_entries[0].event_id == "redo-3"
        assert stack.redo_entries[1].event_id == "redo-4"


class TestUndoStackProperties:
    """Test computed properties for UndoStack.

    STACK-SPECIFIC: Tests property accessors.
    """

    def test_can_undo_true_when_has_entries(self):
        """Verify can_undo is True when undo stack has entries."""
        stack = UndoStack()
        assert not stack.can_undo

        stack.push(create_undo_entry())
        assert stack.can_undo

    def test_can_redo_true_when_has_entries(self):
        """Verify can_redo is True when redo stack has entries."""
        stack = UndoStack()
        assert not stack.can_redo

        stack.push_to_redo(create_undo_entry())
        assert stack.can_redo

    def test_undo_count_tracks_entries(self):
        """Verify undo_count correctly tracks entry count."""
        stack = UndoStack()
        assert stack.undo_count == 0

        stack.push(create_undo_entry())
        assert stack.undo_count == 1

        stack.push(create_undo_entry())
        assert stack.undo_count == 2

        stack.pop_for_undo(1)
        assert stack.undo_count == 1

    def test_redo_count_tracks_entries(self):
        """Verify redo_count correctly tracks entry count."""
        stack = UndoStack()
        assert stack.redo_count == 0

        stack.push_to_redo(create_undo_entry())
        assert stack.redo_count == 1

        stack.pop_for_redo(1)
        assert stack.redo_count == 0
