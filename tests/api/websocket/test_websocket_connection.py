"""Tests for WebSocket connection lifecycle.

Tests basic WebSocket connection operations including:
- Connecting and disconnecting
- Multiple simultaneous connections
- Connection cleanup
"""

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient
from httpx_ws import aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport

from api.dependencies import get_simulation_engine
from api.websocket import ws_manager
from main import app


@pytest.fixture
async def async_client(fresh_engine):
    """Provide an async HTTP client for triggering REST endpoints."""
    app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
async def ws_client(fresh_engine):
    """Provide an async WebSocket test client.
    
    Uses httpx_ws to connect to the FastAPI app's WebSocket endpoint.
    The fresh_engine fixture ensures a clean simulation state.
    """
    app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
    transport = ASGIWebSocketTransport(app=app)
    async with AsyncClient(transport=transport) as client:
        async with aconnect_ws("http://test/ws", client) as ws:
            yield ws
    app.dependency_overrides.clear()


class TestWebSocketConnection:
    """Test WebSocket connection lifecycle."""
    
    @pytest.mark.asyncio
    async def test_connect_establishes_connection(self, ws_client):
        """Test that WebSocket connection is established successfully."""
        # Connection is established by the fixture
        # The fact that we got here without exception means it worked
        assert ws_manager.connection_count >= 1
    
    @pytest.mark.asyncio
    async def test_multiple_connections(self, fresh_engine):
        """Test that multiple WebSocket connections can coexist."""
        app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
        transport = ASGIWebSocketTransport(app=app)
        
        initial_count = ws_manager.connection_count
        
        async with AsyncClient(transport=transport) as client:
            async with aconnect_ws("http://test/ws", client) as ws1:
                assert ws_manager.connection_count >= initial_count + 1
                
                # Need a separate client for second connection
                transport2 = ASGIWebSocketTransport(app=app)
                async with AsyncClient(transport=transport2) as client2:
                    async with aconnect_ws("http://test/ws", client2) as ws2:
                        assert ws_manager.connection_count >= initial_count + 2
        
        app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self, fresh_engine):
        """Test that disconnecting removes the connection from the manager."""
        app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
        transport = ASGIWebSocketTransport(app=app)
        
        initial_count = ws_manager.connection_count
        
        async with AsyncClient(transport=transport) as client:
            async with aconnect_ws("http://test/ws", client):
                during_count = ws_manager.connection_count
                assert during_count >= initial_count + 1
        
        # After context exit, connection should be removed
        # Give a moment for cleanup
        await asyncio.sleep(0.1)
        assert ws_manager.connection_count <= during_count - 1
        
        app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_ping_pong(self, ws_client):
        """Test that ping messages receive pong responses."""
        # Send a ping message (JSON format with action)
        await ws_client.send_json({"action": "ping"})
        
        # Should receive pong
        response = await asyncio.wait_for(ws_client.receive_json(), timeout=5.0)
        assert response.get("action") == "pong"
    
    @pytest.mark.asyncio
    async def test_invalid_json_handled_gracefully(self, ws_client):
        """Test that invalid JSON messages don't crash the connection."""
        # Send invalid JSON
        await ws_client.send_text("not valid json {{{")
        
        # Connection should still work - send ping to verify
        await ws_client.send_json({"action": "ping"})
        response = await asyncio.wait_for(ws_client.receive_json(), timeout=5.0)
        assert response.get("action") == "pong"
