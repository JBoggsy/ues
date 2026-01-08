"""WebSocket connection management and event broadcasting.

This module provides infrastructure for real-time push notifications
to connected clients. It manages WebSocket connections and broadcasts
simulation events.

Example usage:
    # In a REST route that modifies state:
    from api.websocket import ws_manager, WSEventType
    
    @router.post("/simulation/start")
    async def start_simulation(...):
        result = engine.start(...)
        await ws_manager.broadcast(WSEventType.SIMULATION_STARTED, {
            "simulation_id": result["simulation_id"],
            "current_time": result["current_time"],
        })
        return result
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from fastapi import WebSocket
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class WSEventType(str, Enum):
    """WebSocket event types that can be broadcast.
    
    Event types are organized by category with dot notation for easy filtering.
    Clients can subscribe to prefixes (e.g., "time.") to receive all related events.
    """
    
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
    
    # Subscription management
    SUBSCRIPTION_UPDATED = "subscription.updated"


class WSEvent(BaseModel):
    """A WebSocket event to broadcast to connected clients.
    
    Attributes:
        type: The event type identifier (from WSEventType enum).
        data: Event-specific payload data.
        timestamp: ISO 8601 timestamp when the event was created.
    """
    
    type: str
    data: dict[str, Any]
    timestamp: str  # ISO format with Z suffix
    
    @classmethod
    def create(cls, event_type: WSEventType, data: dict[str, Any]) -> "WSEvent":
        """Create a new event with the current UTC timestamp.
        
        Args:
            event_type: The type of event being created.
            data: Event payload data.
        
        Returns:
            A new WSEvent instance ready for broadcasting.
        """
        return cls(
            type=event_type.value,
            data=data,
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
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
            await manager.disconnect(websocket)
        
        # In REST routes:
        await manager.broadcast(WSEventType.TIME_ADVANCED, {"current_time": "..."})
    
    Attributes:
        _connections: Set of active WebSocket connections.
        _subscriptions: Map of connections to their event type filters.
        _lock: Async lock for thread-safe operations.
    """
    
    def __init__(self) -> None:
        """Initialize the connection manager with empty connection set."""
        self._connections: set[WebSocket] = set()
        self._subscriptions: dict[WebSocket, Optional[set[str]]] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection.
        
        The connection is added to the active set and subscribed to all events
        by default (subscription filter is None).
        
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
        
        Safely removes the connection from tracking. If the websocket is not
        in the set (already disconnected), this is a no-op.
        
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
        
        Clients can filter which events they receive by subscribing to specific
        event type prefixes. For example, subscribing to ["time."] will receive
        all time-related events (time.advanced, time.set, etc.).
        
        Args:
            websocket: The WebSocket connection to update.
            event_types: List of event type prefixes to receive.
                        None means all events (unsubscribe from filtering).
                        Examples: ["time.", "email."] or ["simulation.started"]
        """
        async with self._lock:
            if event_types is None:
                self._subscriptions[websocket] = None
            else:
                self._subscriptions[websocket] = set(event_types)
    
    def _should_send(self, websocket: WebSocket, event_type: str) -> bool:
        """Check if an event should be sent to a connection.
        
        An event is sent if:
        - The connection has no filter (receives all events), OR
        - The event type exactly matches a filter, OR
        - The event type starts with a filter prefix
        
        Args:
            websocket: The connection to check.
            event_type: The event type being broadcast.
        
        Returns:
            True if the event matches the connection's subscription filter.
        """
        filters = self._subscriptions.get(websocket)
        if filters is None:
            return True  # No filter = receive all
        
        # Check if event type matches any filter (exact or prefix)
        for filter_pattern in filters:
            if event_type == filter_pattern:
                return True
            if filter_pattern.endswith('.') and event_type.startswith(filter_pattern):
                return True
        return False
    
    async def broadcast(
        self, 
        event_type: WSEventType, 
        data: dict[str, Any]
    ) -> int:
        """Broadcast an event to all subscribed connections.
        
        Creates an event with the current timestamp and sends it to all
        connected clients whose subscription filters match the event type.
        Dead connections are automatically cleaned up.
        
        Args:
            event_type: The type of event to broadcast.
            data: Event payload data.
        
        Returns:
            Number of clients that successfully received the event.
        """
        if not self._connections:
            return 0
        
        event = WSEvent.create(event_type, data)
        message = event.model_dump_json()
        
        sent_count = 0
        dead_connections: list[WebSocket] = []
        
        async with self._lock:
            for websocket in self._connections:
                if not self._should_send(websocket, event_type.value):
                    continue
                
                try:
                    await websocket.send_text(message)
                    sent_count += 1
                except Exception as e:
                    # Connection is dead, mark for removal
                    logger.warning(f"Failed to send to WebSocket: {e}")
                    dead_connections.append(websocket)
        
        # Clean up dead connections outside the lock
        for ws in dead_connections:
            await self.disconnect(ws)
        
        if sent_count > 0:
            logger.debug(f"Broadcast {event_type.value} to {sent_count} clients")
        
        return sent_count
    
    @property
    def connection_count(self) -> int:
        """Get the number of active connections.
        
        Returns:
            The current number of connected WebSocket clients.
        """
        return len(self._connections)
    
    def schedule_broadcast(
        self,
        event_type: WSEventType,
        data: dict[str, Any],
    ) -> None:
        """Schedule a broadcast from synchronous code.
        
        This method can be called from synchronous contexts (like the
        SimulationEngine callback) to schedule an async broadcast.
        It uses the running event loop to schedule the coroutine.
        
        If no event loop is running, the broadcast is silently skipped.
        
        Args:
            event_type: The type of event to broadcast.
            data: Event payload data.
        """
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(event_type, data))
        except RuntimeError:
            # No running event loop (e.g., during testing)
            logger.debug(f"No event loop for broadcast: {event_type.value}")


# Global connection manager instance
# This is shared across all routes for broadcasting events
ws_manager = ConnectionManager()
