# WebSocket Implementation Plan for UES

## Overview

This document outlines the step-by-step implementation plan for adding WebSocket support to UES. The goal is to provide real-time push notifications for state changes, complementing (not replacing) the existing REST API.

## Design Goals

1. **Non-breaking**: WebSocket is optional; all existing REST functionality continues to work
2. **Simple client requirements**: Clients can use `websockets` (Python) or native browser WebSocket
3. **Efficient**: Eliminate polling overhead for clients that want real-time updates
4. **Comprehensive**: Notify on all significant state changes
5. **Testable**: WebSocket connections are testable with pytest

## Event Types to Broadcast

### Simulation Lifecycle Events
| Event Type | Trigger | Payload |
|------------|---------|---------|
| `simulation.started` | `/simulation/start` | `{simulation_id, mode, current_time}` |
| `simulation.stopped` | `/simulation/stop` | `{simulation_id, final_time, events_executed}` |
| `simulation.reset` | `/simulation/reset` | `{events_undone, events_reset}` |
| `simulation.cleared` | `/simulation/clear` | `{events_removed, modalities_cleared}` |

### Time Events
| Event Type | Trigger | Payload |
|------------|---------|---------|
| `time.advanced` | `/simulator/time/advance` | `{current_time, previous_time, delta}` |
| `time.set` | `/simulator/time/set` | `{current_time, previous_time}` |
| `time.skipped` | `/simulator/time/skip-to-next` | `{current_time, events_executed}` |
| `time.paused` | `/simulator/time/pause` | `{current_time}` |
| `time.resumed` | `/simulator/time/resume` | `{current_time}` |
| `time.scale_changed` | `/simulator/time/set-scale` | `{time_scale}` |

### Event Queue Events
| Event Type | Trigger | Payload |
|------------|---------|---------|
| `event.scheduled` | `POST /events` | `{event_id, modality, scheduled_time}` |
| `event.executed` | Event execution | `{event_id, modality, status, executed_at}` |
| `event.failed` | Event failure | `{event_id, modality, error}` |
| `event.cancelled` | `DELETE /events/{id}` | `{event_id}` |

### Modality State Events
| Event Type | Trigger | Payload |
|------------|---------|---------|
| `modality.updated` | Any modality submit | `{modality, action, summary}` |
| `email.received` | Email receive action | `{email_id, from, subject}` |
| `email.sent` | Email send action | `{email_id, to, subject}` |
| `sms.received` | SMS receive action | `{message_id, from, preview}` |
| `sms.sent` | SMS send action | `{message_id, to, preview}` |
| `chat.message` | Chat send action | `{conversation_id, role, preview}` |
| `calendar.event_created` | Calendar create | `{event_id, title, start_time}` |
| `calendar.event_updated` | Calendar update | `{event_id, title}` |
| `calendar.event_deleted` | Calendar delete | `{event_id}` |
| `location.updated` | Location update | `{latitude, longitude, address}` |
| `weather.updated` | Weather update | `{location, conditions}` |

### Undo/Redo Events
| Event Type | Trigger | Payload |
|------------|---------|---------|
| `undo.performed` | `/simulation/undo` | `{undone_count, can_undo, can_redo}` |
| `redo.performed` | `/simulation/redo` | `{redone_count, can_undo, can_redo}` |

---

## Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI App                             │
│  ┌─────────────────┐   ┌──────────────────┐   ┌──────────────┐ │
│  │  REST Routes    │   │  WebSocket Route │   │ Broadcaster  │ │
│  │  (existing)     │   │  /ws             │   │              │ │
│  │                 │   │                  │   │  - subscribe │ │
│  │  POST /sim/... ─┼───┼─── broadcast ────┼──→│  - broadcast │ │
│  │  POST /email/.. │   │                  │   │  - clients   │ │
│  └─────────────────┘   └──────────────────┘   └──────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  │ WebSocket connections
                                  ▼
              ┌─────────────────────────────────────────┐
              │              Clients                     │
              │  ┌─────────┐ ┌─────────┐ ┌───────────┐  │
              │  │ Web UI  │ │ Python  │ │ AI Agent  │  │
              │  │(browser)│ │ Script  │ │           │  │
              │  └─────────┘ └─────────┘ └───────────┘  │
              └─────────────────────────────────────────┘
```

### Key Components

1. **ConnectionManager** (`api/websocket.py`)
   - Manages active WebSocket connections
   - Handles connect/disconnect lifecycle
   - Supports subscription filtering (by event type/modality)
   - Thread-safe client list

2. **Event Broadcaster** (integrated into ConnectionManager)
   - Broadcasts events to all connected clients
   - Serializes event data to JSON

3. **WebSocket Route** (`api/routes/websocket.py`)
   - Single endpoint: `ws://localhost:8000/ws`
   - Handles connection handshake
   - Processes subscription messages from clients
   - Keeps connection alive with ping/pong

4. **Integration Points** (existing routes)
   - Each route that modifies state calls `broadcast()`
   - Minimal code changes - just add broadcast calls

---

## Implementation Phases

### Phase 1: Core WebSocket Infrastructure

**Files to create:**
- `api/websocket.py` - ConnectionManager and event broadcasting

**Files to modify:**
- `main.py` - Register WebSocket route
- `pyproject.toml` - Add `websockets` dependency (for testing)

#### `api/websocket.py`

```python
"""WebSocket connection management and event broadcasting.

This module provides infrastructure for real-time push notifications
to connected clients. It manages WebSocket connections and broadcasts
simulation events.
"""

import asyncio
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class WSEventType(str, Enum):
    """WebSocket event types that can be broadcast."""
    
    # Simulation lifecycle
    SIMULATION_STARTED = "simulation.started"
    SIMULATION_STOPPED = "simulation.stopped"
    SIMULATION_RESET = "simulation.reset"
    SIMULATION_CLEARED = "simulation.cleared"
    
    # Time control
    TIME_ADVANCED = "time.advanced"
    TIME_SET = "time.set"
    TIME_SKIPPED = "time.skipped"
    TIME_PAUSED = "time.paused"
    TIME_RESUMED = "time.resumed"
    TIME_SCALE_CHANGED = "time.scale_changed"
    
    # Event queue
    EVENT_SCHEDULED = "event.scheduled"
    EVENT_EXECUTED = "event.executed"
    EVENT_FAILED = "event.failed"
    EVENT_CANCELLED = "event.cancelled"
    
    # Modality updates (generic and specific)
    MODALITY_UPDATED = "modality.updated"
    EMAIL_RECEIVED = "email.received"
    EMAIL_SENT = "email.sent"
    SMS_RECEIVED = "sms.received"
    SMS_SENT = "sms.sent"
    CHAT_MESSAGE = "chat.message"
    CALENDAR_EVENT_CREATED = "calendar.event_created"
    CALENDAR_EVENT_UPDATED = "calendar.event_updated"
    CALENDAR_EVENT_DELETED = "calendar.event_deleted"
    LOCATION_UPDATED = "location.updated"
    WEATHER_UPDATED = "weather.updated"
    
    # Undo/Redo
    UNDO_PERFORMED = "undo.performed"
    REDO_PERFORMED = "redo.performed"


class WSEvent(BaseModel):
    """A WebSocket event to broadcast."""
    
    type: WSEventType
    data: dict[str, Any]
    timestamp: str  # ISO format
    
    @classmethod
    def create(cls, event_type: WSEventType, data: dict[str, Any]) -> "WSEvent":
        """Create a new event with current timestamp."""
        return cls(
            type=event_type,
            data=data,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )


class ConnectionManager:
    """Manages WebSocket connections and broadcasts events.
    
    Thread-safe manager for multiple concurrent WebSocket connections.
    Supports optional subscription filtering so clients can receive
    only the event types they care about.
    
    Usage:
        manager = ConnectionManager()
        
        # In WebSocket route:
        await manager.connect(websocket)
        try:
            while True:
                data = await websocket.receive_text()
                # Handle subscription messages
        except WebSocketDisconnect:
            manager.disconnect(websocket)
        
        # In REST routes:
        await manager.broadcast(WSEventType.TIME_ADVANCED, {"current_time": "..."})
    """
    
    def __init__(self):
        """Initialize the connection manager."""
        self._connections: Set[WebSocket] = set()
        self._subscriptions: dict[WebSocket, Optional[Set[str]]] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection.
        
        Args:
            websocket: The WebSocket connection to accept.
        """
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
            self._subscriptions[websocket] = None  # None = all events
        logger.info(f"WebSocket client connected. Total: {len(self._connections)}")
    
    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection.
        
        Args:
            websocket: The WebSocket connection to remove.
        """
        async with self._lock:
            self._connections.discard(websocket)
            self._subscriptions.pop(websocket, None)
        logger.info(f"WebSocket client disconnected. Total: {len(self._connections)}")
    
    async def subscribe(
        self, 
        websocket: WebSocket, 
        event_types: Optional[list[str]] = None
    ) -> None:
        """Update subscription filter for a connection.
        
        Args:
            websocket: The WebSocket connection.
            event_types: List of event type prefixes to receive.
                        None means all events.
                        Examples: ["time.", "email."] or ["simulation.started"]
        """
        async with self._lock:
            if event_types is None:
                self._subscriptions[websocket] = None
            else:
                self._subscriptions[websocket] = set(event_types)
    
    def _should_send(self, websocket: WebSocket, event_type: str) -> bool:
        """Check if an event should be sent to a connection.
        
        Args:
            websocket: The connection to check.
            event_type: The event type being broadcast.
        
        Returns:
            True if the event matches the connection's subscription.
        """
        filters = self._subscriptions.get(websocket)
        if filters is None:
            return True  # No filter = receive all
        
        # Check if event type matches any filter
        for filter_prefix in filters:
            if event_type.startswith(filter_prefix) or event_type == filter_prefix:
                return True
        return False
    
    async def broadcast(
        self, 
        event_type: WSEventType, 
        data: dict[str, Any]
    ) -> int:
        """Broadcast an event to all subscribed connections.
        
        Args:
            event_type: The type of event.
            data: Event payload data.
        
        Returns:
            Number of clients that received the event.
        """
        if not self._connections:
            return 0
        
        event = WSEvent.create(event_type, data)
        message = event.model_dump_json()
        
        sent_count = 0
        dead_connections = []
        
        async with self._lock:
            for websocket in self._connections:
                if not self._should_send(websocket, event_type.value):
                    continue
                
                try:
                    await websocket.send_text(message)
                    sent_count += 1
                except Exception as e:
                    logger.warning(f"Failed to send to WebSocket: {e}")
                    dead_connections.append(websocket)
        
        # Clean up dead connections
        for ws in dead_connections:
            await self.disconnect(ws)
        
        if sent_count > 0:
            logger.debug(f"Broadcast {event_type.value} to {sent_count} clients")
        
        return sent_count
    
    @property
    def connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self._connections)


# Global connection manager instance
ws_manager = ConnectionManager()
```

#### Changes to `main.py`

Add after the router imports:
```python
from api.routes import websocket as websocket_routes
```

Add after the router registrations:
```python
app.include_router(websocket_routes.router)
```

### Phase 2: WebSocket Route Handler

**Files to create:**
- `api/routes/websocket.py` - WebSocket endpoint

```python
"""WebSocket endpoint for real-time event notifications.

Clients connect to /ws and receive JSON events for simulation state changes.
Optionally, clients can send subscription messages to filter events.

Example client (Python):
    import asyncio
    import websockets
    import json

    async def listen():
        async with websockets.connect("ws://localhost:8000/ws") as ws:
            # Optional: subscribe to specific events
            await ws.send(json.dumps({
                "action": "subscribe",
                "events": ["time.", "email."]  # Prefixes
            }))
            
            async for message in ws:
                event = json.loads(message)
                print(f"Event: {event['type']}, Data: {event['data']}")

    asyncio.run(listen())

Example client (JavaScript):
    const ws = new WebSocket('ws://localhost:8000/ws');
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Event:', data.type, data.data);
    };
    
    // Optional subscription
    ws.send(JSON.stringify({
        action: 'subscribe',
        events: ['time.', 'email.']
    }));
"""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.websocket import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time event notifications.
    
    Connects and listens for events. Clients can optionally send
    subscription messages to filter which events they receive.
    
    Subscription message format:
        {
            "action": "subscribe",
            "events": ["time.", "email.received", "simulation."]
        }
    
    Events are broadcast as JSON:
        {
            "type": "time.advanced",
            "data": {"current_time": "2024-01-01T12:00:00Z", ...},
            "timestamp": "2024-01-01T12:00:00.123Z"
        }
    """
    await ws_manager.connect(websocket)
    
    try:
        while True:
            # Wait for messages from client (subscriptions, ping, etc.)
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                action = message.get("action")
                
                if action == "subscribe":
                    # Update subscription filter
                    events = message.get("events")  # None = all events
                    await ws_manager.subscribe(websocket, events)
                    await websocket.send_text(json.dumps({
                        "type": "subscription.updated",
                        "data": {"events": events or "all"}
                    }))
                
                elif action == "ping":
                    # Respond to ping (keepalive)
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "data": {}
                    }))
                    
            except json.JSONDecodeError:
                # Ignore malformed messages
                logger.debug(f"Received non-JSON WebSocket message: {data[:50]}")
                
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
```

### Phase 3: Integrate Broadcasting into Existing Routes

**Files to modify:**
- `api/routes/simulation.py` - Broadcast simulation lifecycle events
- `api/routes/time.py` - Broadcast time control events
- `api/routes/events.py` - Broadcast event queue changes
- `api/routes/email.py` - Broadcast email events
- `api/routes/sms.py` - Broadcast SMS events
- `api/routes/chat.py` - Broadcast chat events
- `api/routes/calendar.py` - Broadcast calendar events
- `api/routes/location.py` - Broadcast location events
- `api/routes/weather.py` - Broadcast weather events

#### Pattern for Integration

Each route file needs minimal changes. Example for `simulation.py`:

```python
# Add import at top
from api.websocket import ws_manager, WSEventType

# At end of start_simulation():
await ws_manager.broadcast(WSEventType.SIMULATION_STARTED, {
    "simulation_id": result["simulation_id"],
    "mode": result.get("mode"),
    "current_time": result["current_time"],
})

# At end of stop_simulation():
await ws_manager.broadcast(WSEventType.SIMULATION_STOPPED, {
    "simulation_id": result["simulation_id"],
    "final_time": result.get("final_time"),
    "events_executed": result.get("events_executed"),
})

# Similar for reset, clear, undo, redo...
```

#### Integration Points Summary

| File | Endpoints | Broadcast Events |
|------|-----------|------------------|
| `simulation.py` | `start`, `stop`, `reset`, `clear`, `undo`, `redo` | `simulation.*`, `undo.*`, `redo.*` |
| `time.py` | `advance`, `set`, `skip-to-next`, `pause`, `resume`, `set-scale` | `time.*` |
| `events.py` | `POST /events`, `DELETE /events/{id}` | `event.scheduled`, `event.cancelled` |
| `email.py` | All submit actions | `email.*`, `modality.updated` |
| `sms.py` | All submit actions | `sms.*`, `modality.updated` |
| `chat.py` | All submit actions | `chat.*`, `modality.updated` |
| `calendar.py` | All submit actions | `calendar.*`, `modality.updated` |
| `location.py` | Submit action | `location.*`, `modality.updated` |
| `weather.py` | Submit action | `weather.*`, `modality.updated` |

### Phase 4: Event Execution Broadcasting

**Files to modify:**
- `models/simulation.py` - Add callback hook for event execution

The `execute_due_events()` method needs to notify when events are executed. Options:

**Option A: Callback Pattern** (recommended)
Add an optional callback to SimulationEngine that routes can register:

```python
# In SimulationEngine
self._event_executed_callback: Optional[Callable] = None

def set_event_callback(self, callback: Callable[[SimulatorEvent], None]) -> None:
    """Set callback for event execution notifications."""
    self._event_executed_callback = callback

# In execute_due_events():
if self._event_executed_callback:
    self._event_executed_callback(event)
```

**Option B: After-the-fact Broadcasting**
Routes that trigger event execution can broadcast based on the returned list.

### Phase 5: Python Client WebSocket Support

**Files to create:**
- `client/_websocket.py` - WebSocket client for Python library

**Files to modify:**
- `client/client.py` - Add WebSocket support to AsyncUESClient
- `client/__init__.py` - Export WebSocket classes
- `pyproject.toml` - Add `websockets` dependency

```python
"""WebSocket client for real-time event subscriptions.

Example:
    async with AsyncUESClient() as client:
        async with client.subscribe(["time.", "email."]) as events:
            async for event in events:
                print(f"Got event: {event.type}")
"""

import asyncio
import json
from typing import AsyncIterator, Optional

import websockets
from websockets.exceptions import ConnectionClosed

from client.exceptions import ConnectionError


class WSEvent:
    """A received WebSocket event."""
    
    def __init__(self, type: str, data: dict, timestamp: str):
        self.type = type
        self.data = data
        self.timestamp = timestamp
    
    @classmethod
    def from_json(cls, raw: str) -> "WSEvent":
        """Parse an event from JSON."""
        parsed = json.loads(raw)
        return cls(
            type=parsed["type"],
            data=parsed["data"],
            timestamp=parsed["timestamp"],
        )


class WebSocketSubscription:
    """Context manager for WebSocket event subscription."""
    
    def __init__(self, url: str, event_filters: Optional[list[str]] = None):
        self._url = url
        self._filters = event_filters
        self._ws = None
        self._closed = False
    
    async def __aenter__(self) -> "WebSocketSubscription":
        """Connect and subscribe."""
        try:
            self._ws = await websockets.connect(self._url)
        except Exception as e:
            raise ConnectionError(f"WebSocket connection failed: {e}")
        
        if self._filters:
            await self._ws.send(json.dumps({
                "action": "subscribe",
                "events": self._filters,
            }))
            # Wait for confirmation
            await self._ws.recv()
        
        return self
    
    async def __aexit__(self, *args) -> None:
        """Disconnect."""
        self._closed = True
        if self._ws:
            await self._ws.close()
    
    async def __aiter__(self) -> AsyncIterator[WSEvent]:
        """Iterate over events."""
        while not self._closed:
            try:
                raw = await self._ws.recv()
                yield WSEvent.from_json(raw)
            except ConnectionClosed:
                break
```

### Phase 6: Web UI WebSocket Integration

**Files to modify:**
- `webapp/src/api/websocket.ts` - New WebSocket client
- `webapp/src/api/hooks/useWebSocket.ts` - React hook for WebSocket
- `webapp/src/lib/store.ts` - Add WebSocket connection state
- `webapp/src/api/hooks/useTime.ts` - Replace polling with WebSocket (optional)
- `webapp/src/api/hooks/useSimulation.ts` - Replace polling with WebSocket (optional)

#### `webapp/src/api/websocket.ts`

```typescript
/**
 * WebSocket client for real-time event notifications.
 */

export interface WSEvent {
  type: string;
  data: Record<string, unknown>;
  timestamp: string;
}

export type WSEventHandler = (event: WSEvent) => void;

class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private handlers: Map<string, Set<WSEventHandler>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  
  constructor(url: string) {
    this.url = url;
  }
  
  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    
    this.ws = new WebSocket(this.url);
    
    this.ws.onmessage = (event) => {
      const parsed: WSEvent = JSON.parse(event.data);
      this.emit(parsed);
    };
    
    this.ws.onclose = () => {
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        setTimeout(() => {
          this.reconnectAttempts++;
          this.connect();
        }, 1000 * Math.pow(2, this.reconnectAttempts));
      }
    };
    
    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
    };
  }
  
  disconnect(): void {
    this.ws?.close();
    this.ws = null;
  }
  
  subscribe(eventType: string, handler: WSEventHandler): () => void {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, new Set());
    }
    this.handlers.get(eventType)!.add(handler);
    
    // Return unsubscribe function
    return () => {
      this.handlers.get(eventType)?.delete(handler);
    };
  }
  
  private emit(event: WSEvent): void {
    // Exact match handlers
    this.handlers.get(event.type)?.forEach(h => h(event));
    
    // Prefix match handlers (e.g., "time." matches "time.advanced")
    this.handlers.forEach((handlers, pattern) => {
      if (pattern.endsWith('.') && event.type.startsWith(pattern)) {
        handlers.forEach(h => h(event));
      }
    });
    
    // Wildcard handlers
    this.handlers.get('*')?.forEach(h => h(event));
  }
}

export const wsClient = new WebSocketClient('ws://localhost:8000/ws');
```

#### `webapp/src/api/hooks/useWebSocket.ts`

```typescript
/**
 * React hook for WebSocket event subscription.
 */
import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { wsClient, WSEvent } from '../websocket';

export function useWebSocket() {
  const queryClient = useQueryClient();
  
  useEffect(() => {
    wsClient.connect();
    
    // Auto-invalidate queries on relevant events
    const unsubTime = wsClient.subscribe('time.', () => {
      queryClient.invalidateQueries({ queryKey: ['time'] });
    });
    
    const unsubSim = wsClient.subscribe('simulation.', () => {
      queryClient.invalidateQueries({ queryKey: ['simulation'] });
    });
    
    const unsubEvents = wsClient.subscribe('event.', () => {
      queryClient.invalidateQueries({ queryKey: ['events'] });
    });
    
    const unsubModality = wsClient.subscribe('modality.', () => {
      queryClient.invalidateQueries({ queryKey: ['environment'] });
    });
    
    return () => {
      unsubTime();
      unsubSim();
      unsubEvents();
      unsubModality();
      wsClient.disconnect();
    };
  }, [queryClient]);
}

export function useWebSocketEvent(
  eventType: string,
  handler: (event: WSEvent) => void
) {
  useEffect(() => {
    wsClient.connect();
    return wsClient.subscribe(eventType, handler);
  }, [eventType, handler]);
}
```

### Phase 7: Testing

**Files to create:**
- `tests/api/websocket/test_websocket_connection.py` - Connection tests
- `tests/api/websocket/test_websocket_events.py` - Event broadcast tests
- `tests/api/websocket/test_websocket_subscription.py` - Subscription filter tests
- `tests/client/test_websocket.py` - Python client WebSocket tests

#### Test Categories

1. **Connection Tests**
   - Connect/disconnect lifecycle
   - Multiple simultaneous connections
   - Reconnection after server restart
   - Connection cleanup on close

2. **Broadcast Tests**
   - Simulation events broadcast correctly
   - Time events broadcast correctly
   - Modality events broadcast correctly
   - Event queue changes broadcast correctly
   - Undo/redo events broadcast correctly

3. **Subscription Tests**
   - Default subscription receives all events
   - Filtered subscription receives matching events only
   - Multiple filters work with OR logic
   - Subscription update changes filter
   - Prefix matching works correctly

4. **Integration Tests**
   - REST action triggers WebSocket broadcast
   - Multiple clients receive same broadcast
   - High-frequency events don't cause issues

#### Example Test

```python
"""Tests for WebSocket connection and event broadcasting."""

import pytest
from httpx import ASGITransport
from httpx_ws import aconnect_ws
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
async def ws_client():
    """Create a WebSocket test client."""
    async with aconnect_ws("ws://localhost:8000/ws", app) as ws:
        yield ws


class TestWebSocketConnection:
    """Test WebSocket connection lifecycle."""
    
    async def test_connect_and_disconnect(self, ws_client):
        """Test basic connection."""
        # Connection is established by fixture
        # Just verify we can receive a message after triggering an action
        pass
    
    async def test_receives_time_advanced_event(self, client, ws_client):
        """Test that time.advanced is broadcast on /simulator/time/advance."""
        # Start simulation first
        client.post("/simulation/start")
        
        # Advance time
        client.post("/simulator/time/advance", json={"seconds": 60})
        
        # Check WebSocket received the event
        message = await ws_client.receive_json()
        assert message["type"] == "time.advanced"
        assert "current_time" in message["data"]


class TestWebSocketSubscription:
    """Test subscription filtering."""
    
    async def test_subscribe_filters_events(self, client, ws_client):
        """Test that subscription filters work."""
        # Subscribe only to time events
        await ws_client.send_json({
            "action": "subscribe",
            "events": ["time."]
        })
        
        # Confirm subscription
        confirmation = await ws_client.receive_json()
        assert confirmation["type"] == "subscription.updated"
        
        # Start simulation (should NOT be received)
        client.post("/simulation/start")
        
        # Advance time (SHOULD be received)
        client.post("/simulator/time/advance", json={"seconds": 60})
        
        # Only time event should be received
        message = await ws_client.receive_json()
        assert message["type"].startswith("time.")
```

### Phase 8: Documentation

**Files to create/modify:**
- `docs/WEBSOCKET.md` - WebSocket usage documentation
- `docs/API_CLIENT.md` - Add WebSocket section
- `README.md` - Add WebSocket feature mention
- `TODO.md` - Update Phase 4 checklist

#### `docs/WEBSOCKET.md` Outline

1. Overview
2. Connecting
   - Python client example
   - JavaScript/browser example
   - WebSocket URL configuration
3. Event Types Reference
   - Complete list with payloads
4. Subscription Filtering
   - How to subscribe
   - Filter patterns
5. Best Practices
   - When to use WebSocket vs REST polling
   - Handling reconnection
   - Error handling
6. Examples
   - Real-time email notification agent
   - Dashboard state sync

---

## Dependencies

### Python Backend
```toml
# pyproject.toml additions
dependencies = [
    # ... existing ...
    # No new runtime dependencies needed - FastAPI has built-in WebSocket support
]

[dependency-groups]
dev = [
    # ... existing ...
    "websockets>=12.0",  # For testing WebSocket clients
    "httpx-ws>=0.6.0",   # For testing WebSocket with httpx/pytest
]
```

### Web UI
No new dependencies - browsers have native WebSocket support.

---

## File Change Summary

### New Files (9)
| File | Description |
|------|-------------|
| `api/websocket.py` | ConnectionManager and event types |
| `api/routes/websocket.py` | WebSocket endpoint |
| `client/_websocket.py` | Python client WebSocket support |
| `webapp/src/api/websocket.ts` | TypeScript WebSocket client |
| `webapp/src/api/hooks/useWebSocket.ts` | React WebSocket hook |
| `tests/api/websocket/test_websocket_connection.py` | Connection tests |
| `tests/api/websocket/test_websocket_events.py` | Broadcast tests |
| `tests/api/websocket/test_websocket_subscription.py` | Filter tests |
| `docs/WEBSOCKET.md` | Documentation |

### Modified Files (15)
| File | Changes |
|------|---------|
| `main.py` | Register WebSocket router |
| `pyproject.toml` | Add test dependencies |
| `api/routes/simulation.py` | Add broadcast calls |
| `api/routes/time.py` | Add broadcast calls |
| `api/routes/events.py` | Add broadcast calls |
| `api/routes/email.py` | Add broadcast calls |
| `api/routes/sms.py` | Add broadcast calls |
| `api/routes/chat.py` | Add broadcast calls |
| `api/routes/calendar.py` | Add broadcast calls |
| `api/routes/location.py` | Add broadcast calls |
| `api/routes/weather.py` | Add broadcast calls |
| `client/client.py` | Add WebSocket to AsyncUESClient |
| `client/__init__.py` | Export WebSocket classes |
| `docs/API_CLIENT.md` | Document WebSocket support |
| `TODO.md` | Update Phase 4 status |

---

## Implementation Order

1. **Phase 1** - Core infrastructure (`api/websocket.py`)
2. **Phase 2** - WebSocket endpoint (`api/routes/websocket.py`)
3. **Phase 3** - Integrate into simulation/time routes (highest impact)
4. **Phase 7** - Write tests for Phases 1-3
5. **Phase 3 cont.** - Integrate into remaining modality routes
6. **Phase 7 cont.** - Write tests for modality broadcasts
7. **Phase 5** - Python client WebSocket support
8. **Phase 6** - Web UI WebSocket integration
9. **Phase 8** - Documentation

---

## Estimated Effort

| Phase | Estimated Time |
|-------|----------------|
| Phase 1: Core Infrastructure | 1-2 hours |
| Phase 2: WebSocket Route | 30 minutes |
| Phase 3: Route Integration | 2-3 hours |
| Phase 4: Event Execution Hooks | 1 hour |
| Phase 5: Python Client | 1-2 hours |
| Phase 6: Web UI Integration | 2-3 hours |
| Phase 7: Testing | 3-4 hours |
| Phase 8: Documentation | 1-2 hours |
| **Total** | **12-18 hours** |

---

## Open Questions / Decisions

1. **Should WebSocket be enabled by default or opt-in?**
   - Recommendation: Enabled by default, minimal overhead when no clients connected

2. **Should we support multiple WebSocket endpoints?**
   - e.g., `/ws/events` for events only, `/ws/time` for time only
   - Recommendation: Single endpoint with subscription filtering is simpler

3. **How to handle event execution callbacks from SimulationEngine?**
   - Option A: Callback registration (cleaner separation)
   - Option B: Broadcast in routes after execution (simpler)
   - Recommendation: Start with Option B, refactor to A if needed

4. **Should Web UI fully replace polling with WebSocket?**
   - Recommendation: Use WebSocket for invalidation, keep TanStack Query for data fetching
   - This provides automatic caching, error handling, and fallback to polling if WS fails
