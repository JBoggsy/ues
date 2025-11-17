# Simulator Time Management

## Overview

The UES simulator time is **completely decoupled from wall-clock time**. This allows for fast-forwarding through simulations, instant jumps to specific moments, and variable-speed playback without requiring agents to wait in real-time.

This document outlines the design of the `SimulatorTime` class, its responsibilities, methods, and interaction patterns with the broader simulation system.

## Core Concepts

### Simulator Time vs Wall Time
- **Simulator Time**: The virtual time within the simulation (e.g., "March 15, 2024 2:30 PM")
- **Wall Time**: Actual real-world time when the simulation is running
- All events are scheduled using simulator timestamps
- Agents receive simulator time when querying "current time"

### Separation of Concerns

**Key architectural question**: What does `SimulatorTime` own?

- **SimulatorTime**: Tracks current time state, calculates time deltas, provides time queries
- **SimulationEngine**: Decides when/how to advance time, orchestrates execution
- **EventQueue**: Provides next event time for event-driven mode
- **Environment**: Contains SimulatorTime as part of overall state

### Time Control Modes

1. **Paused**: Simulator time is frozen, no events trigger
2. **Real-time (1x)**: Simulator time advances at the same rate as wall time
3. **Fast-forward (Nx)**: Simulator time advances N times faster than wall time
4. **Event-driven**: Instantly jump to the next scheduled event timestamp
5. **Manual**: Explicitly set or advance time via API calls

## Use Cases

### Fast Development/Testing
```
Run simulation at 100x speed to test a full day in minutes
Skip overnight periods with no events
Rapidly iterate on agent behavior across many scenarios
```

### Debugging
```
Pause at specific moments to inspect state
Step through events one at a time
Jump to critical decision points
```

### Realistic Testing
```
Run at 1x speed to observe natural agent timing
Test time-sensitive behaviors (delays, race conditions)
Verify agent handles real-time constraints
```

## SimulatorTime Class

### Purpose
Represents the **current state of time** in the simulation and provides methods for time calculations and queries.

### Core Responsibilities

1. **Store time state** - Current simulator time, scale, pause state
2. **Calculate time deltas** - Compute how much simulator time passes for given wall time
3. **Provide time queries** - Answer questions about current time, elapsed time
4. **Track update history** - Know when time was last updated for delta calculations

### NOT Responsible For

- ❌ Advancing time itself (that's SimulationEngine's job)
- ❌ Executing events (that's SimulatorEvent's job)
- ❌ Managing the event queue
- ❌ Deciding when to advance time

### Required Attributes

#### 1. `current_time: datetime`
- The current simulator timestamp
- This is the "virtual now" that agents see
- Updated by SimulationEngine when time advances
- Must be timezone-aware (recommend UTC)

#### 2. `time_scale: float`
- Multiplier for time advancement (1.0 = real-time)
- Values > 1.0 = fast-forward (e.g., 10.0 = 10x speed)
- Values < 1.0 = slow-motion (e.g., 0.5 = half speed)
- Value of 0.0 not allowed (use is_paused instead)
- Default: 1.0

#### 3. `is_paused: bool`
- Whether time advancement is currently frozen
- When true, time does not advance regardless of time_scale
- Default: False

#### 4. `last_wall_time_update: datetime`
- Wall-clock time when current_time was last updated
- Used to calculate wall time elapsed for automatic advancement
- Updated every time current_time changes
- Must be timezone-aware (UTC)

#### 5. `auto_advance: bool`
- Whether time automatically advances based on wall time
- When false, time only advances via explicit API calls
- When true, time advances based on time_scale and wall time elapsed
- Default: False (manual mode)

#### 6. `mode: TimeMode`
- Current time control mode (enum)
- PAUSED, MANUAL, REAL_TIME, FAST_FORWARD, EVENT_DRIVEN
- Derived from is_paused, auto_advance, and time_scale
- Useful for API responses and UI display

### Required Methods

#### 1. `calculate_advancement(wall_time_elapsed: timedelta) -> timedelta`
```python
def calculate_advancement(self, wall_time_elapsed: timedelta) -> timedelta:
    """Calculate how much simulator time should advance for given wall time.
    
    Takes into account time_scale and is_paused state.
    
    Examples:
        - time_scale=1.0, wall_elapsed=10s → sim_advance=10s
        - time_scale=100.0, wall_elapsed=1s → sim_advance=100s
        - is_paused=True → sim_advance=0s (always)
    
    Args:
        wall_time_elapsed: Wall-clock time that has elapsed
    
    Returns:
        Amount of simulator time to advance
    """
```

**Rationale**: Centralizes the time scaling logic. SimulationEngine calls this to determine how much to advance time.

#### 2. `advance(delta: timedelta) -> None`
```python
def advance(self, delta: timedelta) -> None:
    """Advance simulator time by the specified delta.
    
    Updates current_time and last_wall_time_update.
    Does NOT execute events - that's SimulationEngine's job.
    
    Args:
        delta: Amount of simulator time to advance
    
    Raises:
        ValueError: If delta is negative or time is paused
    """
```

**Rationale**: Simple, explicit time advancement. The engine calculates the delta and tells time to advance.

**Design Decision**: This method doesn't automatically advance based on wall time - it only advances by the specified delta. Auto-advancement logic lives in SimulationEngine.

#### 3. `set_time(new_time: datetime) -> None`
```python
def set_time(self, new_time: datetime) -> None:
    """Set simulator time to a specific value (time jump).
    
    Used for manual time setting via API or event-driven mode.
    Updates current_time and last_wall_time_update.
    
    Args:
        new_time: New simulator time to set
    
    Raises:
        ValueError: If new_time is before current_time (no backwards jumps)
    """
```

**Rationale**: Explicit time jumps for event-driven mode and manual control. Separate from `advance()` to be clear about intent.

**Design Decision**: Disallow backwards time travel to prevent paradoxes and maintain event log integrity.

#### 4. `pause() -> None`
```python
def pause(self) -> None:
    """Pause time advancement.
    
    Sets is_paused=True. Time will not advance until resume() is called.
    """
```

**Rationale**: Simple pause control for debugging and inspection.

#### 5. `resume() -> None`
```python
def resume(self) -> None:
    """Resume time advancement from paused state.
    
    Sets is_paused=False and updates last_wall_time_update to now.
    """
```

**Rationale**: Complements pause(). Updates wall time anchor to prevent time jump when resuming.

#### 6. `set_scale(scale: float) -> None`
```python
def set_scale(self, scale: float) -> None:
    """Set time advancement scale.
    
    Args:
        scale: New time scale (must be > 0.0)
    
    Raises:
        ValueError: If scale <= 0.0
    """
```

**Rationale**: Dynamic time scale adjustment during simulation.

#### 7. `get_elapsed_time(since: datetime) -> timedelta`
```python
def get_elapsed_time(self, since: datetime) -> timedelta:
    """Calculate simulator time elapsed since a specific time.
    
    Args:
        since: Past simulator time to calculate from
    
    Returns:
        Simulator time elapsed (current_time - since)
    
    Raises:
        ValueError: If since is in the future
    """
```

**Rationale**: Common query for agents and analysis - "how much time has passed since X?"

#### 8. `format_time(format_str: Optional[str] = None) -> str`
```python
def format_time(self, format_str: Optional[str] = None) -> str:
    """Format current simulator time as a string.
    
    Args:
        format_str: Optional strftime format string (default: ISO 8601)
    
    Returns:
        Formatted time string
    """
```

**Rationale**: Convenience method for logging and API responses.

#### 9. `to_dict() -> dict`
```python
def to_dict(self) -> dict:
    """Export time state as dictionary for API responses.
    
    Returns:
        Dictionary with all time state fields
    """
```

**Rationale**: Clean API representation, used by GET /simulator/time endpoint.

#### 10. `validate() -> list[str]`
```python
def validate(self) -> list[str]:
    """Validate time state consistency.
    
    Checks:
        - time_scale > 0.0
        - current_time is timezone-aware
        - last_wall_time_update is timezone-aware
        - No logical inconsistencies
    
    Returns:
        List of validation errors (empty if valid)
    """
```

**Rationale**: Self-validation for catching configuration errors.

### TimeMode Enum

```python
from enum import Enum

class TimeMode(str, Enum):
    """Time control mode for the simulation."""
    
    PAUSED = "paused"              # Time is frozen
    MANUAL = "manual"               # Time advances only via explicit API calls
    REAL_TIME = "real_time"         # 1x speed, auto-advance
    FAST_FORWARD = "fast_forward"   # >1x speed, auto-advance
    SLOW_MOTION = "slow_motion"     # <1x speed, auto-advance
    EVENT_DRIVEN = "event_driven"   # Jump to next event automatically
```

**Rationale**: User-friendly categorization of time behavior. Derived from underlying attributes.

### Computed Properties

#### `mode -> TimeMode`
```python
@property
def mode(self) -> TimeMode:
    """Determine current time control mode based on state."""
    if self.is_paused:
        return TimeMode.PAUSED
    if not self.auto_advance:
        return TimeMode.MANUAL
    if self.time_scale == 1.0:
        return TimeMode.REAL_TIME
    if self.time_scale > 1.0:
        return TimeMode.FAST_FORWARD
    return TimeMode.SLOW_MOTION
```

## Interaction Patterns

### Pattern 1: Automatic Time Advancement (Real-Time Mode)

```python
# SimulationEngine's main loop

while simulation_running:
    # 1. Calculate wall time elapsed
    current_wall_time = datetime.now(timezone.utc)
    wall_elapsed = current_wall_time - simulator_time.last_wall_time_update
    
    # 2. Calculate simulator time advancement
    sim_advancement = simulator_time.calculate_advancement(wall_elapsed)
    
    # 3. Advance simulator time
    if sim_advancement > timedelta(0):
        simulator_time.advance(sim_advancement)
        
        # 4. Get and execute due events
        due_events = event_queue.get_due_events(simulator_time.current_time)
        for event in due_events:
            event.execute(environment)
    
    # 5. Sleep briefly to avoid busy loop
    time.sleep(0.01)  # 10ms
```

**Key Point**: Engine polls regularly, calculates advancement, updates time, executes events.

### Pattern 2: Manual Time Advancement (API Call)

```python
# API endpoint: POST /simulator/time/advance
# Body: {"duration": "1h30m"}

# 1. Parse duration
duration = parse_duration(request.json["duration"])  # → timedelta(hours=1, minutes=30)

# 2. Advance time
simulator_time.advance(duration)

# 3. Execute due events
due_events = event_queue.get_due_events(simulator_time.current_time)
for event in due_events:
    event.execute(environment)

# 4. Return new state
return {
    "current_time": simulator_time.current_time,
    "events_executed": len(due_events)
}
```

**Key Point**: Explicit time jump, then execute any events that became due.

### Pattern 3: Time Jump (Set Absolute Time)

```python
# API endpoint: POST /simulator/time/set
# Body: {"time": "2024-03-15T14:30:00Z", "execute_skipped": false}

new_time = datetime.fromisoformat(request.json["time"])
execute_skipped = request.json.get("execute_skipped", False)

# 1. Find events in skipped range
if new_time > simulator_time.current_time:
    skipped_events = event_queue.get_events_in_range(
        start=simulator_time.current_time,
        end=new_time,
        status_filter=EventStatus.PENDING
    )
    
    # 2. Handle skipped events
    if execute_skipped:
        for event in skipped_events:
            event.execute(environment)
    else:
        for event in skipped_events:
            event.skip(reason="Time jumped past scheduled_time")

# 3. Set new time
simulator_time.set_time(new_time)

return {
    "current_time": simulator_time.current_time,
    "skipped_events": len(skipped_events)
}
```

**Key Point**: Time jumps can skip events - engine decides whether to execute or skip them.

### Pattern 4: Event-Driven Mode

```python
# API endpoint: POST /simulator/time/skip-to-next

# 1. Find next pending event
next_event = event_queue.peek_next()

if next_event is None:
    return {"message": "No more events", "simulation_complete": True}

# 2. Jump time to that event
simulator_time.set_time(next_event.scheduled_time)

# 3. Execute all events at that time
due_events = event_queue.get_due_events(simulator_time.current_time)
for event in due_events:
    event.execute(environment)

return {
    "current_time": simulator_time.current_time,
    "events_executed": len(due_events),
    "next_event_time": event_queue.next_event_time
}
```

**Key Point**: Jump directly to next event, execute, repeat. Fast simulation for development.

### Pattern 5: Pause/Resume

```python
# API endpoint: POST /simulator/time/pause

simulator_time.pause()

return {
    "status": "paused",
    "current_time": simulator_time.current_time
}

# Later: POST /simulator/time/resume

simulator_time.resume()

return {
    "status": "running",
    "current_time": simulator_time.current_time,
    "mode": simulator_time.mode
}
```

**Key Point**: Pause freezes time completely, resume resets wall time anchor.

## Design Decisions

### 1. No Backwards Time Travel

**Decision**: `set_time()` raises an error if new_time < current_time.

**Rationale**: 
- Prevents paradoxes (event executed before it was created)
- Maintains event log integrity
- Simplifies reasoning about causality

**Alternative Considered**: Allow backwards jumps but mark all events as "unexecuted". Too complex for MVP.

### 2. SimulatorTime Doesn't Advance Itself

**Decision**: Time is passive - it only advances when told to by SimulationEngine.

**Rationale**:
- Clear separation of concerns
- Engine orchestrates, Time tracks
- Easier to test and reason about
- No background threads or timers

### 3. Wall Time Updates on Every Change

**Decision**: Update `last_wall_time_update` whenever `current_time` changes.

**Rationale**:
- Accurate delta calculations
- Prevents time jumps after pause/resume
- Simple and consistent

### 4. Time Scale Can Be Changed Mid-Simulation

**Decision**: `set_scale()` can be called anytime, immediately affects future advancement.

**Rationale**:
- Flexibility for debugging (start fast, slow down at interesting moment)
- No side effects - only affects future calculations
- Simple implementation

### 5. Separate Pause State from Time Scale

**Decision**: `is_paused` is independent of `time_scale`.

**Rationale**:
- Pause means "completely frozen" - clearer than time_scale=0
- Can pause and resume without losing scale setting
- Better API ergonomics

## Performance Considerations

### Time Calculation Overhead

**Concern**: Calculating time advancement every loop iteration.

**Solution**: Simple arithmetic (multiplication, addition) is negligible. No optimization needed for MVP.

### Wall Time Precision

**Concern**: `datetime.now()` has limited precision.

**Solution**: Accept this limitation. For most simulations, millisecond precision is sufficient. Can use `time.perf_counter()` for higher precision if needed in future.

### Time Zone Handling

**Decision**: All times are UTC internally.

**Rationale**:
- Avoids DST complications
- Consistent serialization
- Time zones are a modality concern (TimeState stores user's preferred timezone)

## Error Handling

### Invalid Time Operations

```python
# Negative advancement
try:
    simulator_time.advance(timedelta(seconds=-10))
except ValueError as e:
    # "Cannot advance time backwards"

# Advancement while paused
simulator_time.pause()
try:
    simulator_time.advance(timedelta(minutes=5))
except ValueError as e:
    # "Cannot advance time while paused"

# Invalid scale
try:
    simulator_time.set_scale(0.0)
except ValueError as e:
    # "Time scale must be positive"
```

**Rationale**: Fail fast for programmer errors. These are configuration mistakes, not runtime conditions.

### Time Jump Validation

```python
# Backwards jump
try:
    simulator_time.set_time(past_time)
except ValueError as e:
    # "Cannot set time backwards"
```

**Rationale**: Prevent logical inconsistencies.

## Testing Strategy

### Unit Tests

**Time Calculations**:
- `calculate_advancement()` with various scales
- Paused time returns zero advancement
- Edge cases (scale=0.001, scale=1000.0)

**State Transitions**:
- Pause/resume cycle
- Scale changes
- Manual vs auto-advance

**Validation**:
- Invalid scales rejected
- Timezone-naive datetimes rejected
- Backwards jumps prevented

### Integration Tests

**With SimulationEngine**:
- Auto-advancement over time
- Event execution after time advance
- Pause prevents event execution

**With EventQueue**:
- Event-driven mode jumps correctly
- Time jumps handle skipped events

## Scope Boundaries

### What SimulatorTime DOES:
✅ Track current simulator time
✅ Calculate time deltas based on scale
✅ Provide time queries
✅ Validate time operations
✅ Update wall time tracking

### What SimulatorTime DOESN'T DO:
❌ Advance itself automatically
❌ Execute events
❌ Manage the event queue
❌ Make decisions about when to advance
❌ Expose REST API endpoints

### What SimulationEngine DOES:
✅ Decide when to advance time
✅ Calculate advancement amounts
✅ Call simulator_time.advance()
✅ Execute due events after advancement
✅ Coordinate pause/resume/jump operations

## Open Questions & Future Considerations

### 1. Sub-Millisecond Precision

**Question**: Do we need sub-millisecond time precision?

**Current Answer**: No. `datetime` with microseconds is sufficient.

**Future**: Could use `time.perf_counter()` with epoch reference if high-precision timing needed.

### 2. Time Dilation by Modality

**Question**: Should different modalities experience time differently?

**Current Answer**: No. All modalities share same simulator time.

**Future**: Could add per-modality time scales if needed for special effects (e.g., slow-motion for screen capture).

### 3. Time Travel for Debugging

**Question**: Should we support backwards time jumps for debugging?

**Current Answer**: No. Too complex, marginal benefit.

**Future**: Instead, support state snapshots and restore for "time travel".

### 4. Distributed Simulations

**Question**: How does time work across multiple simulation instances?

**Current Answer**: Out of scope for MVP. Single-instance only.

**Future**: Would need clock synchronization protocol (e.g., Lamport timestamps, vector clocks).

### 5. Real-Time Constraints

**Question**: Should we enforce maximum lag between simulator time and wall time?

**Current Answer**: No. Simulator runs as fast as it can.

**Future**: Could add "real-time mode" that sleeps to maintain 1:1 ratio if simulation is too fast.

## Summary

`SimulatorTime` provides clean time management for the simulation:

- **Decoupled** from wall time for flexibility
- **Passive** - doesn't advance itself, just tracks state
- **Scalable** - supports pause, fast-forward, slow-motion, event-driven modes
- **Simple** - straightforward arithmetic, no background threads
- **Safe** - validates operations, prevents logical errors

This architecture provides:
✅ Flexible time control (jump, scale, pause)
✅ Clear responsibilities (track state, calculate deltas)
✅ Testability (pure functions, no side effects)
✅ Debuggability (pause, inspect, step through)
✅ API-readiness (clean state export)

## API Design (Planned)

### Time Control Endpoints
```
POST /simulator/time/set
  Body: { "time": "2024-03-15T14:30:00Z" }
  Sets exact simulator time

POST /simulator/time/advance
  Body: { "duration": "1h30m" }
  Advances time by specified duration

POST /simulator/time/skip-to-next
  Advances to the next scheduled event timestamp

POST /simulator/time/scale
  Body: { "scale": 100.0 }
  Sets time multiplier (1.0 = real-time, 100.0 = 100x speed)

POST /simulator/time/pause
  Freezes simulator time

POST /simulator/time/resume
  Continues time advancement from current state

GET /simulator/time
  Returns: {
    "current_time": "2024-03-15T14:30:00Z",
    "time_scale": 1.0,
    "is_paused": false,
    "next_event_time": "2024-03-15T15:00:00Z",
    "wall_time_updated": "2024-11-16T10:30:00Z"
  }
```

## Implementation Notes

### Time Advancement in SimulationEngine

The SimulationEngine is responsible for calling SimulatorTime's methods appropriately:
1. Calculate new simulator time based on scale and wall time elapsed
2. Query event queue for all events with `scheduled_time <= new_time`
3. Execute due events in chronological order
4. Update simulator time to new value
5. Trigger any time-based state changes (weather updates, etc.)

### Preventing Race Conditions
- Events at the exact same timestamp should have a secondary ordering (insertion order or priority)
- Agent queries should always receive a consistent snapshot of time
- Lock simulator state during event execution to prevent mid-event time changes

### Performance Considerations
- Event queue should use efficient data structure (heap/priority queue)
- Consider lazy evaluation for distant future events
- Cache next event time to avoid repeated queue scans
