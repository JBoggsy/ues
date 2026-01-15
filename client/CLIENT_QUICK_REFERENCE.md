# UES Python Client Quick Reference

## Basic Usage

```python
from client import UESClient, AsyncUESClient

# Synchronous (recommended for scripts)
with UESClient(base_url="http://localhost:8000") as client:
    client.simulation.start()
    # ... work with client ...

# Asynchronous
async with AsyncUESClient(base_url="http://localhost:8000") as client:
    await client.simulation.start()
```

**Constructor parameters:**
- `base_url`: Server URL (default: `"http://localhost:8000"`)
- `timeout`: Request timeout in seconds (default: `30.0`)
- `retry_enabled`: Auto-retry on transient failures (default: `False`)
- `max_retries`: Max retry attempts (default: `3`)

---

## Sub-clients

Access via properties on `UESClient` / `AsyncUESClient`:

| Property | Description | Base Path |
|----------|-------------|-----------|
| `client.time` | Time control | `/simulator/time` |
| `client.simulation` | Simulation lifecycle | `/simulation` |
| `client.events` | Event queue management | `/events` |
| `client.environment` | Environment state | `/environment` |
| `client.email` | Email modality | `/email` |
| `client.sms` | SMS/RCS modality | `/sms` |
| `client.chat` | Chat modality | `/chat` |
| `client.calendar` | Calendar modality | `/calendar` |
| `client.location` | Location modality | `/location` |
| `client.weather` | Weather modality | `/weather` |
| `client.webhooks` | Webhook management | `/webhooks` |

**Note:** There is NO `client.scenario` sub-client. Use `httpx` directly for scenario import/export (see below).

---

## Simulation Control (`client.simulation`)

```python
# Start simulation
result = client.simulation.start(auto_advance=False, time_scale=1.0)
# Returns: StartSimulationResponse(simulation_id, status, current_time, auto_advance, time_scale)

# Stop simulation
result = client.simulation.stop()
# Returns: StopSimulationResponse(simulation_id, status, final_time, total_events, events_executed, events_failed)

# Get status
status = client.simulation.status()
# Returns: SimulationStatusResponse(is_running, current_time, is_paused, auto_advance, time_scale, pending_events, executed_events, failed_events, next_event_time)

# Reset (undo all events, reset to PENDING status)
result = client.simulation.reset()
# Returns: ResetSimulationResponse(status, message, cleared_events, events_undone, undo_errors)

# Clear (remove all events and modality states)
result = client.simulation.clear(reset_time_to=datetime(...))  # optional
# Returns: ClearSimulationResponse(status, events_removed, modalities_cleared, time_reset, current_time)

# Undo/Redo
result = client.simulation.undo(count=1)
result = client.simulation.redo(count=1)
```

---

## Time Control (`client.time`)

```python
# Get current time state
state = client.time.get_state()
# Returns: TimeStateResponse(current_time, time_scale, is_paused, auto_advance, mode)

# Advance time by duration (executes events in interval)
result = client.time.advance(seconds=3600)
# Returns: AdvanceTimeResponse(previous_time, current_time, time_advanced, events_executed, events_failed, execution_details)

# Jump to specific time (skips events, doesn't execute)
result = client.time.set(target_time=datetime(...))
# Returns: SetTimeResponse(current_time, previous_time, skipped_events, executed_events)

# Skip to next pending event
result = client.time.skip_to_next()
# Returns: SkipToNextResponse(previous_time, current_time, events_executed, next_event_time)

# Pause/Resume
result = client.time.pause()
result = client.time.resume()
# Returns: PauseResumeResponse(message, current_time, is_paused)
```

---

## Events (`client.events`)

```python
# List events with filters
events = client.events.list_events(
    status="pending",  # "pending", "executed", "failed", "skipped", "cancelled"
    modality="email",
    start_time=datetime(...),
    end_time=datetime(...),
    limit=50,
    offset=0,
)
# Returns: EventListResponse(events, total, pending, executed, failed, skipped)

# Create scheduled event
event = client.events.create(
    scheduled_time=datetime(...),
    modality="email",
    data={"action": "receive", "from_address": "...", ...},
    priority=50,
)
# Returns: EventResponse(event_id, scheduled_time, modality, status, priority, created_at, ...)

# Create immediate event
event = client.events.create_immediate(modality="email", data={...})

# Create batch of events
result = client.events.create_batch(
    events=[{"scheduled_time": ..., "modality": ..., "data": {...}}, ...],
    stop_on_first_error=False,
    validate_only=False,
)
# Returns: BatchCreateEventResponse(total_submitted, total_created, total_failed, events)

# Get event summary/statistics
summary = client.events.summary()
# Returns: EventSummaryResponse(total, pending, executed, failed, skipped, by_modality, next_event_time)

# Cancel event
result = client.events.cancel(event_id="...")
# Returns: CancelEventResponse(cancelled, event_id)
```

---

## Email (`client.email`)

```python
# Get full state
state = client.email.get_state()
# Returns: EmailStateResponse(emails, threads, folders, labels, total_email_count, unread_count, starred_count, ...)

# Get summary state (without full body content)
state = client.email.get_state(summary=True)
# Returns: EmailSummaryStateResponse(emails, threads, statistics, ...)

# Query emails with filters
result = client.email.query(
    folder="inbox",
    is_read=False,
    is_starred=None,
    from_address="sender@example.com",
    subject_contains="meeting",
    received_after=datetime(...),
    received_before=datetime(...),
    limit=50,
    offset=0,
    sort_by="received_at",
    sort_order="desc",
)
# Returns: EmailQueryResponse(emails, total_count, returned_count, query)

# Send email (from user)
client.email.send(
    from_address="user@example.com",
    to_addresses=["recipient@example.com"],
    subject="Subject",
    body_text="Body content",
    cc_addresses=[],
    priority="normal",
)
# Returns: ModalityActionResponse

# Receive email (simulate incoming)
client.email.receive(
    from_address="external@example.com",
    to_addresses=["user@example.com"],
    subject="Subject",
    body_text="Body content",
    thread_id=None,  # auto-generated if new
    in_reply_to=None,
    sent_at=None,  # defaults to current sim time
)
# Returns: ModalityActionResponse

# Other actions
client.email.mark_read(message_id="...")
client.email.mark_unread(message_id="...")
client.email.star(message_id="...")
client.email.unstar(message_id="...")
client.email.move(message_id="...", folder="archive")
client.email.delete(message_id="...")
client.email.reply(message_id="...", body_text="...")
client.email.forward(message_id="...", to_addresses=[...], body_text="...")
```

---

## Environment (`client.environment`)

```python
# Get full environment state
state = client.environment.get_state()
# Returns: EnvironmentStateResponse(current_time, modalities, summary)

# Get compact LLM-optimized snapshot
snapshot = client.environment.get_state(compact=True)
# Returns: CompactSnapshotResponse(snapshot_time, format, modalities, events)

# Get as plain text for LLM prompt
text = client.environment.get_state(compact=True, format="text")
# Returns: str

# List available modalities
modalities = client.environment.list_modalities()
# Returns: ModalityListResponse(modalities, count)

# Validate environment state
result = client.environment.validate()
# Returns: ValidationResponse(valid, errors, checked_at)
```

---

## Scenario Import/Export (Direct HTTP - No Sub-client)

**Note:** The client library does NOT have a `client.scenario` sub-client. Use `httpx` directly:

```python
import httpx
import json

# Import full scenario
with open("scenario.ues-scenario.json") as f:
    scenario_data = json.load(f)

response = httpx.post(
    "http://localhost:8000/scenario/import/full",
    json={"scenario": scenario_data},
    timeout=30.0,
)
response.raise_for_status()
result = response.json()
# Returns: {"success": true, "environment_loaded": true, "events_loaded": 10, ...}

# Export full scenario
response = httpx.get(
    "http://localhost:8000/scenario/export/full",
    params={"author": "Name", "description": "Description"},
    timeout=30.0,
)
scenario = response.json()
```

**Scenario file structure (required fields):**
```json
{
  "metadata": {
    "ues_version": "0.1.0",
    "scenario_version": "1",
    "created_at": "2024-03-15T07:00:00+00:00",
    "author": "Optional",
    "description": "Optional"
  },
  "environment": {
    "time_state": {
      "current_time": "2024-03-15T07:00:00+00:00",
      "time_scale": 1.0,
      "is_paused": true,
      "auto_advance": false,
      "last_wall_time_update": "2024-03-15T07:00:00+00:00"  // Required!
    },
    "modality_states": {
      "email": {
        "modality_type": "email",           // Required for all modalities
        "last_updated": "2024-03-15T07:00:00+00:00",  // Required
        "update_count": 0,                  // Required
        "user_email_address": "user@example.com",
        "emails": {},
        "threads": {},
        "folders": {},
        "labels": {},
        "drafts": {}
      }
      // ... other modalities follow same pattern
    }
  },
  "events": {
    "events": [ ... ]
  }
}
```

**Tip:** Export an existing scenario using `GET /scenario/export/full` to see the correct format.

**Available endpoints:**
- `GET /scenario/export/environment` - Export environment state only
- `GET /scenario/export/events` - Export event queue only
- `GET /scenario/export/full` - Export complete scenario
- `POST /scenario/import/environment` - Import environment state
- `POST /scenario/import/events` - Import event queue
- `POST /scenario/import/full` - Import complete scenario

---

## Other Modalities (Summary)

### SMS (`client.sms`)
```python
state = client.sms.get_state()
result = client.sms.query(thread_id=..., from_number=..., is_read=...)
client.sms.send_message(to_numbers=[...], body="...")
client.sms.receive_message(from_number="...", body="...")
```

### Calendar (`client.calendar`)
```python
state = client.calendar.get_state()
result = client.calendar.query(start_time=..., end_time=..., attendee=...)
client.calendar.create_event(summary="...", start_time=..., end_time=...)
client.calendar.update_event(event_id="...", summary="...")
client.calendar.delete_event(event_id="...")
```

### Location (`client.location`)
```python
state = client.location.get_state()
result = client.location.query(named_location=..., start_time=...)
client.location.update(latitude=..., longitude=..., address="...")
```

### Weather (`client.weather`)
```python
state = client.weather.get_state()
result = client.weather.query(lat=..., lon=..., units="imperial")
client.weather.update(latitude=..., longitude=..., report={...})
```

### Chat (`client.chat`)
```python
state = client.chat.get_state()
result = client.chat.query(conversation_id=..., role=...)
client.chat.send_message(role="user", content="...", conversation_id="...")
```

---

## Exceptions

All exceptions inherit from `UESClientError`:

```python
from client import (
    UESClientError,    # Base exception
    ConnectionError,   # Failed to connect
    TimeoutError,      # Request timed out
    APIError,          # Server returned error
    ValidationError,   # HTTP 422
    NotFoundError,     # HTTP 404
    ConflictError,     # HTTP 409 (e.g., simulation already running)
    ServerError,       # HTTP 5xx
)
```

---

## Common Patterns

### Load scenario and run simulation loop
```python
import json
import httpx
from datetime import timedelta
from client import UESClient

# Load scenario via direct HTTP
with open("scenario.ues-scenario.json") as f:
    scenario = json.load(f)

httpx.post(
    "http://localhost:8000/scenario/import/full",
    json={"scenario": scenario},
    timeout=30.0,
).raise_for_status()

# Run simulation
with UESClient() as client:
    client.simulation.start(auto_advance=False)
    
    for _ in range(10):
        # Advance 1 hour
        result = client.time.advance(seconds=3600)
        print(f"Executed {result.events_executed} events")
        
        # Query recent emails
        current = result.current_time
        emails = client.email.query(
            received_after=current - timedelta(hours=1),
            received_before=current,
        )
        for email in emails.emails:
            print(f"  - {email.from_address}: {email.subject}")
    
    client.simulation.stop()
```
