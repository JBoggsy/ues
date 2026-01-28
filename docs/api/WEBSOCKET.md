# WebSocket API Documentation

This document describes the WebSocket API for real-time event notifications in UES.

## Overview

UES provides a WebSocket endpoint for receiving real-time notifications when simulation state changes. This is more efficient than polling REST endpoints and enables reactive updates in client applications.

**WebSocket URL:** `ws://localhost:8000/ws`

### When to Use WebSocket vs REST

| Use Case | Recommended Approach |
|----------|---------------------|
| Real-time updates | WebSocket |
| Initial data load | REST API |
| Infrequent queries | REST API |
| Dashboard sync | WebSocket for invalidation, REST for data |
| Testing/debugging | REST API (simpler) |

## Connecting

### Python Client

Using the built-in client library:

```python
from client import AsyncUESClient

async with AsyncUESClient() as client:
    # Subscribe to time and email events
    async with client.subscribe(["time.", "email."]) as events:
        async for event in events:
            print(f"Event: {event.type}")
            print(f"Data: {event.data}")
            print(f"Time: {event.timestamp}")
```

Using websockets directly:

```python
import asyncio
import websockets
import json

async def listen():
    async with websockets.connect("ws://localhost:8000/ws") as ws:
        # Optional: subscribe to specific events
        await ws.send(json.dumps({
            "action": "subscribe",
            "events": ["time.", "email."]
        }))
        
        # Wait for confirmation
        confirmation = await ws.recv()
        print(f"Subscribed: {confirmation}")
        
        # Listen for events
        async for message in ws:
            event = json.loads(message)
            print(f"Event: {event['type']}, Data: {event['data']}")

asyncio.run(listen())
```

### JavaScript/Browser

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
    console.log('Connected');
    
    // Optional: subscribe to specific events
    ws.send(JSON.stringify({
        action: 'subscribe',
        events: ['time.', 'email.']
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Event:', data.type, data.data);
};

ws.onclose = () => {
    console.log('Disconnected');
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};
```

### React Hook

```typescript
import { useWebSocket, useWebSocketEvent } from '@/api';

// In your app root - connects and sets up auto-invalidation
function App() {
    useWebSocket();
    return <YourApp />;
}

// In a component - subscribe to specific events
function EmailNotification() {
    const [count, setCount] = useState(0);
    
    useWebSocketEvent('email.received', (event) => {
        setCount(c => c + 1);
        console.log('New email!', event.data);
    });
    
    return <Badge count={count} />;
}
```

## Event Types Reference

### Simulation Lifecycle

| Event Type | Trigger | Data Fields |
|------------|---------|-------------|
| `simulation.started` | POST /simulation/start | `simulation_id`, `current_time`, `mode` |
| `simulation.stopped` | POST /simulation/stop | `simulation_id`, `stop_time` |
| `simulation.reset` | POST /simulation/reset | `simulation_id` |
| `simulation.cleared` | POST /simulation/clear | `simulation_id` |

### Holds (Multi-Agent Coordination)

| Event Type | Trigger | Data Fields |
|------------|---------|-------------|
| `hold.acquired` | POST /simulation/hold | `hold_id`, `agent_id`, `reason`, `timeout_seconds`, `expires_at` |
| `hold.released` | POST /simulation/release/{hold_id} | `hold_id`, `agent_id`, `reason` |
| `hold.expired` | Automatic timeout | `hold_id`, `agent_id`, `reason` |

### Time Control

| Event Type | Trigger | Data Fields |
|------------|---------|-------------|
| `time.advanced` | POST /simulator/time/advance | `current_time`, `previous_time`, `delta_seconds`, `events_executed` |
| `time.set` | POST /simulator/time/set | `current_time`, `previous_time` |
| `time.skipped` | POST /simulator/time/skip-to-next | `current_time`, `previous_time`, `events_executed` |
| `time.paused` | POST /simulator/time/pause | `current_time` |
| `time.resumed` | POST /simulator/time/resume | `current_time` |
| `time.scale_changed` | POST /simulator/time/set-scale | `time_scale`, `previous_scale` |

### Event Queue

| Event Type | Trigger | Data Fields |
|------------|---------|-------------|
| `event.scheduled` | POST /events/create, POST /events/immediate | `event_id`, `modality`, `scheduled_time` |
| `event.executed` | Event execution callback | `event_id`, `modality`, `status`, `scheduled_time`, `executed_time` |
| `event.failed` | Event execution failure | `event_id`, `modality`, `status`, `scheduled_time`, `executed_time` |
| `event.cancelled` | POST /events/{id}/cancel | `event_id`, `modality` |

### Email

| Event Type | Trigger | Data Fields |
|------------|---------|-------------|
| `email.received` | POST /email/receive | `event_id`, `from`, `subject` |
| `email.sent` | POST /email/send | `event_id`, `to`, `subject` |

### SMS/RCS

| Event Type | Trigger | Data Fields |
|------------|---------|-------------|
| `sms.received` | POST /sms/receive | `event_id`, `from_number`, `preview` |
| `sms.sent` | POST /sms/send | `event_id`, `to_number`, `preview` |

### Chat

| Event Type | Trigger | Data Fields |
|------------|---------|-------------|
| `chat.message` | POST /chat/send | `event_id`, `conversation_id`, `role`, `preview` |

### Calendar

| Event Type | Trigger | Data Fields |
|------------|---------|-------------|
| `calendar.event_created` | POST /calendar/create | `event_id`, `calendar_event_id`, `title`, `start_time` |
| `calendar.event_updated` | PUT /calendar/{id} | `event_id`, `calendar_event_id`, `title` |
| `calendar.event_deleted` | DELETE /calendar/{id} | `calendar_event_id` |

### Location

| Event Type | Trigger | Data Fields |
|------------|---------|-------------|
| `location.updated` | POST /location/update | `event_id`, `latitude`, `longitude`, `address` |

### Weather

| Event Type | Trigger | Data Fields |
|------------|---------|-------------|
| `weather.updated` | POST /weather/update | `event_id`, `latitude`, `longitude` |

### Undo/Redo

| Event Type | Trigger | Data Fields |
|------------|---------|-------------|
| `undo.performed` | POST /simulation/undo | `event_id`, `modality` |
| `redo.performed` | POST /simulation/redo | `event_id`, `modality` |

### Subscription

| Event Type | Trigger | Data Fields |
|------------|---------|-------------|
| `subscription.updated` | Client subscribe message | `filters` |

## Subscription Filtering

By default, clients receive all events. You can filter events by sending a subscription message.

### Subscribe Message Format

```json
{
    "action": "subscribe",
    "events": ["time.", "email.received"]
}
```

### Filter Patterns

| Pattern | Matches |
|---------|---------|
| `"time."` | All time events (time.advanced, time.set, etc.) |
| `"email."` | All email events (email.sent, email.received) |
| `"simulation."` | All simulation lifecycle events |
| `"time.advanced"` | Only time.advanced (exact match) |
| `null` or omitted | All events (no filter) |

### Updating Subscription

Send a new subscribe message to change filters. The previous filter is replaced.

```json
{"action": "subscribe", "events": ["calendar.", "location."]}
```

## Message Format

### Event (Server → Client)

```json
{
    "type": "time.advanced",
    "data": {
        "current_time": "2024-01-01T12:00:00Z",
        "previous_time": "2024-01-01T11:00:00Z",
        "delta_seconds": 3600,
        "events_executed": 5
    },
    "timestamp": "2024-01-01T12:00:00.123Z"
}
```

### Subscription Confirmation (Server → Client)

```json
{
    "type": "subscription.updated",
    "data": {
        "filters": ["time.", "email."]
    },
    "timestamp": "2024-01-01T12:00:00.123Z"
}
```

### Subscribe (Client → Server)

```json
{
    "action": "subscribe",
    "events": ["time.", "email."]
}
```

### Ping/Pong (Client ↔ Server)

```json
{"action": "ping"}
{"action": "pong"}
```

## Best Practices

### Handling Reconnection

WebSocket connections can drop. Implement reconnection with exponential backoff:

```python
import asyncio
import websockets

async def connect_with_retry():
    retry_delay = 1
    max_delay = 60
    
    while True:
        try:
            async with websockets.connect("ws://localhost:8000/ws") as ws:
                retry_delay = 1  # Reset on successful connection
                async for message in ws:
                    process_message(message)
        except websockets.ConnectionClosed:
            print(f"Connection lost. Reconnecting in {retry_delay}s...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, max_delay)
```

### Efficient Query Invalidation

Use WebSocket for cache invalidation, not data fetching:

```typescript
// React Query + WebSocket pattern
function useTimeWithWebSocket() {
    const queryClient = useQueryClient();
    
    // Use React Query for data fetching
    const query = useQuery({
        queryKey: ['time'],
        queryFn: fetchTimeState,
    });
    
    // Use WebSocket to invalidate cache
    useWebSocketEvent('time.', () => {
        queryClient.invalidateQueries({ queryKey: ['time'] });
    });
    
    return query;
}
```

### Error Handling

Always handle connection errors gracefully:

```python
try:
    async with client.subscribe(["time."]) as events:
        async for event in events:
            handle_event(event)
except ConnectionError as e:
    logger.error(f"WebSocket connection failed: {e}")
    # Fall back to polling or show user message
```

## Examples

### Real-time Dashboard

```typescript
function Dashboard() {
    const [events, setEvents] = useState<WSEvent[]>([]);
    
    useWebSocketEvent('*', (event) => {
        setEvents(prev => [event, ...prev].slice(0, 100));
    });
    
    return (
        <div>
            <h2>Event Stream</h2>
            <ul>
                {events.map((e, i) => (
                    <li key={i}>
                        <code>{e.type}</code>: {JSON.stringify(e.data)}
                    </li>
                ))}
            </ul>
        </div>
    );
}
```

### Email Notification Agent

```python
async def email_notification_agent():
    """Agent that reacts to new emails in real-time."""
    async with AsyncUESClient() as client:
        async with client.subscribe(["email.received"]) as events:
            async for event in events:
                subject = event.data.get("subject", "")
                sender = event.data.get("from", "")
                
                if "urgent" in subject.lower():
                    await notify_user(f"Urgent email from {sender}: {subject}")
```

## Troubleshooting

### No Events Received

1. Ensure simulation is started (`POST /simulation/start`)
2. Check subscription filter isn't too restrictive
3. Verify WebSocket connection is open

### Connection Keeps Dropping

1. Check network stability
2. Send periodic ping messages to keep connection alive
3. Implement reconnection logic

### Events Delayed

1. Check server load
2. Reduce subscription filter scope
3. Consider using dedicated event streams for high-frequency updates
