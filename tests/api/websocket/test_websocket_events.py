"""Tests for WebSocket event broadcasting.

Tests that REST API actions correctly trigger WebSocket broadcasts
for connected clients.
"""

import asyncio
from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient
from httpx_ws import aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport

from ues.api.dependencies import get_simulation_engine
from ues.main import app


@asynccontextmanager
async def ws_with_http(fresh_engine):
    """Context manager providing both WebSocket and HTTP clients for integration testing."""
    app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
    
    try:
        ws_transport = ASGIWebSocketTransport(app=app)
        http_transport = ASGITransport(app=app)
        
        async with AsyncClient(transport=ws_transport) as ws_http_client:
            async with aconnect_ws("http://test/ws", ws_http_client) as ws:
                async with AsyncClient(transport=http_transport, base_url="http://test") as http:
                    # Start simulation first
                    response = await http.post("/simulation/start", json={"auto_advance": False})
                    assert response.status_code == 200
                    
                    # Consume the simulation.started event
                    try:
                        msg = await asyncio.wait_for(ws.receive_json(), timeout=1.0)
                        assert msg["type"] == "simulation.started"
                    except asyncio.TimeoutError:
                        pass  # Event might have been missed during connection
                    
                    yield ws, http
    finally:
        app.dependency_overrides.clear()





class TestSimulationEventBroadcasts:
    """Test simulation lifecycle event broadcasts."""
    
    @pytest.mark.asyncio
    async def test_simulation_started_broadcast(self, fresh_engine):
        """Test that starting simulation broadcasts simulation.started event."""
        app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
        
        try:
            ws_transport = ASGIWebSocketTransport(app=app)
            http_transport = ASGITransport(app=app)
            
            async with AsyncClient(transport=ws_transport) as ws_http_client:
                async with aconnect_ws("http://test/ws", ws_http_client) as ws:
                    async with AsyncClient(transport=http_transport, base_url="http://test") as http:
                        # Start simulation
                        response = await http.post("/simulation/start", json={"auto_advance": False})
                        assert response.status_code == 200
                        
                        # Should receive simulation.started event
                        msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
                        assert msg["type"] == "simulation.started"
                        assert "simulation_id" in msg["data"]
                        assert "current_time" in msg["data"]
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_simulation_stopped_broadcast(self, fresh_engine):
        """Test that stopping simulation broadcasts simulation.stopped event."""
        async with ws_with_http(fresh_engine) as (ws, http):
            # Stop simulation
            response = await http.post("/simulation/stop")
            assert response.status_code == 200
            
            # Should receive simulation.stopped event
            msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
            assert msg["type"] == "simulation.stopped"


class TestTimeEventBroadcasts:
    """Test time control event broadcasts."""
    
    @pytest.mark.asyncio
    async def test_time_advanced_broadcast(self, fresh_engine):
        """Test that advancing time broadcasts time.advanced event."""
        async with ws_with_http(fresh_engine) as (ws, http):
            # Advance time
            response = await http.post("/simulator/time/advance", json={"seconds": 60})
            assert response.status_code == 200
            
            # Should receive time.advanced event
            msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
            assert msg["type"] == "time.advanced"
            assert "current_time" in msg["data"]
            assert "previous_time" in msg["data"]
    
    @pytest.mark.asyncio
    async def test_time_set_broadcast(self, fresh_engine):
        """Test that setting time broadcasts time.set event."""
        async with ws_with_http(fresh_engine) as (ws, http):
            # Set time
            response = await http.post(
                "/simulator/time/set",
                json={"target_time": "2024-06-15T12:00:00Z"}
            )
            assert response.status_code == 200
            
            # Should receive time.set event
            msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
            assert msg["type"] == "time.set"
            assert "current_time" in msg["data"]


class TestModalityEventBroadcasts:
    """Test modality-specific event broadcasts."""
    
    @pytest.mark.asyncio
    async def test_email_received_broadcast(self, fresh_engine):
        """Test that receiving email broadcasts email.received event."""
        async with ws_with_http(fresh_engine) as (ws, http):
            # Receive an email
            response = await http.post(
                "/email/receive",
                json={
                    "from_address": "sender@example.com",
                    "to_addresses": ["user@example.com"],
                    "subject": "Test Email",
                    "body_text": "Hello, World!",
                }
            )
            assert response.status_code == 200
            
            # Should receive email.received event
            msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
            assert msg["type"] == "email.received"
            assert "subject" in msg["data"]
    
    @pytest.mark.asyncio
    async def test_sms_received_broadcast(self, fresh_engine):
        """Test that receiving SMS broadcasts sms.received event."""
        async with ws_with_http(fresh_engine) as (ws, http):
            # Receive an SMS
            response = await http.post(
                "/sms/receive",
                json={
                    "from_number": "+15551234567",
                    "to_numbers": ["+15550000000"],
                    "body": "Hello!",
                }
            )
            assert response.status_code == 200
            
            # Should receive sms.received event
            msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
            assert msg["type"] == "sms.received"
            assert "preview" in msg["data"]
    
    @pytest.mark.asyncio
    async def test_calendar_event_created_broadcast(self, fresh_engine):
        """Test that creating calendar event broadcasts calendar.event_created."""
        async with ws_with_http(fresh_engine) as (ws, http):
            # Create a calendar event
            response = await http.post(
                "/calendar/create",
                json={
                    "title": "Test Meeting",
                    "start": "2024-06-15T14:00:00Z",
                    "end": "2024-06-15T15:00:00Z",
                }
            )
            assert response.status_code == 200
            
            # Should receive calendar.event_created event
            msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
            assert msg["type"] == "calendar.event_created"
            assert "title" in msg["data"]
    
    @pytest.mark.asyncio
    async def test_location_updated_broadcast(self, fresh_engine):
        """Test that updating location broadcasts location.updated event."""
        async with ws_with_http(fresh_engine) as (ws, http):
            # Update location
            response = await http.post(
                "/location/update",
                json={
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                }
            )
            assert response.status_code == 200
            
            # Should receive location.updated event
            msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
            assert msg["type"] == "location.updated"
            assert "latitude" in msg["data"]
            assert "longitude" in msg["data"]


class TestMultipleClientsReceiveBroadcast:
    """Test that broadcasts reach all connected clients."""
    
    @pytest.mark.asyncio
    async def test_multiple_clients_receive_same_event(self, fresh_engine):
        """Test that multiple WebSocket clients all receive the same broadcast."""
        app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
        
        try:
            ws_transport1 = ASGIWebSocketTransport(app=app)
            ws_transport2 = ASGIWebSocketTransport(app=app)
            http_transport = ASGITransport(app=app)
            
            async with AsyncClient(transport=ws_transport1) as ws_client1:
                async with aconnect_ws("http://test/ws", ws_client1) as ws1:
                    async with AsyncClient(transport=ws_transport2) as ws_client2:
                        async with aconnect_ws("http://test/ws", ws_client2) as ws2:
                            async with AsyncClient(transport=http_transport, base_url="http://test") as http:
                                # Start simulation
                                response = await http.post("/simulation/start", json={"auto_advance": False})
                                assert response.status_code == 200
                                
                                # Both clients should receive the event
                                msg1 = await asyncio.wait_for(ws1.receive_json(), timeout=5.0)
                                msg2 = await asyncio.wait_for(ws2.receive_json(), timeout=5.0)
                                
                                assert msg1["type"] == "simulation.started"
                                assert msg2["type"] == "simulation.started"
                                assert msg1["data"]["simulation_id"] == msg2["data"]["simulation_id"]
        finally:
            app.dependency_overrides.clear()
