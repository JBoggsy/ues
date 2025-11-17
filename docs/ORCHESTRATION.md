# Simulation Orchestration Requirements

## Overview

This document describes everything that needs to happen to make the UES simulation work, focusing on the **orchestration requirements** rather than specific class implementations. The simulation must coordinate time progression, event execution, state management, and API interactions to provide a complete testing environment for AI personal assistants.

**Note**: For implementation details of the hybrid architecture (SimulationEngine + SimulationLoop), see [SIMULATION_ENGINE.md](./SIMULATION_ENGINE.md).

## Core Orchestration Requirements

### 1. Time Management

The simulation must manage virtual time independently from wall-clock time, supporting multiple time control modes.

#### Required Capabilities

**Time Advancement**:
- Calculate how much simulator time should advance based on wall-clock elapsed time and time scale
- Advance simulator time by calculated deltas
- Track when time was last updated for delta calculations
- Update wall-time anchor after each advancement

**Time Control Modes**:
- **Paused**: Time frozen, no automatic advancement
- **Manual**: Time advances only via explicit API calls
- **Real-time (1x)**: Time advances at same rate as wall time
- **Fast-forward (Nx)**: Time advances N times faster than wall time
- **Slow-motion**: Time advances slower than wall time
- **Event-driven**: Time jumps directly to next scheduled event

**Time Operations**:
- Pause: Freeze time advancement
- Resume: Unfreeze and reset wall-time anchor
- Set scale: Change time multiplier (1.0 = real-time, 10.0 = 10x speed)
- Jump to specific time: Set absolute simulator time
- Advance by delta: Move time forward by specific amount

**Time Queries**:
- Get current simulator time
- Get current time mode
- Get time scale
- Calculate elapsed time since a timestamp
- Format time for display

#### Time Advancement Pattern

```python
# For auto-advance mode (real-time, fast-forward, slow-motion)

while simulation_is_running and auto_advance_enabled:
    # 1. Get current wall-clock time
    current_wall_time = now()
    
    # 2. Calculate wall time elapsed since last update
    wall_elapsed = current_wall_time - last_wall_update
    
    # 3. Apply time scale to get simulator advancement
    sim_advancement = wall_elapsed * time_scale
    
    # 4. Advance simulator time
    simulator_time += sim_advancement
    last_wall_update = current_wall_time
    
    # 5. Execute any events that became due
    execute_due_events()
    
    # 6. Brief sleep to avoid busy loop
    sleep(10ms)
```

### 2. Event Execution

The simulation must execute events at appropriate simulator times, modifying environment state.

#### Required Capabilities

**Event Scheduling**:
- Add individual events to queue
- Add bulk events efficiently
- Maintain events sorted by (scheduled_time, -priority, created_at)
- Support event priorities (higher priority executes first)

**Event Discovery**:
- Find all events due for execution (scheduled_time <= current_time)
- Peek at next pending event without executing
- Query events by status (pending, executed, failed, etc.)
- Query events in time range
- Get event counts by status

**Event Execution Flow**:
```python
# For each advancement cycle

# 1. Get events due for execution
due_events = queue.get_events_due(current_simulator_time)

# 2. Execute each event in order (by time, then priority)
for event in due_events:
    try:
        # Event executes itself
        event.execute(environment)
        # Status automatically set to EXECUTED
        # executed_at timestamp recorded
    except Exception as e:
        # Event marks itself as FAILED
        # Error message captured
        # Log but continue (don't crash simulation)
        log_error(f"Event {event.id} failed: {e}")
```

**Skipped Events**:
When time jumps forward, pending events in the skipped range must be handled:
- Option 1: Execute all skipped events instantly (compress time)
- Option 2: Mark as SKIPPED with reason (time jumped past)
- Decision made by orchestration layer based on API request

**Event Creation**:
- User creates events via API
- Agents generate events dynamically during simulation
- Events can be scheduled for any future time
- Events reference modality by name ("email", "location", etc.)

**Event Lifecycle States**:
- PENDING: Created, waiting for scheduled_time
- EXECUTING: Currently being processed
- EXECUTED: Successfully completed
- FAILED: Exception during execution
- SKIPPED: Time jumped past without execution
- CANCELLED: Manually cancelled before execution

#### Event-Driven Time Advancement Pattern

```python
# Skip directly to next event

while has_pending_events:
    # 1. Find next pending event
    next_event = queue.peek_next()
    
    # 2. Jump time to that event
    simulator_time = next_event.scheduled_time
    
    # 3. Execute all events at that time (may be multiple)
    due_events = queue.get_events_due(simulator_time)
    for event in due_events:
        event.execute(environment)
    
    # 4. Return execution summary
```

### 3. State Management

The simulation must maintain and provide access to current environment state.

#### Required Capabilities

**State Container**:
- Hold all modality states in single container
- Hold current time state
- Provide O(1) lookup by modality name
- Support dynamic addition/removal of modalities

**State Access**:
- Get specific modality state (e.g., get_state("email"))
- List all available modalities
- Check if modality exists
- Export complete state snapshot

**State Modification**:
- Events modify states in-place via state.apply_input()
- States track last_updated timestamp
- States track update_count for versioning
- Modifications are immediate and visible

**State Validation**:
- Validate environment consistency before simulation starts
- Validate each modality state
- Check for missing required modalities
- Verify modality names match state types

**State Queries** (for agents/API):
- Query modality state with filters (e.g., "unread emails in inbox")
- Get state snapshot for checkpoint/debugging
- Compare states (before/after events)
- List available modalities for discovery

#### State Snapshot Structure

```python
{
    "time": {
        "current_time": "2024-03-15T14:30:00+00:00",
        "time_scale": 1.0,
        "is_paused": false,
        "mode": "real_time"
    },
    "modalities": {
        "email": {
            "modality_type": "email",
            "inbox_count": 42,
            "unread_count": 5,
            "last_updated": "2024-03-15T14:28:00+00:00"
        },
        "location": {
            "modality_type": "location",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "last_updated": "2024-03-15T14:30:00+00:00"
        }
        # ... other modalities
    }
}
```

### 4. Simulation Lifecycle

The simulation must support standard start/stop/pause/resume operations.

#### Required Capabilities

**Initialization**:
- Load environment configuration (initial states)
- Load event sequence (scheduled events)
- Validate environment consistency
- Set initial simulator time
- Initialize all modality states

**Start**:
- Begin main simulation loop (if auto-advance enabled)
- Mark simulation as running
- Log start event
- Return simulation ID and status

**Stop**:
- Gracefully shut down main loop
- Finish executing current events before stopping
- Mark simulation as stopped
- Persist final state (optional)
- Return execution summary

**Pause**:
- Freeze time advancement (set is_paused = true)
- Stop executing new events
- Keep main loop running but idle
- Allow state queries during pause
- Return current state snapshot

**Resume**:
- Unfreeze time (set is_paused = false)
- Reset wall-time anchor to prevent time jump
- Continue executing events
- Return resumed status

#### Lifecycle State Machine

```
        start()
   ┌──────────────┐
   │              │
   ▼              │
STOPPED ──→ RUNNING ──→ PAUSED
   ▲              │        │
   │              │        │
   └── stop() ────┘        │
           ▲               │
           └── resume() ───┘
```

### 5. REST API Requirements

The simulation must expose a RESTful API for all control operations and state queries.

#### Time Control Endpoints

**GET /simulator/time**
- Returns current simulator time state
- Response: `{current_time, time_scale, is_paused, mode, auto_advance}`

**POST /simulator/time/advance**
- Manually advance time by duration
- Request: `{duration: "1h30m"}` or `{duration_seconds: 5400}`
- Executes events that became due
- Response: `{current_time, events_executed: 3, execution_summary: [...]}`

**POST /simulator/time/set**
- Jump to specific time
- Request: `{time: "2024-03-15T14:30:00Z", execute_skipped: false}`
- Handles skipped events based on flag
- Response: `{current_time, skipped_events: 5, executed_events: 0}`

**POST /simulator/time/skip-to-next**
- Jump to next scheduled event
- Executes all events at that time
- Response: `{current_time, events_executed: 2, next_event_time: "..."}`

**POST /simulator/time/pause**
- Pause simulation
- Response: `{status: "paused", current_time}`

**POST /simulator/time/resume**
- Resume simulation
- Response: `{status: "running", current_time, mode}`

**POST /simulator/time/set-scale**
- Change time multiplier
- Request: `{scale: 10.0}`
- Response: `{time_scale: 10.0, mode: "fast_forward"}`

#### Environment State Endpoints

**GET /environment/state**
- Get complete state snapshot
- Response: Full environment snapshot (time + all modalities)

**GET /environment/modalities**
- List available modalities
- Response: `{modalities: ["email", "location", "weather"]}`

**GET /environment/modalities/{modality}**
- Get specific modality state
- Response: Modality state snapshot

**POST /environment/modalities/{modality}/query**
- Query modality state with filters
- Request: `{folder: "inbox", unread: true, limit: 10}`
- Response: Query results from state.query()

**POST /environment/validate**
- Validate environment consistency
- Response: `{valid: true}` or `{valid: false, errors: [...]}`

#### Event Management Endpoints

**GET /events**
- List events with filters
- Query params: `?status=pending&start_time=...&end_time=...`
- Response: `{events: [...], total: 42, pending: 12, executed: 30}`

**POST /events**
- Create new event
- Request: Event definition with modality, data, scheduled_time
- Response: `{event_id, scheduled_time, status: "pending"}`

**GET /events/{event_id}**
- Get specific event details
- Response: Full event data including status, timestamps, error if failed

**DELETE /events/{event_id}**
- Cancel pending event
- Response: `{cancelled: true, event_id}`

**GET /events/next**
- Peek at next pending event
- Response: Next event or `{message: "No pending events"}`

**GET /events/summary**
- Get event execution statistics
- Response: `{total: 100, pending: 5, executed: 90, failed: 3, skipped: 2}`

#### Simulation Control Endpoints

**POST /simulation/start**
- Start simulation
- Request: `{auto_advance: true, time_scale: 1.0}`
- Response: `{simulation_id, status: "running", current_time}`

**POST /simulation/stop**
- Stop simulation
- Response: `{status: "stopped", events_executed: 42, final_time}`

**GET /simulation/status**
- Get current simulation status
- Response: `{is_running, current_time, mode, pending_events, executed_events, next_event_time}`

**POST /simulation/reset**
- Reset simulation to initial state
- Clears all executed events, resets time
- Response: `{status: "reset", initial_time}`

### 6. Error Handling

The simulation must gracefully handle errors without crashing.

#### Required Capabilities

**Event Execution Errors**:
- Catch exceptions during event.execute()
- Mark event as FAILED with error message
- Log error details for debugging
- Continue simulation (don't stop on single failure)
- Track failure count and rate

**Validation Errors**:
- Catch validation errors during initialization
- Return comprehensive error list
- Fail fast before simulation starts
- Provide actionable error messages

**API Errors**:
- Validate API request parameters
- Return appropriate HTTP status codes (400, 404, 409, 500)
- Include error details in response body
- Log errors for monitoring

**Time Errors**:
- Prevent backwards time travel (raise error)
- Detect time scale <= 0 (invalid)
- Catch timezone-naive datetimes (validation)

**State Errors**:
- Missing modality: Fail event, return helpful error
- Invalid modality state: Caught during validation
- None state references: Defensive checks with clear messages

#### Error Response Format

```python
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid request parameters",
        "details": [
            "time_scale must be greater than 0",
            "scheduled_time cannot be in the past"
        ],
        "timestamp": "2024-03-15T14:30:00Z"
    }
}
```

### 7. Logging and Observability

The simulation must provide visibility into its operation.

#### Required Capabilities

**Event Logging**:
- Log each event execution (success or failure)
- Include event_id, modality, scheduled_time, executed_at
- Log execution duration
- Log error messages for failures

**Time Logging**:
- Log time mode changes
- Log time jumps (manual set_time calls)
- Log pause/resume operations
- Track time advancement rate

**State Logging**:
- Log state modifications (which modality, what changed)
- Log validation errors
- Log API access to states

**Simulation Logging**:
- Log start/stop operations
- Log lifecycle state transitions
- Track simulation uptime
- Log configuration changes

**Metrics**:
- Events executed per second
- Event failure rate
- Time compression ratio (sim time / wall time)
- API request rate and latency
- Memory usage for large state

### 8. Concurrency Considerations

The simulation orchestration must handle concurrent access patterns.

#### Required Capabilities

**API Concurrency**:
- Multiple API requests can arrive simultaneously
- State queries should not block event execution
- Time control operations should be synchronized
- Event additions should be thread-safe

**Event Execution**:
- Events execute sequentially (no parallel execution)
- Priority ensures deterministic order
- No race conditions on state modification

**Time Advancement**:
- Only one component advances time
- Wall-time polling happens on single thread
- API time control synchronized with main loop

**Patterns**:
- Main simulation loop runs on dedicated thread
- API handlers run on web framework threads
- State queries can read concurrently
- State modifications must be serialized

### 9. Configuration and Persistence

The simulation must support saving and loading configurations.

#### Required Capabilities

**Configuration Loading**:
- Load initial environment state from JSON/YAML
- Load event sequence from file
- Load time settings (initial time, scale, mode)
- Validate loaded configuration before starting

**State Persistence**:
- Save environment snapshots at checkpoints
- Save event queue state (pending events)
- Save execution history (executed/failed events)
- Export to JSON/YAML format

**Checkpoint/Resume**:
- Create periodic snapshots during long runs
- Resume from checkpoint (restore state + events)
- Validate checkpoint before resuming
- Handle version compatibility

**Configuration Format**:
```yaml
simulation:
  name: "College Student Scenario"
  initial_time: "2024-03-15T08:00:00Z"
  time_scale: 1.0
  auto_advance: false

environment:
  modalities:
    email:
      type: EmailState
      inbox_count: 5
      # ... initial state
    location:
      type: LocationState
      latitude: 37.7749
      longitude: -122.4194
    # ... other modalities

events:
  - scheduled_time: "2024-03-15T08:30:00Z"
    modality: "email"
    data:
      from: "prof@university.edu"
      subject: "Assignment Due Tomorrow"
      # ... email data
  - scheduled_time: "2024-03-15T09:00:00Z"
    modality: "text"
    data:
      from: "+15551234567"
      body: "Want to grab lunch?"
      # ... text data
  # ... more events
```

### 10. Testing and Validation

The simulation orchestration must be testable and debuggable.

#### Required Capabilities

**Unit Testing**:
- Test time advancement calculations
- Test event execution in isolation
- Test state modifications
- Test API endpoint handlers

**Integration Testing**:
- Test full simulation cycles
- Test time mode transitions
- Test event-driven progression
- Test error handling paths

**Scenario Testing**:
- Load realistic scenarios (college student, busy parent, etc.)
- Run complete simulations
- Validate final state matches expectations
- Measure performance (events/second)

**Debugging Support**:
- Step through events one at a time
- Inspect state before/after each event
- Query event execution history
- Compare state snapshots

**Validation**:
- Validate environment before starting
- Validate events before adding to queue
- Validate API requests
- Provide detailed error messages

## Orchestration Implementation Considerations

### Component Coordination

The orchestration layer coordinates these components:
- **Environment**: Current state container (see [ENVIRONMENT.md](./ENVIRONMENT.md))
- **EventQueue**: Scheduled events
- **SimulatorTime**: Time tracking (see [SIMULATOR_TIME.md](./SIMULATOR_TIME.md))
- **SimulationEngine**: Main orchestrator (see [SIMULATION_ENGINE.md](./SIMULATION_ENGINE.md))
- **SimulationLoop**: Threading component for auto-advance (see [SIMULATION_ENGINE.md](./SIMULATION_ENGINE.md))

### Responsibilities Separation

**What orchestration DOES** (SimulationEngine + SimulationLoop):
- ✅ Coordinate component interactions (SimulationEngine)
- ✅ Implement main simulation loop (SimulationLoop)
- ✅ Handle API requests (SimulationEngine)
- ✅ Decide when to advance time (SimulationEngine)
- ✅ Decide which events to execute (SimulationEngine)
- ✅ Handle errors and logging (SimulationEngine)
- ✅ Manage lifecycle (start/stop/pause) (SimulationEngine)
- ✅ Manage threading for auto-advance (SimulationLoop)

**What orchestration DOES NOT DO**:
- ❌ Execute events (events execute themselves via event.execute())
- ❌ Advance time (tells SimulatorTime to advance)
- ❌ Modify state (events do via state.apply_input())
- ❌ Sort events (EventQueue maintains order)
- ❌ Validate inputs (ModalityInput validates itself)
- ❌ Generate events (users/agents create events)

### Main Orchestration Loop

```python
# Pseudo-code for main simulation loop

initialize():
    load_configuration()
    validate_environment()
    set_initial_time()
    
start():
    is_running = true
    
    if auto_advance:
        start_main_loop()
    else:
        # Manual mode - just wait for API calls
        wait_for_commands()

main_loop():
    # This runs in SimulationLoop on separate thread
    while is_running:
        if is_paused:
            sleep(10ms)
            continue
        
        # Call back to SimulationEngine.tick()
        # All simulation logic happens in tick()
        simulation_engine.tick()
        
        # Brief sleep
        sleep(10ms)

tick():
    # This runs in SimulationEngine (called by SimulationLoop)
    # Calculate time advancement
    wall_elapsed = now() - environment.time_state.last_wall_time_update
    sim_delta = environment.time_state.calculate_advancement(wall_elapsed)
    
    # Advance simulator time
    environment.time_state.advance(sim_delta)
    
    # Execute due events
    due_events = event_queue.get_due_events(environment.time_state.current_time)
    for event in due_events:
        try:
            event.execute(environment)
            log_success(event)
        except Exception as e:
            log_failure(event, e)

handle_api_request(request):
    # Parse request
    # Validate parameters
    # Execute operation
    # Return response
    
    if request.path == "/simulator/time/advance":
        delta = parse_duration(request.body.duration)
        simulator_time.advance(delta)
        due_events = event_queue.get_due_events(simulator_time.current_time)
        execute_events(due_events)
        return {
            "current_time": simulator_time.current_time,
            "events_executed": len(due_events)
        }
    
    # ... other endpoints

stop():
    is_running = false
    finish_current_events()
    persist_state()
    return execution_summary()
```

## Summary

The simulation orchestration requires coordinating:
1. **Time management** - Multiple modes, advancement, control
2. **Event execution** - Scheduling, discovery, execution, skipping
3. **State management** - Container, access, modification, validation
4. **Lifecycle control** - Start, stop, pause, resume
5. **REST API** - Comprehensive endpoints for all operations
6. **Error handling** - Graceful failures, logging, recovery
7. **Logging** - Visibility into all operations
8. **Concurrency** - Thread-safe operations, serialized state changes
9. **Persistence** - Configuration loading, state saving, checkpoints
10. **Testing** - Unit, integration, scenario validation

All orchestration happens through clear interfaces with separated concerns:
- **Components do their specific job** (time tracks, events execute, states hold)
- **SimulationEngine coordinates** without doing the work itself
- **SimulationLoop isolates threading** complexity from coordination logic
- **API exposes all capabilities** via thin route handlers
- **Everything is testable independently** (engine without threads, loop without simulation logic)

For implementation details of the hybrid architecture, see [SIMULATION_ENGINE.md](./SIMULATION_ENGINE.md).
