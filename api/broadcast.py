"""Unified event broadcasting to WebSocket and webhook subscribers.

This module provides a single entry point for broadcasting events to all
connected clients, both via WebSocket (for real-time UIs) and webhooks
(for external services).

Example usage:
    from api.broadcast import broadcast_event
    from api.websocket import WSEventType
    
    # In a REST route that modifies state:
    await broadcast_event(WSEventType.EMAIL_RECEIVED, {
        "email_id": email.message_id,
        "from": email.from_address,
        "subject": email.subject,
    })
"""

from typing import Any

from api.webhooks import webhook_dispatcher
from api.websocket import ws_manager, WSEventType


async def broadcast_event(event_type: WSEventType, data: dict[str, Any]) -> None:
    """Broadcast an event to all WebSocket and webhook subscribers.
    
    This is the standard way to notify clients of state changes.
    Call this instead of directly calling ws_manager.broadcast().
    
    The function broadcasts to both channels:
    1. WebSocket clients (real-time, persistent connections)
    2. Webhook endpoints (HTTP callbacks to registered URLs)
    
    Args:
        event_type: The type of event to broadcast (from WSEventType enum).
        data: Event payload data (will be JSON serialized).
    
    Example:
        After processing an email receive request::
        
            await broadcast_event(WSEventType.EMAIL_RECEIVED, {
                "email_id": email.message_id,
                "from": email.from_address,
                "subject": email.subject,
                "received_at": email.received_at.isoformat(),
            })
    """
    # Broadcast to WebSocket clients
    await ws_manager.broadcast(event_type, data)
    
    # Dispatch to webhook subscribers (async, non-blocking)
    await webhook_dispatcher.dispatch(event_type, data)
