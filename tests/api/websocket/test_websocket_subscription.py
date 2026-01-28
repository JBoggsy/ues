"""Tests for WebSocket subscription filtering.

Tests that clients can filter which events they receive by subscribing
to specific event type prefixes.
"""

import asyncio
from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient
from httpx_ws import aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport

from ues.api.dependencies import get_simulation_engine
from ues.main import app
from tests.api.websocket.conftest import get_auth_headers


@asynccontextmanager
async def ws_with_http(fresh_engine):
    """Context manager providing both WebSocket and HTTP clients for integration testing."""
    app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
    headers = get_auth_headers()
    
    try:
        ws_transport = ASGIWebSocketTransport(app=app)
        http_transport = ASGITransport(app=app)
        
        async with AsyncClient(transport=ws_transport) as ws_http_client:
            async with aconnect_ws("http://test/ws", ws_http_client) as ws:
                async with AsyncClient(
                    transport=http_transport,
                    base_url="http://test",
                    headers=headers,
                ) as http:
                    yield ws, http
    finally:
        app.dependency_overrides.clear()


class TestSubscriptionFiltering:
    """Test subscription filter functionality."""
    
    @pytest.mark.asyncio
    async def test_subscribe_filters_to_specified_events(self, fresh_engine):
        """Test that subscribing filters events to only matching types."""
        async with ws_with_http(fresh_engine) as (ws, http):
            # Subscribe only to time events
            await ws.send_json({
                "action": "subscribe",
                "events": ["time."]
            })
            
            # Should receive subscription confirmation
            msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
            assert msg["type"] == "subscription.updated"
            assert msg["data"]["filters"] == ["time."]
            
            # Start simulation (simulation.started should NOT be received)
            await http.post("/simulation/start", json={"auto_advance": False})
            
            # Advance time (time.advanced SHOULD be received)
            await http.post("/simulator/time/advance", json={"seconds": 60})
            
            # Should receive time.advanced (not simulation.started)
            msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
            assert msg["type"] == "time.advanced"
    
    @pytest.mark.asyncio
    async def test_multiple_filters_with_or_logic(self, fresh_engine):
        """Test that multiple filters work with OR logic."""
        async with ws_with_http(fresh_engine) as (ws, http):
            # Subscribe to both time and simulation events
            await ws.send_json({
                "action": "subscribe",
                "events": ["time.", "simulation."]
            })
            
            # Consume confirmation
            msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
            assert msg["type"] == "subscription.updated"
            
            # Start simulation
            await http.post("/simulation/start", json={"auto_advance": False})
            
            # Should receive simulation.started
            msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
            assert msg["type"] == "simulation.started"
            
            # Advance time
            await http.post("/simulator/time/advance", json={"seconds": 60})
            
            # Should also receive time.advanced
            msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
            assert msg["type"] == "time.advanced"
    
    @pytest.mark.asyncio
    async def test_exact_match_filter(self, fresh_engine):
        """Test that exact event type matching works."""
        async with ws_with_http(fresh_engine) as (ws, http):
            # Subscribe only to simulation.started (exact match)
            await ws.send_json({
                "action": "subscribe",
                "events": ["simulation.started"]
            })
            
            # Consume confirmation
            msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
            assert msg["type"] == "subscription.updated"
            
            # Start simulation
            await http.post("/simulation/start", json={"auto_advance": False})
            
            # Should receive simulation.started
            msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
            assert msg["type"] == "simulation.started"
            
            # Stop simulation - simulation.stopped should NOT be received
            await http.post("/simulation/stop")
            
            # Advance time - time.advanced should NOT be received
            # (simulation is stopped, so this might fail - that's ok)
            # The point is we shouldn't receive any more events
            
            # Give a brief moment for any events to arrive
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(ws.receive_json(), timeout=0.5)
    
    @pytest.mark.asyncio
    async def test_update_subscription(self, fresh_engine):
        """Test that subscription can be updated."""
        async with ws_with_http(fresh_engine) as (ws, http):
            # Initially subscribe to time events
            await ws.send_json({
                "action": "subscribe",
                "events": ["time."]
            })
            
            # Consume confirmation
            msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
            assert msg["type"] == "subscription.updated"
            assert msg["data"]["filters"] == ["time."]
            
            # Update subscription to simulation events
            await ws.send_json({
                "action": "subscribe",
                "events": ["simulation."]
            })
            
            # Should receive new confirmation
            msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
            assert msg["type"] == "subscription.updated"
            assert msg["data"]["filters"] == ["simulation."]
            
            # Start simulation
            await http.post("/simulation/start", json={"auto_advance": False})
            
            # Should now receive simulation events
            msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
            assert msg["type"] == "simulation.started"
    
    @pytest.mark.asyncio
    async def test_default_receives_all_events(self, fresh_engine):
        """Test that without subscription filter, all events are received."""
        async with ws_with_http(fresh_engine) as (ws, http):
            # No subscription message sent - should receive all events
            
            # Start simulation
            await http.post("/simulation/start", json={"auto_advance": False})
            
            # Should receive simulation.started
            msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
            assert msg["type"] == "simulation.started"
            
            # Advance time
            await http.post("/simulator/time/advance", json={"seconds": 60})
            
            # Should also receive time.advanced
            msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
            assert msg["type"] == "time.advanced"
    
    @pytest.mark.asyncio
    async def test_prefix_matching(self, fresh_engine):
        """Test that prefix matching with trailing dot works correctly."""
        async with ws_with_http(fresh_engine) as (ws, http):
            # Subscribe with prefix (trailing dot)
            await ws.send_json({
                "action": "subscribe",
                "events": ["email."]
            })
            
            # Consume confirmation
            await asyncio.wait_for(ws.receive_json(), timeout=5.0)
            
            # Start simulation first
            await http.post("/simulation/start", json={"auto_advance": False})
            
            # simulation.started should NOT be received (filtered out)
            # Send an email to trigger email.sent event
            await http.post(
                "/email/send",
                json={
                    "from_address": "user@example.com",
                    "to_addresses": ["other@example.com"],
                    "subject": "Test",
                    "body_text": "Hello",
                }
            )
            
            # Should receive email.sent
            msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
            assert msg["type"] == "email.sent"
            
            # Receive an email
            await http.post(
                "/email/receive",
                json={
                    "from_address": "sender@example.com",
                    "to_addresses": ["user@example.com"],
                    "subject": "Reply",
                    "body_text": "Hi",
                }
            )
            
            # Should receive email.received
            msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
            assert msg["type"] == "email.received"
