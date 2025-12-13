# UES API Client Library

This document provides comprehensive usage documentation for the UES Python API client library.

## Overview

The UES API client library provides a type-safe Python interface for interacting with the User Environment Simulator (UES) REST API. It supports both synchronous and asynchronous usage patterns.

## Installation

The client library is included in the UES package. Ensure you have the required dependencies:

```bash
uv sync
```

## Quick Start

### Synchronous Usage

```python
from client import UESClient

with UESClient(base_url="http://localhost:8000") as client:
    # Start the simulation
    client.simulation.start()
    
    # Send an email
    client.email.send(
        from_address="user@example.com",
        to_addresses=["recipient@example.com"],
        subject="Hello from UES",
        body_text="This is a test email.",
    )
    
    # Advance time by 1 hour
    result = client.time.advance(seconds=3600)
    print(f"Executed {result.events_executed} events")
    
    # Check email state
    state = client.email.get_state()
    print(f"Total emails: {state.message_count}")
```

### Asynchronous Usage

```python
import asyncio
from client import AsyncUESClient

async def main():
    async with AsyncUESClient(base_url="http://localhost:8000") as client:
        # Start the simulation
        await client.simulation.start()
        
        # Send multiple emails concurrently
        await asyncio.gather(
            client.email.send(
                from_address="sender@example.com",
                to_addresses=["a@example.com"],
                subject="Email 1",
                body_text="First message",
            ),
            client.email.send(
                from_address="sender@example.com",
                to_addresses=["b@example.com"],
                subject="Email 2",
                body_text="Second message",
            ),
        )
        
        # Get simulation status
        status = await client.simulation.status()
        print(f"Events processed: {status.events_processed}")

asyncio.run(main())
```

## Client Configuration

### Constructor Parameters

Both `UESClient` and `AsyncUESClient` accept the same configuration parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_url` | `str` | `"http://localhost:8000"` | Base URL of the UES server |
| `timeout` | `float` | `30.0` | Request timeout in seconds |
| `retry_enabled` | `bool` | `False` | Enable automatic retry on transient failures |
| `max_retries` | `int` | `3` | Maximum retry attempts when retry is enabled |
| `transport` | `Any` | `None` | Custom HTTP transport (for testing) |

### Example with Custom Configuration

```python
from client import UESClient

client = UESClient(
    base_url="http://ues-server:8000",
    timeout=60.0,
    retry_enabled=True,
    max_retries=5,
)
```

## Sub-Clients

The main client provides namespaced access to all API functionality through sub-client properties:

| Property | Sub-Client | Endpoints |
|----------|------------|-----------|
| `client.time` | `TimeClient` | `/simulator/time/*` |
| `client.simulation` | `SimulationClient` | `/simulation/*` |
| `client.events` | `EventsClient` | `/events/*` |
| `client.environment` | `EnvironmentClient` | `/environment/*` |
| `client.email` | `EmailClient` | `/email/*` |
| `client.sms` | `SMSClient` | `/sms/*` |
| `client.chat` | `ChatClient` | `/chat/*` |
| `client.calendar` | `CalendarClient` | `/calendar/*` |
| `client.location` | `LocationClient` | `/location/*` |
| `client.weather` | `WeatherClient` | `/weather/*` |

---

## Simulation Control

### Starting and Stopping

```python
# Start simulation (enables time progression and event execution)
client.simulation.start()

# Start with auto-advance enabled (time progresses automatically)
client.simulation.start(auto_advance=True, time_scale=2.0)

# Stop simulation (preserves state)
client.simulation.stop()

# Get current status
status = client.simulation.status()
print(f"Running: {status.running}")
print(f"Paused: {status.paused}")
print(f"Current time: {status.current_time}")
```

### Reset and Clear

```python
# Reset to initial state (preserves scheduled events)
client.simulation.reset()

# Clear all events and state
client.simulation.clear()

# Clear and reset time to a specific point
from datetime import datetime
client.simulation.clear(reset_time_to=datetime(2025, 1, 1, 9, 0, 0))
```

### Undo/Redo

```python
# Undo the last operation
result = client.simulation.undo()
print(f"Undid: {result.operation}")

# Redo a previously undone operation
result = client.simulation.redo()
print(f"Redid: {result.operation}")

# Get undo/redo history
history = client.simulation.history()
print(f"Can undo: {len(history.undo_stack)} operations")
print(f"Can redo: {len(history.redo_stack)} operations")
```

---

## Time Control

### Getting Current Time

```python
state = client.time.get_state()
print(f"Current time: {state.current_time}")
print(f"Time scale: {state.time_scale}")
print(f"Is paused: {state.is_paused}")
```

### Advancing Time

```python
# Advance by duration (executes pending events)
result = client.time.advance(seconds=3600)  # 1 hour
print(f"New time: {result.current_time}")
print(f"Events executed: {result.events_executed}")

# Advance using timedelta
from datetime import timedelta
result = client.time.advance(delta=timedelta(hours=2, minutes=30))
```

### Setting Absolute Time

```python
from datetime import datetime

# Jump to a specific time
result = client.time.set(target_time=datetime(2025, 6, 15, 14, 30, 0))
print(f"Time set to: {result.current_time}")
```

### Skip to Next Event

```python
# Jump to the next pending event's timestamp
result = client.time.skip_to_next()
if result.event_executed:
    print(f"Executed event: {result.event_id}")
else:
    print("No pending events")
```

### Pause and Resume

```python
# Pause time progression (for auto-advance mode)
client.time.pause()

# Resume time progression
client.time.resume()

# Set time scale (2.0 = twice real-time speed)
client.time.set_scale(scale=2.0)
```

---

## Event Management

### Listing Events

```python
# Get all events
events = client.events.list()
for event in events.events:
    print(f"{event.event_id}: {event.modality} at {event.scheduled_time}")

# Filter by status
pending = client.events.list(status="pending")
executed = client.events.list(status="executed")

# Paginate results
page1 = client.events.list(limit=10, offset=0)
page2 = client.events.list(limit=10, offset=10)
```

### Creating Events

```python
from datetime import datetime, timedelta

# Schedule an event for a future time
result = client.events.create(
    modality="email",
    action="receive",
    data={
        "from_address": "sender@example.com",
        "to_addresses": ["user@example.com"],
        "subject": "Scheduled Email",
        "body_text": "This email arrives at the scheduled time.",
    },
    scheduled_time=datetime.now() + timedelta(hours=1),
)
print(f"Created event: {result.event_id}")

# Create an immediate event (executes now)
result = client.events.create(
    modality="sms",
    action="receive_message",
    data={
        "message_data": {
            "sender": "+1234567890",
            "content": "Hello!",
        }
    },
    immediate=True,
)
```

### Getting Event Details

```python
# Get a specific event
event = client.events.get(event_id="evt_12345")
print(f"Status: {event.status}")
print(f"Modality: {event.modality}")

# Get the next pending event
next_event = client.events.next()
if next_event:
    print(f"Next event at: {next_event.scheduled_time}")
```

### Cancelling Events

```python
# Cancel a pending event
result = client.events.cancel(event_id="evt_12345")
if result.cancelled:
    print("Event cancelled successfully")
```

### Event Queue Summary

```python
summary = client.events.summary()
print(f"Total events: {summary.total_events}")
print(f"Pending: {summary.pending_count}")
print(f"Executed: {summary.executed_count}")
print(f"Next event: {summary.next_event_time}")
```

---

## Email Modality

### Getting Email State

```python
# Get complete email state
state = client.email.get_state()
print(f"Total messages: {state.message_count}")
print(f"Unread: {state.unread_count}")

# Get summary state (counts only, no message details)
summary = client.email.get_summary_state()
print(f"Inbox count: {summary.inbox_count}")
```

### Querying Emails

```python
from datetime import datetime, timedelta

# Query with filters
results = client.email.query(
    folder="inbox",
    is_read=False,
    since=datetime.now() - timedelta(days=7),
    search="meeting",
    limit=20,
)
for email in results.emails:
    print(f"From: {email.from_address}, Subject: {email.subject}")
```

### Sending Emails

```python
# Send an email (creates immediate event)
result = client.email.send(
    from_address="user@example.com",
    to_addresses=["recipient@example.com"],
    subject="Hello",
    body_text="Plain text body",
    body_html="<p>HTML body</p>",
    cc_addresses=["cc@example.com"],
    attachments=[{
        "filename": "doc.pdf",
        "content_type": "application/pdf",
        "size": 1024,
    }],
)
print(f"Sent email: {result.event_id}")
```

### Receiving Emails

```python
# Simulate receiving an email
result = client.email.receive(
    from_address="external@example.com",
    to_addresses=["user@example.com"],
    subject="Incoming Message",
    body_text="You have a new message.",
)
```

### Managing Emails

```python
# Mark as read/unread
client.email.mark_read(message_ids=["msg_123", "msg_456"])
client.email.mark_unread(message_ids=["msg_789"])

# Star/unstar emails
client.email.star(message_ids=["msg_123"])
client.email.unstar(message_ids=["msg_123"])

# Move to folder
client.email.move(message_ids=["msg_123"], folder="archive")

# Archive emails
client.email.archive(message_ids=["msg_123", "msg_456"])

# Delete emails
client.email.delete(message_ids=["msg_789"])

# Add/remove labels
client.email.add_labels(message_ids=["msg_123"], labels=["important", "work"])
client.email.remove_labels(message_ids=["msg_123"], labels=["work"])
```

---

## SMS Modality

### Getting SMS State

```python
state = client.sms.get_state()
print(f"Total messages: {state.message_count}")
print(f"Conversations: {state.conversation_count}")
```

### Querying Messages

```python
# Query SMS messages
results = client.sms.query(
    conversation_id="+1234567890",
    is_read=False,
    message_type="sms",
    limit=50,
)
for msg in results.messages:
    print(f"{msg.sender}: {msg.content}")
```

### Sending SMS

```python
# Send an SMS
result = client.sms.send(
    recipient="+1234567890",
    content="Hello from UES!",
    message_type="sms",
)

# Send RCS message with rich content
result = client.sms.send(
    recipient="+1234567890",
    content="Check out this image",
    message_type="rcs",
    attachments=[{
        "url": "https://example.com/image.jpg",
        "content_type": "image/jpeg",
    }],
)
```

### Receiving SMS

```python
# Simulate receiving an SMS
result = client.sms.receive(
    sender="+1987654321",
    content="Hey, are you free tonight?",
    message_type="sms",
)
```

### Managing SMS

```python
# Mark as read
client.sms.mark_read(message_ids=["sms_123"])

# Delete messages
client.sms.delete(message_ids=["sms_456"])

# Add reaction (RCS only)
client.sms.react(message_id="sms_123", reaction="👍")
```

---

## Chat Modality

### Getting Chat State

```python
state = client.chat.get_state()
print(f"Total messages: {state.total_message_count}")
print(f"Conversations: {state.conversation_count}")
```

### Querying Messages

```python
# Query chat messages
results = client.chat.query(
    conversation_id="default",
    role="user",
    search="help",
    limit=20,
)
for msg in results.messages:
    print(f"[{msg.role}]: {msg.content}")
```

### Sending Messages

```python
# Send a user message
client.chat.send(
    role="user",
    content="What's the weather like today?",
    conversation_id="default",
)

# Send an assistant response
client.chat.send(
    role="assistant",
    content="The weather is sunny with a high of 75°F.",
    conversation_id="default",
    metadata={"model": "gpt-4", "tokens": 42},
)
```

### Managing Chat

```python
# Delete a message
client.chat.delete(message_id="chat_123")

# Clear a conversation
client.chat.clear(conversation_id="default")
```

---

## Calendar Modality

### Getting Calendar State

```python
state = client.calendar.get_state()
print(f"Calendars: {state.calendar_count}")
print(f"Events: {state.event_count}")
```

### Querying Events

```python
from datetime import datetime, timedelta

# Query upcoming events
results = client.calendar.query(
    start=datetime.now(),
    end=datetime.now() + timedelta(days=7),
    status="confirmed",
)
for event in results.events:
    print(f"{event.title}: {event.start} - {event.end}")
```

### Creating Events

```python
from datetime import datetime

# Create a simple event
result = client.calendar.create(
    title="Team Meeting",
    start=datetime(2025, 1, 15, 10, 0),
    end=datetime(2025, 1, 15, 11, 0),
    location="Conference Room A",
    description="Weekly sync",
)

# Create a recurring event
result = client.calendar.create(
    title="Daily Standup",
    start=datetime(2025, 1, 15, 9, 0),
    end=datetime(2025, 1, 15, 9, 15),
    recurrence={
        "frequency": "DAILY",
        "count": 30,
        "by_day": ["MO", "TU", "WE", "TH", "FR"],
    },
)

# Create event with attendees
result = client.calendar.create(
    title="Project Review",
    start=datetime(2025, 1, 20, 14, 0),
    end=datetime(2025, 1, 20, 15, 0),
    attendees=[
        {"email": "alice@example.com", "display_name": "Alice"},
        {"email": "bob@example.com", "optional": True},
    ],
    reminders=[
        {"method": "popup", "minutes": 15},
        {"method": "email", "minutes": 60},
    ],
)
```

### Updating Events

```python
# Update event details
client.calendar.update(
    event_id="cal_123",
    title="Updated Meeting Title",
    location="New Location",
)

# Update recurring event (all instances)
client.calendar.update(
    event_id="cal_456",
    recurrence_scope="all",
    start=datetime(2025, 1, 15, 9, 30),
    end=datetime(2025, 1, 15, 9, 45),
)
```

### Deleting Events

```python
# Delete a single event
client.calendar.delete(event_id="cal_123")

# Delete recurring event (this and future)
client.calendar.delete(
    event_id="cal_456",
    recurrence_scope="future",
)
```

---

## Location Modality

### Getting Location State

```python
state = client.location.get_state()
print(f"Current: {state.current}")
print(f"History entries: {len(state.history)}")
```

### Querying Location History

```python
from datetime import datetime, timedelta

# Query location history
results = client.location.query(
    since=datetime.now() - timedelta(days=1),
    named_location="Office",
    limit=10,
)
for loc in results.locations:
    print(f"{loc['timestamp']}: {loc['named_location']}")
```

### Updating Location

```python
# Update current location
client.location.update(
    latitude=40.7128,
    longitude=-74.0060,
    address="350 5th Ave, New York, NY",
    named_location="Office",
    altitude=10.0,
    accuracy=5.0,
)
```

---

## Weather Modality

### Getting Weather State

```python
state = client.weather.get_state()
print(f"Tracked locations: {state.location_count}")
```

### Querying Weather

```python
# Query weather for a location
results = client.weather.query(
    lat=40.7128,
    lon=-74.0060,
    units="imperial",
)
for report in results.reports:
    current = report.get("current", {})
    print(f"Temperature: {current.get('temp')}°F")
```

### Updating Weather

```python
# Set weather for a location
client.weather.update(
    latitude=40.7128,
    longitude=-74.0060,
    report={
        "lat": 40.7128,
        "lon": -74.0060,
        "timezone": "America/New_York",
        "current": {
            "dt": 1640000000,
            "temp": 45.0,
            "feels_like": 40.0,
            "humidity": 65,
            "weather": [{"id": 800, "main": "Clear", "description": "clear sky"}],
        },
    },
)
```

---

## Environment State

### Getting Complete State

```python
# Get all modality states
state = client.environment.get_state()
print(f"Current time: {state.current_time}")
print(f"Available modalities: {list(state.modalities.keys())}")
```

### Getting Specific Modality State

```python
# Get state for a specific modality
email_state = client.environment.get_modality_state("email")
print(f"Email messages: {email_state.get('message_count')}")
```

### Querying Across Modalities

```python
# Query a specific modality through environment endpoint
results = client.environment.query_modality(
    modality="email",
    query_params={"folder": "inbox", "is_read": False},
)
```

---

## Exception Handling

The client library provides a hierarchy of exceptions for error handling:

```python
from client import (
    UESClientError,      # Base exception
    ConnectionError,     # Failed to connect
    TimeoutError,        # Request timed out
    APIError,            # Server returned an error
    ValidationError,     # Request validation failed (422)
    NotFoundError,       # Resource not found (404)
    ConflictError,       # State conflict (409)
    ServerError,         # Server-side error (5xx)
)

try:
    client.email.get_state()
except ConnectionError:
    print("Could not connect to server")
except TimeoutError:
    print("Request timed out")
except NotFoundError as e:
    print(f"Resource not found: {e.detail}")
except ValidationError as e:
    print(f"Invalid request: {e.detail}")
except APIError as e:
    print(f"API error {e.status_code}: {e.detail}")
except UESClientError as e:
    print(f"Client error: {e}")
```

### APIError Properties

```python
try:
    client.events.get(event_id="nonexistent")
except APIError as e:
    print(f"Status code: {e.status_code}")
    print(f"Error type: {e.error_type}")
    print(f"Detail: {e.detail}")
    print(f"Request ID: {e.request_id}")
```

---

## Testing with the Client

### Using ASGITransport for Integration Tests

```python
import pytest
from httpx import ASGITransport
from client import UESClient
from main import app

@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    with UESClient(
        base_url="http://test",
        transport=transport,
    ) as client:
        client.simulation.start()
        yield client
        client.simulation.stop()

def test_send_email(client):
    result = client.email.send(
        from_address="test@example.com",
        to_addresses=["recipient@example.com"],
        subject="Test",
        body_text="Test body",
    )
    assert result.success is True
```

### Async Testing

```python
import pytest
from httpx import ASGITransport
from client import AsyncUESClient
from main import app

@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncUESClient(
        base_url="http://test",
        transport=transport,
    ) as client:
        await client.simulation.start()
        yield client
        await client.simulation.stop()

@pytest.mark.asyncio
async def test_async_send_email(async_client):
    result = await async_client.email.send(
        from_address="test@example.com",
        to_addresses=["recipient@example.com"],
        subject="Test",
        body_text="Test body",
    )
    assert result.success is True
```

---

## Response Models

The client returns strongly-typed Pydantic models for all responses. Key models include:

### General Models

- `ModalityActionResponse`: Response for modality actions (send, delete, etc.)
- `ModalityStateResponse`: Response for state endpoints
- `ModalityQueryResponse`: Response for query endpoints
- `EventSummaryResponse`: Event queue summary
- `SimulationStatusResponse`: Simulation status

### Email Models

- `Email`: Complete email message
- `EmailStateResponse`: Email modality state
- `EmailQueryResponse`: Email query results

### SMS Models

- `SMSMessage`: SMS/RCS message
- `SMSConversation`: Conversation with metadata
- `SMSStateResponse`: SMS modality state

### Calendar Models

- `CalendarEvent`: Calendar event with all properties
- `Attendee`: Event attendee
- `RecurrenceRule`: Recurrence configuration

See the API reference documentation for complete model details.

---

## Best Practices

### 1. Use Context Managers

Always use context managers to ensure proper resource cleanup:

```python
# Good
with UESClient() as client:
    client.email.send(...)

# Avoid (requires manual cleanup)
client = UESClient()
try:
    client.email.send(...)
finally:
    client.close()
```

### 2. Handle Errors Appropriately

Catch specific exceptions rather than generic ones:

```python
# Good
try:
    client.events.get(event_id=event_id)
except NotFoundError:
    print("Event not found")
except APIError:
    print("Server error")

# Avoid
try:
    client.events.get(event_id=event_id)
except Exception:
    print("Something went wrong")
```

### 3. Use Async for Concurrent Operations

When performing multiple independent operations, use async for better performance:

```python
async with AsyncUESClient() as client:
    # Concurrent operations
    results = await asyncio.gather(
        client.email.send(...),
        client.sms.send(...),
        client.calendar.create(...),
    )
```

### 4. Enable Retries for Production

For production use with unreliable networks:

```python
client = UESClient(
    retry_enabled=True,
    max_retries=3,
    timeout=60.0,
)
```

### 5. Use Query Filters

Avoid fetching all data when you only need a subset:

```python
# Good - specific query
emails = client.email.query(folder="inbox", is_read=False, limit=10)

# Avoid - fetching everything
state = client.email.get_state()  # Gets all emails
```
