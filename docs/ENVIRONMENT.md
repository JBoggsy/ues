# Environment Class Design

## Overview

The `Environment` class represents the **complete current state** of the simulated world at any given simulator time. It is a pure state container that holds modality states and time state, without any orchestration or configuration responsibilities.

## Core Concept

Think of `Environment` as a **snapshot of reality** from the AI agent's perspective at a single point in simulator time. It answers the question: "What is the current state of the world?"

The Environment is:
- **Passive**: It doesn't orchestrate, schedule, or execute anything
- **Current**: It only holds current state, not history or future plans
- **Complete**: It contains everything needed to answer queries about the present moment
- **Mutable**: States within it are modified in-place by event execution

## Separation of Concerns

### Environment vs Other Components

The key architectural question: **What does Environment own?**

- **Environment**: Holds current modality states and time state
- **SimulationEngine**: Orchestrates simulation flow, makes decisions
- **EventQueue**: Stores scheduled future events
- **SimulatorTime**: Tracks time calculations and state
- **SimulationConfig** (future): Stores metadata, settings, initial configuration

### What Environment IS

✅ **State Container**: Holds all current modality states  
✅ **Time Container**: Holds current simulator time state  
✅ **State Accessor**: Provides lookup methods for states  
✅ **Serializable**: Can export current state as dictionary  
✅ **Validatable**: Can check internal consistency  

### What Environment IS NOT

❌ **Orchestrator**: Doesn't manage simulation flow  
❌ **Event Manager**: Doesn't schedule or execute events  
❌ **Configuration Store**: Doesn't hold simulation metadata/settings  
❌ **History Tracker**: Doesn't store past states  
❌ **Time Controller**: Doesn't advance time  
❌ **API Handler**: Doesn't expose REST endpoints  

## Design Rationale

### Why Separate State from Configuration?

**Decision**: Environment only holds current state, not simulation metadata or configuration.

**Rationale**:
1. **Clear Responsibility**: Environment represents "what is now", configuration represents "how the simulation is set up"
2. **Serialization Clarity**: State snapshots should be separate from configuration snapshots
3. **API Design**: GET /environment/state vs GET /simulation/config are semantically different
4. **Reusability**: Same configuration can be used to run multiple simulation instances
5. **State Size**: Environment state can be large and changes frequently; configuration is small and static

**Alternative Considered**: Including metadata in Environment made it unclear whether serialization should include configuration or just current state.

### Why Hold Time State in Environment?

**Decision**: Environment contains the SimulatorTime instance.

**Rationale**:
1. **Temporal Context**: All state is inherently temporal - states exist "at" a time
2. **Event Execution**: Events need to access both state and time when executing
3. **Snapshot Completeness**: A complete state snapshot must include "when"
4. **Simplicity**: One place to pass around (environment) instead of two (states + time)

**Evidence from Code**:
```python
# From models/event.py, line 128:
self.executed_at = environment.time_state.current_time
```

Events access time through environment, reinforcing this design.

## Required Attributes

### 1. `modality_states: dict[str, ModalityState]`

Dictionary mapping modality names to their current state instances.

**Type**: `dict[str, ModalityState]`

**Keys**: String modality identifiers
- "email" → EmailState
- "calendar" → CalendarState  
- "location" → LocationState
- "text" → TextState
- etc.

**Values**: Concrete ModalityState subclass instances
- Must match the modality key
- Hold the complete current state for that modality
- Modified in-place by event execution

**Usage Pattern**:
```python
# Event execution looks up state
state = environment.get_state("email")

# Agent queries state
email_state = environment.modality_states["email"]
inbox = email_state.query({"folder": "inbox"})
```

**Design Considerations**:
- Dictionary allows O(1) lookup by modality name
- Modality names must be unique
- States are mutable (modified in-place during simulation)
- Some modalities may be optional (not all simulations need all modalities)

### 2. `time_state: SimulatorTime`

The current simulator time state.

**Type**: `SimulatorTime`

**Contains**:
- `current_time`: The "virtual now" timestamp
- `time_scale`: Time advancement multiplier
- `is_paused`: Whether time is frozen
- `last_wall_time_update`: Wall-clock anchor for calculations
- `auto_advance`: Whether time advances automatically

**Usage Pattern**:
```python
# Events access current time
executed_at = environment.time_state.current_time

# Engine advances time
environment.time_state.advance(delta)

# API queries time
return {
    "current_time": environment.time_state.current_time,
    "mode": environment.time_state.mode
}
```

**Design Considerations**:
- Single source of truth for simulator time
- Passed by reference (changes visible everywhere)
- Updated in-place by SimulationEngine
- Accessed by events during execution

## Required Methods

### 1. `get_state(modality: str) -> ModalityState`

Retrieve the state for a specific modality.

```python
def get_state(self, modality: str) -> ModalityState:
    """Retrieve the state for a specific modality.
    
    This is the primary method used by events to access the state
    they need to modify.
    
    Args:
        modality: The modality name (e.g., "email", "location")
    
    Returns:
        The current state for that modality
    
    Raises:
        KeyError: If modality doesn't exist in this environment
    
    Example:
        >>> state = environment.get_state("email")
        >>> state.apply_input(email_input)
    """
```

**Rationale**: 
- Primary access method used by event execution
- Raises KeyError (not returns None) to catch configuration errors early
- Simple delegation to dictionary lookup with error handling

**Evidence**: Used in models/event.py line 119:
```python
state = environment.get_state(self.modality)
```

### 2. `get_snapshot() -> dict[str, dict]`

Export complete current state as nested dictionaries.

```python
def get_snapshot(self) -> dict[str, dict]:
    """Export complete current state snapshot.
    
    Creates a nested dictionary representation of all current state:
    - Time state (current_time, time_scale, etc.)
    - All modality states (each as a dictionary)
    
    This snapshot represents a complete "freeze frame" of the simulation
    at the current moment. It can be saved, compared, or restored.
    
    Does NOT include:
    - Event queue (future state)
    - Simulation configuration/metadata
    - Execution history
    
    Returns:
        Dictionary with 'time' and 'modalities' keys
    
    Example:
        >>> snapshot = environment.get_snapshot()
        >>> snapshot.keys()
        dict_keys(['time', 'modalities'])
        >>> snapshot['time']['current_time']
        datetime(2024, 3, 15, 14, 30, tzinfo=timezone.utc)
        >>> snapshot['modalities']['email']
        {'modality_type': 'email', 'inbox': [...], ...}
    """
```

**Rationale**:
- Essential for saving simulation checkpoints
- Enables state comparison (before/after)
- Clean separation from configuration
- Delegates to each state's get_snapshot() method

**Usage Scenarios**:
- API endpoint: GET /environment/state → returns current snapshot
- Checkpoint saving: periodic snapshots for resume capability
- Debugging: compare state before/after event execution
- Testing: assert expected state shape

### 3. `validate() -> list[str]`

Validate environment consistency.

```python
def validate(self) -> list[str]:
    """Validate environment consistency and return any issues.
    
    Checks:
    - time_state is valid (has valid time, scale, etc.)
    - All modality states are valid (call state.validate())
    - No None or invalid state references
    - Modality names match state types
    
    Returns:
        List of validation error messages (empty if valid)
    
    Example:
        >>> errors = environment.validate()
        >>> if errors:
        ...     print(f"Invalid environment: {errors}")
        >>> # []
    """
```

**Rationale**:
- Catches configuration errors before simulation starts
- Useful for debugging state corruption
- Each component validates itself (delegation pattern)
- Returns list of strings (not raises) for comprehensive error reporting

**Validation Checks**:
1. `time_state` is not None and is valid
2. `modality_states` is not empty (at least one modality)
3. Each modality state is valid (delegate to `state.validate()`)
4. Modality keys match state.modality_type values
5. No duplicate modality types

### 4. `list_modalities() -> list[str]`

List all available modalities in this environment.

```python
def list_modalities(self) -> list[str]:
    """List all available modality names.
    
    Returns sorted list of modality names that can be queried
    or accessed in this environment.
    
    Returns:
        Sorted list of modality name strings
    
    Example:
        >>> environment.list_modalities()
        ['calendar', 'email', 'location', 'text', 'weather']
    """
```

**Rationale**:
- Useful for API discovery (what modalities are available?)
- Helps agents understand their environment
- Simple convenience method
- Sorted for consistent ordering

## Interaction Patterns

### Pattern 1: Event Execution

The primary interaction pattern for Environment.

```python
# From models/event.py execute() method

def execute(self, environment: Environment) -> None:
    """Execute event by modifying environment state."""
    
    # 1. Validate input
    self.data.validate_input()
    
    # 2. Get appropriate state from environment
    state = environment.get_state(self.modality)
    
    # 3. Apply input to state (modifies environment in-place)
    state.apply_input(self.data)
    
    # 4. Record execution time from environment
    self.executed_at = environment.time_state.current_time
```

**Key Points**:
- Environment is passed to event
- Event looks up its target state
- State is modified in-place
- Current time is accessed for execution timestamp

### Pattern 2: State Query (Agent/API)

Agents and API endpoints query current state.

```python
# Agent wants to check email inbox

# Get email state
email_state = environment.get_state("email")

# Query specific data
inbox_emails = email_state.query({
    "folder": "inbox",
    "unread": True,
    "limit": 10
})

# Process results
for email in inbox_emails:
    agent.process_email(email)
```

**Key Points**:
- Direct state access for queries
- No event needed for read operations
- State provides query methods
- Environment is just the container

### Pattern 3: Snapshot Export

Saving current state for checkpointing or debugging.

```python
# API endpoint: GET /environment/state

snapshot = environment.get_snapshot()

return {
    "timestamp": snapshot["time"]["current_time"],
    "modalities": snapshot["modalities"],
    "modality_count": len(snapshot["modalities"])
}
```

**Key Points**:
- Complete state export
- Nested dictionary structure
- Separates time from modality states
- Can be serialized to JSON

### Pattern 4: Validation

Checking environment consistency before or during simulation.

```python
# Before starting simulation

errors = environment.validate()

if errors:
    raise ValueError(
        f"Cannot start simulation - environment is invalid:\n" +
        "\n".join(f"  - {error}" for error in errors)
    )

# Start simulation
engine.start()
```

**Key Points**:
- Validation before simulation starts
- Comprehensive error reporting
- Each component validates itself
- Fails fast on configuration errors

### Pattern 5: Time Access

Events and components access current simulator time.

```python
# Inside event execution

# Get current time for timestamp
current_time = environment.time_state.current_time

# Check if time is paused
if environment.time_state.is_paused:
    logger.warning("Executing event while time is paused")

# Access time mode
mode = environment.time_state.mode
```

**Key Points**:
- Time state always available through environment
- Single source of truth
- Read-only access from events
- Only SimulationEngine modifies time

## Error Handling

### Missing Modality

```python
# Event tries to access non-existent modality

try:
    state = environment.get_state("nonexistent")
except KeyError as e:
    # This is a configuration error - simulation is misconfigured
    logger.error(f"Event references unknown modality: {e}")
    # Event execution fails, simulation continues
```

**Rationale**: Missing modality is a configuration error that should be caught during validation, but if it happens during execution, fail the individual event rather than crashing the simulation.

### Invalid State

```python
# State validation fails

errors = environment.validate()

if "EmailState has invalid email addresses" in errors:
    # Configuration problem - fix before running
    raise ValueError("Environment has invalid state - cannot start simulation")
```

**Rationale**: State validation should be run before simulation starts. Invalid state is a setup error, not a runtime condition.

### None Values

```python
# Defensive checks

def get_state(self, modality: str) -> ModalityState:
    """Get state with defensive checks."""
    
    if modality not in self.modality_states:
        raise KeyError(f"Modality '{modality}' not found in environment")
    
    state = self.modality_states[modality]
    
    if state is None:
        raise ValueError(f"State for modality '{modality}' is None")
    
    return state
```

**Rationale**: None states should never happen (validation should prevent), but defensive checks provide better error messages if corruption occurs.

## Performance Considerations

### Memory Usage

**Consideration**: Environment holds complete current state, which can be large.

**Implications**:
- Email state with thousands of messages
- File system state with full directory tree
- Calendar state with years of events

**Mitigations**:
1. States should implement efficient storage (don't duplicate data)
2. Use lazy loading where possible (load details on query)
3. Implement state pruning (archive old emails, etc.)
4. Monitor memory usage in long-running simulations

### State Lookup

**Consideration**: `get_state()` is called for every event execution.

**Performance**: O(1) dictionary lookup - not a concern even at high event rates.

### Snapshot Export

**Consideration**: `get_snapshot()` creates deep nested dictionary.

**Implications**:
- Can be expensive for large states
- Blocks execution while serializing

**Mitigations**:
1. Don't snapshot too frequently
2. Use async/background snapshots for long-running simulations
3. Implement incremental snapshots (only changed states)
4. Consider binary serialization for large states

## Testing Strategy

### Unit Tests

**Test State Access**:
```python
def test_get_state_existing_modality():
    """get_state returns correct state for existing modality."""
    env = Environment(...)
    email_state = env.get_state("email")
    assert isinstance(email_state, EmailState)
    assert email_state.modality_type == "email"

def test_get_state_missing_modality():
    """get_state raises KeyError for missing modality."""
    env = Environment(...)
    with pytest.raises(KeyError, match="nonexistent"):
        env.get_state("nonexistent")
```

**Test Validation**:
```python
def test_validate_empty_states():
    """validate returns error if no modality states."""
    env = Environment(modality_states={}, time_state=...)
    errors = env.validate()
    assert any("empty" in err.lower() for err in errors)

def test_validate_invalid_state():
    """validate returns errors from invalid states."""
    invalid_state = EmailState(...)  # Intentionally invalid
    env = Environment(modality_states={"email": invalid_state}, ...)
    errors = env.validate()
    assert len(errors) > 0
```

**Test Snapshot**:
```python
def test_get_snapshot_structure():
    """get_snapshot returns correct structure."""
    env = Environment(...)
    snapshot = env.get_snapshot()
    
    assert "time" in snapshot
    assert "modalities" in snapshot
    assert "current_time" in snapshot["time"]
    assert "email" in snapshot["modalities"]

def test_get_snapshot_serializable():
    """get_snapshot returns JSON-serializable data."""
    env = Environment(...)
    snapshot = env.get_snapshot()
    
    # Should not raise
    json_str = json.dumps(snapshot, default=str)
    assert len(json_str) > 0
```

### Integration Tests

**Test with Event Execution**:
```python
def test_event_modifies_environment():
    """Event execution modifies environment state in-place."""
    env = Environment(...)
    initial_snapshot = env.get_snapshot()
    
    # Create and execute event
    event = SimulatorEvent(
        scheduled_time=env.time_state.current_time,
        modality="email",
        data=EmailInput(...)
    )
    event.execute(env)
    
    # State should be different
    final_snapshot = env.get_snapshot()
    assert initial_snapshot != final_snapshot
```

**Test with SimulationEngine**:
```python
def test_engine_uses_environment():
    """SimulationEngine accesses environment correctly."""
    env = Environment(...)
    queue = EventQueue(events=[...])
    engine = SimulationEngine(environment=env, event_queue=queue)
    
    engine.advance_time(timedelta(hours=1))
    
    # Environment time should be updated
    assert env.time_state.current_time > initial_time
```

## Design Decisions

### 1. In-Place State Modification

**Decision**: States are modified in-place, not replaced.

**Rationale**:
- Consistent with `ModalityState.apply_input()` pattern
- Avoids expensive copying
- Simpler reference management
- Matches how real state works (mutates over time)

**Alternative Considered**: Immutable states that return new instances. Rejected due to performance concerns and complexity.

### 2. Dictionary for State Storage

**Decision**: Use `dict[str, ModalityState]` not list or tuple.

**Rationale**:
- O(1) lookup by modality name
- Clear key-value semantics
- Easy serialization to JSON
- Extensible (add new modalities without code changes)

**Alternative Considered**: List of states with linear search. Rejected due to performance and clarity.

### 3. No Configuration Storage

**Decision**: Environment doesn't hold simulation metadata or configuration.

**Rationale**:
- Clear separation of state (current) vs configuration (setup)
- Different serialization needs
- Different API endpoints
- Different update patterns

**Alternative Considered**: Including metadata dict in Environment. Rejected due to unclear responsibilities.

### 4. Time State Included

**Decision**: Environment contains SimulatorTime instance.

**Rationale**:
- States are inherently temporal
- Events need both state and time
- Simpler API (one object to pass)
- Complete snapshot includes time

**Alternative Considered**: Separate time parameter in all methods. Rejected due to API complexity.

### 5. Mutable Reference to Time

**Decision**: `time_state` is mutable, changes visible to all references.

**Rationale**:
- Matches how time works (advances globally)
- Simpler than updating all references
- Consistent with state modification pattern

**Consideration**: Must be careful not to accidentally create multiple time instances.

## Future Considerations

### 1. State History

**Question**: Should Environment track state history?

**Current Answer**: No - Environment only holds current state.

**Future**: Could add a separate StateHistory component that snapshots environment over time.

### 2. Lazy State Loading

**Question**: Should states be loaded lazily?

**Current Answer**: No - all states present in memory.

**Future**: For very large simulations, could implement lazy loading where states are loaded on first access.

### 3. State Diff

**Question**: Should Environment provide state diffing?

**Current Answer**: No - use `get_snapshot()` and compare externally.

**Future**: Could add `get_diff(other: Environment) -> dict` for efficient state comparison.

### 4. Partial Snapshots

**Question**: Should we support snapshotting specific modalities?

**Current Answer**: No - always snapshot everything.

**Future**: Could add `get_snapshot(modalities: list[str])` for partial exports.

### 5. State Locking

**Question**: Should we prevent concurrent state modifications?

**Current Answer**: No - single-threaded execution assumed.

**Future**: If multi-threaded simulation needed, would need locking or transaction semantics.

## Summary

The `Environment` class is a **pure state container** with minimal responsibilities:

✅ **Holds current state** - All modality states plus time state  
✅ **Provides access** - Simple lookup methods  
✅ **Validates consistency** - Ensures internal correctness  
✅ **Exports snapshots** - Serializes current state  

❌ **No orchestration** - Doesn't manage simulation flow  
❌ **No configuration** - Doesn't store metadata or settings  
❌ **No history** - Only current state, not past  
❌ **No events** - Doesn't schedule or execute  

This clean separation makes Environment simple to understand, test, and use throughout the simulation system.
