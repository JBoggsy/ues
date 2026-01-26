"""Tests for event attribution (agent_id tracking).

This module tests that events are correctly attributed to the agent/API key
that created them. This is critical for the AgentBeats competition where
the executor needs to track which events were created by the Purple agent.

Key behaviors tested:
- agent_id from request is used when access control is disabled
- agent_id filter works correctly in list_events
- agent_id is included in EventResponse

Note: Tests for agent_id extraction from AccessContext when access control
is enabled are in test_event_attribution_access_control.py to avoid
middleware state pollution.
"""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_simulation_engine
from main import app
from tests.api.helpers import (
    chat_event_data,
    email_event_data,
    make_event_request,
)


# =============================================================================
# Tests: Event Attribution Without Access Control
# =============================================================================


class TestEventAttributionNoAccessControl:
    """Tests for agent_id when access control is disabled."""
    
    def test_create_event_with_agent_id_in_request(self, client_with_engine):
        """When access control is disabled, agent_id from request should be used."""
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        event_time = current_time + timedelta(hours=1)
        
        # Create event with agent_id in request
        request_data = make_event_request(
            event_time,
            "chat",
            chat_event_data(content="Test from purple agent"),
        )
        request_data["agent_id"] = "purple-agent"
        
        response = client.post("/events", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == "purple-agent"
    
    def test_create_event_without_agent_id(self, client_with_engine):
        """When no agent_id is provided, it should be None."""
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        event_time = current_time + timedelta(hours=1)
        
        # Create event without agent_id
        request_data = make_event_request(
            event_time,
            "chat",
            chat_event_data(content="Test message"),
        )
        
        response = client.post("/events", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] is None
    
    def test_create_immediate_event_with_agent_id(self, client_with_engine):
        """Immediate event creation should also support agent_id."""
        client, engine = client_with_engine
        
        response = client.post(
            "/events/immediate",
            json={
                "modality": "chat",
                "data": chat_event_data(content="Immediate message"),
                "agent_id": "purple-agent",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == "purple-agent"
    
    def test_create_batch_events_with_agent_id(self, client_with_engine):
        """Batch event creation should support agent_id per event."""
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        events = [
            {
                "scheduled_time": (current_time + timedelta(hours=1)).isoformat(),
                "modality": "chat",
                "data": chat_event_data(content="Message 1"),
                "agent_id": "purple-agent",
            },
            {
                "scheduled_time": (current_time + timedelta(hours=2)).isoformat(),
                "modality": "chat",
                "data": chat_event_data(content="Message 2"),
                "agent_id": "green-agent",
            },
        ]
        
        response = client.post("/events/batch", json={"events": events})
        
        assert response.status_code == 201
        data = response.json()
        assert len(data["events"]) == 2
        
        # Get the created events to verify agent_id
        events_response = client.get("/events")
        events_data = events_response.json()
        agent_ids = {e["agent_id"] for e in events_data["events"]}
        assert "purple-agent" in agent_ids
        assert "green-agent" in agent_ids


# =============================================================================
# Tests: Event Attribution Filtering
# =============================================================================


class TestEventAttributionFiltering:
    """Tests for filtering events by agent_id."""
    
    def test_filter_events_by_agent_id(self, client_with_engine):
        """Events can be filtered by agent_id."""
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create events from different agents
        for i, agent in enumerate(["purple-agent", "purple-agent", "green-agent"]):
            request_data = make_event_request(
                current_time + timedelta(hours=i + 1),
                "chat",
                chat_event_data(content=f"Message from {agent}"),
            )
            request_data["agent_id"] = agent
            response = client.post("/events", json=request_data)
            assert response.status_code == 200
        
        # Filter by purple-agent
        response = client.get("/events", params={"agent_id": "purple-agent"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 2
        for event in data["events"]:
            assert event["agent_id"] == "purple-agent"
        
        # Filter by green-agent
        response = client.get("/events", params={"agent_id": "green-agent"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 1
        assert data["events"][0]["agent_id"] == "green-agent"
    
    def test_filter_events_by_nonexistent_agent(self, client_with_engine):
        """Filtering by nonexistent agent_id returns empty list."""
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create an event
        request_data = make_event_request(
            current_time + timedelta(hours=1),
            "chat",
            chat_event_data(content="Test"),
        )
        request_data["agent_id"] = "purple-agent"
        client.post("/events", json=request_data)
        
        # Filter by nonexistent agent
        response = client.get("/events", params={"agent_id": "nonexistent-agent"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 0
    
    def test_agent_id_filter_combined_with_status(self, client_with_engine):
        """agent_id filter can be combined with other filters."""
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create events
        for i in range(3):
            request_data = make_event_request(
                current_time + timedelta(hours=i + 1),
                "chat",
                chat_event_data(content=f"Message {i}"),
            )
            request_data["agent_id"] = "purple-agent"
            client.post("/events", json=request_data)
        
        # Filter by agent_id and status
        response = client.get(
            "/events",
            params={"agent_id": "purple-agent", "status": "pending"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 3
        for event in data["events"]:
            assert event["agent_id"] == "purple-agent"
            assert event["status"] == "pending"
    
    def test_agent_id_filter_combined_with_modality(self, client_with_engine):
        """agent_id filter can be combined with modality filter."""
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create chat event
        request_data = make_event_request(
            current_time + timedelta(hours=1),
            "chat",
            chat_event_data(content="Chat message"),
        )
        request_data["agent_id"] = "purple-agent"
        client.post("/events", json=request_data)
        
        # Create email event
        request_data = make_event_request(
            current_time + timedelta(hours=2),
            "email",
            email_event_data(
                operation="receive",
                from_address="sender@example.com",
                to_addresses=["user@example.com"],
                subject="Test",
                body_text="Test body",
            ),
        )
        request_data["agent_id"] = "purple-agent"
        client.post("/events", json=request_data)
        
        # Filter by agent_id and modality
        response = client.get(
            "/events",
            params={"agent_id": "purple-agent", "modality": "email"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 1
        assert data["events"][0]["modality"] == "email"


# =============================================================================
# Tests: Event Response Contains agent_id
# =============================================================================


class TestEventResponseAgentId:
    """Tests that agent_id is properly included in event responses."""
    
    def test_event_response_includes_agent_id(self, client_with_engine):
        """EventResponse should include agent_id field."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        event_time = current_time + timedelta(hours=1)
        
        request_data = make_event_request(
            event_time,
            "chat",
            chat_event_data(content="Test"),
        )
        request_data["agent_id"] = "test-agent"
        
        response = client.post("/events", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify agent_id is in response
        assert "agent_id" in data
        assert data["agent_id"] == "test-agent"
    
    def test_get_event_includes_agent_id(self, client_with_engine):
        """GET /events/{id} should include agent_id in response."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        event_time = current_time + timedelta(hours=1)
        
        # Create event
        request_data = make_event_request(
            event_time,
            "chat",
            chat_event_data(content="Test"),
        )
        request_data["agent_id"] = "test-agent"
        
        create_response = client.post("/events", json=request_data)
        event_id = create_response.json()["event_id"]
        
        # Get event
        response = client.get(f"/events/{event_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == "test-agent"
    
    def test_list_events_includes_agent_id(self, client_with_engine):
        """GET /events should include agent_id in each event."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create events with different agent_ids
        for agent in ["agent-1", "agent-2"]:
            request_data = make_event_request(
                current_time + timedelta(hours=1),
                "chat",
                chat_event_data(content="Test"),
            )
            request_data["agent_id"] = agent
            client.post("/events", json=request_data)
        
        # List all events
        response = client.get("/events")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all events have agent_id
        for event in data["events"]:
            assert "agent_id" in event
