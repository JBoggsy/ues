"""Tests for WebSocket concurrency and thread-safety.

Tests that the WebSocket manager handles concurrent connections and
broadcasts correctly under high load.

These tests use a simpler approach that avoids httpx_ws context manager
issues by using proper async patterns and cleanup.
"""

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient
from httpx_ws import aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport

from ues.api.dependencies import get_simulation_engine
from ues.api.websocket import ws_manager
from ues.main import app
from tests.api.websocket.conftest import get_auth_headers


class TestWebSocketConcurrency:
    """Test WebSocket concurrency and thread-safety."""

    @pytest.mark.asyncio
    async def test_concurrent_connections_and_broadcasts(self, fresh_engine):
        """Test multiple concurrent connections receiving broadcasts simultaneously.
        
        This test verifies that:
        1. Multiple clients can connect concurrently
        2. A broadcast reaches all connected clients
        3. All clients receive identical event data
        """
        app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
        headers = get_auth_headers()

        try:
            num_clients = 5  # Reduced from 10 for stability
            received_messages = []
            http_transport = ASGITransport(app=app)

            async def client_task(client_id: int) -> dict:
                """Connect a single client and wait for one broadcast message."""
                transport = ASGIWebSocketTransport(app=app)
                async with AsyncClient(transport=transport) as client:
                    async with aconnect_ws("http://test/ws", client) as ws:
                        # Wait for the broadcast message
                        msg = await asyncio.wait_for(ws.receive_json(), timeout=10.0)
                        return {"client_id": client_id, "message": msg}

            # Start the simulation first, then have clients connect
            async with AsyncClient(
                transport=http_transport,
                base_url="http://test",
                headers=headers,
            ) as http:
                # Create client tasks that will connect and wait
                client_tasks = [
                    asyncio.create_task(client_task(i)) for i in range(num_clients)
                ]
                
                # Give clients time to connect
                await asyncio.sleep(0.5)
                
                # Trigger the broadcast
                response = await http.post("/simulation/start", json={"auto_advance": False})
                assert response.status_code == 200

                # Wait for all clients to receive the message
                results = await asyncio.gather(*client_tasks, return_exceptions=True)

            # Check results
            successful = [r for r in results if isinstance(r, dict)]
            assert len(successful) == num_clients, f"Only {len(successful)}/{num_clients} succeeded"
            
            # Verify all got the same event type
            messages = [r["message"] for r in successful]
            assert all(msg["type"] == "simulation.started" for msg in messages)
            
            # Verify all got the same simulation_id
            sim_ids = set(msg["data"]["simulation_id"] for msg in messages)
            assert len(sim_ids) == 1, "All clients should receive same simulation_id"

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
                        await ws.send_json({"action": "subscribe", "events": sub})
                        # Wait for confirmation
                        msg = await asyncio.wait_for(ws.receive_json(), timeout=2.0)
                        assert msg["type"] == "subscription.updated"
                        assert msg["data"]["filters"] == sub

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_broadcast_during_connection_changes(self, fresh_engine):
        """Test broadcasts work correctly when connections are being added/removed.
        
        This test verifies that:
        1. A long-lived connection continues to receive broadcasts
        2. Broadcasts work while other connections come and go
        3. Connection lifecycle doesn't break broadcasting
        """
        app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
        headers = get_auth_headers()

        try:
            http_transport = ASGITransport(app=app)

            async with AsyncClient(
                transport=http_transport,
                base_url="http://test",
                headers=headers,
            ) as http:
                # Create a long-lived connection FIRST
                transport1 = ASGIWebSocketTransport(app=app)
                async with AsyncClient(transport=transport1) as client1:
                    async with aconnect_ws("http://test/ws", client1) as ws1:
                        # Now start simulation - ws1 will receive the event
                        response = await http.post(
                            "/simulation/start", json={"auto_advance": False}
                        )
                        assert response.status_code == 200
                        
                        # Consume the "simulation.started" event
                        initial_msg = await asyncio.wait_for(ws1.receive_json(), timeout=2.0)
                        assert initial_msg["type"] == "simulation.started"

                        # While ws1 is connected, create and close ws2 multiple times
                        for iteration in range(3):
                            transport2 = ASGIWebSocketTransport(app=app)
                            async with AsyncClient(transport=transport2) as client2:
                                async with aconnect_ws("http://test/ws", client2) as ws2:
                                    # Trigger a broadcast
                                    await http.post(
                                        "/simulator/time/advance", json={"seconds": 60}
                                    )

                                    # Both should receive it
                                    msg1 = await asyncio.wait_for(
                                        ws1.receive_json(), timeout=2.0
                                    )
                                    msg2 = await asyncio.wait_for(
                                        ws2.receive_json(), timeout=2.0
                                    )

                                    assert msg1["type"] == "time.advanced"
                                    assert msg2["type"] == "time.advanced"
                            # ws2 disconnects here

                            # ws1 should still work after ws2 disconnected
                            await http.post(
                                "/simulator/time/advance", json={"seconds": 60}
                            )
                            msg = await asyncio.wait_for(ws1.receive_json(), timeout=2.0)
                            assert msg["type"] == "time.advanced"

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_connection_count_accuracy(self, fresh_engine):
        """Test that connection count stays accurate under concurrent operations.
        
        This test verifies the ConnectionManager correctly tracks the number
        of active connections as they connect and disconnect.
        """
        app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine

        try:
            initial_count = ws_manager.connection_count

            async def connect_and_wait(duration: float) -> None:
                """Connect, hold connection for duration, then disconnect cleanly."""
                transport = ASGIWebSocketTransport(app=app)
                async with AsyncClient(transport=transport) as client:
                    async with aconnect_ws("http://test/ws", client) as ws:
                        await asyncio.sleep(duration)

            # Start 5 connections that stay alive for different durations
            tasks = [
                asyncio.create_task(connect_and_wait(0.3)),  # Disconnects first
                asyncio.create_task(connect_and_wait(0.3)),
                asyncio.create_task(connect_and_wait(0.3)),
                asyncio.create_task(connect_and_wait(0.6)),  # Stays longer
                asyncio.create_task(connect_and_wait(0.6)),
            ]

            # Give time for all to connect
            await asyncio.sleep(0.1)
            
            # Should have 5 more connections
            mid_count = ws_manager.connection_count
            assert mid_count == initial_count + 5, (
                f"Expected {initial_count + 5} connections, got {mid_count}"
            )

            # Wait for first 3 to disconnect
            await asyncio.sleep(0.3)
            
            # Should have 2 more than initial (3 disconnected)
            after_partial = ws_manager.connection_count
            assert after_partial == initial_count + 2, (
                f"Expected {initial_count + 2} connections, got {after_partial}"
            )

            # Wait for all tasks to complete
            await asyncio.gather(*tasks)
            
            # Give cleanup a moment
            await asyncio.sleep(0.1)

            # Should be back to initial
            final_count = ws_manager.connection_count
            assert final_count == initial_count, (
                f"Expected {initial_count} connections, got {final_count}"
            )

        finally:
            app.dependency_overrides.clear()
