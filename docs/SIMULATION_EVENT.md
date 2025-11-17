# Simulation Event & Queue Architecture

## Overview

This document outlines the design of `SimulatorEvent` and `EventQueue`, focusing on how they coordinate event execution, interact with simulator time, and delegate responsibilities to the broader simulation system.

## Core Concepts

### Event Lifecycle

```
Created → Scheduled → Pending → Due → Executing → Executed/Failed/Skipped
   ↓         ↓          ↓        ↓        ↓            ↓
 Agent    Queue      Queue    Time      Event      Queue
 /User    Insert    Waiting  Advance   Execute    Update
```

### Separation of Concerns

The key architectural question: **What does each component own?**

- **SimulatorEvent**: Represents a single scheduled action, knows how to execute itself
- **EventQueue**: Manages ordering and retrieval of events, doesn't execute them
- **SimulatorTime**: Tracks current time, doesn't advance itself
- **Simulation Engine** (future): Orchestrates time advancement and event execution
- **Environment**: Holds all state, doesn't manage event scheduling

## SimulatorEvent Class

### Purpose
Represents a **single scheduled action** at a specific simulator time that carries a `ModalityInput` payload.

### Core Responsibilities

1. **Store event data** - Hold all information about when/what/who
2. **Execute itself** - Apply its input to the appropriate state
3. **Track execution status** - Know whether it's pending, executed, failed, etc.
4. **Provide metadata** - Summary, affected entities, validation

### NOT Responsible For

- ❌ Managing time advancement
- ❌ Deciding when to execute (that's the simulation engine's job)
- ❌ Managing the event queue
- ❌ Creating new events (that's agents' job)

### Required Attributes

#### 1. `event_id: str`
- Unique identifier for this event
- Auto-generated UUID
- Used for logging, debugging, event references

#### 2. `scheduled_time: datetime`
- **When** this event should execute (simulator time)
- Immutable once created (events don't reschedule themselves)
- Used for queue ordering and due event detection

#### 3. `modality: str`
- Which modality this event affects ("email", "location", "text")
- Must match a valid modality in the environment
- Used to route the input to the correct state

#### 4. `data: ModalityInput`
- The payload containing what changes
- Strongly typed - must be appropriate ModalityInput subclass
- Validated before execution

#### 5. `status: EventStatus`
- Current execution state
- Enum: PENDING, EXECUTING, EXECUTED, FAILED, SKIPPED, CANCELLED
- Updated as event progresses through lifecycle

#### 6. `created_at: datetime`
- When this event was created (simulator time)
- Useful for debugging, metrics, event age tracking
- Immutable

#### 7. `executed_at: Optional[datetime]`
- When this event was actually executed (simulator time)
- None if not yet executed
- May differ from scheduled_time (late execution)

#### 8. `agent_id: Optional[str]`
- ID of agent that generated this event
- None for user-created or system events
- Used for attribution, debugging, agent metrics

#### 9. `priority: int`
- Secondary ordering for events at same scheduled_time
- Default 0, higher = executed first
- Allows critical events to jump ahead

#### 10. `error_message: Optional[str]`
- Error details if status is FAILED
- None for successful/pending events
- Includes exception message and traceback

#### 11. `metadata: dict[str, Any]`
- Flexible additional data
- Examples: tags, execution duration, retry count
- Extensible without schema changes

### Required Methods

#### 1. `execute(environment: Environment) -> None`
```python
def execute(self, environment: Environment) -> None:
    """Execute this event by applying its input to the appropriate state.
    
    This is the core execution method. It:
    1. Validates the input
    2. Looks up the correct state from environment
    3. Applies the input to the state
    4. Updates event status and timing
    5. Handles errors gracefully
    
    Args:
        environment: The environment containing modality states
    
    Raises:
        ValueError: If modality doesn't exist or input is invalid
        RuntimeError: If event is already executed or in wrong state
    """
```

**Rationale**: Events are responsible for executing themselves. This keeps execution logic close to event data and makes testing easier.

**Design Decision**: Events modify the environment in-place rather than returning a new environment. This is consistent with the `ModalityState.apply_input()` pattern and avoids expensive copying.

#### 2. `can_execute(current_time: datetime) -> bool`
```python
def can_execute(self, current_time: datetime) -> bool:
    """Check if this event is eligible for execution.
    
    An event can execute if:
    - Status is PENDING
    - scheduled_time <= current_time
    - Input is valid
    
    Args:
        current_time: Current simulator time
    
    Returns:
        True if event can be executed, False otherwise
    """
```

**Rationale**: Separates the "can we execute?" check from actual execution. Allows simulation engine to query executability without side effects.

#### 3. `validate() -> list[str]`
```python
def validate(self) -> list[str]:
    """Validate event consistency and return any issues.
    
    Checks:
    - scheduled_time is not in distant past (vs created_at)
    - modality is non-empty and valid format
    - data is compatible with modality
    - status is valid for event age
    
    Returns:
        List of validation error messages (empty if valid)
    """
```

**Rationale**: Events should be self-validating. Catches configuration errors early.

#### 4. `get_summary() -> str`
```python
def get_summary(self) -> str:
    """Return human-readable summary of this event.
    
    Format: "[{scheduled_time}] {modality}: {data.get_summary()}"
    
    Example: "[2024-03-15 14:30] email: Email from boss@company.com: 'Q1 Report Due'"
    
    Returns:
        Brief description for logging and UI display
    """
```

**Rationale**: Delegates to `ModalityInput.get_summary()` for payload details, adds event-level context.

#### 5. `skip(reason: str) -> None`
```python
def skip(self, reason: str) -> None:
    """Mark this event as skipped without executing it.
    
    Used when:
    - Simulation jumps past scheduled_time
    - Event is invalidated by previous events
    - User manually cancels event
    
    Args:
        reason: Why this event was skipped
    """
```

**Rationale**: Skipped events remain in history for debugging. Different from CANCELLED (user action) vs SKIPPED (system decision).

#### 6. `cancel(reason: str) -> None`
```python
def cancel(self, reason: str) -> None:
    """Cancel this event before execution.
    
    Only works if status is PENDING. Once executed, cannot be undone.
    
    Args:
        reason: Why this event was cancelled
    
    Raises:
        RuntimeError: If event is already executed
    """
```

**Rationale**: Explicit cancellation separate from skipping. Allows user/agent to prevent event execution.

### Optional Methods

#### `get_dependencies() -> list[str]`
```python
def get_dependencies(self) -> list[str]:
    """Return list of entity IDs this event depends on.
    
    Used for:
    - Detecting conflicts (multiple events affecting same entity)
    - Ordering events with dependencies
    - Query optimization
    
    Delegates to data.get_affected_entities()
    """
```

**Rationale**: Nice-to-have for advanced scheduling and conflict detection.

## EventQueue Class

### Purpose
Manages an **ordered collection of events** and provides efficient retrieval of due events.

### Core Responsibilities

1. **Maintain event ordering** - Keep events sorted by scheduled_time + priority
2. **Efficient querying** - Quickly find events due for execution
3. **Queue operations** - Add, remove, peek events
4. **Status tracking** - Count pending/executed/failed events

### NOT Responsible For

- ❌ Executing events (that's SimulatorEvent's job)
- ❌ Advancing time (that's SimulatorTime + engine)
- ❌ Creating events (that's agents + users)
- ❌ Managing environment state

### Required Attributes

#### 1. `events: list[SimulatorEvent]`
- All events in the queue (pending, executed, failed, etc.)
- Kept sorted by (scheduled_time, priority, created_at)
- Immutable references (events don't change after insertion)

**Design Question**: Should executed events stay in queue?

**Answer**: Yes, for history tracking. Queue is the event log. We can filter by status for active events.

#### 2. `_next_pending_index: int` (internal optimization)
- Cache index of next pending event
- Avoids repeated linear scans
- Updated when events execute or new events inserted

### Computed Properties (Not Stored)

These are calculated on-demand from the events list:

#### `next_event_time -> Optional[datetime]`
```python
@property
def next_event_time(self) -> Optional[datetime]:
    """Timestamp of the next pending event, or None if queue is empty."""
```

#### `pending_count -> int`
```python
@property
def pending_count(self) -> int:
    """Number of pending events in the queue."""
```

#### `executed_count -> int`
```python
@property  
def executed_count(self) -> int:
    """Number of executed events in the queue."""
```

### Required Methods

#### 1. `add_event(event: SimulatorEvent) -> None`
```python
def add_event(self, event: SimulatorEvent) -> None:
    """Add an event to the queue maintaining sorted order.
    
    Uses bisect to insert in O(n) time (O(log n) search + O(n) insert).
    For bulk inserts, prefer add_events() which sorts once.
    
    Args:
        event: Event to add
    
    Raises:
        ValueError: If event with same event_id already exists
    """
```

**Rationale**: Individual event insertion for agent-generated events during simulation.

#### 2. `add_events(events: list[SimulatorEvent]) -> None`
```python
def add_events(self, events: list[SimulatorEvent]) -> None:
    """Add multiple events to the queue efficiently.
    
    Merges new events with existing ones and sorts once in O(n log n).
    More efficient than calling add_event() repeatedly.
    
    Args:
        events: List of events to add
    
    Raises:
        ValueError: If any event_id conflicts with existing events
    """
```

**Rationale**: Bulk insertion for initial setup or batch agent generation.

#### 3. `get_due_events(current_time: datetime) -> list[SimulatorEvent]`
```python
def get_due_events(self, current_time: datetime) -> list[SimulatorEvent]:
    """Get all pending events with scheduled_time <= current_time.
    
    Returns events in execution order (by scheduled_time, then priority).
    Does NOT modify event status - that's the simulation engine's job.
    
    Args:
        current_time: Current simulator time
    
    Returns:
        List of events ready for execution (may be empty)
    """
```

**Rationale**: The simulation engine calls this when time advances, then executes the returned events.

**Design Decision**: This method returns events but doesn't execute them. Separation of concerns - queue manages ordering, engine manages execution.

#### 4. `peek_next() -> Optional[SimulatorEvent]`
```python
def peek_next(self) -> Optional[SimulatorEvent]:
    """Get the next pending event without removing it.
    
    Returns:
        Next pending event, or None if no pending events
    """
```

**Rationale**: Allows simulation engine to check next event time without modifying queue.

#### 5. `get_events_by_status(status: EventStatus) -> list[SimulatorEvent]`
```python
def get_events_by_status(self, status: EventStatus) -> list[SimulatorEvent]:
    """Get all events with a specific status.
    
    Args:
        status: Status to filter by
    
    Returns:
        List of events with matching status
    """
```

**Rationale**: Useful for queries, debugging, and metrics.

#### 6. `get_events_in_range(start: datetime, end: datetime) -> list[SimulatorEvent]`
```python
def get_events_in_range(
    self, 
    start: datetime, 
    end: datetime,
    status_filter: Optional[EventStatus] = None
) -> list[SimulatorEvent]:
    """Get events scheduled within a time range.
    
    Efficient binary search since events are sorted by time.
    
    Args:
        start: Start of time range (inclusive)
        end: End of time range (inclusive)
        status_filter: Optional status to filter by
    
    Returns:
        Events in the specified time range
    """
```

**Rationale**: Essential for queries like "what events happen tomorrow?" or "show me failed events from last hour".

#### 7. `remove_event(event_id: str) -> SimulatorEvent`
```python
def remove_event(self, event_id: str) -> SimulatorEvent:
    """Remove an event from the queue.
    
    Primarily used for cancelling pending events.
    Executed events typically stay in queue for history.
    
    Args:
        event_id: ID of event to remove
    
    Returns:
        The removed event
    
    Raises:
        KeyError: If event_id not found
    """
```

**Rationale**: Allows cancelling scheduled events before execution.

#### 8. `clear_executed(before: Optional[datetime] = None) -> int`
```python
def clear_executed(self, before: Optional[datetime] = None) -> int:
    """Remove executed/failed events from queue to save memory.
    
    Args:
        before: Only remove events executed before this time (None = all)
    
    Returns:
        Number of events removed
    """
```

**Rationale**: For long-running simulations, the queue can grow large. Allows pruning old history.

#### 9. `validate() -> list[str]`
```python
def validate(self) -> list[str]:
    """Validate queue consistency.
    
    Checks:
    - Events are properly sorted
    - No duplicate event_ids
    - All events are valid (call event.validate())
    - Status counts match actual events
    
    Returns:
        List of validation errors (empty if valid)
    """
```

**Rationale**: Catches queue corruption, useful for debugging.

### Internal Helpers

#### `_sort_events() -> None`
```python
def _sort_events(self) -> None:
    """Sort events by (scheduled_time, -priority, created_at).
    
    Called after bulk insertions or modifications.
    Negative priority so higher priority executes first.
    """
```

#### `_find_insert_index(event: SimulatorEvent) -> int`
```python
def _find_insert_index(self, event: SimulatorEvent) -> int:
    """Find correct insertion index using binary search.
    
    Returns index where event should be inserted to maintain sort order.
    """
```

## Interaction Patterns

### Pattern 1: Time Advances, Events Execute

```python
# Simulation Engine orchestrates this flow

# 1. Check if any events are due
due_events = event_queue.get_due_events(simulator_time.current_time)

# 2. Execute each event in order
for event in due_events:
    try:
        event.execute(environment)
    except Exception as e:
        # Event handles its own failure status
        logger.error(f"Event {event.event_id} failed: {e}")

# 3. Update simulator time
simulator_time.advance(delta)
```

**Key Point**: Queue provides events, engine executes them, events modify environment.

### Pattern 2: Agent Generates New Event

```python
# Agent decides to create an event

# 1. Agent creates input
email_input = EmailInput(
    modality_type="email",
    timestamp=current_time,
    from_address="agent@simulator.internal",
    ...
)

# 2. Agent creates event
event = SimulatorEvent(
    scheduled_time=current_time + timedelta(hours=1),
    modality="email",
    data=email_input,
    agent_id=agent.id
)

# 3. Agent adds to queue
event_queue.add_event(event)

# 4. Event will execute when time reaches scheduled_time
```

**Key Point**: Agents create events, queue stores them, engine executes them when due.

### Pattern 3: API Time Jump

```python
# API endpoint: POST /simulator/time/set

# 1. New time is set
new_time = request.json["time"]

# 2. Find all events between old and new time
skipped_events = event_queue.get_events_in_range(
    start=simulator_time.current_time,
    end=new_time,
    status_filter=EventStatus.PENDING
)

# 3. Decide what to do with skipped events
if request.json.get("execute_skipped", False):
    # Execute them all instantly
    for event in skipped_events:
        event.execute(environment)
else:
    # Mark as skipped
    for event in skipped_events:
        event.skip(reason="Time jumped past scheduled_time")

# 4. Update time
simulator_time.current_time = new_time
```

**Key Point**: Queue helps identify affected events, engine decides how to handle them.

### Pattern 4: Event-Driven Mode

```python
# API endpoint: POST /simulator/time/skip-to-next

# 1. Find next pending event
next_event = event_queue.peek_next()

if next_event is None:
    return {"message": "No more events"}

# 2. Jump time to that event
simulator_time.current_time = next_event.scheduled_time

# 3. Get all events at that time (might be multiple)
due_events = event_queue.get_due_events(simulator_time.current_time)

# 4. Execute them
for event in due_events:
    event.execute(environment)

return {
    "time": simulator_time.current_time,
    "executed": len(due_events)
}
```

**Key Point**: Queue enables efficient time skipping by providing next event time.

## EventStatus Enum

```python
from enum import Enum

class EventStatus(str, Enum):
    """Status of a simulator event."""
    
    PENDING = "pending"       # Created, waiting for scheduled_time
    EXECUTING = "executing"   # Currently being executed
    EXECUTED = "executed"     # Successfully completed
    FAILED = "failed"         # Execution raised exception
    SKIPPED = "skipped"       # Time jumped past without execution
    CANCELLED = "cancelled"   # Manually cancelled before execution
```

**Design Choice**: Use string enum for JSON serialization and human readability.

## Error Handling Strategy

### Event Execution Errors

**Question**: What happens if an event fails to execute?

**Answer**: Events are fault-tolerant at the individual level:

```python
def execute(self, environment: Environment) -> None:
    """Execute with comprehensive error handling."""
    
    # Update status
    self.status = EventStatus.EXECUTING
    
    try:
        # Validate input
        self.data.validate_input()
        
        # Get state
        state = environment.get_state(self.modality)
        
        # Apply input
        state.apply_input(self.data)
        
        # Success
        self.status = EventStatus.EXECUTED
        self.executed_at = environment.time_state.current_time
        
    except Exception as e:
        # Failure
        self.status = EventStatus.FAILED
        self.error_message = f"{type(e).__name__}: {str(e)}"
        self.executed_at = environment.time_state.current_time
        
        # Don't re-raise - simulation continues
        # Logging happens at engine level
```

**Rationale**: One bad event shouldn't crash the entire simulation. Failed events are logged but don't block other events.

### Queue Validation Errors

**Question**: What if the queue becomes corrupted?

**Answer**: Queue validates itself and raises exceptions for corruption:

```python
def add_event(self, event: SimulatorEvent) -> None:
    """Add event with validation."""
    
    # Check for duplicate ID
    if any(e.event_id == event.event_id for e in self.events):
        raise ValueError(f"Event {event.event_id} already exists in queue")
    
    # Validate event itself
    errors = event.validate()
    if errors:
        raise ValueError(f"Invalid event: {errors}")
    
    # Add and sort
    self.events.append(event)
    self._sort_events()
```

**Rationale**: Queue corruption is a programming error, not a runtime condition. Fail fast.

## Performance Considerations

### Queue Size

**Problem**: Long simulations accumulate many events.

**Solutions**:
1. Periodic pruning via `clear_executed()`
2. Separate archive storage for old events
3. Lazy loading for historical events (future)

### Event Lookup

**Problem**: Finding due events should be fast.

**Solution**: Binary search on sorted list is O(log n) for next event, O(k) for k due events.

**Alternative Considered**: Priority queue (heapq) would be O(1) for peek, but we need range queries and iteration, so sorted list is better.

### Memory Usage

**Problem**: Each event carries a full ModalityInput which can be large (emails with attachments).

**Solution**: Accept this for MVP. Future optimization could store inputs separately and reference by ID.

## Scope Boundaries

### What SimulatorEvent DOES:
✅ Store event data
✅ Execute itself
✅ Track its own status
✅ Provide metadata

### What SimulatorEvent DOESN'T DO:
❌ Manage time
❌ Schedule other events
❌ Modify the queue
❌ Create state

### What EventQueue DOES:
✅ Store events in order
✅ Provide efficient queries
✅ Maintain sorting invariants
✅ Track event statistics

### What EventQueue DOESN'T DO:
❌ Execute events
❌ Advance time
❌ Create events
❌ Modify environment

### What Simulation Engine DOES (future component):
✅ Advance time
✅ Decide when to execute events
✅ Handle skipped events
✅ Coordinate components
✅ Expose REST API

## Testing Strategy

### SimulatorEvent Tests

**Unit Tests**:
- Event creation and validation
- Execution with mock environment
- Status transitions
- Error handling
- Summary generation

**Integration Tests**:
- Event execution with real states
- Multiple events affecting same state
- Failed events don't crash system

### EventQueue Tests

**Unit Tests**:
- Adding events maintains sort order
- get_due_events returns correct events
- Range queries work correctly
- Status filtering
- Duplicate detection

**Integration Tests**:
- Queue with thousands of events
- Concurrent access patterns (future)
- Memory usage under load

## Open Questions & Future Considerations

### 1. Event Retries

**Question**: Should failed events automatically retry?

**Current Answer**: No. Events fail once and remain failed.

**Future**: Could add retry logic with exponential backoff if needed.

### 2. Event Priorities

**Question**: How should priority work across different modalities?

**Current Answer**: Simple integer, higher = first. All modalities use same scale.

**Future**: Could have modality-specific priority schemes.

### 3. Event Dependencies

**Question**: Should events declare dependencies on other events?

**Current Answer**: No. Events are independent.

**Future**: Could add dependency tracking for complex scenarios (e.g., "email response must come after email sent").

### 4. Concurrent Events

**Question**: What if two events modify the same state simultaneously?

**Current Answer**: Events execute sequentially in priority order. No true concurrency.

**Future**: Could add transaction-like semantics if needed.

### 5. Event Persistence

**Question**: Should events be persisted to disk?

**Current Answer**: Not in MVP. Queue is in-memory only.

**Future**: Could add database backend for durability and distributed simulations.

## Summary

`SimulatorEvent` and `EventQueue` provide a clean event-sourcing foundation:

- **Events** are self-contained actions that know how to execute themselves
- **Queue** is an efficient ordered collection that doesn't execute events
- **Separation** between scheduling (queue), timing (SimulatorTime), and execution (engine)
- **Fault-tolerant** - failed events don't crash the simulation
- **Queryable** - rich API for finding events by time, status, modality
- **Scalable** - efficient algorithms for large event counts

This architecture provides:
✅ Clear responsibilities (events execute, queue orders, engine coordinates)
✅ Testability (each component is independent)
✅ Flexibility (time can jump, skip, fast-forward)
✅ Debuggability (full event history with status tracking)
✅ API-readiness (query methods for REST endpoints)
