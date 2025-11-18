# User Environment Simulator

The User Environment Simulator (UES) is an AI-driven testing and prototyping tool for AI personal assistants such as my AIPA project. The UES provides a simple web app-based UI through which the developer can simulate a variety of different input modalities to a personal assistant agent, allowing for customizable and replicable testing of AI capabilities.

## Supported Modalities

The UES will eventually support simulation of:
* User Location
* Current Time
* Current Weather Data
* Chat-style User Interaction
* Email
* Calendar
* Text (SMS/RCS)
* File System
* Discord
* Slack
* Social Media
* Screen Simulation

## Overview

Beyond these modalities, the UES allows the developer to design the entire user environment the agent is accessing and to coordinate sequences of events and inputs to the agent. The objective is to allow the developer to simulate all the inputs a user might receive in a fluid, realistic manner, so that they can test how the agent handles a variety of circumstances. 

For example, the developer could simulate a college student by adding in emails about classes, clubs, school events and announcements, targeted ads, etc.; add texts from classmates, friends, and parents about homework, social life, gossip, clubs, and dating; add calendar entries for classes, clubs, and social events; set the user's location to a college campus; add homework documents to their file system; and so on. Then the developer can set up a sequence of events, with new emails and texts being received, new files being created, old files being edited, user queries, and time passing. Then, by hooking up their AI agent to the simulator, the agent "sees" all these modalities as if they are happening in real time. 

Crucially, AI agents can be easily integrated directly into the simulation process, automatically generating new inputs (emails, texts, even user interactions) on the fly and in response to the personal assistant agent's actions. This process can be carefully controlled or disabled by the developer to ensure the generating inputs are themselves replicable and relevant.

The various modalities are exposed using a RESTful API, which makes connecting agents a breeze, and the web app provides a simple and clear interface for designing the environment. 

## Architecture

### Event-Sourcing Design

UES uses an **event-sourcing architecture** where the simulation state progresses through discrete events:

1. **Events** carry `ModalityInput` payloads that describe changes to occur
2. **ModalityStates** represent the current state of each modality (email inbox, location, etc.)
3. **Environment** holds all current modality states and the simulator time
4. **SimulationEngine** orchestrates time advancement and event execution

When an event executes, its input is applied to the appropriate modality state, updating the environment. This design ensures:
- **Replicability**: Same event sequence produces same results
- **Time Control**: Support for manual, event-driven, and auto-advance modes
- **State Snapshots**: Complete environment state at any simulator time
- **Testability**: Each component has clear, isolated responsibilities

### Simulation Modes

The simulator supports three time control modes:

**Manual Mode**: Time advances only via explicit API calls
- Developer controls exactly when time moves forward
- Useful for step-by-step debugging and precise control

**Event-Driven Mode**: Time skips directly to next scheduled event
- Efficiently moves through sparse event sequences
- Each skip executes all events at that time

**Auto-Advance Mode**: Time progresses automatically at configurable speed
- Real-time (1x), fast-forward (10x, 100x), or slow-motion (0.5x)
- Events execute when their scheduled time is reached
- Simulation runs on background thread with pause/resume support

### Component Architecture

```
SimulationEngine (Orchestrator)
    ├── Environment (Current state)
    │   ├── SimulatorTime (Virtual time tracking)
    │   └── ModalityStates (Email, Location, Calendar, etc.)
    ├── EventQueue (Scheduled events)
    └── SimulationLoop (Auto-advance threading)
```

The **SimulationEngine** coordinates all operations through a clean delegation pattern:
- Owns all core components (Environment, EventQueue, SimulationLoop)
- Implements time control operations (advance, set, skip-to-next, pause, resume)
- Manages event execution (add, execute, query)
- Provides state access and validation
- Handles API requests and error logging

The **SimulationLoop** isolates threading complexity:
- Runs main loop on dedicated thread for auto-advance mode
- Polls wall-clock time and calculates simulator time advancement
- Calls back to SimulationEngine.tick() for actual work
- Simple interface: start(), stop(), no simulation logic

For detailed architecture documentation, see:
- `docs/SIMULATION_ENGINE.md` - Orchestration design
- `docs/ENVIRONMENT.md` - State container design
- `docs/SIMULATOR_TIME.md` - Time management
- `docs/ORCHESTRATION.md` - Complete orchestration requirements

## REST API

The UES exposes a comprehensive RESTful API organized into four categories:

### Time Control (`/simulator/time`)
- `GET /simulator/time` - Get current time state (time, scale, paused status, mode)
- `POST /simulator/time/advance` - Manually advance time by duration
- `POST /simulator/time/set` - Jump to specific time (with skip handling)
- `POST /simulator/time/skip-to-next` - Jump to next event (event-driven mode)
- `POST /simulator/time/pause` - Freeze time advancement
- `POST /simulator/time/resume` - Unfreeze time
- `POST /simulator/time/set-scale` - Change time multiplier (1x, 10x, etc.)

### Environment State (`/environment`)
- `GET /environment/state` - Get complete state snapshot (time + all modalities)
- `GET /environment/modalities` - List available modalities
- `GET /environment/modalities/{modality}` - Get specific modality state
- `POST /environment/modalities/{modality}/query` - Query with filterss
- `POST /environment/validate` - Validate environment consistency

### Event Management (`/events`)
- `GET /events` - List events with filters (status, time range, modality)
- `POST /events` - Create new scheduled event with full control over timing and metadata
- `POST /events/immediate` - Submit event for immediate execution at current simulator time (convenience endpoint for agent actions)
- `GET /events/{event_id}` - Get specific event details
- `DELETE /events/{event_id}` - Cancel pending event
- `GET /events/next` - Peek at next pending event
- `GET /events/summary` - Get execution statistics
- `POST /modalities/{modality}/submit` - Submit immediate action to specific modality (highest-level convenience for agents)

### Simulation Control (`/simulation`)
- `POST /simulation/start` - Start simulation (manual or auto-advance mode)
- `POST /simulation/stop` - Stop simulation gracefully
- `GET /simulation/status` - Get current status and metrics
- `POST /simulation/reset` - Reset to initial state

All endpoints return JSON responses with appropriate HTTP status codes. The API is designed for:
- **Simplicity**: Intuitive endpoints that match developer mental model
- **Completeness**: Full control over all simulation operations
- **Real-time Updates**: WebSocket support planned for state streaming
- **Error Handling**: Comprehensive validation with detailed error messages

#### Agent Action Convenience Endpoints

While all state changes flow through the event pipeline (`POST /events`), two convenience endpoints simplify common agent use cases:

**`POST /events/immediate`** - Submits an event scheduled for immediate execution:
- Automatically sets `scheduled_time` to current simulator time
- Sets high priority (100) to execute before other same-time events
- Requires full `ModalityInput` payload but handles event metadata automatically
- Returns created event with assigned ID
- Use when agent needs to respond immediately (e.g., chat reply, email sent)

**`POST /modalities/{modality}/submit`** - Highest-level convenience for modality-specific actions:
- Even simpler payload, just the action-specific fields
- Internally creates appropriate `ModalityInput` and submits as immediate event
- Most ergonomic for agents: `POST /modalities/chat/submit {"role": "assistant", "content": "Hello!"}`
- Returns both the created event and updated modality state

Both endpoints maintain architectural consistency by using the same event pipeline, ensuring all agent actions are captured in the event history for replicability and debugging.

## Environment Design

The simulated environment consists of a set of developer-created inputs for each modality, such as emails, texts, calendar events, user location, etc., each of which has a timestamp, the initial simulator time, and optionally one or more agents with developer-designed prompts which can be set up to either generate new inputs or to react to agent responses. These are all designed via the web app interface.

### Initial State Configuration

Environments begin with **initial states** for each modality:
- **Email**: Starting inbox contents, folder structure, read status
- **Calendar**: Initial event schedule, recurring meetings
- **Location**: Starting coordinates, movement patterns
- **File System**: Directory structure, file contents, permissions
- And so on for all supported modalities

### Event Sequences

Developers define **timed event sequences** that modify states over simulator time:
- New email arrives at T+1:30:00
- Text message received at T+2:15:00
- User moves location at T+3:00:00
- File is edited at T+4:45:00

Each event carries a `ModalityInput` that describes the change and is applied to the appropriate `ModalityState` when executed.

### Event Agent Integration (Planned)

AI agents can be integrated to dynamically generate events:
- **Trigger-based**: Generate email when certain conditions met
- **Response-based**: React to personal assistant's actions
- **Scheduled**: Periodic generation (e.g., daily weather update)
- **Controlled**: Developer can enable/disable, seed for reproducibility

This creates realistic, dynamic environments while maintaining developer control over replicability.

## Current Status

**Phase 1: Data Models** - ✅ Complete
- ✅ Base classes (`ModalityInput`, `ModalityState`)
- ✅ Core infrastructure (`SimulatorEvent`, `EventQueue`, `SimulatorTime`, `Environment`)
- ✅ Orchestration layer (`SimulationEngine`, `SimulationLoop`)
- ✅ Comprehensive testing (manual mode, auto-advance, pause/resume)

**Phase 2: Modality Implementations** - 🚧 In Progress
- Priority 1: Location, Time, Weather (simple foundational modalities)
- Priority 2: Email, Calendar, SMS/RCS (message-based modalities)
- Priority 3: File System, Discord, Slack, Social Media, Screen (complex integrations)

**Phase 3: REST API** - 📋 Planned
- FastAPI implementation
- Endpoint handlers with dependency injection
- WebSocket support for real-time updates
- API documentation (auto-generated via OpenAPI)

**Phase 4: Web UI** - 📋 Planned
- Environment designer interface
- Event sequence builder
- Real-time simulation monitoring
- State inspection and debugging tools