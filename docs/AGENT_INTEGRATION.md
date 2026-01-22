# Agent Integration Guide

This comprehensive guide covers how to integrate AI agents with the User Environment Simulator (UES). Whether you're testing an AI personal assistant or building simulator-side content generation agents, this document provides the patterns, examples, and best practices you need.

## Overview

UES is designed as a **pure simulation engine** with no built-in LLM dependencies. All agent interactions happen externally through the REST API. This architecture supports two types of agents:

1. **User-Side Agents (Being Tested)**: Your AI personal assistant that queries the simulated environment and takes actions
2. **Simulator-Side Agents (Content Generation)**: External agents that generate realistic content and react to simulation events

```
┌─────────────────────────────────────────────────────────────────┐
│                    UES Core (Pure Simulation)                   │
│  • Deterministic scenario execution                             │
│  • State management & event scheduling                          │
│  • REST API + WebSocket + Webhooks                              │
└───────────────────────────────┬─────────────────────────────────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         │                      │                      │
   Simulator-Side         User-Side Agent         Developer
   Agent (optional)       (being tested)          (Web UI)
         │                      │                      │
         └──────────────────────┴──────────────────────┘
                    All use the same REST API
```

## Table of Contents

1. [Quick Start](#quick-start)
2. [Python Client Library](#python-client-library)
3. [Real-Time Notifications](#real-time-notifications)
4. [Compact State Snapshots](#compact-state-snapshots)
5. [Batch Event Submission](#batch-event-submission)
6. [Webhook Integration](#webhook-integration)
7. [Multi-Agent Coordination (Holds)](#multi-agent-coordination-holds)
8. [Example Agent Patterns](#example-agent-patterns)
9. [Best Practices](#best-practices)

---

## Quick Start

### Prerequisites

1. UES server running: `uv run uvicorn main:app --reload`
2. Server accessible at `http://localhost:8000`

### Your First Agent (5 Minutes)

```python
from client import UESClient

with UESClient(base_url="http://localhost:8000") as client:
    # Start the simulation
    client.simulation.start()
    
    # Get compact environment snapshot (LLM-optimized)
    snapshot = client.environment.get_state(compact=True, format="text")
    print(snapshot)
    
    # Simulate receiving an email
    client.email.receive(
        from_address="boss@company.com",
        to_addresses=["user@example.com"],
        subject="Meeting at 3pm",
        body_text="Don't forget our meeting this afternoon."
    )
    
    # Query unread emails
    unread = client.email.query(folder="inbox", is_read=False)
    print(f"Unread emails: {len(unread.emails)}")
    
    # Advance time to trigger scheduled events
    result = client.time.advance(seconds=3600)
    print(f"Executed {result.events_executed} events")
```

### Using curl

```bash
# Start simulation
curl -X POST http://localhost:8000/simulation/start -H "Content-Type: application/json" -d '{}'

# Get compact state snapshot
curl "http://localhost:8000/environment/state?compact=true&format=text"

# Receive an email
curl -X POST http://localhost:8000/email/receive \
  -H "Content-Type: application/json" \
  -d '{
    "from_address": "boss@company.com",
    "to_addresses": ["user@example.com"],
    "subject": "Meeting at 3pm",
    "body_text": "Don't forget our meeting this afternoon."
  }'

# Query emails
curl -X POST http://localhost:8000/email/query \
  -H "Content-Type: application/json" \
  -d '{"folder": "inbox", "is_read": false}'
```

---

## Python Client Library

The UES Python client provides a type-safe, intuitive interface for all API operations.

### Installation

```bash
# Client is included in the UES package
uv sync
```

### Synchronous vs Asynchronous

```python
# Synchronous (simple scripts, testing)
from client import UESClient

with UESClient() as client:
    client.email.send(...)

# Asynchronous (high-performance agents, concurrent operations)
import asyncio
from client import AsyncUESClient

async def main():
    async with AsyncUESClient() as client:
        # Run multiple operations concurrently
        results = await asyncio.gather(
            client.email.send(...),
            client.sms.send(...),
            client.calendar.create(...),
        )

asyncio.run(main())
```

### Sub-Clients

The client organizes functionality into logical sub-clients:

| Sub-Client | Purpose | Key Methods |
|------------|---------|-------------|
| `client.simulation` | Lifecycle control | `start()`, `stop()`, `status()`, `reset()`, `undo()`, `redo()`, `hold()`, `release()`, `list_holds()` |
| `client.time` | Time control | `get_state()`, `advance()`, `set()`, `skip_to_next()`, `pause()`, `resume()` |
| `client.events` | Event management | `list()`, `create()`, `create_batch()`, `cancel()`, `get()`, `next()` |
| `client.environment` | State queries | `get_state()`, `list_modalities()`, `validate()` |
| `client.email` | Email operations | `send()`, `receive()`, `query()`, `mark_read()`, `delete()`, `archive()` |
| `client.sms` | SMS/RCS operations | `send()`, `receive()`, `query()`, `mark_read()`, `react()` |
| `client.chat` | Chat operations | `send()`, `query()`, `delete()`, `clear()` |
| `client.calendar` | Calendar operations | `create()`, `update()`, `delete()`, `query()` |
| `client.location` | Location operations | `update()`, `query()`, `get_state()` |
| `client.weather` | Weather operations | `update()`, `query()`, `get_state()` |
| `client.webhooks` | Webhook management | `register()`, `list()`, `test()`, `pause()`, `delete()` |

### Error Handling

```python
from client import (
    UESClientError,      # Base exception
    ConnectionError,     # Server unreachable
    TimeoutError,        # Request timeout
    NotFoundError,       # Resource not found (404)
    ValidationError,     # Invalid request (422)
    ConflictError,       # State conflict (409) - also returned when holds block time
    ServerError,         # Server error (5xx)
)

try:
    event = client.events.get(event_id="nonexistent")
except NotFoundError as e:
    print(f"Event not found: {e.detail}")
except ValidationError as e:
    print(f"Invalid request: {e.detail}")
except ConnectionError:
    print("Could not connect to UES server")
```

For complete client documentation, see [API_CLIENT.md](API_CLIENT.md).

---

## Real-Time Notifications

UES provides two mechanisms for real-time event notifications:

### WebSocket (Persistent Connection)

Best for: Real-time UIs, low-latency reactive agents, dashboard updates

```python
from client import AsyncUESClient

async with AsyncUESClient() as client:
    # Subscribe to email and time events
    async with client.subscribe(["email.", "time."]) as events:
        async for event in events:
            print(f"Event: {event.type}")
            print(f"Data: {event.data}")
            
            if event.type == "email.received":
                # React to new email
                await handle_new_email(event.data)
```

**Event Type Patterns:**

| Pattern | Matches |
|---------|---------|
| `"email."` | All email events |
| `"email.received"` | Only received emails (exact match) |
| `"time."` | All time events |
| `"simulation."` | Simulation lifecycle events |
| `null` / omitted | All events |

### Webhooks (HTTP Callbacks)

Best for: Serverless functions, external services, guaranteed delivery with retries

```python
# Register a webhook
webhook = client.webhooks.register(
    url="https://my-agent.example.com/callback",
    events=["email.received", "sms.received"],
    secret="my-hmac-secret",  # For signature verification
    metadata={"agent": "EmailBot"}
)

# Webhook will receive POST requests like:
# {
#   "id": "del_xyz789",
#   "webhook_id": "wh_abc123",
#   "event_type": "email.received",
#   "timestamp": "2025-01-01T10:05:00Z",
#   "data": {"email_id": "msg_123", "from": "sender@example.com", "subject": "Hello"}
# }
```

**When to Use Which:**

| Aspect | WebSocket | Webhook |
|--------|-----------|---------|
| Connection | Persistent | Server pushes to your URL |
| Latency | Lowest | HTTP overhead |
| Reliability | Missed if disconnected | Retries, delivery tracking |
| Use Case | Real-time UIs | Serverless, external services |
| Implementation | Maintain connection | Expose HTTP endpoint |

For detailed documentation, see [WEBSOCKET.md](WEBSOCKET.md) and [WEBHOOKS.md](WEBHOOKS.md).

---

## Compact State Snapshots

When building LLM-powered agents, you need to inject environment context into prompts without exceeding token limits. The compact snapshot endpoint provides an optimized representation (~2KB vs 50KB+ for full state).

### JSON Format

```python
snapshot = client.environment.get_state(compact=True)

# Returns CompactSnapshotResponse with:
# - snapshot_time: Current simulator time
# - modalities: Dict of modality summaries
# - events: Pending event count and next event time
```

### Plain Text Format (LLM Injection)

```python
snapshot_text = client.environment.get_state(compact=True, format="text")

# Returns human-readable text like:
# === UES Environment Snapshot ===
# Time: 2024-03-15 14:30 PST (America/Los_Angeles)
# 
# 📍 LOCATION: San Francisco, CA (37.7749, -122.4194)
# 🌤️ WEATHER: Partly cloudy, 68°F (20°C)
# 📧 EMAIL: 5 unread, 23 total
#   • [2h ago] "Re: Project Update" from alice@work.com
# 📅 CALENDAR: 2 events today
#   • NOW: Team Standup (ends in 15 min)
#   • 3:00 PM: 1:1 with Manager
# 💬 SMS: 2 unread conversations
# ⏳ PENDING EVENTS: 3 scheduled
```

### Using with LLMs

```python
from openai import OpenAI

def assistant_with_context(user_message: str) -> str:
    """AI assistant with UES environment awareness."""
    
    # Get current world state
    with UESClient() as ues:
        context = ues.environment.get_state(compact=True, format="text")
    
    # Inject into LLM prompt
    openai_client = OpenAI()
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": f"""You are a helpful personal assistant. Here is the current environment:

{context}

Use this context to provide relevant, timely assistance."""
            },
            {"role": "user", "content": user_message}
        ]
    )
    
    return response.choices[0].message.content
```

### What's Included

| Modality | Full State | Compact Snapshot |
|----------|------------|------------------|
| **Email** | All emails with full bodies | Unread count, recent subjects (no bodies) |
| **SMS** | All messages, full histories | Unread conversations, last message preview |
| **Chat** | Complete message history | Recent count, last exchange |
| **Calendar** | All events with details | Current/next event, today's count |
| **Location** | Current + full history | Current location only |
| **Weather** | All locations, full forecast | Current conditions |
| **Time** | Full state | Timezone, format preferences |

---

## Batch Event Submission

For scenarios requiring many events (test setup, simulation initialization), batch submission is far more efficient than individual API calls.

### Basic Usage

```python
from datetime import datetime, timedelta

# Get current simulator time
current_time = client.time.get_state().current_time

# Create multiple events at once (up to 1000)
result = client.events.create_batch([
    {
        "scheduled_time": current_time + timedelta(minutes=30),
        "modality": "email",
        "data": {
            "action": "receive",
            "from_address": "sender@example.com",
            "to_addresses": ["user@example.com"],
            "subject": "First Email",
            "body_text": "Message 1",
        },
    },
    {
        "scheduled_time": current_time + timedelta(hours=1),
        "modality": "sms",
        "data": {
            "action": "receive_message",
            "from_number": "+1234567890",
            "to_numbers": ["+0987654321"],
            "body": "Hello!",
        },
    },
    {
        "scheduled_time": current_time + timedelta(hours=2),
        "modality": "location",
        "data": {
            "action": "update",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "named_location": "Office",
        },
    },
])

print(f"Created {result.total_created}/{result.total_submitted} events")
```

### Batch Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| Default | Create valid events, skip invalid | Lenient batch import |
| `stop_on_first_error=True` | Reject all if any invalid | Strict validation |
| `validate_only=True` | Dry-run, no creation | Pre-flight check |

```python
# Strict mode: all-or-nothing
try:
    result = client.events.create_batch(events, stop_on_first_error=True)
except ValidationError:
    print("Batch rejected due to invalid events")

# Validation only: check without creating
validation = client.events.create_batch(events, validate_only=True)
print(f"Valid: {validation.total_valid}, Invalid: {validation.total_invalid}")
for event in validation.events:
    if not event.valid:
        print(f"  Event {event.index}: {event.error}")
```

---

## Webhook Integration

Webhooks enable external services to receive real-time notifications without maintaining persistent connections.

### Setting Up a Webhook Receiver

Here's a complete Flask-based webhook receiver:

```python
from flask import Flask, request, jsonify
import hmac
import hashlib

app = Flask(__name__)
WEBHOOK_SECRET = "my-secret-key"

def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify the UES HMAC signature."""
    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    if not signature.startswith("sha256="):
        return False
    
    return hmac.compare_digest(expected, signature[7:])

@app.route("/webhook", methods=["POST"])
def handle_webhook():
    # Verify signature
    signature = request.headers.get("X-UES-Signature", "")
    if not verify_signature(request.data, signature):
        return jsonify({"error": "Invalid signature"}), 401
    
    event = request.json
    event_type = event["event_type"]
    data = event["data"]
    
    # Handle different event types
    if event_type == "email.received":
        handle_email_received(data)
    elif event_type == "sms.received":
        handle_sms_received(data)
    elif event_type.startswith("calendar."):
        handle_calendar_event(event_type, data)
    
    return jsonify({"status": "ok"}), 200

def handle_email_received(data):
    """React to incoming email."""
    subject = data.get("subject", "")
    sender = data.get("from", "")
    
    if "urgent" in subject.lower():
        # Trigger notification, escalate, etc.
        print(f"URGENT email from {sender}: {subject}")

if __name__ == "__main__":
    app.run(port=5001)
```

### Registering the Webhook

```python
with UESClient() as client:
    webhook = client.webhooks.register(
        url="https://my-server.com/webhook",
        events=["email.received", "sms.received", "calendar."],
        secret="my-secret-key",
        metadata={"agent": "NotificationBot"}
    )
    print(f"Registered: {webhook['id']}")
    
    # Test the webhook
    result = client.webhooks.test(webhook['id'])
    if result['success']:
        print(f"Test succeeded in {result['response_time_ms']}ms")
```

### Webhook Management

```python
# List webhooks
webhooks = client.webhooks.list(status="active")

# Pause during maintenance
client.webhooks.pause(webhook_id)

# Resume
client.webhooks.resume(webhook_id)

# View delivery history for debugging
deliveries = client.webhooks.get_deliveries(webhook_id)
for d in deliveries["items"]:
    status = "✓" if d["status"] == "delivered" else "✗"
    print(f"{status} {d['event_type']}: {d['response_time_ms']}ms")

# Delete when done
client.webhooks.delete(webhook_id)
```

---

## Multi-Agent Coordination (Holds)

When multiple agents interact with the same simulation, race conditions can occur. For example:
- Agent A receives a webhook notification about a new email
- Agent A starts processing the email (calling LLM, deciding on response)
- Meanwhile, another process advances simulation time
- Events scheduled by Agent A may now be in the past

**Holds** solve this by allowing agents to temporarily block time advancement while they process events.

### Basic Hold Pattern

```python
from client import UESClient

def process_email_safely(client: UESClient, email_data: dict):
    """Process an email with hold protection."""
    
    # Acquire a hold before processing
    hold = client.simulation.hold(
        agent_id="email-processor",
        reason="Processing email from " + email_data.get("from", "unknown"),
        timeout_seconds=30.0,  # Auto-expires to prevent deadlocks
    )
    
    try:
        # Time is frozen for this simulation while we process
        # Other agents can still acquire their own holds
        
        # Do potentially slow operations
        response = call_llm_for_email_response(email_data)
        
        # Schedule our response
        client.email.send(
            from_address="user@example.com",
            to_addresses=[email_data["from"]],
            subject=f"Re: {email_data['subject']}",
            body_text=response,
        )
        
    finally:
        # ALWAYS release the hold when done
        client.simulation.release(hold.hold_id)
```

### Async Hold Pattern

```python
import asyncio
from client import AsyncUESClient

async def process_with_hold(client: AsyncUESClient):
    """Async pattern for hold-protected processing."""
    
    hold = await client.simulation.hold(
        agent_id="async-agent",
        reason="Async processing",
        timeout_seconds=60.0,
    )
    
    try:
        # Run multiple async operations while time is frozen
        results = await asyncio.gather(
            analyze_current_state(client),
            fetch_external_data(),
            compute_next_actions(),
        )
        
        # Apply computed actions
        for action in results[2]:
            await apply_action(client, action)
            
    finally:
        await client.simulation.release(hold.hold_id)
```

### WebSocket + Hold Integration

The most common pattern: react to WebSocket events with hold protection:

```python
import asyncio
from client import AsyncUESClient

async def reactive_agent_with_holds():
    """Agent that reacts to events with hold protection."""
    
    async with AsyncUESClient() as client:
        await client.simulation.start()
        
        async with client.subscribe(["email.received", "sms.received"]) as events:
            async for event in events:
                # Acquire hold immediately when we receive an event
                hold = await client.simulation.hold(
                    agent_id="reactive-agent",
                    reason=f"Processing {event.type}",
                    timeout_seconds=30.0,
                )
                
                try:
                    if event.type == "email.received":
                        await handle_email(client, event.data)
                    elif event.type == "sms.received":
                        await handle_sms(client, event.data)
                finally:
                    await client.simulation.release(hold.hold_id)

asyncio.run(reactive_agent_with_holds())
```

### Handling Blocked Time Operations

When holds are active, time operations return a `409 Conflict` error:

```python
from client import UESClient, ConflictError

def advance_time_with_retry(client: UESClient, seconds: int, max_retries: int = 5):
    """Advance time, waiting for holds to clear."""
    
    for attempt in range(max_retries):
        try:
            return client.time.advance(seconds=seconds)
        except ConflictError as e:
            # Extract hold info from the error
            holds = e.detail.get("active_holds", [])
            print(f"Blocked by {len(holds)} hold(s):")
            for h in holds:
                print(f"  - {h['agent_id']}: {h['reason']}")
            
            # Wait and retry
            time.sleep(1.0)
    
    raise RuntimeError("Could not advance time - holds persist")
```

### Monitoring Active Holds

```python
# List all currently active holds
holds = client.simulation.list_holds()
print(f"Active holds: {holds.active_count}")

for h in holds.holds:
    print(f"  Hold {h.hold_id}:")
    print(f"    Agent: {h.agent_id}")
    print(f"    Reason: {h.reason}")
    print(f"    Acquired: {h.acquired_at}")
    print(f"    Expires: {h.expires_at}")
```

### Hold WebSocket Events

Subscribe to hold events for monitoring:

```python
async with client.subscribe(["hold."]) as events:
    async for event in events:
        if event.type == "hold.acquired":
            print(f"Hold acquired: {event.data['agent_id']} - {event.data['reason']}")
        elif event.type == "hold.released":
            print(f"Hold released: {event.data['hold_id']}")
        elif event.type == "hold.expired":
            print(f"Hold EXPIRED: {event.data['agent_id']} - {event.data['reason']}")
            # Log warning - agent may have crashed without releasing
```

### Best Practices for Holds

1. **Always use try/finally**: Ensure holds are released even on exceptions
2. **Set reasonable timeouts**: Default is 30s, max is 300s. Don't set too high.
3. **Use descriptive reasons**: Helps debugging when holds block operations
4. **Include agent_id**: Makes it easy to identify which agent holds are from
5. **Monitor for expired holds**: May indicate crashed agents
6. **Don't hold during long waits**: Release before external API calls if possible

---

## Example Agent Patterns

### Pattern 1: Polling-Based Agent

Simple agent that polls for changes and reacts:

```python
import time
from client import UESClient

class PollingAgent:
    def __init__(self, client: UESClient, poll_interval: float = 1.0):
        self.client = client
        self.poll_interval = poll_interval
        self.seen_emails = set()
    
    def run(self):
        """Main loop: poll and react."""
        while True:
            self.check_emails()
            time.sleep(self.poll_interval)
    
    def check_emails(self):
        """Check for new unread emails and process them."""
        emails = self.client.email.query(folder="inbox", is_read=False)
        
        for email in emails.emails:
            if email.message_id not in self.seen_emails:
                self.seen_emails.add(email.message_id)
                self.process_email(email)
    
    def process_email(self, email):
        """Process a new email (override in subclass)."""
        print(f"New email from {email.from_address}: {email.subject}")

# Usage
with UESClient() as client:
    client.simulation.start()
    agent = PollingAgent(client)
    agent.run()
```

### Pattern 2: WebSocket-Based Reactive Agent

Real-time agent using WebSocket subscriptions:

```python
import asyncio
from client import AsyncUESClient

async def reactive_email_agent():
    """Agent that reacts to emails in real-time."""
    async with AsyncUESClient() as client:
        await client.simulation.start()
        
        async with client.subscribe(["email.received"]) as events:
            async for event in events:
                email_data = event.data
                subject = email_data.get("subject", "")
                sender = email_data.get("from", "")
                
                # Example: Auto-reply to urgent emails
                if "urgent" in subject.lower():
                    await client.email.send(
                        from_address="user@example.com",
                        to_addresses=[sender],
                        subject=f"Re: {subject}",
                        body_text="Thanks for the urgent email. I'll respond shortly.",
                    )
                    print(f"Auto-replied to urgent email from {sender}")

asyncio.run(reactive_email_agent())
```

### Pattern 3: LLM-Powered Content Generator

Agent that uses LLMs to generate realistic simulation content:

```python
from datetime import timedelta
from client import UESClient
from openai import OpenAI

class ContentGeneratorAgent:
    def __init__(self, ues_client: UESClient, llm_client: OpenAI):
        self.ues = ues_client
        self.llm = llm_client
        self.characters = {
            "boss": {
                "name": "Sarah Chen",
                "email": "sarah.chen@company.com",
                "personality": "Professional, direct, values efficiency",
            },
            "friend": {
                "name": "Mike Johnson",
                "email": "mike.j@email.com",
                "personality": "Casual, uses emojis, friendly",
            },
        }
    
    def generate_email_from_character(self, character_key: str, topic: str) -> dict:
        """Generate realistic email content using LLM."""
        char = self.characters[character_key]
        
        # Get current context
        context = self.ues.environment.get_state(compact=True, format="text")
        
        response = self.llm.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": f"""Generate a realistic email from {char['name']}.
Personality: {char['personality']}
Current simulation context:
{context}

Respond with JSON: {{"subject": "...", "body": "..."}}"""
                },
                {"role": "user", "content": f"Write an email about: {topic}"}
            ]
        )
        
        import json
        content = json.loads(response.choices[0].message.content)
        return {
            "from_address": char["email"],
            "subject": content["subject"],
            "body_text": content["body"],
        }
    
    def schedule_character_email(self, character_key: str, topic: str, delay_minutes: int = 15):
        """Generate and schedule an email from a character."""
        content = self.generate_email_from_character(character_key, topic)
        
        current_time = self.ues.time.get_state().current_time
        scheduled_time = current_time + timedelta(minutes=delay_minutes)
        
        self.ues.events.create(
            modality="email",
            action="receive",
            data={
                "from_address": content["from_address"],
                "to_addresses": ["user@example.com"],
                "subject": content["subject"],
                "body_text": content["body_text"],
            },
            scheduled_time=scheduled_time,
        )
        print(f"Scheduled email from {character_key} for {scheduled_time}")

# Usage
with UESClient() as ues:
    llm = OpenAI()
    agent = ContentGeneratorAgent(ues, llm)
    
    ues.simulation.start()
    
    # Generate and schedule emails from characters
    agent.schedule_character_email("boss", "project deadline update", delay_minutes=10)
    agent.schedule_character_email("friend", "weekend plans", delay_minutes=30)
```

### Pattern 4: Trigger-Based Agent

Agent that monitors conditions and triggers actions:

```python
from datetime import datetime
from client import UESClient

class TriggerAgent:
    def __init__(self, client: UESClient):
        self.client = client
        self.triggers = []
    
    def add_trigger(self, condition_fn, action_fn):
        """Add a trigger: when condition is true, run action."""
        self.triggers.append((condition_fn, action_fn))
    
    def check_triggers(self):
        """Evaluate all triggers against current state."""
        # Get current state
        snapshot = self.client.environment.get_state(compact=True)
        
        for condition_fn, action_fn in self.triggers:
            if condition_fn(snapshot):
                action_fn(self.client, snapshot)

# Example: Send reminder if meeting is soon and user is not at office
def meeting_soon_not_at_office(snapshot):
    """Check if user has meeting soon but isn't at office."""
    calendar = snapshot.modalities.get("calendar", {})
    location = snapshot.modalities.get("location", {})
    
    next_event = calendar.get("next_event")
    current_loc = location.get("current", {}).get("named_location", "")
    
    if next_event and current_loc != "Office":
        # Meeting within 30 minutes
        return True
    return False

def send_location_reminder(client, snapshot):
    """Send SMS reminder about location."""
    client.sms.send(
        recipient="+1234567890",
        content="Reminder: You have a meeting soon. Are you heading to the office?",
    )

# Usage
with UESClient() as client:
    client.simulation.start()
    
    agent = TriggerAgent(client)
    agent.add_trigger(meeting_soon_not_at_office, send_location_reminder)
    
    # Run periodically
    while True:
        agent.check_triggers()
        time.sleep(60)  # Check every minute
```

### Pattern 5: AI Assistant Under Test

Structure for testing an AI personal assistant:

```python
import asyncio
from client import AsyncUESClient

class AIAssistantTestHarness:
    def __init__(self, assistant_fn):
        """
        Args:
            assistant_fn: Function that takes context and returns action
        """
        self.assistant = assistant_fn
    
    async def run_test(self, scenario_file: str):
        """Run assistant against a scenario."""
        async with AsyncUESClient() as client:
            # Load test scenario
            with open(scenario_file) as f:
                scenario = json.load(f)
            
            await client.scenario.import_full(scenario)
            await client.simulation.start()
            
            # Subscribe to events that should trigger assistant
            async with client.subscribe(["email.received", "sms.received", "chat.message"]) as events:
                async for event in events:
                    # Get current context for assistant
                    context = await client.environment.get_state(compact=True, format="text")
                    
                    # Let assistant decide what to do
                    action = self.assistant(context, event)
                    
                    if action:
                        await self.execute_action(client, action)
    
    async def execute_action(self, client, action):
        """Execute an action decided by the assistant."""
        if action["type"] == "send_email":
            await client.email.send(**action["params"])
        elif action["type"] == "send_sms":
            await client.sms.send(**action["params"])
        elif action["type"] == "create_calendar_event":
            await client.calendar.create(**action["params"])
        # ... handle other actions

# Example assistant function
def my_assistant(context: str, event: dict) -> dict | None:
    """Simple assistant that replies to emails with 'help' in subject."""
    if event["type"] == "email.received":
        subject = event["data"].get("subject", "").lower()
        if "help" in subject:
            return {
                "type": "send_email",
                "params": {
                    "from_address": "user@example.com",
                    "to_addresses": [event["data"]["from"]],
                    "subject": f"Re: {event['data']['subject']}",
                    "body_text": "How can I help you?",
                }
            }
    return None

# Run test
harness = AIAssistantTestHarness(my_assistant)
asyncio.run(harness.run_test("test_scenario.json"))
```

---

## Best Practices

### 1. Use Context Managers

Always use context managers for proper resource cleanup:

```python
# ✓ Good
with UESClient() as client:
    client.email.send(...)

# ✗ Avoid (requires manual cleanup)
client = UESClient()
try:
    client.email.send(...)
finally:
    client.close()
```

### 2. Use Compact Snapshots for LLM Context

Don't dump full state into LLM prompts:

```python
# ✓ Good - optimized for LLM context
context = client.environment.get_state(compact=True, format="text")

# ✗ Avoid - wastes tokens, may exceed context limit
full_state = client.environment.get_state()  # 50KB+
```

### 3. Use Batch Operations for Multiple Events

```python
# ✓ Good - single API call
client.events.create_batch([event1, event2, event3])

# ✗ Avoid - 3 separate API calls
client.events.create(event1)
client.events.create(event2)
client.events.create(event3)
```

### 4. Handle Errors Specifically

```python
# ✓ Good - specific error handling
try:
    client.events.get(event_id=event_id)
except NotFoundError:
    print("Event not found")
except ValidationError as e:
    print(f"Invalid request: {e.detail}")

# ✗ Avoid - swallowing all errors
try:
    client.events.get(event_id=event_id)
except Exception:
    pass
```

### 5. Use Async for Concurrent Operations

```python
# ✓ Good - concurrent operations
async with AsyncUESClient() as client:
    results = await asyncio.gather(
        client.email.query(folder="inbox"),
        client.sms.query(is_read=False),
        client.calendar.query(start=today),
    )

# ✗ Slower - sequential operations
state1 = client.email.get_state()
state2 = client.sms.get_state()
state3 = client.calendar.get_state()
```

### 6. Implement Reconnection for WebSockets

```python
async def robust_subscription():
    """WebSocket subscription with reconnection."""
    retry_delay = 1
    max_delay = 60
    
    while True:
        try:
            async with AsyncUESClient() as client:
                async with client.subscribe(["email."]) as events:
                    retry_delay = 1  # Reset on success
                    async for event in events:
                        process_event(event)
        except ConnectionError:
            print(f"Connection lost. Reconnecting in {retry_delay}s...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, max_delay)
```

### 7. Export Scenarios for Reproducibility

After interactive testing, capture the scenario for replay:

```python
# After a good test session, export for future use
scenario = client.scenario.export_full(
    author="Test Session",
    description="Interactive test that found bug #123"
)

with open("bug_123_repro.ues-scenario.json", "w") as f:
    f.write(json.dumps(scenario, indent=2))

# Now this scenario can be replayed deterministically
```

### 8. Use Query Filters Instead of Full State

```python
# ✓ Good - fetch only what you need
unread = client.email.query(folder="inbox", is_read=False, limit=10)

# ✗ Avoid - fetching everything then filtering
all_emails = client.email.get_state()
unread = [e for e in all_emails.emails.values() if not e.is_read][:10]
```

---

## See Also

- [API_CLIENT.md](API_CLIENT.md) - Complete Python client documentation
- [REST_API.md](REST_API.md) - Full REST API reference
- [WEBSOCKET.md](WEBSOCKET.md) - WebSocket API details
- [WEBHOOKS.md](WEBHOOKS.md) - Webhook integration guide
- [SCENARIOS.md](SCENARIOS.md) - Scenario concepts and design patterns
- [EVENT_GENERATION_AGENT.md](simulation_agents/EVENT_GENERATION_AGENT.md) - Content generation agent patterns
- [guides/QUICKSTART.md](guides/QUICKSTART.md) - Getting started guide
