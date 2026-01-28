"""WebSocket client for real-time event subscriptions.

This module provides async WebSocket support for subscribing to UES events.
Events are pushed from the server in real-time when state changes occur.

Example:
    Using with AsyncUESClient::
    
        async with AsyncUESClient() as client:
            # Subscribe to all time and email events
            async with client.subscribe(["time.", "email."]) as events:
                async for event in events:
                    print(f"Event: {event.type} - {event.data}")
    
    Standalone subscription::
    
        from ues.client import WebSocketSubscription, WSEvent
        
        subscription = WebSocketSubscription("ws://localhost:8000/ws")
        await subscription.connect(event_filters=["simulation."])
        
        async for event in subscription:
            if event.type == "simulation.started":
                print("Simulation started!")
                break
        
        await subscription.close()
"""

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Optional

import websockets
from websockets.exceptions import ConnectionClosed

from ues.client.exceptions import ConnectionError, UESClientError

logger = logging.getLogger(__name__)


class WSEvent:
    """A received WebSocket event.
    
    Attributes:
        type: Event type identifier (e.g., "time.advanced", "email.received").
        data: Event-specific payload data.
        timestamp: ISO 8601 timestamp when the event was created on the server.
    
    Example:
        Accessing event data::
        
            async for event in subscription:
                if event.type == "email.received":
                    print(f"New email: {event.data.get('subject')}")
                    print(f"Received at: {event.timestamp}")
    """
    
    def __init__(self, type: str, data: dict[str, Any], timestamp: str) -> None:
        """Initialize the event.
        
        Args:
            type: Event type identifier.
            data: Event payload data.
            timestamp: ISO 8601 timestamp string.
        """
        self.type = type
        self.data = data
        self.timestamp = timestamp
    
    @classmethod
    def from_json(cls, raw: str) -> "WSEvent":
        """Parse an event from a JSON string.
        
        Args:
            raw: JSON string containing event data.
        
        Returns:
            Parsed WSEvent instance.
        
        Raises:
            ValueError: If JSON parsing fails or required fields are missing.
        """
        try:
            parsed = json.loads(raw)
            return cls(
                type=parsed["type"],
                data=parsed["data"],
                timestamp=parsed["timestamp"],
            )
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Invalid event JSON: {e}") from e
    
    def __repr__(self) -> str:
        """Return string representation of the event."""
        return f"WSEvent(type={self.type!r}, data={self.data!r})"


class WebSocketSubscription:
    """Async context manager for WebSocket event subscription.
    
    Manages the WebSocket connection lifecycle and provides an async iterator
    for receiving events. Supports filtering events by type prefix.
    
    Attributes:
        url: WebSocket server URL.
        event_filters: List of event type prefixes to receive (None = all events).
    
    Example:
        As async context manager::
        
            async with WebSocketSubscription("ws://localhost:8000/ws") as sub:
                await sub.subscribe(["time.", "simulation."])
                async for event in sub:
                    print(event.type)
        
        Manual lifecycle::
        
            sub = WebSocketSubscription("ws://localhost:8000/ws")
            await sub.connect()
            await sub.subscribe(["email."])
            
            try:
                async for event in sub:
                    if event.type == "email.received":
                        break
            finally:
                await sub.close()
    """
    
    def __init__(
        self,
        url: str,
        event_filters: Optional[list[str]] = None,
    ) -> None:
        """Initialize the subscription.
        
        Args:
            url: WebSocket server URL (e.g., "ws://localhost:8000/ws").
            event_filters: Optional list of event type prefixes to filter.
                Use prefix with trailing dot (e.g., "time.") to receive all
                events in that category. None means receive all events.
        """
        self._url = url
        self._filters = event_filters
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._closed = False
    
    @property
    def url(self) -> str:
        """Get the WebSocket URL."""
        return self._url
    
    @property
    def event_filters(self) -> Optional[list[str]]:
        """Get the current event filters."""
        return self._filters
    
    @property
    def is_connected(self) -> bool:
        """Check if the WebSocket is connected."""
        return self._ws is not None and not self._closed
    
    async def connect(self, event_filters: Optional[list[str]] = None) -> None:
        """Connect to the WebSocket server.
        
        Args:
            event_filters: Optional event filters to subscribe to after connecting.
                If provided, overrides the filters passed to __init__.
        
        Raises:
            ConnectionError: If connection fails.
        """
        if self._ws is not None:
            raise UESClientError("Already connected")
        
        try:
            self._ws = await websockets.connect(self._url)
            self._closed = False
            logger.info(f"WebSocket connected to {self._url}")
        except Exception as e:
            raise ConnectionError(f"WebSocket connection failed: {e}") from e
        
        # Apply filters if provided
        filters_to_use = event_filters if event_filters is not None else self._filters
        if filters_to_use is not None:
            await self.subscribe(filters_to_use)
    
    async def subscribe(self, event_types: list[str]) -> None:
        """Update the event subscription filter.
        
        Sends a subscription message to the server to filter which events
        this client receives.
        
        Args:
            event_types: List of event type prefixes to receive.
                Examples: ["time."], ["email.", "sms."], ["simulation.started"]
        
        Raises:
            UESClientError: If not connected.
        """
        if self._ws is None:
            raise UESClientError("Not connected")
        
        self._filters = event_types
        await self._ws.send(json.dumps({
            "action": "subscribe",
            "events": event_types,
        }))
        
        # Wait for confirmation (server sends subscription.updated event)
        try:
            raw = await asyncio.wait_for(self._ws.recv(), timeout=5.0)
            event = WSEvent.from_json(raw)
            if event.type == "subscription.updated":
                logger.debug(f"Subscription confirmed: {event_types}")
            else:
                # If we got a different event, it's still fine - just log it
                logger.debug(f"Received event during subscription: {event.type}")
        except asyncio.TimeoutError:
            logger.warning("No subscription confirmation received")
    
    async def close(self) -> None:
        """Close the WebSocket connection.
        
        Safe to call multiple times. Any pending receives will be interrupted.
        """
        self._closed = True
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception as e:
                logger.debug(f"Error closing WebSocket: {e}")
            finally:
                self._ws = None
            logger.info("WebSocket disconnected")
    
    async def __aenter__(self) -> "WebSocketSubscription":
        """Enter async context manager - connect to WebSocket.
        
        Returns:
            The connected subscription instance.
        """
        await self.connect()
        return self
    
    async def __aexit__(self, *args: Any) -> None:
        """Exit async context manager - close WebSocket."""
        await self.close()
    
    def __aiter__(self) -> AsyncIterator[WSEvent]:
        """Return async iterator for events.
        
        Returns:
            Self (implements async iteration).
        """
        return self
    
    async def __anext__(self) -> WSEvent:
        """Get the next event.
        
        Returns:
            The next received WSEvent.
        
        Raises:
            StopAsyncIteration: When connection is closed.
            UESClientError: If not connected.
        """
        if self._ws is None:
            raise UESClientError("Not connected")
        
        if self._closed:
            raise StopAsyncIteration
        
        try:
            raw = await self._ws.recv()
            return WSEvent.from_json(raw)
        except ConnectionClosed:
            self._closed = True
            logger.info("WebSocket connection closed by server")
            raise StopAsyncIteration
        except Exception as e:
            if self._closed:
                raise StopAsyncIteration
            logger.error(f"Error receiving WebSocket message: {e}")
            raise UESClientError(f"WebSocket receive failed: {e}") from e
    
    async def receive_one(self, timeout: Optional[float] = None) -> Optional[WSEvent]:
        """Receive a single event with optional timeout.
        
        Convenience method for receiving one event without using async iteration.
        
        Args:
            timeout: Maximum time to wait in seconds (None = wait forever).
        
        Returns:
            The received event, or None if timeout expired.
        
        Raises:
            UESClientError: If not connected or connection closed.
        """
        if self._ws is None:
            raise UESClientError("Not connected")
        
        try:
            if timeout is not None:
                raw = await asyncio.wait_for(self._ws.recv(), timeout=timeout)
            else:
                raw = await self._ws.recv()
            return WSEvent.from_json(raw)
        except asyncio.TimeoutError:
            return None
        except ConnectionClosed:
            self._closed = True
            raise UESClientError("WebSocket connection closed")
