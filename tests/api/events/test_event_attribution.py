"""Integration tests for event attribution (Phase 5: API Access Control).

This module tests that events created via the API are properly attributed:
- agent_id defaults to the API key's key_id when not provided
- agent_id from request takes precedence when explicitly provided
- metadata["created_by_key"] is always set to the creating key's key_id
- Attribution works for all event creation endpoints:
  - POST /events (scheduled events)
  - POST /events/immediate (immediate execution events)
  - POST /events/batch (batch event creation)

These tests verify the Phase 5 requirements from the API Access Control plan.
"""

from datetime import datetime, timedelta
from typing import Any, Optional

import pytest
from fastapi.testclient import TestClient

from ues.api.auth import initialize_api_key_registry, shutdown_api_key_registry
from ues.api.dependencies import get_simulation_engine
from ues.main import app
from ues.models.event import EventStatus, SimulatorEvent
from tests.api.helpers import (
    make_event_request,
    chat_event_data,
    email_event_data,
    sms_event_data,
)


def find_event_by_id(engine, event_id: str) -> Optional[SimulatorEvent]:
    """Helper to find an event in the engine's queue by ID.
    
    Args:
        engine: The SimulationEngine instance.
        event_id: The event ID to find.
    
    Returns:
        The SimulatorEvent if found, None otherwise.
    """
    for event in engine.event_queue.events:
        if event.event_id == event_id:
            return event
    return None


class TestScheduledEventAttribution:
    """Tests for event attribution on POST /events endpoint."""
    
    def test_agent_id_defaults_to_api_key_id(self, client_with_engine):
        """When agent_id is not provided, it should default to API key's key_id."""
        client, engine = client_with_engine
        
        # Get current time and API key info
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Get the admin key's ID
        keys_response = client.get("/keys")
        admin_key = keys_response.json()["keys"][0]
        admin_key_id = admin_key["key_id"]
        
        # Create event without specifying agent_id
        event_time = current_time + timedelta(hours=1)
        response = client.post(
            "/events",
            json=make_event_request(
                event_time,
                "chat",
                chat_event_data(content="Test attribution"),
            ),
        )
        
        assert response.status_code == 200
        event_id = response.json()["event_id"]
        
        # Verify the event has agent_id set to the API key's key_id
        event = find_event_by_id(engine, event_id)
        assert event is not None
        assert event.agent_id == admin_key_id
    
    def test_explicit_agent_id_takes_precedence(self, client_with_engine):
        """When agent_id is provided in request, it should override the default."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        custom_agent_id = "my-custom-agent-123"
        
        # Create event with explicit agent_id
        event_time = current_time + timedelta(hours=1)
        response = client.post(
            "/events",
            json=make_event_request(
                event_time,
                "chat",
                chat_event_data(content="Test explicit agent_id"),
                agent_id=custom_agent_id,
            ),
        )
        
        assert response.status_code == 200
        event_id = response.json()["event_id"]
        
        # Verify the event uses the provided agent_id
        event = find_event_by_id(engine, event_id)
        assert event is not None
        assert event.agent_id == custom_agent_id
    
    def test_created_by_key_always_set_in_metadata(self, client_with_engine):
        """metadata["created_by_key"] should always be set to API key's key_id."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        keys_response = client.get("/keys")
        admin_key_id = keys_response.json()["keys"][0]["key_id"]
        
        # Create event without any metadata
        event_time = current_time + timedelta(hours=1)
        response = client.post(
            "/events",
            json=make_event_request(
                event_time,
                "chat",
                chat_event_data(content="Test created_by_key"),
            ),
        )
        
        assert response.status_code == 200
        event_id = response.json()["event_id"]
        
        # Verify metadata has created_by_key
        event = find_event_by_id(engine, event_id)
        assert event is not None
        assert "created_by_key" in event.metadata
        assert event.metadata["created_by_key"] == admin_key_id
    
    def test_created_by_key_with_explicit_agent_id(self, client_with_engine):
        """created_by_key should be set even when agent_id is explicitly provided."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        keys_response = client.get("/keys")
        admin_key_id = keys_response.json()["keys"][0]["key_id"]
        
        custom_agent_id = "different-agent"
        
        # Create event with custom agent_id
        event_time = current_time + timedelta(hours=1)
        response = client.post(
            "/events",
            json=make_event_request(
                event_time,
                "chat",
                chat_event_data(content="Test"),
                agent_id=custom_agent_id,
            ),
        )
        
        assert response.status_code == 200
        event_id = response.json()["event_id"]
        
        event = find_event_by_id(engine, event_id)
        assert event is not None
        # agent_id is the custom one
        assert event.agent_id == custom_agent_id
        # created_by_key is still the API key
        assert event.metadata["created_by_key"] == admin_key_id
    
    def test_user_metadata_preserved_alongside_created_by_key(self, client_with_engine):
        """User-provided metadata should be preserved, with created_by_key added."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        keys_response = client.get("/keys")
        admin_key_id = keys_response.json()["keys"][0]["key_id"]
        
        user_metadata = {
            "source": "test-suite",
            "version": "1.0.0",
            "custom_field": {"nested": "value"},
        }
        
        # Create event with user metadata
        event_time = current_time + timedelta(hours=1)
        response = client.post(
            "/events",
            json=make_event_request(
                event_time,
                "chat",
                chat_event_data(content="Test metadata merge"),
                metadata=user_metadata,
            ),
        )
        
        assert response.status_code == 200
        event_id = response.json()["event_id"]
        
        event = find_event_by_id(engine, event_id)
        assert event is not None
        
        # Verify user metadata is preserved
        assert event.metadata["source"] == "test-suite"
        assert event.metadata["version"] == "1.0.0"
        assert event.metadata["custom_field"] == {"nested": "value"}
        
        # Verify created_by_key is added
        assert event.metadata["created_by_key"] == admin_key_id
    
    def test_attribution_with_different_modalities(self, client_with_engine):
        """Attribution should work consistently across different modalities."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        keys_response = client.get("/keys")
        admin_key_id = keys_response.json()["keys"][0]["key_id"]
        
        test_cases = [
            ("chat", chat_event_data(content="Test")),
            ("email", email_event_data(subject="Test")),
            ("sms", sms_event_data(body="Test")),
        ]
        
        for modality, data in test_cases:
            event_time = current_time + timedelta(hours=1)
            response = client.post(
                "/events",
                json=make_event_request(event_time, modality, data),
            )
            
            assert response.status_code == 200, f"Failed for modality: {modality}"
            event_id = response.json()["event_id"]
            
            event = find_event_by_id(engine, event_id)
            assert event is not None
            assert event.agent_id == admin_key_id, f"agent_id mismatch for {modality}"
            assert event.metadata["created_by_key"] == admin_key_id, f"created_by_key mismatch for {modality}"


class TestImmediateEventAttribution:
    """Tests for event attribution on POST /events/immediate endpoint."""
    
    def test_agent_id_set_to_api_key(self, client_with_engine):
        """Immediate events should have agent_id set to the API key's key_id."""
        client, engine = client_with_engine
        
        keys_response = client.get("/keys")
        admin_key_id = keys_response.json()["keys"][0]["key_id"]
        
        response = client.post(
            "/events/immediate",
            json={
                "modality": "chat",
                "data": chat_event_data(content="Immediate test"),
            },
        )
        
        assert response.status_code == 200
        event_id = response.json()["event_id"]
        
        event = find_event_by_id(engine, event_id)
        assert event is not None
        assert event.agent_id == admin_key_id
    
    def test_created_by_key_set_in_metadata(self, client_with_engine):
        """Immediate events should have created_by_key in metadata."""
        client, engine = client_with_engine
        
        keys_response = client.get("/keys")
        admin_key_id = keys_response.json()["keys"][0]["key_id"]
        
        response = client.post(
            "/events/immediate",
            json={
                "modality": "chat",
                "data": chat_event_data(content="Immediate test"),
            },
        )
        
        assert response.status_code == 200
        event_id = response.json()["event_id"]
        
        event = find_event_by_id(engine, event_id)
        assert event is not None
        assert "created_by_key" in event.metadata
        assert event.metadata["created_by_key"] == admin_key_id
    
    def test_immediate_event_with_different_modalities(self, client_with_engine):
        """Attribution should work for immediate events across modalities."""
        client, engine = client_with_engine
        
        keys_response = client.get("/keys")
        admin_key_id = keys_response.json()["keys"][0]["key_id"]
        
        test_cases = [
            ("chat", chat_event_data(content="Test")),
            ("email", email_event_data(subject="Test")),
            ("sms", sms_event_data(body="Test")),
        ]
        
        for modality, data in test_cases:
            response = client.post(
                "/events/immediate",
                json={"modality": modality, "data": data},
            )
            
            assert response.status_code == 200, f"Failed for modality: {modality}"
            event_id = response.json()["event_id"]
            
            event = find_event_by_id(engine, event_id)
            assert event is not None
            assert event.agent_id == admin_key_id, f"agent_id mismatch for {modality}"
            assert event.metadata["created_by_key"] == admin_key_id, f"created_by_key mismatch for {modality}"


class TestBatchEventAttribution:
    """Tests for event attribution on POST /events/batch endpoint."""
    
    def test_agent_id_defaults_for_all_batch_events(self, client_with_engine):
        """All events in batch should have agent_id set from API key when not provided."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        keys_response = client.get("/keys")
        admin_key_id = keys_response.json()["keys"][0]["key_id"]
        
        # Create batch of events without agent_id
        events = [
            make_event_request(
                current_time + timedelta(hours=i),
                "chat",
                chat_event_data(content=f"Batch event {i}"),
            )
            for i in range(1, 4)
        ]
        
        response = client.post(
            "/events/batch",
            json={"events": events},
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["total_created"] == 3
        
        # Verify all events have correct agent_id
        for event_result in data["events"]:
            event = find_event_by_id(engine, event_result["event_id"])
            assert event is not None
            assert event.agent_id == admin_key_id
    
    def test_explicit_agent_id_takes_precedence_in_batch(self, client_with_engine):
        """Individual events in batch can override agent_id."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        keys_response = client.get("/keys")
        admin_key_id = keys_response.json()["keys"][0]["key_id"]
        
        custom_agent_id = "batch-custom-agent"
        
        # Mix of events: some with agent_id, some without
        events = [
            make_event_request(
                current_time + timedelta(hours=1),
                "chat",
                chat_event_data(content="Event 1 - no agent_id"),
            ),
            make_event_request(
                current_time + timedelta(hours=2),
                "chat",
                chat_event_data(content="Event 2 - custom agent_id"),
                agent_id=custom_agent_id,
            ),
            make_event_request(
                current_time + timedelta(hours=3),
                "chat",
                chat_event_data(content="Event 3 - no agent_id"),
            ),
        ]
        
        response = client.post(
            "/events/batch",
            json={"events": events},
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Event 1: defaults to API key
        event1 = find_event_by_id(engine, data["events"][0]["event_id"])
        assert event1.agent_id == admin_key_id
        
        # Event 2: uses custom agent_id
        event2 = find_event_by_id(engine, data["events"][1]["event_id"])
        assert event2.agent_id == custom_agent_id
        
        # Event 3: defaults to API key
        event3 = find_event_by_id(engine, data["events"][2]["event_id"])
        assert event3.agent_id == admin_key_id
    
    def test_created_by_key_set_for_all_batch_events(self, client_with_engine):
        """All events in batch should have created_by_key in metadata."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        keys_response = client.get("/keys")
        admin_key_id = keys_response.json()["keys"][0]["key_id"]
        
        events = [
            make_event_request(
                current_time + timedelta(hours=i),
                "chat",
                chat_event_data(content=f"Batch event {i}"),
            )
            for i in range(1, 4)
        ]
        
        response = client.post(
            "/events/batch",
            json={"events": events},
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify all events have created_by_key
        for event_result in data["events"]:
            event = find_event_by_id(engine, event_result["event_id"])
            assert event is not None
            assert "created_by_key" in event.metadata
            assert event.metadata["created_by_key"] == admin_key_id
    
    def test_created_by_key_with_custom_agent_id_in_batch(self, client_with_engine):
        """created_by_key should always be API key, even when agent_id is custom."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        keys_response = client.get("/keys")
        admin_key_id = keys_response.json()["keys"][0]["key_id"]
        
        custom_agent_id = "another-custom-agent"
        
        events = [
            make_event_request(
                current_time + timedelta(hours=1),
                "chat",
                chat_event_data(content="Event with custom agent"),
                agent_id=custom_agent_id,
            ),
        ]
        
        response = client.post(
            "/events/batch",
            json={"events": events},
        )
        
        assert response.status_code == 201
        event_id = response.json()["events"][0]["event_id"]
        
        event = find_event_by_id(engine, event_id)
        assert event is not None
        assert event.agent_id == custom_agent_id
        assert event.metadata["created_by_key"] == admin_key_id
    
    def test_user_metadata_preserved_in_batch(self, client_with_engine):
        """User metadata should be preserved in batch events with created_by_key added."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        keys_response = client.get("/keys")
        admin_key_id = keys_response.json()["keys"][0]["key_id"]
        
        user_metadata = {"batch_id": "test-batch-001", "priority_level": "high"}
        
        events = [
            make_event_request(
                current_time + timedelta(hours=1),
                "chat",
                chat_event_data(content="Event with metadata"),
                metadata=user_metadata,
            ),
        ]
        
        response = client.post(
            "/events/batch",
            json={"events": events},
        )
        
        assert response.status_code == 201
        event_id = response.json()["events"][0]["event_id"]
        
        event = find_event_by_id(engine, event_id)
        assert event is not None
        
        # User metadata preserved
        assert event.metadata["batch_id"] == "test-batch-001"
        assert event.metadata["priority_level"] == "high"
        
        # created_by_key added
        assert event.metadata["created_by_key"] == admin_key_id
    
    def test_attribution_in_validate_only_mode(self, client_with_engine):
        """validate_only mode should not create events, so no attribution to verify."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Get initial event count
        initial_events = len(engine.event_queue.events)
        
        events = [
            make_event_request(
                current_time + timedelta(hours=1),
                "chat",
                chat_event_data(content="Validation test"),
            ),
        ]
        
        response = client.post(
            "/events/batch",
            json={"events": events, "validate_only": True},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["validation_only"] is True
        assert data["total_valid"] == 1
        
        # No events should be created
        assert len(engine.event_queue.events) == initial_events


class TestAttributionWithDifferentApiKeys:
    """Tests for event attribution with multiple API keys."""
    
    def test_different_keys_have_different_attribution(self, fresh_engine):
        """Events created by different keys should have different attribution."""
        from ues.api.auth import get_api_key_registry
        
        # Setup
        app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
        admin_secret, admin_key = initialize_api_key_registry()
        
        client = TestClient(app)
        client.headers["X-API-Key"] = admin_secret
        
        # Start simulation
        response = client.post("/simulation/start", json={"auto_advance": False})
        assert response.status_code == 200
        
        # Create a second API key with limited permissions
        response = client.post(
            "/keys",
            json={
                "name": "limited-agent-key",
                "permissions": ["events:create", "events:list", "events:read", "time:read"],
            },
        )
        assert response.status_code == 201
        limited_key_data = response.json()
        limited_key_id = limited_key_data["key_id"]
        limited_key_secret = limited_key_data["secret"]
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create event with admin key
        event_time = current_time + timedelta(hours=1)
        response = client.post(
            "/events",
            json=make_event_request(
                event_time,
                "chat",
                chat_event_data(content="Admin event"),
            ),
        )
        assert response.status_code == 200
        admin_event_id = response.json()["event_id"]
        
        # Switch to limited key and create event
        client.headers["X-API-Key"] = limited_key_secret
        
        event_time = current_time + timedelta(hours=2)
        response = client.post(
            "/events",
            json=make_event_request(
                event_time,
                "chat",
                chat_event_data(content="Limited key event"),
            ),
        )
        assert response.status_code == 200
        limited_event_id = response.json()["event_id"]
        
        # Verify different attributions
        admin_event = find_event_by_id(fresh_engine, admin_event_id)
        limited_event = find_event_by_id(fresh_engine, limited_event_id)
        
        assert admin_event.agent_id == admin_key.key_id
        assert admin_event.metadata["created_by_key"] == admin_key.key_id
        
        assert limited_event.agent_id == limited_key_id
        assert limited_event.metadata["created_by_key"] == limited_key_id
        
        # Cleanup
        shutdown_api_key_registry()
        app.dependency_overrides.clear()


class TestAttributionEdgeCases:
    """Edge case tests for event attribution."""
    
    def test_empty_string_agent_id_uses_default(self, client_with_engine):
        """Empty string agent_id should be treated as not provided (use default)."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        keys_response = client.get("/keys")
        admin_key_id = keys_response.json()["keys"][0]["key_id"]
        
        # Create event with empty string agent_id
        event_time = current_time + timedelta(hours=1)
        response = client.post(
            "/events",
            json=make_event_request(
                event_time,
                "chat",
                chat_event_data(content="Test"),
                agent_id="",  # Empty string
            ),
        )
        
        assert response.status_code == 200
        event_id = response.json()["event_id"]
        
        event = find_event_by_id(engine, event_id)
        assert event is not None
        # Empty string should trigger default to API key
        assert event.agent_id == admin_key_id
    
    def test_null_agent_id_uses_default(self, client_with_engine):
        """Null/None agent_id should use default (API key)."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        keys_response = client.get("/keys")
        admin_key_id = keys_response.json()["keys"][0]["key_id"]
        
        # Create event with explicit null agent_id
        event_time = current_time + timedelta(hours=1)
        request_data = {
            "scheduled_time": event_time.isoformat(),
            "modality": "chat",
            "data": chat_event_data(content="Test"),
            "agent_id": None,
        }
        
        response = client.post("/events", json=request_data)
        
        assert response.status_code == 200
        event_id = response.json()["event_id"]
        
        event = find_event_by_id(engine, event_id)
        assert event is not None
        assert event.agent_id == admin_key_id
    
    def test_whitespace_agent_id_is_preserved(self, client_with_engine):
        """Whitespace-only agent_id should be treated as provided (not default)."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create event with whitespace agent_id
        event_time = current_time + timedelta(hours=1)
        response = client.post(
            "/events",
            json=make_event_request(
                event_time,
                "chat",
                chat_event_data(content="Test"),
                agent_id="   ",  # Whitespace only - this is truthy in Python
            ),
        )
        
        assert response.status_code == 200
        event_id = response.json()["event_id"]
        
        event = find_event_by_id(engine, event_id)
        assert event is not None
        # Whitespace string is truthy, so it should be preserved
        assert event.agent_id == "   "
    
    def test_created_by_key_cannot_be_overwritten_by_user_metadata(self, client_with_engine):
        """User cannot override created_by_key in their metadata."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        keys_response = client.get("/keys")
        admin_key_id = keys_response.json()["keys"][0]["key_id"]
        
        # Try to set created_by_key in user metadata
        malicious_metadata = {
            "created_by_key": "fake-key-id",
            "other_field": "value",
        }
        
        event_time = current_time + timedelta(hours=1)
        response = client.post(
            "/events",
            json=make_event_request(
                event_time,
                "chat",
                chat_event_data(content="Test"),
                metadata=malicious_metadata,
            ),
        )
        
        assert response.status_code == 200
        event_id = response.json()["event_id"]
        
        event = find_event_by_id(engine, event_id)
        assert event is not None
        
        # created_by_key should be the actual API key, not the fake one
        assert event.metadata["created_by_key"] == admin_key_id
        # Other user metadata should still be there
        assert event.metadata["other_field"] == "value"
