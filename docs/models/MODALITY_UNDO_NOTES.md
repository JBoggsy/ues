# Modality Undo Implementation Notes

This document captures lessons learned and patterns established from implementing undo functionality for WeatherState and ChatState. Use this as a guide when implementing undo for remaining modalities.

## Core Design Principles

### 1. Distinguish Additive vs. Destructive Operations

Each modality should identify its operation types and store the **minimum data needed** for each:

- **Additive operations** (add new item): Store only the ID/key needed to remove it
- **Destructive operations** (update/delete existing): Store the full object being replaced/deleted

Example from WeatherState:
```python
# Adding new location - minimal data
{"action": "remove_location", "location_key": "40.71,-74.01"}

# Updating existing location - full previous state
{"action": "restore_previous", "location_key": "...", "previous_report": {...}, ...}
```

### 2. Always Capture State-Level Metadata

Every undo operation must capture these fields (universal pattern for all modalities):

```python
"state_previous_update_count": self.update_count,
"state_previous_last_updated": self.last_updated.isoformat(),
```

### 3. Always Include an "action" Key

The undo data dict must include an `action` field that describes the undo operation:

```python
{"action": "remove_location", ...}
{"action": "restore_previous", ...}
{"action": "delete_message", ...}
```

This enables clean dispatch in `apply_undo()` and helps with debugging.

### 4. Handle No-op Operations

Some operations may be no-ops (e.g., deleting a non-existent message). These still increment `update_count`, so the undo must restore state-level metadata even when there's nothing else to undo:

```python
if action == "noop":
    # Restore state-level metadata only
    self.update_count = undo_data["state_previous_update_count"]
    self.last_updated = datetime.fromisoformat(undo_data["state_previous_last_updated"])
    return
```

### 5. Call validate_input() in create_undo_data When Needed

If the input model has auto-generated fields (like ChatInput's `message_id`), ensure `validate_input()` is called in `create_undo_data()` so those fields are populated:

```python
def create_undo_data(self, input_data: ModalityInput) -> dict[str, Any]:
    if not isinstance(input_data, ChatInput):
        raise ValueError(...)
    
    # Ensure input is validated (auto-generates message_id for send_message)
    input_data.validate_input()
    
    # Now input_data.message_id is guaranteed to be set
    ...
```

This is necessary because `create_undo_data` is called BEFORE `apply_input`, but `apply_input` normally calls `validate_input()`.

## Serialization Guidelines

### Datetime Fields
Use ISO format for datetime serialization (undo data may be persisted):

```python
# Capture
"previous_last_updated": location.last_updated.isoformat()

# Restore
datetime.fromisoformat(undo_data["previous_last_updated"])
```

### Pydantic Models
Use `.model_dump()` for Pydantic model serialization:

```python
# Capture
"previous_report": location.current_report.model_dump()

# Restore
WeatherReport(**undo_data["previous_report"])
```

## Handling Capacity Limits

If a modality has history/capacity limits (e.g., `max_history_per_location`, `max_history_size`), the undo must handle edge cases:

```python
def create_undo_data(self, input_data):
    # Check if we're at capacity BEFORE apply
    if len(location.report_history) >= self.max_history_per_location:
        oldest = location.report_history[0]
        undo_data["removed_history_entry"] = {
            "timestamp": oldest.timestamp.isoformat(),
            "report": oldest.report.model_dump(),
        }

def apply_undo(self, undo_data):
    # Restore removed entry at position 0 if it was captured
    if "removed_history_entry" in undo_data:
        restored_entry = ...
        location.report_history.insert(0, restored_entry)
```

## Handling Side Effects

### Entity Creation as Side Effect

When an operation creates a new entity as a side effect (e.g., `send_message` creating a new conversation), track this for proper undo:

```python
def create_undo_data(self, input_data):
    is_new_conversation = conversation_id not in self.conversations
    undo_data = {
        "action": "remove_message",
        "message_id": input_data.message_id,
        "was_new_conversation": is_new_conversation,
        ...
    }
    
    if not is_new_conversation:
        # Only capture metadata if conversation already exists
        undo_data["previous_conv_metadata"] = {...}

def apply_undo(self, undo_data):
    if undo_data.get("was_new_conversation"):
        # Remove the conversation that was created
        del self.conversations[conversation_id]
    else:
        # Restore previous conversation metadata
        ...
```

### Maintaining Collection Order

After restoring items to a sorted collection, re-sort to maintain invariants:

```python
def apply_undo(self, undo_data):
    # Restore message
    self.messages.append(restored_message)
    # Re-sort to maintain chronological order
    self.messages.sort(key=lambda m: (m.timestamp, m.message_id))
```

## Handling Operations with Multiple Variants

Some operations have different behaviors based on scope or mode (e.g., CalendarState's recurring event operations with `recurrence_scope`). Each variant may require a different undo action:

```python
def create_undo_data(self, input_data):
    if input_data.operation == "update":
        event = self.events[input_data.event_id]
        previous_event = event.model_dump(mode="json")
        
        if event.is_recurring():
            if input_data.recurrence_scope == "all":
                # Simple update - restore full event
                return {"action": "restore_event", "previous_event": previous_event, ...}
            elif input_data.recurrence_scope == "this_and_future":
                # Creates a split event - need to find and remove it
                return {
                    "action": "restore_event_remove_split",
                    "previous_event": previous_event,
                    "previous_event_ids": list(calendar.event_ids),  # To find created event
                    ...
                }
            elif input_data.recurrence_scope == "this" and input_data.recurrence_id:
                # Creates a modified occurrence - need to find and remove it  
                return {
                    "action": "restore_event_remove_occurrence",
                    "previous_event": previous_event,
                    "recurrence_id": input_data.recurrence_id,
                    "previous_event_ids": list(calendar.event_ids),
                    ...
                }
        # Non-recurring: simple restore
        return {"action": "restore_event", "previous_event": previous_event, ...}
```

### Tracking Created Entities from Scope Operations

When an operation creates new entities as a side effect (e.g., split events), capture enough information to identify them later:

```python
# Capture previous entity IDs before operation
"previous_event_ids": list(calendar.event_ids)

# In apply_undo, find created entity by diff
created_event_ids = set(calendar.event_ids) - set(undo_data["previous_event_ids"])
for created_id in created_event_ids:
    del self.events[created_id]
    calendar.event_ids.remove(created_id)
```

## Handling Bulk Operations

Some operations affect multiple items at once (e.g., `clear_conversation` removes all messages in a conversation). The undo must capture and restore ALL affected items:

```python
def create_undo_data(self, input_data):
    if input_data.operation == "clear_conversation":
        # Capture ALL messages that will be cleared
        conv_messages = [m for m in self.messages if m.conversation_id == conversation_id]
        cleared_messages = [
            {
                "message_id": m.message_id,
                "content": m.content,
                "timestamp": m.timestamp.isoformat(),
                ...
            }
            for m in conv_messages
        ]
        return {
            "action": "restore_conversation",
            "cleared_messages": cleared_messages,
            "conv_metadata": {...},  # Also capture conversation metadata
        }

def apply_undo(self, undo_data):
    if action == "restore_conversation":
        # Restore ALL cleared messages
        for msg_data in undo_data.get("cleared_messages", []):
            restored_message = ChatMessage(...)
            self.messages.append(restored_message)
        self.messages.sort(key=lambda m: (m.timestamp, m.message_id))
        
        # Restore conversation metadata
        if undo_data.get("conv_metadata"):
            self.conversations[conversation_id] = ConversationMetadata(...)
```

## Error Handling

### In create_undo_data()

Validate input type and fail fast:

```python
if not isinstance(input_data, WeatherInput):
    raise ValueError(
        f"WeatherState can only create undo data for WeatherInput, got {type(input_data)}"
    )
```

### In apply_undo()

Check for:
- Missing `action` field → `ValueError`
- Missing required keys → `ValueError`
- Unknown action types → `ValueError`
- State inconsistencies (e.g., entity doesn't exist) → `RuntimeError`

```python
action = undo_data.get("action")
if not action:
    raise ValueError("Undo data missing 'action' field")

location_key = undo_data.get("location_key")
if not location_key:
    raise ValueError("Undo data missing 'location_key' field")

if location_key not in self.locations:
    raise RuntimeError(f"Cannot undo: location '{location_key}' not found in state")

if action not in ("remove_location", "restore_previous"):
    raise ValueError(f"Unknown undo action: {action}")
```

## Testing Patterns

### Test Categories to Cover

**create_undo_data tests:**
- Each operation type captures correct action
- Captures state-level metadata
- Handles edge cases (capacity limits, etc.)
- Raises for invalid input type
- Doesn't modify state (read-only)

**apply_undo tests:**
- Each operation type reverses correctly
- Restores item-level metadata
- Restores state-level metadata
- Handles edge cases (capacity restoration)
- Error handling (missing fields, unknown actions, missing entities)
- Full cycle tests (create_undo → apply → apply_undo = original state)
- Multiple sequential undos work correctly

### Important Test Pitfalls

#### Use Different Data for Before/After

When testing that state changed after an operation, ensure the inputs have **actually different data**:

```python
# BAD - may have identical report data
second_weather = create_weather_input(latitude=first_weather.latitude, ...)

# GOOD - explicitly different report  
second_weather = create_weather_input(
    latitude=first_weather.latitude, 
    report=RAINY_WEATHER.report  # Different fixture
)
```

#### Compare model_dump(), Not Object References

Objects may be moved, replaced, or recreated during undo. Compare by value:

```python
# Store a copy of the data, not the object reference
original_report_dict = state.locations[location_key].current_report.model_dump()

# Compare by value after undo
assert state.locations[location_key].current_report.model_dump() == original_report_dict
```

#### Non-Message Operations Need Special Input Construction

For operations like `delete_message` or `clear_conversation`, the input may have different required/optional fields than `send_message`. Check the input validation rules:

```python
# delete_message doesn't need content or role
delete_input = ChatInput(
    timestamp=datetime.now(timezone.utc),
    operation="delete_message",
    message_id=msg_input.message_id,
    conversation_id="test",
)
# NOT: content="" (this fails validation for text content)
```

#### Test Snapshot Keys Match Implementation

Verify the actual keys returned by `get_snapshot()` before writing assertions:

```python
# Check what keys actually exist
snapshot = state.get_snapshot()
# May be "total_message_count", not "message_count"
assert restored_snapshot["total_message_count"] == original_snapshot["total_message_count"]
```

## Modality-Specific Considerations

| Modality | Likely Operations | Key Undo Considerations |
|----------|------------------|------------------------|
| **Location** | Update location | Store previous coords, address, history entry if at capacity |
| **Time** | Update preferences | Store previous timezone, format, settings history entry |
| **Weather** | Add/update location | Add: store location_key. Update: store full previous report + metadata |
| **Chat** | send/delete/clear | send: store message_id + was_new_conversation flag + capacity overflow. delete: store full message. clear: store ALL messages + metadata |
| **Email** | Add/move/delete email | Add: store email_id. Delete/move: store full email + original folder |
| **Calendar** | Create/update/delete event | Create: store event_id + was_new_calendar. Update: store full previous event + handle recurring splits. Delete: store full event + handle recurring exceptions |
| **SMS** | Send/receive/delete | Send/receive: store message_id. Delete: store full message |

**Rule of thumb**: The more destructive the operation, the more data needs to be captured.

## Implementation Checklist

For each modality:

- [ ] Identify all operation types in `apply_input()`
- [ ] For each operation type, determine minimum undo data needed
- [ ] Implement `create_undo_data()`:
  - [ ] Validate input type
  - [ ] Call `validate_input()` if input has auto-generated fields
  - [ ] Return dict with `action` key
  - [ ] Include `state_previous_update_count` and `state_previous_last_updated`
  - [ ] Capture operation-specific data
  - [ ] Handle capacity edge cases
  - [ ] Handle side effects (entity creation)
  - [ ] Handle no-op cases (return `"action": "noop"`)
- [ ] Implement `apply_undo()`:
  - [ ] Validate required fields
  - [ ] Handle `"noop"` action first (restore metadata only)
  - [ ] Dispatch on `action` type
  - [ ] Restore item-level state
  - [ ] Handle side effect cleanup (remove created entities)
  - [ ] Re-sort collections if needed
  - [ ] Restore state-level metadata
  - [ ] Handle capacity restoration
  - [ ] Proper error handling
- [ ] Write tests:
  - [ ] create_undo_data tests for each operation type
  - [ ] apply_undo tests for each operation type
  - [ ] No-op handling tests
  - [ ] Side effect tests (entity creation/removal)
  - [ ] Bulk operation tests (if applicable)
  - [ ] Error handling tests
  - [ ] Full cycle integration tests
  - [ ] Multiple sequential undo tests

## Progress Tracking

| Modality | create_undo_data | apply_undo | Tests | Notes |
|----------|-----------------|------------|-------|-------|
| Weather  | ✅ | ✅ | ✅ 20 tests | First implementation, established patterns |
| Chat     | ✅ | ✅ | ✅ 29 tests | Multiple operations, no-op handling, bulk clear |
| Calendar | ✅ | ✅ | ✅ 29 tests | Recurring events with scope variations (this/this_and_future/all) |
| Location | ✅ | ✅ | ✅ 19 tests | Single operation type, history capacity handling |
| Time     | ✅ | ✅ | ✅ 17 tests | Single operation type, always has defaults so always creates history |
| Email    | ✅ | ✅ | ✅ 40 tests | 19 operation types, bulk operations, thread restoration, label cleanup |
| SMS      | ✅ | ✅ | ✅ 38 tests | 13 action types, group/participant management, mark_all_read affects multiple messages |
