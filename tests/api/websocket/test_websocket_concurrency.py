"""Tests for WebSocket concurrency and thread-safety.

Tests that the WebSocket manager handles concurrent connections and
broadcasts correctly under high load.
"""

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient
from httpx_ws import aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport

from api.dependencies import get_simulation_engine
from api.websocket import ws_manager
from main import app


class TestWebSocketConcurrency:
    """Test WebSocket concurrency and thread-safety."""
    
    @pytest.mark.asyncio
    async def test_concurrent_connections_and_broadcasts(self, fresh_engine):
        """Test multiple concurrent connections receiving broadcasts simultaneously."""
        app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
        
        try:
            num_clients = 10
            ws_clients = []
            http_transport = ASGITransport(app=app)
            
            # Create multiple WebSocket connections
            for _ in range(num_clients):
                transport = ASGIWebSocketTransport(app=app)
                client = AsyncClient(transport=transport)
                ws_clients.append((client, transport))
            
            # Connect all clients
            connections = []
            for client, _ in ws_clients:
                ws = await client.__aenter__()
                conn = await aconnect_ws("http://test/ws", ws).__aenter__()
                connections.append(conn)
            
            # Use HTTP client to trigger broadcasts
            async with AsyncClient(transport=http_transport, base_url="http://test") as http:
                # Start simulation
                response = await http.post("/simulation/start", json={"auto_advance": False})
                assert response.status_code == 200
                
                # All clients should receive the broadcast
                messages = await asyncio.gather(
                    *[asyncio.wait_for(conn.receive_json(), timeout=5.0) for conn in connections]
                )
                
                # Verify all got the same event
                assert all(msg["type"] == "simulation.started" for msg in messages)
                assert len(set(msg["data"]["simulation_id"] for msg in messages)) == 1
            
            # Clean up connections
            for conn in connections:
                await conn.__aexit__(None, None, None)
            
            for client, _ in ws_clients:
                await client.__aexit__(None, None, None)
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_rapid_subscribe_unsubscribe(self, fresh_engine):
        """Test rapid subscription updates don't cause race conditions."""
        app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
        
        try:
            transport = ASGIWebSocketTransport(app=app)
            async with AsyncClient(transport=transport) as client:
                async with aconnect_ws("http://test/ws", client) as ws:
                    # Rapidly change subscriptions
                    subscriptions = [
                        ["time."],
                        ["simulation."],
                        ["email.", "sms."],
                        ["time.", "simulation.", "email."],
                        None,  # All events
                    ]
                    
                    for sub in subscriptions:
                        await ws.send_json({
                            "action": "subscribe",
                            "events": sub
                        })
                        # Wait for confirmation
                        msg = await asyncio.wait_for(ws.receive_json(), timeout=2.0)
                        assert msg["type"] == "subscription.updated"
                        assert msg["data"]["filters"] == sub
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_broadcast_during_connection_changes(self, fresh_engine):
        """Test broadcasts work correctly when connections are being added/removed."""
        app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
        
        try:
            http_transport = ASGITransport(app=app)
            
            # Start simulation first
            async with AsyncClient(transport=http_transport, base_url="http://test") as http:
                response = await http.post("/simulation/start", json={"auto_advance": False})
                assert response.status_code == 200
                
                # Create a long-lived connection
                transport1 = ASGIWebSocketTransport(app=app)
                async with AsyncClient(transport=transport1) as client1:
                    async with aconnect_ws("http://test/ws", client1) as ws1:
                        # Consume initial event
                        await asyncio.wait_for(ws1.receive_json(), timeout=2.0)
                        
                        # While ws1 is connected, add and remove ws2 multiple times
                        for _ in range(3):
                            transport2 = ASGIWebSocketTransport(app=app)
                            async with AsyncClient(transport=transport2) as client2:
                                async with aconnect_ws("http://test/ws", client2) as ws2:
                                    # Trigger a broadcast
                                    await http.post("/simulator/time/advance", json={"seconds": 60})
                                    
                                    # Both should receive it
                                    msg1 = await asyncio.wait_for(ws1.receive_json(), timeout=2.0)
                                    msg2 = await asyncio.wait_for(ws2.receive_json(), timeout=2.0)
                                    
                                    assert msg1["type"] == "time.advanced"
                                    assert msg2["type"] == "time.advanced"
                                # ws2 disconnects here
                            
                            # ws1 should still work after ws2 disconnected
                            await http.post("/simulator/time/advance", json={"seconds": 60})
                            msg = await asyncio.wait_for(ws1.receive_json(), timeout=2.0)
                            assert msg["type"] == "time.advanced"
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_connection_count_accuracy(self, fresh_engine):
        """Test that connection count stays accurate under concurrent operations."""
        app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
        
        try:
            initial_count = ws_manager.connection_count
            
            # Add 5 connections
            transports = []
            clients = []
            connections = []
            
            for _ in range(5):
                transport = ASGIWebSocketTransport(app=app)
                client = AsyncClient(transport=transport)
                transports.append(transport)
                clients.append(client)
            
            for client in clients:
                ws_client = await client.__aenter__()
                conn = await aconnect_ws("http://test/ws", ws_client).__aenter__()
                connections.append(conn)
            
            # Should have 5 more connections
            assert ws_manager.connection_count == initial_count + 5
            
            # Remove 3 connections
            for i in range(3):
                await connections[i].__aexit__(None, None, None)
                await clients[i].__aexit__(None, None, None)
            
            # Give a moment for cleanup
            await asyncio.sleep(0.2)
            
            # Should have 2 more than initial
            assert ws_manager.connection_count == initial_count + 2
            
            # Clean up remaining
            for i in range(3, 5):
                await connections[i].__aexit__(None, None, None)
                await clients[i].__aexit__(None, None, None)
            
            await asyncio.sleep(0.2)
            
            # Should be back to initial
            assert ws_manager.connection_count == initial_count
        
        finally:
            app.dependency_overrides.clear()
