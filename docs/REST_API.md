# UES REST API Specification

## Overview

The User Environment Simulator (UES) exposes a comprehensive RESTful API for controlling simulations, managing events, and querying environment state. The API is designed for simplicity, completeness, and real-time interaction with AI personal assistants.

All endpoints return JSON responses with appropriate HTTP status codes. The API supports:
- **Full simulation control**: Start, stop, pause, resume operations
- **Flexible time management**: Manual, event-driven, and auto-advance modes
- **Complete event management**: Create, query, cancel scheduled events
- **Rich state access**: Query environment state with filtering and search
- **Agent convenience**: High-level endpoints for common AI agent actions

## API Categories

The UES REST API is organized into four main categories:

1. **Time Control** (`/simulator/time`) - Virtual time management and control
2. **Environment State** (`/environment`) - Current state queries and validation
3. **Event Management** (`/events`) - Event scheduling and lifecycle
4. **Simulation Control** (`/simulation`) - Simulation lifecycle and status

Additionally, modality-specific convenience endpoints are provided under `/modalities/{modality}`.

---

## 1. Time Control (`/simulator/time`)

Virtual time management independent from wall-clock time.

### `GET /simulator/time`

Get current simulator time state.

**Response:**
```json
{
  "current_time": "2024-03-15T14:30:00Z",
  "time_scale": 1.0,
  "is_paused": false,
  "mode": "real_time",
  "auto_advance": true,
  "last_wall_time_update": "2024-03-15T14:30:00Z"
}
```

**Response Fields:**
- `current_time` (datetime): Current simulator time
- `time_scale` (float): Time multiplier (1.0 = real-time, 10.0 = 10x speed)
- `is_paused` (bool): Whether time advancement is frozen
- `mode` (string): Current time mode - "manual", "real_time", "fast_forward", "slow_motion", "event_driven"
- `auto_advance` (bool): Whether time advances automatically
- `last_wall_time_update` (datetime): Last wall-clock time reference

---

### `POST /simulator/time/advance`

Manually advance time by a specified duration.

**Request:**
```json
{
  "duration": "1h30m"
}
```
OR
```json
{
  "duration_seconds": 5400
}
```

**Request Fields:**
- `duration` (string): Human-readable duration string. Format: combine number+unit pairs where units are `d` (days), `h` (hours), `m` (minutes), `s` (seconds). Examples: "1h30m", "45s", "2d", "1d12h30m"
- `duration_seconds` (int): Duration in seconds (alternative to `duration` string)

**Response:**
```json
{
  "current_time": "2024-03-15T16:00:00Z",
  "events_executed": 3,
  "execution_summary": [
    {
      "event_id": "evt_123",
      "scheduled_time": "2024-03-15T15:00:00Z",
      "modality": "email",
      "status": "executed",
      "priority": 50,
      "created_at": "2024-03-15T14:00:00Z"
    }
  ]
}
```

**Notes:**
- Executes all events that became due during advancement
- Only available when `auto_advance` is false (manual mode)

---

### `POST /simulator/time/set`

Jump to a specific simulator time.

**Request:**
```json
{
  "time": "2024-03-15T18:00:00Z",
  "execute_skipped": false
}
```

**Request Fields:**
- `time` (datetime): Target simulator time
- `execute_skipped` (bool, optional): Whether to execute events between current and target time (default: false)

**Response:**
```json
{
  "current_time": "2024-03-15T18:00:00Z",
  "events_skipped": 5,
  "events_executed": 0,
  "execution_summary": [
    {
      "event_id": "evt_123",
      "scheduled_time": "2024-03-15T17:00:00Z",
      "modality": "sms",
      "status": "skipped",
      "priority": 50,
      "created_at": "2024-03-15T14:00:00Z"
    }
  ]
}
```

**Notes:**
- Cannot jump backwards in time (returns error)
- If `execute_skipped` is true, executes all events in chronological order
- If false, marks skipped events with status "skipped"

---

### `POST /simulator/time/skip-to-next`

Jump directly to the next scheduled event time (event-driven mode).

**Request:** (empty body)

**Response:**
```json
{
  "current_time": "2024-03-15T15:30:00Z",
  "events_executed": 2,
  "execution_summary": [
    {
      "event_id": "evt_124",
      "scheduled_time": "2024-03-15T15:30:00Z",
      "modality": "chat",
      "status": "executed",
      "priority": 50,
      "created_at": "2024-03-15T14:00:00Z"
    }
  ],
  "next_event_time": "2024-03-15T16:00:00Z"
}
```

**Notes:**
- Executes all events scheduled at the target time
- If no pending events, returns error
- Useful for sparse event sequences

---

### `POST /simulator/time/pause`

Freeze time advancement (pauses auto-advance).

**Request:** (empty body)

**Response:**
```json
{
  "status": "paused",
  "current_time": "2024-03-15T14:30:00Z"
}
```

**Notes:**
- State queries still work during pause
- No new events execute until resumed
- Main simulation loop remains running but idle

---

### `POST /simulator/time/resume`

Unfreeze time advancement (resumes auto-advance).

**Request:** (empty body)

**Response:**
```json
{
  "status": "running",
  "current_time": "2024-03-15T14:30:00Z",
  "mode": "real_time"
}
```

**Notes:**
- Resets wall-time anchor to prevent time jump
- Resumes event execution
- Only affects auto-advance mode

---

### `POST /simulator/time/set-scale`

Change time multiplier (speed up or slow down simulation).

**Request:**
```json
{
  "scale": 10.0
}
```

**Request Fields:**
- `scale` (float): Time multiplier
  - `1.0` = real-time
  - `> 1.0` = fast-forward (e.g., `10.0` = 10x speed)
  - `< 1.0` = slow-motion (e.g., `0.5` = half speed)
  - Must be > 0

**Response:**
```json
{
  "time_scale": 10.0,
  "mode": "fast_forward",
  "current_time": "2024-03-15T14:30:00Z"
}
```

---

## 2. Environment State (`/environment`)

Access to current modality states and environment snapshots.

### `GET /environment/state`

Get complete environment snapshot (time + all modality states).

**Response:**
```json
{
  "simulator_time": "2024-03-15T14:30:00Z",
  "time_state": {
    "current_time": "2024-03-15T14:30:00Z",
    "is_paused": false,
    "time_scale": 1.0
  },
  "modalities": {
    "email": {
      "modality_type": "email",
      "inbox_count": 42,
      "unread_count": 5,
      "last_updated": "2024-03-15T14:28:00Z"
    },
    "location": {
      "modality_type": "location",
      "latitude": 37.7749,
      "longitude": -122.4194,
      "last_updated": "2024-03-15T14:30:00Z"
    }
  }
}
```

**Notes:**
- Returns complete state for all initialized modalities
- Large responses for complex environments
- Use modality-specific endpoints for filtered access

---

### `GET /environment/modalities`

List all available (initialized) modalities.

**Response:**
```json
{
  "modalities": ["email", "location", "weather", "chat", "calendar", "sms"]
}
```

---

### `GET /environment/modalities/{modality}`

Get current state for a specific modality.

**Path Parameters:**
- `modality` (string): Modality name (e.g., "email", "location", "weather")

**Response:** (varies by modality)

**Example (Location):**
```json
{
  "modality_type": "location",
  "current_location": {
    "latitude": 37.7749,
    "longitude": -122.4194,
    "altitude": 10.0,
    "accuracy": 5.0,
    "address": "123 Main St, San Francisco, CA",
    "named_location": "Home"
  },
  "location_history": [],
  "last_updated": "2024-03-15T14:30:00Z",
  "update_count": 5
}
```

**Example (Email):**
```json
{
  "modality_type": "email",
  "folders": {
    "inbox": ["msg_001", "msg_002"],
    "sent": ["msg_003"]
  },
  "threads": {
    "thread_001": {
      "thread_id": "thread_001",
      "subject": "Meeting Tomorrow",
      "message_count": 3,
      "unread_count": 1
    }
  },
  "unread_counts": {
    "inbox": 5,
    "sent": 0
  },
  "total_count": 42
}
```

**HTTP Status Codes:**
- `200 OK`: Success
- `404 Not Found`: Modality not initialized

---

### `POST /environment/modalities/{modality}/query`

Query modality state with filters and search criteria.

**Path Parameters:**
- `modality` (string): Modality name

**Request:** (varies by modality, see modality-specific sections below)

**Response:** (varies by modality)

**Common Query Parameters:**
- `limit` (int): Maximum results to return
- `offset` (int): Pagination offset
- `sort_by` (string): Sort field
- `sort_order` (string): "asc" or "desc"

**HTTP Status Codes:**
- `200 OK`: Success
- `400 Bad Request`: Invalid query parameters
- `404 Not Found`: Modality not found

---

### `POST /environment/validate`

Validate environment consistency and integrity.

**Request:** (empty body)

**Response (valid):**
```json
{
  "valid": true,
  "checked_at": "2024-03-15T14:30:00Z"
}
```

**Response (invalid):**
```json
{
  "valid": false,
  "errors": [
    "Email state: message_id 'msg_999' in folder 'inbox' not found in emails dict",
    "Calendar state: event end time before start time for event 'evt_123'"
  ],
  "checked_at": "2024-03-15T14:30:00Z"
}
```

---

## 3. Event Management (`/events`)

Create, query, and manage simulation events.

### `GET /events`

List events with optional filters. Events are summarized, use the `event_id` field to query the 
`GET /events/{event_id}` for the specific event.

**Query Parameters:**
- `status` (string): Filter by status - "pending", "executed", "failed", "skipped"
- `start_time` (datetime): Minimum scheduled time (inclusive)
- `end_time` (datetime): Maximum scheduled time (inclusive)
- `modality` (string): Filter by modality type
- `limit` (int): Maximum results to return
- `offset` (int): Pagination offset

**Response:**
```json
{
  "events": [
    {
      "event_id": "evt_001",
      "scheduled_time": "2024-03-15T15:00:00Z",
      "modality": "email",
      "status": "pending",
      "priority": 50,
      "created_at": "2024-03-15T14:00:00Z"
    }
  ],
  "total": 42,
  "pending": 12,
  "executed": 28,
  "failed": 2,
  "skipped": 0
}
```

---

### `POST /events`

Create a new scheduled event.

**Request:**
```json
{
  "scheduled_time": "2024-03-15T15:00:00Z",
  "modality": "email",
  "data": {
    "operation": "receive",
    "from_address": "boss@company.com",
    "to_addresses": ["user@example.com"],
    "subject": "Urgent: Project Update",
    "body_text": "Please review the attached document.",
    "priority": "high"
  },
  "priority": 75,
  "metadata": {
    "source": "test_scenario",
    "category": "work"
  }
}
```

**Request Fields:**
- `scheduled_time` (datetime, required): When event should execute
- `modality` (string, required): Modality type ("email", "sms", "location", etc.)
- `data` (object, required): ModalityInput payload (varies by modality)
- `priority` (int, optional): Execution priority 0-100, higher = first (default: 50)
- `metadata` (object, optional): Custom metadata for tracking
- `agent_id` (string, optional): ID of agent that created event

**Response:**
```json
{
  "event_id": "evt_001",
  "scheduled_time": "2024-03-15T15:00:00Z",
  "modality": "email",
  "status": "pending",
  "created_at": "2024-03-15T14:30:00Z"
}
```

**HTTP Status Codes:**
- `200 OK`: Event created successfully
- `400 Bad Request`: Invalid event data or validation error
- `409 Conflict`: Scheduled time in the past

---

### `POST /events/immediate`

Submit event for immediate execution at current simulator time (convenience endpoint).

**Request:**
```json
{
  "modality": "chat",
  "data": {
    "role": "assistant",
    "content": "Based on the current weather data, it's sunny and 72°F."
  }
}
```

**Request Fields:**
- `modality` (string, required): Modality type
- `data` (object, required): ModalityInput payload

**Response:**
```json
{
  "event_id": "evt_002",
  "scheduled_time": "2024-03-15T14:30:00Z",
  "modality": "chat",
  "status": "pending",
  "priority": 100,
  "created_at": "2024-03-15T14:30:00Z"
}
```

**Notes:**
- Automatically sets `scheduled_time` to current simulator time
- Sets high priority (100) to execute before other same-time events
- Ideal for AI agent responses that need immediate execution
- Returns created event with assigned ID

---

### `GET /events/{event_id}`

Get details for a specific event.

**Path Parameters:**
- `event_id` (string): Event identifier

**Response:**
```json
{
  "event_id": "evt_001",
  "scheduled_time": "2024-03-15T15:00:00Z",
  "executed_at": "2024-03-15T15:00:01Z",
  "modality": "email",
  "status": "executed",
  "priority": 50,
  "data": {
    "operation": "receive",
    "from_address": "boss@company.com",
    "subject": "Urgent: Project Update"
  },
  "metadata": {
    "source": "test_scenario"
  },
  "created_at": "2024-03-15T14:00:00Z",
  "error_message": null
}
```

**HTTP Status Codes:**
- `200 OK`: Success
- `404 Not Found`: Event not found

---

### `DELETE /events/{event_id}`

Cancel a pending event.

**Path Parameters:**
- `event_id` (string): Event identifier

**Response:**
```json
{
  "cancelled": true,
  "event_id": "evt_001"
}
```

**HTTP Status Codes:**
- `200 OK`: Event cancelled
- `400 Bad Request`: Event already executed/failed (cannot cancel)
- `404 Not Found`: Event not found

---

### `GET /events/next`

Peek at the next pending event without executing it.

**Response:**
```json
{
  "event_id": "evt_003",
  "scheduled_time": "2024-03-15T15:30:00Z",
  "modality": "sms",
  "status": "pending",
  "priority": 50,
  "created_at": "2024-03-15T14:00:00Z"
}
```

**Response (no pending events):**
```json
{
  "message": "No pending events"
}
```

---

### `GET /events/summary`

Get event execution statistics.

**Response:**
```json
{
  "total": 100,
  "pending": 5,
  "executed": 90,
  "failed": 3,
  "skipped": 2,
  "by_modality": {
    "email": 45,
    "sms": 30,
    "location": 10,
    "chat": 15
  },
  "next_event_time": "2024-03-15T15:30:00Z"
}
```

---

## 4. Simulation Control (`/simulation`)

Simulation lifecycle management.

### `POST /simulation/start`

Start the simulation.

**Request:**
```json
{
  "auto_advance": true,
  "time_scale": 1.0
}
```

**Request Fields:**
- `auto_advance` (bool, optional): Enable automatic time advancement (default: false)
- `time_scale` (float, optional): Time multiplier for auto-advance (default: 1.0)

**Response:**
```json
{
  "simulation_id": "sim_001",
  "status": "running",
  "current_time": "2024-03-15T08:00:00Z",
  "auto_advance": true,
  "time_scale": 1.0
}
```

**HTTP Status Codes:**
- `200 OK`: Simulation started
- `409 Conflict`: Simulation already running

---

### `POST /simulation/stop`

Stop the simulation gracefully.

**Request:** (empty body)

**Response:**
```json
{
  "status": "stopped",
  "events_executed": 42,
  "execution_summary": [
    {
      "event_id": "evt_125",
      "scheduled_time": "2024-03-15T17:45:00Z",
      "modality": "email",
      "status": "executed",
      "priority": 50,
      "created_at": "2024-03-15T14:00:00Z"
    }
  ],
  "final_time": "2024-03-15T18:00:00Z",
  "duration": "10h"
}
```

**Notes:**
- Finishes executing current events before stopping
- Persists final state (if configured)
- Returns execution summary

---

### `GET /simulation/status`

Get current simulation status and metrics.

**Response:**
```json
{
  "is_running": true,
  "current_time": "2024-03-15T14:30:00Z",
  "mode": "real_time",
  "is_paused": false,
  "time_scale": 1.0,
  "pending_events": 12,
  "executed_events": 28,
  "failed_events": 2,
  "next_event_time": "2024-03-15T15:00:00Z",
  "uptime": "6h30m"
}
```

---

### `POST /simulation/reset`

Reset simulation to initial state.

**Request:** (empty body)

**Response:**
```json
{
  "status": "reset",
  "initial_time": "2024-03-15T08:00:00Z",
  "cleared_events": 100,
  "reset_modalities": ["email", "location", "weather"]
}
```

**Notes:**
- Clears all executed events
- Resets environment to initial state
- Resets simulator time to initial time
- Keeps event queue (pending events remain)

---

## 5. Modality-Specific Endpoints

### Queries

Query modality states with filters. Each modality has its own set of filters. The general format is

#### `POST /environment/modalities/{modality}/query`

Query {modality} state with filters

**Request:**
```json
{
    "filter_1": filter_1_value,
    "filter_2": filter_2_value,
    ...
}
```

**Response:**
```json
{
  "modality_type": "modality_name",
  "query": query_params,
  "results": results
}
```

#### `POST /environment/modalities/email/query`

Query email state with filters.

**Request:**
```json
{
  "folder": "inbox",
  "label": "Work",
  "is_read": false,
  "is_starred": false,
  "has_attachments": true,
  "from_address": "boss@company.com",
  "to_address": "user@company.com",
  "subject_contains": "urgent",
  "body_contains": "ASAP",
  "date_from": "2024-03-15T00:00:00Z",
  "date_to": "2024-03-15T23:59:59Z",
  "thread_id": "thead-123",
  "limit": 10,
  "offset": 0,
  "sort_by": "date",
  "sort_order": "desc"
}
```

**Query Parameters:**
- `folder` (string): Filter by folder ("inbox", "sent", "drafts", "trash", "spam", "archive")
- `label` (string): Filter by label
- `is_read` (bool): Filter by read status
- `is_starred` (bool): Filter by starred status
- `has_attachments` (bool): Filter by attachment presence
- `from_address` (string): Filter by sender
- `to_address` (string): Filter by recipient
- `subject_contains` (string): Search subject
- `body_contains` (string): Search body
- `date_from` (datetime): Start of date range
- `date_to` (datetime): End of date range
- `thread_id` (string): Get specific thread
- `limit` (int): Max results
- `offset` (int): Pagination offset
- `sort_by` (string): "date", "from", "subject"
- `sort_order` (string): "asc" or "desc"

**Response:**
```json
{
  "modality_type": "email",
  "query": {
    "folder": "inbox",
    "is_read": false,
    "limit": 10,
    "offset": 0,
    "sort_by": "date",
    "sort_order": "desc"
  },
  "results": {
    "emails": [
      {
        "message_id": "msg_001",
        "from_address": "boss@company.com",
        "to_addresses": ["user@example.com"],
        "cc_addresses": [],
        "bcc_addresses": [],
        "subject": "Urgent: Project Update",
        "body_text": "Please review the attached document ASAP.",
        "body_html": "<p>Please review the attached document ASAP.</p>",
        "attachments": [
          {
            "filename": "report.pdf",
            "size": 245760,
            "mime_type": "application/pdf"
          }
        ],
        "thread_id": "thread_001",
        "is_read": false,
        "is_starred": false,
        "received_at": "2024-03-15T14:00:00Z",
        "labels": ["Work", "Important"]
      }
    ],
    "total_count": 42,
    "returned_count": 10,
    "query": {
      "folder": "inbox",
      "is_read": false,
      "limit": 10,
      "offset": 0,
      "sort_by": "date",
      "sort_order": "desc"
    }
  }
}
```

**Response Fields:**
- `modality_type` (string): Always "email"
- `query` (object): Echo of the query parameters sent
- `results` (object): Query results containing:
  - `emails` (array): Array of email objects matching the query
  - `total_count` (int): Total number of emails matching query (before pagination)
  - `returned_count` (int): Number of emails in this response (after pagination)
  - `query` (object): Echo of query parameters (also included in results for consistency)

---

#### `POST /environment/modalities/calendar/query`

Query calendar events with filters.

**Request:**
```json
{
  "calendar_id": "work",
  "start_date": "2024-03-15T00:00:00Z",
  "end_date": "2024-03-31T23:59:59Z",
  "expand_recurring": true,
  "status": "confirmed",
  "has_attendees": true,
  "search_text": "meeting",
  "limit": 50
}
```

**Query Parameters:**
- `calendar_id` (string or list): Filter by calendar(s)
- `start_date` (datetime): Start of date range
- `end_date` (datetime): End of date range
- `expand_recurring` (bool): Generate individual occurrences for recurring events (default: false)
- `status` (string): "confirmed", "tentative", "cancelled"
- `has_attendees` (bool): Filter by attendee presence
- `recurring` (bool): Filter by recurring vs one-time
- `search_text` (string): Search title/description/location
- `color` (string): Filter by event color
- `limit` (int): Max results
- `offset` (int): Pagination offset
- `sort_by` (string): Sort field - "start", "end", "status" (default: "start")
- `sort_order` (string): "asc" or "desc" (default: "asc")

**Response:**
```json
{
  "modality_type": "calendar",
  "query": {
    "calendar_id": "work",
    "start_date": "2024-03-15T00:00:00Z",
    "end_date": "2024-03-31T23:59:59Z",
    "expand_recurring": true,
    "status": "confirmed",
    "limit": 15,
    "offset": 0,
    "sort_by": "start",
    "sort_order": "asc"
  },
  "results": {
    "events": [
      {
        "event_id": "evt_cal_001",
        "calendar_id": "work",
        "title": "Team Standup",
        "description": "Daily sync meeting",
        "location": "Conference Room A",
        "start": "2024-03-15T09:00:00Z",
        "end": "2024-03-15T09:30:00Z",
        "all_day": false,
        "status": "confirmed",
        "attendees": [
          {
            "email": "alice@company.com",
            "name": "Alice Smith",
            "response_status": "accepted",
            "is_organizer": true
          },
          {
            "email": "bob@company.com",
            "name": "Bob Jones",
            "response_status": "accepted",
            "is_organizer": false
          }
        ],
        "recurrence_rule": "FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR",
        "color": "blue",
        "reminders": [
          {
            "method": "popup",
            "minutes_before": 15
          }
        ],
        "visibility": "default"
      }
    ],
    "count": 15,
    "total_count": 42
  }
}
```

**Response Fields:**
- `modality_type` (string): Always "calendar"
- `query` (object): Echo of the query parameters sent
- `results` (object): Query results containing:
  - `events` (array): Array of calendar event objects matching the query
  - `count` (int): Number of events returned (after pagination)
  - `total_count` (int): Total number of events matching query (before pagination)

---

#### `POST /environment/modalities/sms/query`

Query SMS conversations and messages.

**Request:**
```json
{
  "thread_id": "thread_123",
  "phone_number": "+15551234567",
  "direction": "incoming",
  "message_type": "rcs",
  "is_read": false,
  "has_attachments": true,
  "search_text": "lunch",
  "since": "2024-03-15T00:00:00Z",
  "until": "2024-03-15T23:59:59Z",
  "limit": 20
}
```

**Query Parameters (all optional):**
- `thread_id` (string): Filter messages by conversation thread
- `phone_number` (string): Filter messages involving this phone number
- `direction` (string): Filter by "incoming" or "outgoing"
- `message_type` (string): Filter by "sms" or "rcs"
- `is_read` (bool): Filter by read status
- `has_attachments` (bool): Filter messages with attachments
- `search_text` (string): Search message body text (case-insensitive)
- `since` (datetime): Filter messages sent after this time
- `until` (datetime): Filter messages sent before this time
- `limit` (int): Maximum number of messages to return
- `offset` (int): Pagination offset
- `sort_by` (string): Sort field - "sent_at", "from_number", "direction" (default: "sent_at")
- `sort_order` (string): "asc" or "desc" (default: "asc")

**Response:**
```json
{
  "modality_type": "sms",
  "query": {
    "phone_number": "+15551234567",
    "is_read": false,
    "limit": 20,
    "offset": 0,
    "sort_by": "sent_at",
    "sort_order": "asc"
  },
  "results": {
    "messages": [
      {
        "message_id": "msg_sms_001",
        "thread_id": "thread_123",
        "from_number": "+15551234567",
        "to_numbers": ["+15559876543"],
        "body": "Want to grab lunch?",
        "attachments": [],
        "reactions": [],
        "message_type": "sms",
        "direction": "incoming",
        "sent_at": "2024-03-15T14:00:00Z",
        "is_read": false,
        "delivery_status": "delivered",
        "is_deleted": false,
        "is_spam": false
      }
    ],
    "count": 1,
    "total_count": 25,
    "query_params": {
      "phone_number": "+15551234567",
      "is_read": false,
      "limit": 20
    }
  }
}
```

**Response Fields:**
- `modality_type` (string): Always "sms"
- `query` (object): Echo of the query parameters sent
- `results` (object): Query results containing:
  - `messages` (array): Array of SMS/RCS message objects matching the query
  - `count` (int): Number of messages returned (after pagination)
  - `total_count` (int): Total number of messages matching query (before pagination)
  - `query_params` (object): Echo of query parameters (also included in results for consistency)

---

#### `POST /environment/modalities/weather/query`

Query weather data for a location.

**Request:**
```json
{
  "lat": 37.7749,
  "lon": -122.4194,
  "exclude": "minutely,hourly",
  "units": "imperial",
  "from": 1710504000,
  "to": 1710590400,
  "real": false
}
```

**Query Parameters (all optional except lat/lon):**
- `lat` (float, **required**): Latitude (-90 to 90)
- `lon` (float, **required**): Longitude (-180 to 180)
- `exclude` (string): Comma-delimited list of parts to exclude: "current", "minutely", "hourly", "daily", "alerts"
- `units` (string): "standard" (Kelvin), "metric" (Celsius), or "imperial" (Fahrenheit)
- `from` (int): Unix timestamp - return all reports since this time
- `to` (int): Unix timestamp - return reports until this time (requires `from`)
- `real` (bool): Query OpenWeather API for real data (requires `OPENWEATHER_API_KEY` env var)
- `limit` (int): Maximum number of reports to return
- `offset` (int): Pagination offset
- `to` (int): Unix timestamp - return reports until this time (requires `from`)
- `real` (bool): Query OpenWeather API for real data (requires `OPENWEATHER_API_KEY` env var)

**Response:**
```json
{
  "modality_type": "weather",
  "query": {
    "lat": 37.7749,
    "lon": -122.4194,
    "exclude": "minutely,hourly",
    "units": "imperial"
  },
  "results": {
    "reports": [
      {
        "lat": 37.7749,
        "lon": -122.4194,
        "timezone": "America/Los_Angeles",
        "timezone_offset": -28800,
        "current": {
          "dt": 1710504000,
          "sunrise": 1710508800,
          "sunset": 1710550800,
          "temp": 72.5,
          "feels_like": 70.3,
          "pressure": 1013,
          "humidity": 65,
          "dew_point": 60.8,
          "uvi": 5.2,
          "clouds": 20,
          "visibility": 10000,
          "wind_speed": 8.5,
          "wind_deg": 270,
          "weather": [
            {
              "id": 801,
              "main": "Clouds",
              "description": "few clouds",
              "icon": "02d"
            }
          ]
        },
        "daily": [
          {
            "dt": 1710518400,
            "sunrise": 1710508800,
            "sunset": 1710550800,
            "temp": {
              "day": 72.5,
              "min": 58.3,
              "max": 75.2,
              "night": 62.1,
              "eve": 68.9,
              "morn": 60.4
            },
            "feels_like": {
              "day": 70.3,
              "night": 60.1,
              "eve": 67.2,
              "morn": 58.7
            },
            "pressure": 1013,
            "humidity": 65,
            "dew_point": 60.8,
            "wind_speed": 8.5,
            "wind_deg": 270,
            "weather": [
              {
                "id": 801,
                "main": "Clouds",
                "description": "few clouds",
                "icon": "02d"
              }
            ],
            "clouds": 20,
            "pop": 0.1,
            "uvi": 5.2
          }
        ]
      }
    ],
    "count": 1,
    "total_count": 1
  }
}
```

**Response Fields:**
- `modality_type` (string): Always "weather"
- `query` (object): Echo of the query parameters sent
- `results` (object): Query results containing:
  - `reports` (array): Array of weather report objects for the specified location(s)
  - `count` (int): Number of weather reports returned (after pagination)
  - `total_count` (int): Total number of reports matching query (before pagination)
  - `error` (string, optional): Error message if no data available for location

**Notes:**
- If `real=true`, queries OpenWeather API and updates state with result
- See [OpenWeather One Call API](https://openweathermap.org/api/one-call-3) for complete format

---

#### `POST /environment/modalities/location/query`

Query location history.

**Request:**
```json
{
  "since": "2024-03-15T00:00:00Z",
  "until": "2024-03-15T23:59:59Z",
  "named_location": "Office",
  "limit": 10
}
```

**Query Parameters:**
- `since` (datetime): Start of time range
- `until` (datetime): End of time range
- `named_location` (string): Filter by location name
- `limit` (int): Max results
- `offset` (int): Pagination offset
- `include_current` (bool): Include current location in results (default: true)
- `sort_by` (string): Sort field - "timestamp", "latitude", "longitude" (default: "timestamp")
- `sort_order` (string): "asc" or "desc" (default: "desc")

**Response:**
```json
{
  "modality_type": "location",
  "query": {
    "since": "2024-03-15T00:00:00Z",
    "until": "2024-03-15T23:59:59Z",
    "named_location": "Office",
    "limit": 10
  },
  "results": {
    "locations": [
      {
        "timestamp": "2024-03-15T14:30:00Z",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "altitude": 10.0,
        "accuracy": 5.0,
        "speed": 0.0,
        "bearing": 270.0,
        "address": "123 Main St, San Francisco, CA",
        "named_location": "Office",
        "is_current": true
      },
      {
        "timestamp": "2024-03-15T09:00:00Z",
        "latitude": 37.7849,
        "longitude": -122.4094,
        "altitude": 15.0,
        "accuracy": 8.0,
        "address": "456 Oak Ave, San Francisco, CA",
        "named_location": "Office",
        "is_current": false
      }
    ],
    "count": 2,
    "total_count": 15
  }
}
```

**Response Fields:**
- `modality_type` (string): Always "location"
- `query` (object): Echo of the query parameters sent
- `results` (object): Query results containing:
  - `locations` (array): Array of location objects matching the query
  - `count` (int): Number of locations returned (after pagination)
  - `total_count` (int): Total number of locations matching query (before pagination)

---

#### `POST /environment/modalities/time/query`

Query time preference history.

**Request:**
```json
{
  "since": "2024-03-01T00:00:00Z",
  "until": "2024-03-31T23:59:59Z",
  "timezone": "Europe/London",
  "limit": 10
}
```

**Query Parameters:**
- `since` (datetime): Start of time range
- `until` (datetime): End of time range
- `timezone` (string): Filter by specific timezone
- `format_preference` (string): Filter by format preference ("12h" or "24h")
- `limit` (int): Max results
- `offset` (int): Pagination offset
- `include_current` (bool): Include current settings in results (default: true)
- `sort_by` (string): Sort field - "timestamp", "timezone", "format_preference" (default: "timestamp")
- `sort_order` (string): "asc" or "desc" (default: "desc")

**Response:**
```json
{
  "modality_type": "time",
  "query": {
    "since": "2024-03-01T00:00:00Z",
    "until": "2024-03-31T23:59:59Z",
    "timezone": "Europe/London",
    "limit": 10
  },
  "results": {
    "settings": [
      {
        "timestamp": "2024-03-15T14:30:00Z",
        "timezone": "Europe/London",
        "format_preference": "24h",
        "date_format": "DD/MM/YYYY",
        "locale": "en_GB",
        "week_start": "monday",
        "is_current": true
      },
      {
        "timestamp": "2024-03-10T08:00:00Z",
        "timezone": "Europe/London",
        "format_preference": "12h",
        "date_format": "DD/MM/YYYY",
        "locale": "en_GB",
        "week_start": "monday",
        "is_current": false
      }
    ],
    "count": 2,
    "total_count": 8
  }
}
```

**Response Fields:**
- `modality_type` (string): Always "time"
- `query` (object): Echo of the query parameters sent
- `results` (object): Query results containing:
  - `settings` (array): Array of time preference settings matching the query
  - `count` (int): Number of settings entries returned (after pagination)
  - `total_count` (int): Total number of settings matching query (before pagination)

---

#### `POST /environment/modalities/chat/query`

Query conversation history.

**Request:**
```json
{
  "conversation_id": "default",
  "role": "user",
  "since": "2024-03-15T00:00:00Z",
  "search_content": "weather",
  "limit": 10
}
```

**Query Parameters:**
- `conversation_id` (string): Filter by conversation
- `role` (string): Filter by role ("user", "assistant", "system")
- `since` (datetime): Messages after this time
- `until` (datetime): Messages before this time
- `search` (string): Search message content
- `limit` (int): Max results
- `offset` (int): Pagination offset
- `sort_by` (string): Sort field - "timestamp", "role", "conversation_id" (default: "timestamp")
- `sort_order` (string): "asc" or "desc" (default: "asc")

**Response:**
```json
{
  "modality_type": "chat",
  "query": {
    "conversation_id": "default",
    "role": "user",
    "since": "2024-03-15T00:00:00Z",
    "search": "weather",
    "limit": 10
  },
  "results": {
    "messages": [
      {
        "message_id": "msg_chat_001",
        "conversation_id": "default",
        "role": "user",
        "content": "What's the weather like today?",
        "timestamp": "2024-03-15T14:00:00Z",
        "metadata": {}
      },
      {
        "message_id": "msg_chat_002",
        "conversation_id": "default",
        "role": "assistant",
        "content": "It's sunny and 72°F in San Francisco.",
        "timestamp": "2024-03-15T14:00:05Z",
        "metadata": {}
      }
    ],
    "count": 2,
    "total_count": 42
  }
}
```

**Response Fields:**
- `modality_type` (string): Always "chat"
- `query` (object): Echo of the query parameters sent
- `results` (object): Query results containing:
  - `messages` (array): Array of chat message objects matching the query
  - `count` (int): Number of messages returned (after pagination)
  - `total_count` (int): Total number of messages matching query (before pagination)

---

### `POST /modalities/{modality}/submit`

**Highest-level convenience endpoint** for modality-specific actions (agent-friendly).

**Path Parameters:**
- `modality` (string): Modality name

**Request:** (varies by modality, action-specific fields only)

**Example (Chat):**
```json
{
  "role": "assistant",
  "content": "Hello! How can I help you today?"
}
```

**Example (Email - Send):**
```json
{
  "operation": "send",
  "to_addresses": ["colleague@company.com"],
  "subject": "Quick Question",
  "body_text": "Do you have a moment to discuss the project?"
}
```

**Response:**
```json
{
  "event": {
    "event_id": "evt_003",
    "scheduled_time": "2024-03-15T14:30:00Z",
    "status": "pending"
  },
  "state": {
    "modality_type": "chat",
    "message_count": 15,
    "last_message_at": "2024-03-15T14:30:00Z"
  }
}
```

**Notes:**
- Most ergonomic for AI agents - just provide action-specific fields
- Internally creates appropriate ModalityInput and submits as immediate event
- Returns both created event and updated modality state
- Maintains architectural consistency via event pipeline

---

## 6. Error Handling

All error responses follow a consistent format:

### Error Response Format

```json
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

### Common Error Codes

- `VALIDATION_ERROR` (400): Invalid request data or parameters
- `NOT_FOUND` (404): Resource not found (event, modality, etc.)
- `CONFLICT` (409): Operation conflicts with current state (e.g., simulation already running)
- `INTERNAL_ERROR` (500): Server-side error during processing
- `TIME_ERROR` (400): Invalid time operation (e.g., backwards time travel)
- `EVENT_ERROR` (400): Event execution failed

### HTTP Status Codes

- `200 OK`: Successful request (including resource creation)
- `400 Bad Request`: Invalid request parameters or validation error
- `404 Not Found`: Resource not found
- `409 Conflict`: State conflict (e.g., already running, scheduled time in past)
- `500 Internal Server Error`: Server-side error

---

## 7. Agent Action Patterns

### Pattern 1: Immediate Response (Chat)

AI agent responds to user message immediately:

```
1. User message arrives via scheduled event
2. Agent queries current state: GET /environment/modalities/chat
3. Agent generates response
4. Agent submits response: POST /modalities/chat/submit
   {
     "role": "assistant",
     "content": "Based on your calendar, you're free at 3pm."
   }
```

### Pattern 2: Proactive Action (Email)

AI agent sends email based on conditions:

```
1. Agent monitors environment state periodically
2. Agent decides to send email
3. Agent submits via convenience endpoint: POST /modalities/email/submit
   {
     "operation": "send",
     "to_addresses": ["user@example.com"],
     "subject": "Reminder: Meeting in 15 minutes",
     "body_text": "Your meeting with Alice starts at 2:00pm."
   }
```

### Pattern 3: Scheduled Future Action

AI agent schedules event for future execution:

```
1. Agent creates scheduled event: POST /events
   {
     "scheduled_time": "2024-03-15T18:00:00Z",
     "modality": "sms",
     "data": {
       "action": "send_message",
       "message_data": {
         "to_numbers": ["+15551234567"],
         "body": "Don't forget to pick up milk!"
       }
     }
   }
```

---

## 8. Best Practices

### For Developers

1. **Use convenience endpoints** (`/modalities/{modality}/submit`) for simple agent actions
2. **Use `/events/immediate`** when you need the event ID for tracking
3. **Use `/events` (full scheduling)** for complex scenarios with precise timing
4. **Query state efficiently** - use modality-specific endpoints with filters
5. **Validate before starting** - call `POST /environment/validate` before `POST /simulation/start`
6. **Monitor status** - poll `GET /simulation/status` during long runs
7. **Handle errors gracefully** - check for validation errors in responses

### For AI Agents

1. **Prefer immediate actions** over scheduled events for responses
2. **Use highest-level endpoints** (`/modalities/{modality}/submit`) when possible
3. **Query before acting** - check current state before generating responses
4. **Include context** in metadata fields for debugging
5. **Handle async execution** - events may not execute instantly in auto-advance mode

### For Testing

1. **Use manual mode** for step-by-step control: `auto_advance: false`
2. **Use event-driven mode** for sparse scenarios: `POST /simulator/time/skip-to-next`
3. **Use fast-forward** for long simulations: `time_scale: 100.0`
4. **Save snapshots** periodically: `GET /environment/state`
5. **Monitor failures** - check event execution status regularly

---

## 9. Future Enhancements

Planned API additions (not yet implemented):

### WebSocket Endpoints (Real-time Updates)

- `WS /simulator/stream` - Real-time time and event updates
- `WS /environment/stream` - Real-time state change stream
- `WS /events/stream` - Real-time event execution notifications

### Bulk Operations

- `POST /events/bulk` - Create multiple events in one request
- `DELETE /events/bulk` - Cancel multiple events
- `POST /events/import` - Import event sequence from file

### State Management

- `POST /simulation/checkpoint` - Create state snapshot
- `POST /simulation/rollback` - Restore from checkpoint
- `GET /simulation/checkpoints` - List available checkpoints
- `POST /environment/export` - Export configuration to file
- `POST /environment/import` - Import configuration from file

### Performance & Analytics

- `GET /simulation/metrics` - Detailed performance metrics
- `GET /events/analytics` - Event execution analytics
- `GET /modalities/{modality}/analytics` - Modality-specific analytics

### Multi-Tenancy

- `POST /simulations` - Create new simulation instance
- `GET /simulations` - List all simulation instances
- `DELETE /simulations/{id}` - Delete simulation instance
- Per-simulation authentication tokens

---

## 10. Implementation Notes

### Technology Stack

- **Framework**: FastAPI (async, auto-generated OpenAPI docs)
- **Server**: Uvicorn (ASGI server)
- **Validation**: Pydantic models (automatic request/response validation)
- **Documentation**: Auto-generated via FastAPI's OpenAPI support

### API Versioning

Currently single version (v1 implicit). Future versions will use URL versioning:
- `/v1/simulator/time`
- `/v2/simulator/time`

### Rate Limiting

Not implemented in MVP. Future considerations:
- Per-client rate limiting
- Per-simulation resource limits
- Throttling for expensive operations (e.g., state snapshots)

### Authentication

Not implemented in MVP. Future considerations:
- API key authentication
- JWT tokens for multi-tenancy
- Per-simulation access control

### CORS

Configured to allow web UI access during development. Production deployment should restrict origins.
