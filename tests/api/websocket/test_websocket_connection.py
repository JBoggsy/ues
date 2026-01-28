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

from ues.api.dependencies import get_simulation_engine
from ues.api.websocket import ws_manager
from ues.main import app





class TestWebSocketConnection:
    """Test WebSocket connection lifecycle."""
    
    @pytest.mark.asyncio
    async def test_connect_establishes_connection(self, fresh_engine):
        """Test that WebSocket connection is established successfully."""
        app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
        transport = ASGIWebSocketTransport(app=app)
        
        try:
            async with AsyncClient(transport=transport) as client:
                async with aconnect_ws("http://test/ws", client):
                    # Connection is established
                    # The fact that we got here without exception means it worked
                    assert ws_manager.connection_count >= 1
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_multiple_connections(self, fresh_engine):
        """Test that multiple WebSocket connections can coexist."""
        app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
        
        try:
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
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self, fresh_engine):
        """Test that disconnecting removes the connection from the manager."""
        app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
        
        try:
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
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_ping_pong(self, fresh_engine):
        """Test that ping messages receive pong responses."""
        app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
        
        try:
            transport = ASGIWebSocketTransport(app=app)
            async with AsyncClient(transport=transport) as client:
                async with aconnect_ws("http://test/ws", client) as ws:
                    # Send a ping message (JSON format with action)
                    await ws.send_json({"action": "ping"})
                    
                    # Should receive pong
                    response = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
                    assert response.get("action") == "pong"
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_invalid_json_handled_gracefully(self, fresh_engine):
        """Test that invalid JSON messages don't crash the connection."""
        app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
        
        try:
            transport = ASGIWebSocketTransport(app=app)
            async with AsyncClient(transport=transport) as client:
                async with aconnect_ws("http://test/ws", client) as ws:
                    # Send invalid JSON
                    await ws.send_text("not valid json {{{")
                    
                    # Connection should still work - send ping to verify
                    await ws.send_json({"action": "ping"})
                    response = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
                    assert response.get("action") == "pong"
        finally:
            app.dependency_overrides.clear()
