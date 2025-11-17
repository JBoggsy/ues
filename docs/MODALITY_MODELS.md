# Modality Models Architecture

## Overview

This document outlines the design of the `ModalityInput` and `ModalityState` base classes, their interactions, and the patterns they establish for the UES simulation system.

## Core Concepts

### Event-Sourcing Pattern

The UES follows an event-sourcing architecture where:
1. **Events** carry **Inputs** that describe what should change
2. **States** represent the current state of the system
3. **Inputs** are applied to **States** to produce new states
4. The sequence of events + initial states = complete simulation history

### The Three-Part Flow

```
SimulatorEvent → ModalityInput → ModalityState
     (when)         (what)          (current)
```

## ModalityInput Base Class

### Purpose
`ModalityInput` represents **what changes** when an event occurs. It's the payload that describes a state mutation.

### Required Attributes (Common to All Subclasses)

1. **`modality_type: str`** - Identifies which modality this input affects (e.g., "email", "location", "text")
   - Used for routing inputs to correct states
   - Must be a class-level constant or computed property
   - Enables type-safe state lookups in Environment

2. **`timestamp: datetime`** - When this input logically occurred (simulator time)
   - Not when the event is scheduled (that's in SimulatorEvent)
   - Relevant for inputs that need temporal context (e.g., message sent time)
   - May differ from event scheduled_time for retroactive inputs

3. **`input_id: str`** (optional) - Unique identifier for this specific input
   - Useful for tracking which inputs have been applied
   - Enables idempotency checks (prevent duplicate application)
   - Generated automatically if not provided

### Required Methods

#### 1. `validate_input() -> None`
```python
def validate_input(self) -> None:
    """Perform modality-specific validation beyond Pydantic field validation.
    
    Examples:
    - EmailInput: Validate email address formats, check attachment sizes
    - LocationInput: Ensure lat/long within valid ranges
    - CalendarEventInput: Verify start_time < end_time
    
    Raises:
        ValueError: If validation fails with descriptive message
    """
```

**Rationale**: Pydantic handles type validation, but complex cross-field or semantic validation needs custom logic.

#### 2. `get_affected_entities() -> list[str]`
```python
def get_affected_entities(self) -> list[str]:
    """Return list of entity IDs affected by this input.
    
    Examples:
    - EmailInput: Returns [thread_id] or generates one if new thread
    - TextInput: Returns [conversation_id]
    - CalendarEventInput: Returns [event_id]
    
    Returns:
        List of string identifiers for entities this input affects
    """
```

**Rationale**: Allows the system to track which entities are modified by which events. Useful for:
- Conflict detection (multiple events affecting same entity)
- Dependency tracking
- Query optimization (which states need updating)

#### 3. `get_summary() -> str`
```python
def get_summary(self) -> str:
    """Return human-readable one-line summary of this input.
    
    Examples:
    - EmailInput: "Email from john@example.com: 'Meeting Tomorrow'"
    - LocationInput: "Moved to 123 Main St, Springfield"
    - TextInput: "Text from (555) 123-4567: 'Running late'"
    
    Returns:
        Brief, human-readable description for logging/UI display
    """
```

**Rationale**: Essential for debugging, logging, and UI display. Users need to quickly understand what an event does.

### Optional Methods (Can Be Overridden)

#### `should_merge_with(other: ModalityInput) -> bool`
```python
def should_merge_with(self, other: 'ModalityInput') -> bool:
    """Determine if this input should be merged with another input.
    
    Default: False (no merging)
    
    Examples:
    - LocationInput: Merge if timestamps are within 1 second (just position updates)
    - WeatherInput: Merge if timestamps are within 5 minutes (redundant updates)
    
    Args:
        other: Another input of the same type
    
    Returns:
        True if inputs should be merged, False otherwise
    """
    return False
```

**Rationale**: Prevents duplicate or redundant inputs from cluttering the simulation. Subclasses opt-in to merging behavior.

## ModalityState Base Class

### Purpose
`ModalityState` represents **what currently exists** in a modality. It's the current snapshot of that aspect of the user's environment.

### Required Attributes (Common to All Subclasses)

1. **`modality_type: str`** - Identifies which modality this state represents
   - Must match corresponding ModalityInput.modality_type
   - Class-level constant for type safety

2. **`last_updated: datetime`** - Simulator time when this state was last modified
   - Automatically updated when inputs are applied
   - Used for staleness checks and temporal queries

3. **`update_count: int`** - Number of times this state has been modified
   - Starts at 0, increments with each applied input
   - Useful for debugging and change tracking

### Required Methods

#### 1. `apply_input(input_data: ModalityInput) -> None`
```python
def apply_input(self, input_data: ModalityInput) -> None:
    """Apply a ModalityInput to modify this state.
    
    This is the core state mutation method. Each subclass implements
    the specific logic for how inputs change state.
    
    Examples:
    - EmailState.apply_input(EmailInput): Add email to inbox, update thread
    - LocationState.apply_input(LocationInput): Update current location, add to history
    - TextState.apply_input(TextInput): Add message to conversation
    
    Args:
        input_data: The ModalityInput to apply to this state
    
    Raises:
        ValueError: If input_data is wrong type or incompatible
        RuntimeError: If state is in invalid condition for this input
    """
```

**Rationale**: This is where the event-sourcing magic happens. It's the single point where inputs modify state, making the system predictable and debuggable.

**Important Design Decision**: This method modifies state **in-place** rather than returning a new state. Why?
- Performance: Avoids copying large state objects
- Simplicity: Easier to reason about for developers
- Consistency: All modifications go through one path
- Trade-off: Must be careful about concurrent modifications (future consideration)

#### 2. `get_snapshot() -> dict`
```python
def get_snapshot(self) -> dict:
    """Return a complete snapshot of current state for API responses.
    
    This is what external agents see when they query the modality.
    Should include all relevant information but may omit internal metadata.
    
    Examples:
    - EmailState: Returns {inbox: [...], sent: [...], unread_count: 5}
    - LocationState: Returns {current: {...}, history: [...]}
    
    Returns:
        Dictionary representation of current state suitable for API responses
    """
```

**Rationale**: Separates internal representation from external API. Allows state to have complex internal structures while presenting clean API.

#### 3. `validate_state() -> list[str]`
```python
def validate_state(self) -> list[str]:
    """Validate internal state consistency and return any issues.
    
    Examples:
    - EmailState: Check all thread_ids reference existing threads
    - CalendarState: Check no overlapping events (if that's a constraint)
    - TextState: Verify all conversations have at least one message
    
    Returns:
        List of validation error messages (empty list if valid)
    """
```

**Rationale**: After applying many inputs, state might become inconsistent. This method catches corruption and helps with debugging.

#### 4. `query(query_params: dict) -> dict`
```python
def query(self, query_params: dict) -> dict:
    """Execute a query against this state.
    
    Allows filtering, searching, and aggregating state data without
    exposing internal structure.
    
    Examples:
    - EmailState.query({type: "unread", limit: 10}): Get 10 unread emails
    - TextState.query({from: "555-1234", since: datetime(...)}): Get messages from number
    - CalendarState.query({date: "2024-03-15"}): Get events on specific date
    
    Args:
        query_params: Dictionary of query parameters (modality-specific)
    
    Returns:
        Dictionary containing query results
    """
```

**Rationale**: States can be large (thousands of emails, hundreds of calendar events). Agents need efficient querying without pulling entire state.

### Optional Methods

#### `get_diff(other: ModalityState) -> dict`
```python
def get_diff(self, other: 'ModalityState') -> dict:
    """Calculate difference between this state and another state.
    
    Useful for showing what changed, implementing undo, or incremental updates.
    
    Args:
        other: Another state of the same type to compare against
    
    Returns:
        Dictionary describing the differences
    """
```

**Rationale**: Nice-to-have for advanced features like showing "what changed" or time-travel debugging.

## SimulatorEvent Integration

### How Events Apply Inputs to States

The `SimulatorEvent` acts as the coordinator:

```python
class SimulatorEvent:
    scheduled_time: datetime
    modality: str  # e.g., "email", "location"
    data: ModalityInput
    status: EventStatus
    agent_id: Optional[str]
    
    def execute(self, environment: Environment) -> None:
        """Execute this event by applying its input to the appropriate state.
        
        1. Validate the input
        2. Look up the correct state from environment
        3. Apply the input to the state
        4. Update event status
        5. Log the execution
        """
        # 1. Validate
        self.data.validate_input()
        
        # 2. Look up state
        state = environment.get_state(self.modality)
        
        # 3. Apply
        state.apply_input(self.data)
        
        # 4. Update status
        self.status = EventStatus.EXECUTED
        
        # 5. Log
        logger.info(f"Event {self.id}: {self.data.get_summary()}")
```

### Key Design Decisions

1. **Events don't modify states directly** - They delegate to `ModalityInput.apply()` via `ModalityState.apply_input()`
2. **States are responsible for their own mutation** - Each state knows how to update itself
3. **Inputs are immutable** - Once created, inputs don't change (they're value objects)
4. **Type safety via modality_type** - String matching ensures correct input types go to correct states

## Environment Integration

### State Management

The `Environment` class manages all modality states:

```python
class Environment:
    modality_states: dict[str, ModalityState]
    time_state: SimulatorTime
    metadata: dict
    
    def get_state(self, modality_type: str) -> ModalityState:
        """Get the state for a specific modality."""
        return self.modality_states[modality_type]
    
    def apply_event(self, event: SimulatorEvent) -> None:
        """Apply an event to the environment."""
        event.execute(self)
```

### State Initialization

States must have sensible defaults:

```python
# Example: Empty EmailState
email_state = EmailState(
    modality_type="email",
    last_updated=initial_time,
    update_count=0,
    inbox=[],
    sent=[],
    drafts=[],
    threads={}
)
```

## Practical Examples

### Example 1: Email Delivery

```python
# 1. Create input
email_input = EmailInput(
    modality_type="email",
    timestamp=datetime(2024, 3, 15, 14, 30),
    from_address="boss@company.com",
    to_addresses=["user@company.com"],
    subject="Q1 Report Due",
    body="Please submit by EOD Friday",
    thread_id=None  # New thread
)

# 2. Create event
event = SimulatorEvent(
    scheduled_time=datetime(2024, 3, 15, 14, 30),
    modality="email",
    data=email_input,
    status=EventStatus.PENDING
)

# 3. Execute event (when simulator reaches 14:30)
event.execute(environment)

# 4. Inside execute(), this happens:
email_state = environment.get_state("email")
email_state.apply_input(email_input)  # Adds to inbox, creates thread
```

### Example 2: Location Update

```python
# 1. Create input
location_input = LocationInput(
    modality_type="location",
    timestamp=datetime(2024, 3, 15, 9, 0),
    lat=40.7128,
    long=-74.0060,
    address="123 Work St, NYC",
    named_location="Office"
)

# 2. Execute via event
location_state.apply_input(location_input)

# 3. Inside apply_input():
# - Updates current_lat, current_long, current_address
# - Adds previous location to history
# - Increments update_count
# - Sets last_updated timestamp
```

## Testing Strategy

### Unit Tests for Each Input
- Validation logic
- get_summary() output
- get_affected_entities() correctness

### Unit Tests for Each State
- apply_input() with various inputs
- query() with different parameters
- validate_state() catches issues
- get_snapshot() returns correct format

### Integration Tests
- Event execution flow
- Multiple inputs applied in sequence
- State consistency after many operations
- Query results match expected state

## Open Questions & Future Considerations
* May need locks, transactions, or optimistic concurrency control.
* Could add `unapply_input()` method if time-travel debugging is needed.

## Summary

The `ModalityInput` and `ModalityState` base classes establish a clean event-sourcing pattern:

- **Inputs** describe changes (immutable value objects)
- **States** hold current data (mutable but controlled)
- **Events** coordinate applying inputs to states (orchestration)
- **Environment** manages the collection of states (container)

This architecture provides:
✅ Clear separation of concerns
✅ Testability (each component in isolation)
✅ Debuggability (full event history)
✅ Extensibility (new modalities follow pattern)
✅ Type safety (modality_type routing)
✅ API-readiness (get_snapshot, query methods)
