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
- `POST /environment/validate` - Validate environment consistency

### Event Management (`/events`)
- `GET /events` - List events with filters (status, time range, modality)
- `POST /events` - Create new scheduled event with full control over timing and metadata
- `POST /events/immediate` - Submit event for immediate execution at current simulator time
- `GET /events/{event_id}` - Get specific event details
- `DELETE /events/{event_id}` - Cancel pending event
- `GET /events/next` - Peek at next pending event
- `GET /events/summary` - Get execution statistics

### Modality-Specific Routes
Each modality has dedicated endpoints for type-safe interactions:

**Email (`/email`)**
- `GET /email/state` - Current email state (all folders, threads)
- `POST /email/query` - Query emails with filters
- `POST /email/send` - Send a new email
- `POST /email/receive` - Simulate receiving an email
- `POST /email/read`, `/unread`, `/star`, `/unstar` - Mark emails
- `POST /email/archive`, `/delete`, `/move` - Organize emails
- `POST /email/label`, `/unlabel` - Manage labels

**SMS (`/sms`)**
- `GET /sms/state` - Current SMS state (all threads, messages)
- `POST /sms/query` - Query messages with filters
- `POST /sms/send` - Send a message
- `POST /sms/receive` - Simulate receiving a message
- `POST /sms/read`, `/unread`, `/delete` - Manage messages
- `POST /sms/react` - Add reaction (RCS)

**Chat (`/chat`)**
- `GET /chat/state` - Current chat state (all conversations)
- `POST /chat/query` - Query chat history
- `POST /chat/send` - Send a chat message
- `POST /chat/delete` - Delete a message
- `POST /chat/clear` - Clear conversation history

**Calendar (`/calendar`)**
- `GET /calendar/state` - Current calendar state (all events)
- `POST /calendar/query` - Query events with filters
- `POST /calendar/create` - Create a calendar event
- `POST /calendar/update` - Update an event
- `POST /calendar/delete` - Delete an event
- `POST /calendar/accept`, `/decline`, `/tentative` - Respond to invitations

**Location (`/location`)**
- `GET /location/state` - Current location
- `POST /location/update` - Update coordinates
- `POST /location/move-to` - Move to named place

**Weather (`/weather`)**
- `GET /weather/state` - Current weather state
- `POST /weather/update` - Update weather conditions
- `POST /weather/set-location` - Change weather location

### Simulation Control (`/simulation`)
- `POST /simulation/start` - Start simulation (manual or auto-advance mode)
- `POST /simulation/stop` - Stop simulation gracefully
- `GET /simulation/status` - Get current status and metrics
- `POST /simulation/reset` - Reset to initial state

All endpoints return JSON responses with appropriate HTTP status codes. The API is designed for:
- **Type Safety**: Pydantic models for all requests and responses
- **Simplicity**: Action-specific endpoints (e.g., `/email/send`) are more intuitive than generic submission
- **Completeness**: Full control over all simulation operations
- **Documentation**: FastAPI auto-generates OpenAPI docs from typed models
- **Real-time Updates**: WebSocket support planned for state streaming
- **Error Handling**: Comprehensive validation with detailed error messages

For detailed API documentation, see `docs/REST_API.md` and `docs/MODALITY_ROUTES.md`.

## Environment Design

The simulated environment consists of developer-created inputs for each modality—emails, texts, calendar events, user location, etc.—each with a timestamp. Scenarios define the initial state and scheduled events, which are designed via the web app interface or created programmatically through the API.

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

### External Agent Integration

UES is designed as an **agent-interactable simulation platform**. While the core UES framework is purely deterministic (scenarios are data, not code), it exposes a comprehensive REST API that enables powerful agent integrations:

```
┌─────────────────────────────────────────────────────────────────┐
│                    UES Core (Pure Simulation)                   │
│  • Deterministic scenario execution                             │
│  • State management & event scheduling                          │
│  • REST API + WebSocket (planned)                               │
└───────────────────────────────┬─────────────────────────────────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         │                      │                      │
   Simulator-Side         User-Side Agent         Developer
   Agent (external)       (being tested)          (Web UI)
         │                      │                      │
         └──────────────────────┴──────────────────────┘
                    All use the same REST API
```

**Key Design Principle**: Both simulator-side agents (that generate test content) and user-side agents (being tested) are external to UES. They connect via the same API, enabling:

- **Framework Freedom**: Use any LLM provider, agent framework, or programming language
- **Cost Control**: Manage your own API keys and model selection
- **Custom Logic**: Implement reactive behaviors, triggers, or content generation as needed
- **No UES Modifications**: Build sophisticated test environments without changing UES core
- **Reproducibility by Default**: Export any simulation state as a deterministic scenario

**Example Use Cases**:
- **Reactive Agents**: Monitor for sent emails, automatically generate and schedule reply events
- **Content Generation**: Use LLMs to create realistic email bodies, SMS messages, calendar descriptions
- **Trigger-based Events**: Watch for conditions (location, time, state) and schedule events when met
- **Character Simulation**: Maintain character personalities that respond consistently to user actions

For detailed patterns and examples, see `docs/SCENARIOS.md` and `docs/simulation_agents/EVENT_GENERATION_AGENT.md`.

## Current Status

**Phase 1: Data Models** - ✅ Complete
- ✅ Base classes (`ModalityInput`, `ModalityState`)
- ✅ Core infrastructure (`SimulatorEvent`, `EventQueue`, `SimulatorTime`, `Environment`)
- ✅ Orchestration layer (`SimulationEngine`, `SimulationLoop`)
- ✅ Comprehensive testing (manual mode, auto-advance, pause/resume)

**Phase 2: Modality Implementations** - ✅ Priority 1 & 2 Complete
- ✅ Location, Time, Weather (simple foundational modalities)
- ✅ Email, Calendar, SMS/RCS, Chat (message-based modalities)
- 📋 File System, Discord, Slack, Social Media, Screen (complex integrations planned)

**Phase 3: REST API** - 🚧 In Progress
- ✅ FastAPI implementation with core routes
- ✅ Modality-specific typed endpoints (Email, SMS, Chat, Calendar, Location, Weather)
- ✅ Event management and time control endpoints
- ✅ Shared base models and utilities
- 🚧 Integration tests for all routes
- 📋 WebSocket support for real-time updates

**Phase 4: Web UI** - 📋 Planned
- Environment designer interface
- Event sequence builder
- Real-time simulation monitoring
- State inspection and debugging tools