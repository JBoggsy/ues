# UES REST API Overview

The User Environment Simulator exposes a comprehensive RESTful API for controlling simulation time, managing events, querying environment state, and interacting with individual modalities.

## API Organization

The API is organized into six main categories:

1. **Time Control** - Manage simulator time advancement and scaling
2. **Environment State** - Query current state across all modalities
3. **Event Management** - Create, query, and manage simulation events
4. **Simulation Control** - Start, stop, and reset simulations
5. **Scenario Save/Load** - Export and import simulation state
6. **Modality-Specific Routes** - Type-safe endpoints for each modality

## Documentation Resources

### For Detailed API Reference

- **Interactive API Docs**: When the server is running, visit:
  - `http://localhost:8000/docs` - Swagger UI (interactive testing)
  - `http://localhost:8000/redoc` - ReDoc (alternative view)
  - `http://localhost:8000/openapi.json` - OpenAPI schema

- **Modality Route Patterns**: See `docs/MODALITY_ROUTES.md` for detailed implementation patterns and examples for modality-specific endpoints

- **Code Documentation**: All route handlers include comprehensive docstrings describing request/response formats, parameters, and behavior

### For Implementation Details

- **Route Handlers**: See `api/routes/` directory for all endpoint implementations
- **Shared Models**: See `api/models.py` for common request/response models
- **Utilities**: See `api/utils.py` for helper functions used across routes

---

## Quick Reference

### 1. Time Control (`/simulator/time`)

Control the flow of simulator time:

- `GET /simulator/time` - Get current time state
- `POST /simulator/time/advance` - Advance time by duration
- `POST /simulator/time/set` - Jump to specific time
- `POST /simulator/time/skip-to-next` - Jump to next event
- `POST /simulator/time/pause` - Pause time advancement
- `POST /simulator/time/resume` - Resume time advancement
- `POST /simulator/time/set-scale` - Change time multiplier (e.g., 10x speed)

**Use Cases:**
- Step through simulation manually
- Fast-forward to next event
- Control auto-advance speed

---

### 2. Environment State (`/environment`)

Query the current state of the simulated environment:

- `GET /environment/state` - Complete snapshot (all modalities + time)
  - `?compact=true` - Return LLM-optimized compact snapshot (~2KB vs 50KB+)
  - `?format=text` - Return plain text (only with `compact=true`)
- `GET /environment/modalities` - List available modalities
- `GET /environment/modalities/{modality}` - Get specific modality state
- `POST /environment/validate` - Validate environment consistency

**Compact Snapshot (`GET /environment/state?compact=true`):**

Returns a compact, LLM-context-optimized snapshot ideal for AI agent integration. This provides a middle ground between the full state dump (too verbose for LLM context windows) and brief summaries (insufficient for decision-making).

**Query Parameters:**
| Parameter | Values | Description |
|-----------|--------|-------------|
| `compact` | `true`/`false` | Enable compact snapshot mode (default: false) |
| `format` | `json`/`text` | Output format (default: json, text only with compact) |

**What's Included in Compact vs Full State:**

| Modality | Full State | Compact Snapshot |
|----------|------------|------------------|
| **Email** | All emails with full bodies, all metadata | Unread count, recent subjects (no bodies), flagged items |
| **SMS** | All messages, full conversation histories | Unread conversations, last message preview per conversation |
| **Chat** | Complete message history | Recent message count, last user/assistant exchange |
| **Calendar** | All events with full details | Current/next event, today's event count |
| **Location** | Current + full history | Current location only (with address if available) |
| **Weather** | All tracked locations, full forecast data | Current conditions at tracked locations |
| **Time** | Full state | Current timezone, time format preferences |

**Example Use Cases:**

1. **LLM Context Injection** - Inject current world state into an LLM system prompt:
   ```python
   snapshot = client.environment.get_state(compact=True, format="text")
   response = llm.complete(
       system_prompt=f"You are an assistant. Current context:\n{snapshot}",
       user_prompt=user_message
   )
   ```

2. **Reactive Agent Decision-Making** - Quickly assess context after a webhook notification:
   ```python
   async def on_email_received(webhook_event):
       snapshot = await client.environment.get_state(compact=True)
       # Feed to LLM with the new email details for decision-making
   ```

3. **Test Assertions** - Capture compact state for before/after comparisons:
   ```python
   before = client.environment.get_state(compact=True)
   await agent.handle_request("Schedule a meeting")
   after = client.environment.get_state(compact=True)
   assert after.modalities["calendar"]["today_count"] > before.modalities["calendar"]["today_count"]
   ```

**Example Compact JSON Response:**
```json
{
  "snapshot_time": "2024-01-15T10:00:00Z",
  "format": "compact",
  "modalities": {
    "email": {"unread_count": 3, "recent_unread": [...]},
    "calendar": {"today_count": 2, "current_event": {...}},
    "location": {"current": {"latitude": 37.7749, "longitude": -122.4194}}
  },
  "events": {"pending_count": 5, "next_event_time": "2024-01-15T12:00:00Z"}
}
```

**Example Text Format Output:**
```
=== UES Environment Snapshot ===
Time: 2024-03-15 14:30 PST (America/Los_Angeles)

📍 LOCATION: San Francisco, CA (37.7749, -122.4194)
🌤️ WEATHER: Partly cloudy, 68°F (20°C)
📧 EMAIL: 5 unread, 23 total
  • [2h ago] "Re: Project Update" from alice@work.com
📅 CALENDAR: 2 events today
  • NOW: Team Standup (ends in 15 min)
  • 3:00 PM: 1:1 with Manager
💬 SMS: 2 unread conversations
⏳ PENDING EVENTS: 3 scheduled
```

---

### 3. Event Management (`/events`)

Create and manage simulation events:

- `GET /events` - List events with filters (status, time range, modality)
- `POST /events` - Create new scheduled event
- `POST /events/batch` - Create multiple events in one request (up to 1000)
- `POST /events/immediate` - Execute event at current time
- `GET /events/{event_id}` - Get event details
- `DELETE /events/{event_id}` - Cancel pending event
- `GET /events/next` - Preview next pending event
- `GET /events/summary` - Get execution statistics

**Batch Event Submission (`POST /events/batch`):**

Create multiple events efficiently in a single request. Supports three modes:

| Mode | Behavior | HTTP Status |
|------|----------|-------------|
| Default | Create valid events, skip invalid ones | 201 (all pass) or 207 (partial) |
| `stop_on_first_error=true` | Reject all if any invalid | 201 (pass) or 400 (fail) |
| `validate_only=true` | Dry-run validation only | 200 |

Response includes per-event results with `index`, `success`, `event_id`, and `error` fields.

**Use Cases:**
- Schedule future modality changes
- Batch schedule multiple events efficiently (scenario setup, agent responses)
- Query event history
- Execute immediate actions
- Track event execution

---

### 4. Simulation Control (`/simulation`)

Manage simulation lifecycle:

- `POST /simulation/start` - Start simulation
- `POST /simulation/stop` - Stop simulation gracefully
- `GET /simulation/status` - Get status and metrics
- `POST /simulation/reset` - Reset to initial state (**NOT YET IMPLEMENTED**)
- `POST /simulation/clear` - Clear all events and states (**NOT YET IMPLEMENTED**)

**Reset vs Clear:**
- **Reset** (planned): Restores simulation to a defined "initial state" - the time, events, and modality states that existed when the simulation was first configured. Useful for replaying the same scenario multiple times. Requires infrastructure for tracking/loading initial state.
- **Clear** (planned): Completely empties the simulation - destroys all events, resets all modality states to empty defaults, and resets time. Useful for starting completely fresh.

**Use Cases:**
- Initialize new simulation run
- Monitor simulation health
- Reset for replaying scenarios (when implemented)
- Clear for fresh testing (when implemented)

---

### 5. Scenario Save/Load (`/scenario`)

Export and import simulation state for saving scenarios to files:

**Export Endpoints:**
- `GET /scenario/export/environment` - Export environment state only
- `GET /scenario/export/events` - Export event queue only
- `GET /scenario/export/full` - Export complete scenario with metadata

**Import Endpoints:**
- `POST /scenario/import/environment` - Import environment state
- `POST /scenario/import/events` - Import event queue (replace or merge)
- `POST /scenario/import/full` - Import complete scenario

**File Extensions:**
- `.ues-env.json` - Environment-only exports
- `.ues-events.json` - Event queue-only exports
- `.ues-scenario.json` - Complete scenario exports

**Use Cases:**
- Save simulation state for later restoration
- Share scenarios between users
- Create regression test fixtures
- Checkpoint long-running simulations

#### Export Examples

```bash
# Export complete scenario
GET /scenario/export/full?author=Developer&description=Test%20scenario

# Response:
{
  "scenario": {
    "metadata": {
      "ues_version": "0.1.0",
      "scenario_version": "1",
      "created_at": "2025-01-01T00:00:00Z",
      "author": "Developer",
      "description": "Test scenario"
    },
    "environment": {
      "time_state": {...},
      "modality_states": {...}
    },
    "events": {
      "events": [...]
    }
  }
}
```

```bash
# Export environment only
GET /scenario/export/environment

# Response:
{
  "environment": {
    "time_state": {...},
    "modality_states": {...}
  },
  "modalities_exported": ["weather", "email", "sms", "chat", ...]
}
```

```bash
# Export events only
GET /scenario/export/events

# Response:
{
  "events": {
    "events": [...]
  },
  "total_events": 10,
  "pending_events": 5,
  "executed_events": 4
}
```

#### Import Examples

```bash
# Import complete scenario
POST /scenario/import/full
{
  "scenario": {
    "metadata": {...},
    "environment": {...},
    "events": {...}
  },
  "strict_modalities": false
}

# Response:
{
  "success": true,
  "environment_loaded": true,
  "events_loaded": 10,
  "modalities_loaded": ["weather", "email", ...],
  "modalities_skipped": [],
  "warnings": [],
  "scenario_metadata": {
    "ues_version": "0.1.0",
    "created_at": "2025-01-01T00:00:00Z",
    "author": "Developer"
  }
}
```

```bash
# Import environment with historic event handling
POST /scenario/import/environment
{
  "data": {
    "time_state": {...},
    "modality_states": {...}
  },
  "historic_event_handling": "delete",  # "ignore", "delete", or "apply"
  "strict_modalities": false
}
```

```bash
# Import events (merge with existing)
POST /scenario/import/events
{
  "data": {
    "events": [...]
  },
  "merge": true  # false = replace all events
}
```

**Important Notes:**
- Simulation must be stopped before importing (returns 409 Conflict if running)
- Import clears the undo stack (except event merge)
- Use `strict_modalities: false` for partial compatibility with older scenarios
- Event IDs are regenerated on import to avoid conflicts

---

### 6. Modality-Specific Routes

Each modality has dedicated, type-safe endpoints following a consistent pattern:

#### Standard Pattern

Every modality implements:
- `GET /{modality}/state` - Current state snapshot
- `POST /{modality}/query` - Query with filters (where applicable)
- `POST /{modality}/{action}` - Action-specific endpoints

#### Email (`/email`)

**Core Endpoints:**
- `GET /email/state` - Current email state (all folders, threads, etc.)
- `POST /email/query` - Query emails with filters

**Action Endpoints:**
- `POST /email/send` - Send a new email
- `POST /email/receive` - Simulate receiving an email
- `POST /email/read` - Mark email(s) as read
- `POST /email/unread` - Mark email(s) as unread
- `POST /email/star` - Star/favorite email(s)
- `POST /email/unstar` - Unstar email(s)
- `POST /email/archive` - Archive email(s)
- `POST /email/delete` - Move email(s) to trash
- `POST /email/label` - Add label(s) to email(s)
- `POST /email/unlabel` - Remove label(s) from email(s)
- `POST /email/move` - Move email(s) to different folder

**Example:**
```bash
# Send an email
POST /email/send
{
  "to_addresses": ["user@example.com"],
  "subject": "Meeting Tomorrow",
  "body_text": "Let's meet at 2pm"
}

# Query unread emails
POST /email/query
{
  "folder": "inbox",
  "is_read": false,
  "limit": 10
}
```

#### SMS (`/sms`)

**Core Endpoints:**
- `GET /sms/state` - Current SMS state (all threads, messages)
- `POST /sms/query` - Query messages/threads with filters

**Action Endpoints:**
- `POST /sms/send` - Send a new SMS/RCS message
- `POST /sms/receive` - Simulate receiving a message
- `POST /sms/read` - Mark message(s) as read
- `POST /sms/unread` - Mark message(s) as unread
- `POST /sms/delete` - Delete message(s)
- `POST /sms/react` - Add reaction to a message (RCS)

**Example:**
```bash
# Send an SMS
POST /sms/send
{
  "phone_number": "+1234567890",
  "message_text": "Running 5 minutes late"
}

# Query messages from a contact
POST /sms/query
{
  "phone_number": "+1234567890",
  "limit": 20
}
```

#### Chat (`/chat`)

**Core Endpoints:**
- `GET /chat/state` - Current chat state (all conversations)
- `POST /chat/query` - Query chat history

**Action Endpoints:**
- `POST /chat/send` - Send a chat message (user or assistant)
- `POST /chat/delete` - Delete a message from history
- `POST /chat/clear` - Clear conversation history

**Example:**
```bash
# Send a user message
POST /chat/send
{
  "role": "user",
  "content": "What's the weather like today?"
}

# Send an assistant response
POST /chat/send
{
  "role": "assistant",
  "content": "It's sunny and 72°F"
}
```

#### Calendar (`/calendar`)

**Core Endpoints:**
- `GET /calendar/state` - Current calendar state (all calendars and events)
- `POST /calendar/query` - Query calendar events with filters

**Action Endpoints:**
- `POST /calendar/create` - Create a new calendar event
- `POST /calendar/update` - Update an existing event
- `POST /calendar/delete` - Delete a calendar event

**Example:**
```bash
# Create a calendar event
POST /calendar/create
{
  "title": "Team Meeting",
  "start": "2024-03-15T14:00:00Z",
  "end": "2024-03-15T15:00:00Z",
  "location": "Conference Room A",
  "attendees": [{"email": "team@example.com"}]
}

# Query events for a date range
POST /calendar/query
{
  "start": "2024-03-15T00:00:00Z",
  "end": "2024-03-16T00:00:00Z",
  "status": "confirmed"
}
```

#### Location (`/location`)

**Core Endpoints:**
- `GET /location/state` - Current location with history
- `POST /location/query` - Query location history

**Action Endpoints:**
- `POST /location/update` - Update current location coordinates

**Example:**
```bash
# Update location
POST /location/update
{
  "latitude": 40.7128,
  "longitude": -74.0060,
  "address": "New York, NY",
  "named_location": "Office"
}

# Query location history
POST /location/query
{
  "since": "2024-03-15T00:00:00Z",
  "limit": 10
}
```

#### Weather (`/weather`)

**Core Endpoints:**
- `GET /weather/state` - Current weather state for all locations
- `POST /weather/query` - Query weather data with filters

**Action Endpoints:**
- `POST /weather/update` - Update weather conditions

**Example:**
```bash
# Update weather for a location
POST /weather/update
{
  "latitude": 40.7128,
  "longitude": -74.0060,
  "report": {
    "lat": 40.7128,
    "lon": -74.0060,
    "timezone": "America/New_York",
    "timezone_offset": -14400,
    "current": {
      "dt": 1710518400,
      "temp": 295.15,
      "feels_like": 294.15,
      ...
    }
  }
}

# Query weather with real API
POST /weather/query
{
  "lat": 40.7128,
  "lon": -74.0060,
  "real": true,
  "units": "imperial"
}
```

**See `docs/MODALITY_ROUTES.md` for detailed endpoint specifications and additional examples.**

---

## Design Principles

### Type Safety
All requests and responses use Pydantic models with full type validation. This ensures:
- Automatic validation of incoming data
- Clear error messages for invalid requests
- Type hints for better IDE support
- Self-documenting API schemas

### Event-Sourcing Architecture
All modality changes flow through the event system:
- Actions create `SimulatorEvent` objects
- Events carry `ModalityInput` payloads
- Events execute at specified simulator time
- State changes are deterministic and reproducible

### Consistent Response Format
All action endpoints return a standard structure:
```json
{
  "event_id": "evt_abc123",
  "scheduled_time": "2024-03-15T14:30:00Z",
  "status": "completed",
  "message": "Email sent successfully",
  "modality": "email"
}
```

### Error Handling
API uses standard HTTP status codes:
- `200` - Success
- `201` - Created
- `400` - Bad Request (validation error)
- `404` - Not Found (modality/event/resource)
- `409` - Conflict (invalid state transition)
- `500` - Internal Server Error

All errors return structured JSON:
```json
{
  "detail": "Human-readable error message",
  "error_type": "ValidationError",
  "context": {...}
}
```

---

## Getting Started

### Starting the Server

```bash
# Install dependencies
uv sync

# Run the development server
uv run uvicorn main:app --reload

# Server will be available at:
# http://localhost:8000
```

### Example Workflow

1. **Start simulation:**
   ```bash
   POST /simulation/start
   {"auto_advance": false}
   ```

2. **Check current time:**
   ```bash
   GET /simulator/time
   ```

3. **Send an email:**
   ```bash
   POST /email/send
   {
     "to_addresses": ["user@example.com"],
     "subject": "Test Email",
     "body_text": "Hello from the simulator!"
   }
   ```

4. **Query email state:**
   ```bash
   GET /email/state
   ```

5. **Send an SMS:**
   ```bash
   POST /sms/send
   {
     "phone_number": "+1234567890",
     "message_text": "Quick test message"
   }
   ```

6. **Advance time:**
   ```bash
   POST /simulator/time/advance
   {"seconds": 3600}
   ```

### Using the Interactive Docs

The Swagger UI at `http://localhost:8000/docs` provides:
- Complete endpoint listing
- Request/response schemas
- Interactive testing (try it out!)
- Model definitions
- Authentication (when implemented)

This is the recommended way to explore and test the API during development.

---

## Additional Resources

- **Architecture**: See `docs/SIMULATION_ENGINE.md` for orchestration design
- **Modality Models**: See `docs/MODALITY_MODELS.md` for data structure details
- **Time Management**: See `docs/SIMULATOR_TIME.md` for time control details
- **Event System**: See `docs/SIMULATION_EVENT.md` for event lifecycle
- **Testing**: See `docs/UNIT_TESTS.md` for testing patterns
