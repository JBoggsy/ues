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
            
            # Wait for subscription confirmation
            confirmation = await ws.recv()
            print(f"Subscription confirmed: {confirmation}")
            
            # Listen for events
            async for message in ws:
                event = json.loads(message)
                print(f"Event: {event['type']}, Data: {event['data']}")

    asyncio.run(listen())

Example client (JavaScript):
    const ws = new WebSocket('ws://localhost:8000/ws');
    
    ws.onopen = () => {
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

Event Format:
    All events are broadcast as JSON with this structure:
    {
        "type": "time.advanced",
        "data": {"current_time": "2024-01-01T12:00:00Z", ...},
        "timestamp": "2024-01-01T12:00:00.123Z"
    }

Subscription Message Format:
    {
        "action": "subscribe",
        "events": ["time.", "email.received", "simulation."]
    }
    
    - Use event type prefixes ending with "." to match all events in a category
    - Use exact event types for specific events only
    - Send with events: null or omit to receive all events (default)
"""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.websocket import ws_manager, WSEventType

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time event notifications.
    
    Accepts WebSocket connections and broadcasts simulation events.
    Clients can optionally filter which events they receive by sending
    subscription messages.
    
    The connection remains open until the client disconnects or an error occurs.
    All state-changing REST API calls will broadcast events to connected clients.
    
    Message Types (client -> server):
        subscribe: Update event type filter
            {
                "action": "subscribe",
                "events": ["time.", "email."]  // null for all events
            }
        
        ping: Keep-alive (server responds with pong)
            {"action": "ping"}
    
    Message Types (server -> client):
        Events: Simulation state changes
            {
                "type": "time.advanced",
                "data": {...},
                "timestamp": "2024-01-01T12:00:00.123Z"
            }
        
        subscription.updated: Confirmation of subscription change
            {
                "type": "subscription.updated",
                "data": {"filters": ["time.", "email."]},
                "timestamp": "..."
            }
        
        pong: Response to ping
            {"action": "pong"}
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
                    event_filters = message.get("events")
                    await ws_manager.subscribe(websocket, event_filters)
                    
                    # Send confirmation
                    await websocket.send_json({
                        "type": WSEventType.SUBSCRIPTION_UPDATED.value,
                        "data": {"filters": event_filters},
                        "timestamp": "",  # Will be filled by client if needed
                    })
                    logger.debug(f"Client subscribed to: {event_filters}")
                    
                elif action == "ping":
                    # Respond to keep-alive ping
                    await websocket.send_json({"action": "pong"})
                    
                else:
                    # Unknown action - log but don't disconnect
                    logger.debug(f"Unknown WebSocket action: {action}")
                    
            except json.JSONDecodeError:
                # Ignore malformed messages but log them
                logger.debug(f"Received non-JSON WebSocket message: {data[:50]}")
                
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
