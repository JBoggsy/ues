# Simulation Engine Architecture

## Overview

The UES simulation orchestration layer uses a **hybrid architecture** that separates coordination concerns from threading complexity. This design splits responsibilities between two cooperating classes:

- **SimulationEngine**: High-level orchestrator that handles coordination, API requests, and state management
- **SimulationLoop**: Threading-isolated component that implements the auto-advance main loop

This separation provides the benefits of both single-class simplicity and multi-class specialization while keeping the codebase manageable and maintainable.

## Design Rationale

### Why Hybrid Architecture?

**The Problem**: Simulation orchestration involves two distinct concerns:
1. **Coordination Logic**: Time control, event management, validation, API handling
2. **Threading Complexity**: Auto-advance loop, wall-clock polling, thread lifecycle

Mixing these concerns in a single class leads to:
- Large, complex classes (500-1000+ lines)
- Threading bugs affecting coordination logic
- Difficult unit testing (can't test coordination without threading)
- Poor separation of concerns

Splitting everything into multiple controllers adds:
- Complex inter-controller communication
- Unclear ownership of operations
- Over-engineered for MVP needs

**The Solution**: Split only the threading concern into its own class, keep everything else coordinated by SimulationEngine.

### Benefits of Hybrid Approach

1. **Threading Isolation**: Auto-advance complexity contained in SimulationLoop
2. **Clean Coordination**: SimulationEngine handles all non-threading logic
3. **Simple Interface**: SimulationLoop exposes just start(), stop(), tick()
4. **Testability**: Test coordination logic without threads, test loop logic in isolation
5. **Manageable Size**: SimulationEngine ~200-300 lines, SimulationLoop ~100-150 lines
6. **Easy Refactoring**: Can split further if needed without changing external API
7. **MVP Speed**: Faster to implement than full multi-controller architecture

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        REST API Layer                       │
│                       (FastAPI routes)                      │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ delegates to
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     SimulationEngine                        │
│  (Orchestrator - coordinates all simulation operations)     │
│                                                             │
│  Responsibilities:                                          │
│  • Time control operations (advance, set, skip-to-next)     │
│  • Event management (add, execute, query)                   │
│  • State access and validation                              │
│  • Lifecycle management (start, stop, pause, resume)        │
│  • Mode coordination (manual, event-driven)                 │
│  • Error handling and logging                               │
│  • API request handling                                     │
│                                                             │
│  Delegates to:                                              │
│  • Environment (state container)                            │
│  • EventQueue (event storage)                               │
│  • SimulatorTime (time tracking)                            │
│  • SimulationLoop (auto-advance threading)                  │
└───────────────┬───────────────────────────────┬─────────────┘
                │                               │
                │ owns & delegates              │ owns & controls
                ▼                               ▼
┌───────────────────────────────┐  ┌──────────────────────────┐
│        Environment            │  │     SimulationLoop       │
│                               │  │                          │
│  • SimulatorTime              │  │  (Threading Component)   │
│  • ModalityStates             │  │                          │
│                               │  │  Responsibilities:       │
│  Accessed via:                │  │  • Auto-advance loop     │
│  • get_state()                │  │  • Wall-clock polling    │
│  • get_snapshot()             │  │  • Thread lifecycle      │
│  • validate()                 │  │  • Calls tick()          │
└───────────────┬───────────────┘  └────────┬─────────────────┘
                │                           │
                │                           │ calls back
                │                           ▼
                │                  ┌─────────────────────────┐
                │                  │  SimulationEngine       │
                │                  │  .tick()                │
                │                  │  (time advance + events)│
                │                  └─────────────────────────┘
                │
                ▼
┌───────────────────────────────┐
│         EventQueue            │
│                               │
│  • Scheduled events           │
│  • Priority ordering          │
│                               │
│  Accessed via:                │
│  • add_event()                │
│  • get_due_events()           │
│  • peek_next()                │
└───────────────────────────────┘
```

## SimulationEngine Class

### Purpose

The **SimulationEngine** is the primary orchestrator that coordinates all simulation operations. It owns all components (Environment, EventQueue, SimulationLoop) and handles all coordination logic except the auto-advance threading.

### Core Concept

Think of SimulationEngine as the **simulation controller** - it receives commands (from API or internal logic) and orchestrates the appropriate sequence of operations across components. It is the single point of control for all simulation operations.

### Design Principles

1. **Strong Delegation**: SimulationEngine coordinates but doesn't do the work itself
2. **State Management**: Owns Environment and EventQueue, provides access to both
3. **Mode Coordinator**: Implements all time control modes (manual, event-driven, auto-advance)
4. **API Gateway**: All REST API requests go through SimulationEngine methods
5. **Error Handler**: Catches and logs errors, decides whether to continue or fail
6. **Thread-Free**: No threading logic except starting/stopping SimulationLoop

### Attributes

```python
class SimulationEngine:
    """Primary orchestrator for UES simulation.
    
    Coordinates time advancement, event execution, state management,
    and API interactions. Delegates auto-advance threading to
    SimulationLoop.
    """
    
    # Core components (owned by SimulationEngine)
    environment: Environment
    event_queue: EventQueue
    
    # Threading component (owned and controlled)
    _loop: Optional[SimulationLoop]
    
    # Simulation state
    simulation_id: str
    is_running: bool
    
    # Configuration (future - for now use defaults)
    # config: SimulationConfig
```

#### Attribute Details

**`environment: Environment`**
- Complete simulation state container
- Holds all modality states + time state
- Modified by events, queried by API
- Validates consistency before operations

**`event_queue: EventQueue`**
- Collection of all scheduled events
- Maintains sort order (time, priority, created_at)
- Queried for due events, next event
- Thread-safe for additions during simulation

**`_loop: Optional[SimulationLoop]`**
- Auto-advance threading component
- Created when auto_advance mode is enabled
- Destroyed when simulation stops
- Private attribute - external code uses start/stop methods

**`simulation_id: str`**
- Unique identifier for this simulation instance
- Used in logging, metrics, API responses
- Generated at SimulationEngine creation

**`is_running: bool`**
- Whether simulation is active
- Controls whether operations are allowed
- Set to True on start(), False on stop()
- Independent of is_paused (can be running but paused)

### Methods

SimulationEngine has approximately **16 public methods** organized into these categories:

#### Lifecycle Methods (4)

**`__init__(environment: Environment, event_queue: EventQueue, simulation_id: Optional[str] = None)`**
```python
def __init__(
    self,
    environment: Environment,
    event_queue: EventQueue,
    simulation_id: Optional[str] = None
) -> None:
    """Initialize simulation engine with components.
    
    Args:
        environment: State container with initial states
        event_queue: Queue of scheduled events
        simulation_id: Optional unique ID (generated if not provided)
    
    Raises:
        ValueError: If environment or event_queue validation fails
    """
```

**`start(auto_advance: bool = False, time_scale: float = 1.0) -> dict`**
```python
def start(self, auto_advance: bool = False, time_scale: float = 1.0) -> dict:
    """Start the simulation.
    
    If auto_advance is True, creates and starts SimulationLoop.
    If auto_advance is False, just marks simulation as running.
    
    Args:
        auto_advance: Whether to start auto-advance loop
        time_scale: Time multiplier for auto-advance mode
    
    Returns:
        Status dict with simulation_id, current_time, mode
    
    Raises:
        RuntimeError: If simulation is already running
    """
```

**`stop() -> dict`**
```python
def stop(self) -> dict:
    """Stop the simulation gracefully.
    
    If SimulationLoop is running, stops it first.
    Finishes executing any in-progress events.
    Returns execution summary.
    
    Returns:
        Summary dict with final_time, events_executed, etc.
    """
```

**`reset() -> None`**
```python
def reset(self) -> None:
    """Reset simulation to initial state.
    
    Stops simulation if running.
    Clears all executed event records.
    Resets time to initial value.
    Resets environment to initial states.
    """
```

#### Time Control Methods (5)

**`advance_time(delta: timedelta) -> dict`**
```python
def advance_time(self, delta: timedelta) -> dict:
    """Manually advance simulator time by specified amount.
    
    This is the manual time control method.
    1. Validates delta (must be positive)
    2. Advances environment.time_state
    3. Gets and executes due events
    4. Returns execution summary
    
    Args:
        delta: Amount of simulator time to advance
    
    Returns:
        Dict with current_time, events_executed, execution_details
    
    Raises:
        ValueError: If delta <= 0 or simulation not running
    """
```

**`set_time(new_time: datetime, execute_skipped: bool = False) -> dict`**
```python
def set_time(
    self,
    new_time: datetime,
    execute_skipped: bool = False
) -> dict:
    """Jump to specific simulator time.
    
    Handles events in skipped range based on execute_skipped flag.
    
    Args:
        new_time: Target simulator time
        execute_skipped: If True, execute all skipped events instantly.
                        If False, mark them as SKIPPED.
    
    Returns:
        Dict with current_time, skipped_events, executed_events
    
    Raises:
        ValueError: If new_time is in the past
    """
```

**`skip_to_next_event() -> dict`**
```python
def skip_to_next_event(self) -> dict:
    """Jump to next scheduled event and execute it.
    
    Implements event-driven time advancement:
    1. Peek at next pending event
    2. Jump time to that event's scheduled_time
    3. Execute all events at that time (may be multiple with same time)
    4. Return execution summary
    
    Returns:
        Dict with current_time, events_executed, next_event_time
        Or {message: "No pending events"} if queue is empty
    """
```

**`pause() -> None`**
```python
def pause(self) -> None:
    """Pause the simulation.
    
    Freezes time advancement (sets environment.time_state.is_paused = True).
    If SimulationLoop is running, it will idle but remain active.
    """
```

**`resume() -> None`**
```python
def resume(self) -> None:
    """Resume simulation from paused state.
    
    Unfreezes time (sets is_paused = False).
    Resets wall_time_anchor to prevent time jump.
    """
```

#### Event Management Methods (3)

**`add_event(event: SimulatorEvent) -> None`**
```python
def add_event(self, event: SimulatorEvent) -> None:
    """Add new event to simulation.
    
    Validates event and adds to queue.
    If event is already due, may execute immediately depending on mode.
    
    Args:
        event: Event to add
    
    Raises:
        ValueError: If event validation fails
    """
```

**`execute_due_events() -> list[SimulatorEvent]`**
```python
def execute_due_events(self) -> list[SimulatorEvent]:
    """Execute all events that are currently due.
    
    Called by:
    - advance_time() after time advances
    - skip_to_next_event() after jumping
    - tick() during auto-advance loop
    
    Returns:
        List of executed events (both successful and failed)
    """
```

**`query_events(status: Optional[EventStatus] = None, ...) -> list[SimulatorEvent]`**
```python
def query_events(
    self,
    status: Optional[EventStatus] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    modality: Optional[str] = None
) -> list[SimulatorEvent]:
    """Query events with filters.
    
    Delegates to event_queue.query().
    
    Args:
        status: Filter by event status
        start_time: Filter by scheduled_time >= start_time
        end_time: Filter by scheduled_time <= end_time
        modality: Filter by modality name
    
    Returns:
        List of matching events
    """
```

#### State Access Methods (3)

**`get_state() -> Environment`**
```python
def get_state(self) -> Environment:
    """Get complete environment state.
    
    Returns reference to environment for direct access.
    Prefer get_snapshot() for serialization.
    
    Returns:
        Environment instance
    """
```

**`get_snapshot() -> dict`**
```python
def get_snapshot(self) -> dict:
    """Get complete state snapshot for API responses.
    
    Includes:
    - Time state
    - All modality states
    - Simulation metadata (id, is_running, etc.)
    - Event queue summary
    
    Returns:
        Serializable dict snapshot
    """
```

**`validate() -> list[str]`**
```python
def validate(self) -> list[str]:
    """Validate simulation consistency.
    
    Checks:
    - Environment validation (time + modalities)
    - Event queue validation
    - Simulation state consistency
    
    Returns:
        List of validation errors (empty if valid)
    """
```

#### Internal/Helper Method (1)

**`tick() -> None`**
```python
def tick(self) -> None:
    """Execute one simulation tick (called by SimulationLoop).
    
    This is the core auto-advance operation:
    1. Calculate time advancement since last tick
    2. Advance environment.time_state
    3. Execute due events
    4. Log results
    
    Called repeatedly by SimulationLoop in auto-advance mode.
    Should not be called directly by external code.
    """
```

### Interaction Patterns

#### Pattern 1: Manual Time Advancement (API Request)

```python
# API handler receives request to advance time by 1 hour

# 1. API calls SimulationEngine
result = simulation_engine.advance_time(timedelta(hours=1))

# 2. SimulationEngine advances time
simulation_engine.environment.time_state.advance(timedelta(hours=1))

# 3. SimulationEngine gets due events
due_events = simulation_engine.event_queue.get_due_events(
    simulation_engine.environment.time_state.current_time
)

# 4. SimulationEngine executes each event
for event in due_events:
    try:
        event.execute(simulation_engine.environment)
        log_success(event)
    except Exception as e:
        log_failure(event, e)

# 5. SimulationEngine returns summary
return {
    "current_time": simulation_engine.environment.time_state.current_time,
    "events_executed": len(due_events),
    "execution_details": [...]
}
```

#### Pattern 2: Event-Driven Mode (Skip to Next)

```python
# API handler receives request to skip to next event

# 1. API calls SimulationEngine
result = simulation_engine.skip_to_next_event()

# 2. SimulationEngine peeks at next event
next_event = simulation_engine.event_queue.peek_next()
if not next_event:
    return {"message": "No pending events"}

# 3. SimulationEngine jumps time
simulation_engine.environment.time_state.set_time(next_event.scheduled_time)

# 4. SimulationEngine executes all events at that time
due_events = simulation_engine.event_queue.get_due_events(
    next_event.scheduled_time
)
for event in due_events:
    event.execute(simulation_engine.environment)

# 5. SimulationEngine returns summary
return {
    "current_time": next_event.scheduled_time,
    "events_executed": len(due_events),
    "next_event_time": simulation_engine.event_queue.peek_next()?.scheduled_time
}
```

#### Pattern 3: Auto-Advance Mode (SimulationLoop)

```python
# API handler starts simulation with auto_advance=True

# 1. API calls SimulationEngine.start()
simulation_engine.start(auto_advance=True, time_scale=10.0)

# 2. SimulationEngine creates and starts SimulationLoop
simulation_engine._loop = SimulationLoop(
    engine=simulation_engine,
    time_scale=10.0
)
simulation_engine._loop.start()

# 3. SimulationLoop runs on separate thread
while loop.is_running:
    if not environment.time_state.is_paused:
        # Calculate wall time elapsed
        wall_elapsed = now() - last_update
        
        # Call back to SimulationEngine.tick()
        simulation_engine.tick()
    
    sleep(0.01)  # 10ms

# 4. SimulationEngine.tick() handles advancement
def tick(self):
    # Calculate advancement
    wall_elapsed = now() - environment.time_state.last_wall_time_update
    sim_delta = environment.time_state.calculate_advancement(wall_elapsed)
    
    # Advance and execute
    environment.time_state.advance(sim_delta)
    execute_due_events()
```

#### Pattern 4: API State Query

```python
# API handler receives request for current state

# 1. API calls SimulationEngine
snapshot = simulation_engine.get_snapshot()

# 2. SimulationEngine delegates to Environment
env_snapshot = simulation_engine.environment.get_snapshot()

# 3. SimulationEngine adds simulation metadata
return {
    "simulation_id": simulation_engine.simulation_id,
    "is_running": simulation_engine.is_running,
    "mode": "auto_advance" if simulation_engine._loop else "manual",
    "environment": env_snapshot,
    "event_queue": {
        "pending_events": simulation_engine.event_queue.count_pending(),
        "next_event": simulation_engine.event_queue.peek_next()
    }
}
```

### What SimulationEngine IS Responsible For

✅ **Coordination** - Orchestrate all simulation operations  
✅ **Component Ownership** - Own Environment, EventQueue, SimulationLoop  
✅ **Time Control** - Implement all time control operations (advance, set, skip)  
✅ **Event Management** - Add events, execute due events, query events  
✅ **State Access** - Provide access to environment state  
✅ **Validation** - Validate simulation consistency  
✅ **Lifecycle** - Handle start, stop, pause, resume  
✅ **Mode Coordination** - Implement manual, event-driven, auto-advance modes  
✅ **Error Handling** - Catch errors, log, decide whether to continue  
✅ **API Gateway** - All REST API requests go through SimulationEngine  
✅ **Loop Control** - Start/stop SimulationLoop for auto-advance mode

### What SimulationEngine IS NOT Responsible For

❌ **Auto-Advance Threading** - SimulationLoop handles this  
❌ **Executing Events** - Events execute themselves  
❌ **Storing Events** - EventQueue manages storage  
❌ **Calculating Time Deltas** - SimulatorTime calculates  
❌ **Holding State** - Environment holds state  
❌ **Sorting Events** - EventQueue maintains order  
❌ **Validating Inputs** - ModalityInput validates itself  
❌ **Applying Inputs** - ModalityState applies inputs  
❌ **Wall-Clock Polling** - SimulationLoop does this

## SimulationLoop Class

### Purpose

The **SimulationLoop** is a threading-isolated component that implements the auto-advance main loop. It runs on a dedicated thread, polls wall-clock time, and calls back to SimulationEngine.tick() to perform the actual simulation work.

### Core Concept

Think of SimulationLoop as the **heartbeat generator** - it creates a steady rhythm of tick calls, but doesn't do the simulation work itself. It's a thin threading wrapper around SimulationEngine coordination logic.

### Design Principles

1. **Threading Isolation**: All threading complexity lives here
2. **Minimal Logic**: Just loop, timing, and tick callbacks
3. **Clean Interface**: Exposes only start(), stop(), is_running
4. **No Simulation Logic**: Delegates all work to SimulationEngine.tick()
5. **Graceful Shutdown**: Finishes current tick before stopping

### Attributes

```python
class SimulationLoop:
    """Auto-advance threading component for simulation.
    
    Runs main simulation loop on dedicated thread, calling back
    to SimulationEngine.tick() at regular intervals.
    """
    
    # Reference to parent engine
    engine: SimulationEngine
    
    # Threading state
    _thread: Optional[threading.Thread]
    _stop_event: threading.Event
    is_running: bool
    
    # Configuration
    tick_interval: float  # Seconds between ticks (default: 0.01 = 10ms)
```

#### Attribute Details

**`engine: SimulationEngine`**
- Reference to parent SimulationEngine
- Used to call engine.tick() on each loop iteration
- Provides access to is_paused state

**`_thread: Optional[threading.Thread]`**
- Thread running the main loop
- Created in start(), joined in stop()
- Private - external code uses start/stop methods

**`_stop_event: threading.Event`**
- Thread-safe stop signal
- Set by stop(), checked by loop
- Allows graceful shutdown

**`is_running: bool`**
- Whether loop thread is active
- Set to True in start(), False in stop()
- Can be queried without locking

**`tick_interval: float`**
- Seconds between tick calls
- Default: 0.01 (10ms = 100 ticks/second)
- Configurable for performance tuning

### Methods

SimulationLoop has just **4 public methods** - a minimal interface:

**`__init__(engine: SimulationEngine, tick_interval: float = 0.01)`**
```python
def __init__(
    self,
    engine: SimulationEngine,
    tick_interval: float = 0.01
) -> None:
    """Initialize simulation loop.
    
    Args:
        engine: Parent SimulationEngine to call back to
        tick_interval: Seconds between ticks (default 10ms)
    """
```

**`start() -> None`**
```python
def start(self) -> None:
    """Start the simulation loop thread.
    
    Creates new thread running _run_loop().
    
    Raises:
        RuntimeError: If loop is already running
    """
```

**`stop() -> None`**
```python
def stop(self) -> None:
    """Stop the simulation loop gracefully.
    
    Sets stop event, waits for thread to finish current tick.
    """
```

**`_run_loop() -> None`** (internal)
```python
def _run_loop(self) -> None:
    """Main loop that runs on dedicated thread.
    
    Continuously:
    1. Check stop event
    2. Check if paused
    3. Call engine.tick()
    4. Sleep for tick_interval
    """
```

### Implementation

```python
import threading
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .engine import SimulationEngine


class SimulationLoop:
    """Auto-advance threading component for simulation.
    
    Runs main simulation loop on dedicated thread, calling back
    to SimulationEngine.tick() at regular intervals.
    """
    
    def __init__(
        self,
        engine: "SimulationEngine",
        tick_interval: float = 0.01
    ) -> None:
        """Initialize simulation loop.
        
        Args:
            engine: Parent SimulationEngine to call back to
            tick_interval: Seconds between ticks (default 10ms)
        """
        self.engine = engine
        self.tick_interval = tick_interval
        
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.is_running = False
    
    def start(self) -> None:
        """Start the simulation loop thread.
        
        Creates new thread running _run_loop().
        
        Raises:
            RuntimeError: If loop is already running
        """
        if self.is_running:
            raise RuntimeError("Simulation loop is already running")
        
        self.is_running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
    
    def stop(self) -> None:
        """Stop the simulation loop gracefully.
        
        Sets stop event, waits for thread to finish current tick.
        """
        if not self.is_running:
            return
        
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        
        self.is_running = False
        self._thread = None
    
    def _run_loop(self) -> None:
        """Main loop that runs on dedicated thread.
        
        Continuously:
        1. Check stop event
        2. Check if paused
        3. Call engine.tick()
        4. Sleep for tick_interval
        """
        while not self._stop_event.is_set():
            # Skip tick if paused, but keep loop running
            if self.engine.environment.time_state.is_paused:
                time.sleep(self.tick_interval)
                continue
            
            try:
                # Let engine handle all simulation logic
                self.engine.tick()
            except Exception as e:
                # Log but don't crash thread
                print(f"Error during simulation tick: {e}")
                # Could add circuit breaker here if errors persist
            
            # Brief sleep to avoid busy loop
            time.sleep(self.tick_interval)
```

### Interaction Patterns

#### Pattern 1: Start Auto-Advance

```python
# SimulationEngine.start() creates and starts loop

def start(self, auto_advance: bool = False, time_scale: float = 1.0):
    if auto_advance:
        # Create loop with reference to self
        self._loop = SimulationLoop(engine=self)
        
        # Configure time scale
        self.environment.time_state.time_scale = time_scale
        
        # Start loop thread
        self._loop.start()
        # Loop now running on separate thread, calling self.tick()
```

#### Pattern 2: Stop Auto-Advance

```python
# SimulationEngine.stop() stops loop first

def stop(self):
    if self._loop and self._loop.is_running:
        # Signal loop to stop
        self._loop.stop()
        # Thread joins and finishes
        
    self._loop = None
    self.is_running = False
```

#### Pattern 3: Tick Callback

```python
# SimulationLoop._run_loop() calls back to engine

def _run_loop(self):
    while not self._stop_event.is_set():
        if not self.engine.environment.time_state.is_paused:
            # All simulation logic in engine
            self.engine.tick()
        
        time.sleep(self.tick_interval)

# SimulationEngine.tick() does the work

def tick(self):
    # 1. Calculate time advancement
    wall_elapsed = (
        datetime.now(timezone.utc) -
        self.environment.time_state.last_wall_time_update
    )
    sim_delta = self.environment.time_state.calculate_advancement(wall_elapsed)
    
    # 2. Advance time
    self.environment.time_state.advance(sim_delta)
    
    # 3. Execute due events
    self.execute_due_events()
```

### What SimulationLoop IS Responsible For

✅ **Thread Management** - Create, start, stop thread  
✅ **Main Loop** - Continuously call tick() until stopped  
✅ **Timing** - Sleep between ticks to control rate  
✅ **Stop Signal** - Respond to stop event gracefully  
✅ **Error Isolation** - Catch tick() errors without crashing thread  
✅ **Pause Handling** - Skip ticks when paused but keep loop running

### What SimulationLoop IS NOT Responsible For

❌ **Time Advancement** - SimulationEngine.tick() does this  
❌ **Event Execution** - SimulationEngine.tick() does this  
❌ **State Access** - Only references engine, not environment directly  
❌ **Validation** - No simulation logic at all  
❌ **Logging** - Engine handles logging  
❌ **Error Handling** - Just catches and logs, doesn't decide recovery  
❌ **Pause Logic** - Just checks is_paused flag, doesn't implement pause

## Component Interaction Summary

### Call Flow: API Request → Engine → Loop

```
REST API Handler
    │
    │ calls method
    ▼
SimulationEngine.advance_time()
    │
    ├─→ environment.time_state.advance()
    ├─→ event_queue.get_due_events()
    ├─→ event.execute(environment)
    └─→ return summary
```

### Call Flow: Auto-Advance Loop

```
SimulationLoop._run_loop()
    │ (on separate thread)
    │
    │ calls every 10ms
    ▼
SimulationEngine.tick()
    │
    ├─→ calculate time advancement
    ├─→ environment.time_state.advance()
    ├─→ execute_due_events()
    │       ├─→ event_queue.get_due_events()
    │       └─→ event.execute(environment)
    └─→ log results
```

### Component Ownership

```
SimulationEngine (owns everything)
    ├── Environment
    │   ├── SimulatorTime
    │   └── ModalityStates
    ├── EventQueue
    │   └── SimulatorEvents
    └── SimulationLoop (optional, for auto-advance)
```

## REST API Handling

### Architecture

The REST API layer sits **above** the SimulationEngine and delegates all operations to it. This is a clean separation:

```
FastAPI Routes
    │
    │ HTTP requests
    ▼
Route Handlers (thin wrappers)
    │
    │ call methods
    ▼
SimulationEngine (business logic)
    │
    │ delegates to
    ▼
Components (Environment, EventQueue, etc.)
```

### Design Principles

1. **Thin API Layer**: Route handlers just parse requests and call engine methods
2. **Engine as Gateway**: All simulation operations go through SimulationEngine
3. **No Business Logic in API**: Validation, coordination, execution all in engine
4. **Serialization Boundary**: API converts engine responses to JSON
5. **Error Translation**: API catches engine exceptions, returns HTTP status codes

### API Implementation Pattern

```python
# api/routes/time.py

from fastapi import APIRouter, HTTPException
from datetime import timedelta
from ..dependencies import get_simulation_engine

router = APIRouter(prefix="/simulator/time", tags=["time"])


@router.post("/advance")
async def advance_time(
    duration_seconds: float,
    engine: SimulationEngine = Depends(get_simulation_engine)
):
    """Advance simulator time by specified duration.
    
    Delegates to SimulationEngine.advance_time().
    """
    try:
        # Parse request
        delta = timedelta(seconds=duration_seconds)
        
        # Delegate to engine
        result = engine.advance_time(delta)
        
        # Return response (engine returns dict, FastAPI serializes to JSON)
        return result
        
    except ValueError as e:
        # Translate engine errors to HTTP errors
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Unexpected errors
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/set")
async def set_time(
    time: str,  # ISO format
    execute_skipped: bool = False,
    engine: SimulationEngine = Depends(get_simulation_engine)
):
    """Jump to specific simulator time."""
    try:
        # Parse request
        from datetime import datetime
        new_time = datetime.fromisoformat(time)
        
        # Delegate to engine
        result = engine.set_time(new_time, execute_skipped)
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/skip-to-next")
async def skip_to_next_event(
    engine: SimulationEngine = Depends(get_simulation_engine)
):
    """Skip to next scheduled event."""
    # No parsing needed, just delegate
    result = engine.skip_to_next_event()
    return result


@router.post("/pause")
async def pause(engine: SimulationEngine = Depends(get_simulation_engine)):
    """Pause simulation."""
    engine.pause()
    return {"status": "paused"}


@router.post("/resume")
async def resume(engine: SimulationEngine = Depends(get_simulation_engine)):
    """Resume simulation."""
    engine.resume()
    return {"status": "running"}


@router.get("/")
async def get_time_state(
    engine: SimulationEngine = Depends(get_simulation_engine)
):
    """Get current time state."""
    # Engine method returns serializable dict
    snapshot = engine.get_snapshot()
    return snapshot["environment"]["time"]
```

### Dependency Injection

```python
# api/dependencies.py

from typing import Annotated
from fastapi import Depends

# Global simulation engine instance (created at startup)
_simulation_engine: Optional[SimulationEngine] = None


def get_simulation_engine() -> SimulationEngine:
    """FastAPI dependency that provides simulation engine.
    
    Used in route handlers via Depends().
    """
    if _simulation_engine is None:
        raise RuntimeError("Simulation engine not initialized")
    return _simulation_engine


def set_simulation_engine(engine: SimulationEngine) -> None:
    """Called during app startup to set engine instance."""
    global _simulation_engine
    _simulation_engine = engine


# Type alias for convenience
SimEngine = Annotated[SimulationEngine, Depends(get_simulation_engine)]


# Usage in routes:
@router.get("/status")
async def get_status(engine: SimEngine):
    return engine.get_snapshot()
```

### Application Startup

```python
# main.py (or api/app.py)

from fastapi import FastAPI
from api.dependencies import set_simulation_engine
from api.routes import time, events, environment, simulation
from models import Environment, EventQueue, SimulationEngine, SimulatorTime
from datetime import datetime, timezone


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="User Environment Simulator",
        description="AI-driven testing tool for personal assistants",
        version="0.1.0"
    )
    
    # Create simulation components
    initial_time = datetime(2024, 3, 15, 8, 0, tzinfo=timezone.utc)
    time_state = SimulatorTime(
        current_time=initial_time,
        time_scale=1.0,
        is_paused=False,
        last_wall_time_update=datetime.now(timezone.utc),
        auto_advance=False
    )
    
    environment = Environment(
        modality_states={},  # Empty initially, populated via API
        time_state=time_state
    )
    
    event_queue = EventQueue()
    
    engine = SimulationEngine(
        environment=environment,
        event_queue=event_queue
    )
    
    # Set global engine for dependency injection
    set_simulation_engine(engine)
    
    # Register routes
    app.include_router(time.router)
    app.include_router(events.router)
    app.include_router(environment.router)
    app.include_router(simulation.router)
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Concurrency Considerations

**Thread Safety**:
- SimulationLoop runs on dedicated thread
- FastAPI handlers run on web framework threads
- SimulationEngine methods are called from both

**Synchronization Strategy**:
- Read operations (get_snapshot, query_events) can run concurrently
- Write operations (advance_time, execute_events) should be synchronized
- Use threading.Lock for critical sections in SimulationEngine

**Example**:
```python
class SimulationEngine:
    def __init__(self, ...):
        # ... other attributes
        self._operation_lock = threading.Lock()
    
    def advance_time(self, delta: timedelta) -> dict:
        """Thread-safe time advancement."""
        with self._operation_lock:
            # Critical section - only one thread advances time
            self.environment.time_state.advance(delta)
            return self.execute_due_events()
    
    def tick(self) -> None:
        """Called by SimulationLoop - uses same lock."""
        with self._operation_lock:
            # Calculate and advance
            wall_elapsed = ...
            sim_delta = ...
            self.environment.time_state.advance(sim_delta)
            self.execute_due_events()
    
    def get_snapshot(self) -> dict:
        """Read-only operation - no lock needed if reads are atomic."""
        # Python dict reads are atomic, but for consistency:
        return self.environment.get_snapshot()
```

## Testing Strategy

### Unit Testing

**Test SimulationEngine in Isolation**:
```python
def test_advance_time():
    """Test time advancement without threading."""
    # Create components
    env = create_test_environment()
    queue = EventQueue()
    engine = SimulationEngine(env, queue)
    
    # Add event
    event = create_test_event(scheduled_time=env.time_state.current_time + timedelta(hours=1))
    queue.add_event(event)
    
    # Advance time
    result = engine.advance_time(timedelta(hours=1))
    
    # Verify
    assert result["events_executed"] == 1
    assert event.status == EventStatus.EXECUTED
```

**Test SimulationLoop in Isolation**:
```python
def test_simulation_loop_calls_tick():
    """Test loop calls tick() repeatedly."""
    # Create mock engine that counts tick calls
    class MockEngine:
        def __init__(self):
            self.tick_count = 0
            self.environment = Mock()
            self.environment.time_state.is_paused = False
        
        def tick(self):
            self.tick_count += 1
    
    mock_engine = MockEngine()
    loop = SimulationLoop(mock_engine, tick_interval=0.01)
    
    # Start loop
    loop.start()
    
    # Wait briefly
    time.sleep(0.1)
    
    # Stop loop
    loop.stop()
    
    # Verify tick was called multiple times
    assert mock_engine.tick_count >= 5  # ~10 ticks in 100ms
```

### Integration Testing

**Test Engine + Loop Together**:
```python
def test_auto_advance_executes_events():
    """Test auto-advance mode executes events at correct time."""
    # Create real components
    env = create_test_environment()
    queue = EventQueue()
    engine = SimulationEngine(env, queue)
    
    # Add events at future times
    event1 = create_test_event(
        scheduled_time=env.time_state.current_time + timedelta(seconds=0.05)
    )
    event2 = create_test_event(
        scheduled_time=env.time_state.current_time + timedelta(seconds=0.1)
    )
    queue.add_event(event1)
    queue.add_event(event2)
    
    # Start auto-advance at 10x speed
    engine.start(auto_advance=True, time_scale=10.0)
    
    # Wait for events to execute (0.1s * 10x = 0.01s real time, but add margin)
    time.sleep(0.2)
    
    # Stop
    engine.stop()
    
    # Verify both events executed
    assert event1.status == EventStatus.EXECUTED
    assert event2.status == EventStatus.EXECUTED
```

### API Testing

**Test REST API Layer**:
```python
from fastapi.testclient import TestClient

def test_advance_time_endpoint():
    """Test time advancement via API."""
    # Create app with test engine
    app = create_test_app()
    client = TestClient(app)
    
    # Make API request
    response = client.post("/simulator/time/advance", json={
        "duration_seconds": 3600
    })
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert "current_time" in data
    assert data["events_executed"] >= 0
```

## Implementation Checklist

### Phase 1: Core Classes

- [ ] Implement SimulationEngine class (~300 lines)
  - [ ] Lifecycle methods (init, start, stop, reset)
  - [ ] Time control methods (advance, set, skip-to-next, pause, resume)
  - [ ] Event management methods (add, execute_due, query)
  - [ ] State access methods (get_state, get_snapshot, validate)
  - [ ] tick() method for loop callback
  - [ ] Threading lock for synchronization

- [ ] Implement SimulationLoop class (~150 lines)
  - [ ] init, start, stop methods
  - [ ] _run_loop() main loop implementation
  - [ ] Thread management and stop event
  - [ ] Error handling in loop

### Phase 2: Integration

- [ ] Update models/__init__.py to export both classes
- [ ] Write unit tests for SimulationEngine
- [ ] Write unit tests for SimulationLoop
- [ ] Write integration tests for engine + loop
- [ ] Test all time control modes (manual, event-driven, auto-advance)

### Phase 3: API Layer

- [ ] Create api/ directory structure
- [ ] Implement dependency injection (dependencies.py)
- [ ] Implement time control routes (api/routes/time.py)
- [ ] Implement event routes (api/routes/events.py)
- [ ] Implement environment routes (api/routes/environment.py)
- [ ] Implement simulation control routes (api/routes/simulation.py)
- [ ] Write API integration tests
- [ ] Test concurrent API requests

### Phase 4: Documentation & Examples

- [ ] Add docstrings to all public methods
- [ ] Create usage examples for each mode
- [ ] Document threading model and synchronization
- [ ] Add troubleshooting guide

## Design Decisions

### Decision 1: Why Separate SimulationLoop?

**Rationale**: Threading is complex and error-prone. Isolating it in a separate class:
- Makes SimulationEngine testable without threads
- Contains threading bugs to one small class
- Provides clear interface (start/stop/tick)
- Allows easy swap of threading implementation (could use asyncio later)

**Alternative Considered**: Keep loop in SimulationEngine as _run_loop() method
**Why Rejected**: Makes engine harder to test, mixes concerns, harder to understand

### Decision 2: Why tick() in SimulationEngine?

**Rationale**: The simulation work (advancing time, executing events) is coordination logic that belongs in SimulationEngine, not threading logic.

**Alternative Considered**: Put simulation logic in SimulationLoop._run_loop()
**Why Rejected**: Violates separation of concerns, makes loop class too complex, harder to test

### Decision 3: Why Single Lock Instead of Fine-Grained?

**Rationale**: For MVP, a single operation lock is simpler and sufficient. Performance won't be bottlenecked by lock contention initially.

**Alternative Considered**: Separate locks for time, events, state
**Why Rejected**: More complex, easy to introduce deadlocks, premature optimization

**Future Consideration**: If profiling shows lock contention, can refactor to reader-writer locks

### Decision 4: Why Dependency Injection for API?

**Rationale**: FastAPI's Depends() pattern is idiomatic and allows easy testing with mock engines.

**Alternative Considered**: Global singleton, middleware-injected engine
**Why Rejected**: Harder to test, less explicit, couples routes to global state

### Decision 5: Why Engine Owns Loop Instead of Vice Versa?

**Rationale**: SimulationEngine is the primary orchestrator. Loop is just a helper for one specific mode (auto-advance).

**Alternative Considered**: Loop owns engine and calls its methods
**Why Rejected**: Inverts control flow, makes engine feel like a utility instead of orchestrator

## Future Considerations

### Refactoring Triggers

**When to split SimulationEngine further**:
- Engine exceeds 500 lines
- Time control methods become complex (>50 lines each)
- API handling logic grows beyond simple delegation
- Need different strategies for event execution

**Potential Future Classes**:
- TimeController: Dedicated time management
- EventExecutor: Event execution strategies
- StateValidator: Complex validation logic
- ConfigManager: Configuration loading/saving

### Performance Optimizations

**If tick rate needs improvement**:
- Reduce tick_interval (currently 10ms)
- Optimize execute_due_events() with early exit
- Cache next_event_time instead of peeking every tick
- Use threading.Condition instead of sleep for instant wakeup

**If lock contention becomes issue**:
- Implement reader-writer lock for state queries
- Use lock-free data structures for event queue
- Separate locks for time vs events vs state

### API Enhancements

**Future API Features**:
- WebSocket endpoint for real-time state streaming
- Bulk event upload (POST /events/bulk)
- State persistence (POST /simulation/checkpoint)
- State rollback (POST /simulation/rollback)
- Performance metrics (GET /simulation/metrics)

**Authentication & Multi-Tenancy**:
- Multiple simultaneous simulations
- Per-simulation authentication tokens
- Simulation-scoped event queues

## Summary

The hybrid architecture provides:

1. **Clear Separation**: Coordination (SimulationEngine) vs Threading (SimulationLoop)
2. **Testability**: Each component testable in isolation
3. **Manageable Size**: ~300 + ~150 lines instead of 500-1000
4. **Clean API**: Thin routes delegate to engine methods
5. **Thread Safety**: Single lock protects critical sections
6. **Extensibility**: Easy to refactor further if needed

This design balances MVP speed with long-term maintainability while providing a solid foundation for implementing the complete orchestration requirements from ORCHESTRATION.md.
