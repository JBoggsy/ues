"""Integration tests for individual modality state retrieval.

This module tests the GET /environment/modalities/{modality_name} endpoint, which allows clients to:
- Get the current state of a specific modality
- Fetch only the needed modality data (more efficient than full environment state)
- Include current time context with the state

Following patterns from API_TESTING_GUIDELINES.md.
"""

from datetime import datetime, timedelta

from tests.api.helpers import (
    make_event_request,
    email_event_data,
    location_event_data,
    chat_event_data,
    sms_event_data,
)


class TestGetModalityState:
    """Tests for GET /environment/modalities/{modality_name} endpoint."""
    
    def test_get_modality_state_returns_state(self, client_with_engine):
        """Test that GET /environment/modalities/{name} returns modality state.
        
        Verifies that the endpoint returns:
        - modality_type field
        - current_time field
        - state field with the modality's data
        """
        client, _ = client_with_engine
        
        # Get a specific modality state (e.g., location)
        response = client.get("/environment/modalities/location")
        
        # Verify response structure
        assert response.status_code == 200
        data = response.json()
        
        assert "modality_type" in data
        assert "current_time" in data
        assert "state" in data
        
        # Verify modality_type == "location"
        assert data["modality_type"] == "location"
        
        # Verify current_time is valid ISO format
        current_time = datetime.fromisoformat(data["current_time"])
        assert current_time is not None
        assert current_time.tzinfo is not None
        
        # Verify state contains expected fields for location modality
        state = data["state"]
        assert isinstance(state, dict)
        assert "modality_type" in state
        assert state["modality_type"] == "location"
        # LocationState has these fields
        assert "current_latitude" in state
        assert "current_longitude" in state
        assert "current_address" in state
        assert "location_history" in state
    
    def test_get_modality_state_all_modalities(self, client_with_engine):
        """Test that endpoint works for all registered modalities.
        
        Verifies that the endpoint returns valid state for each modality type.
        Tests all 7 implemented modalities: location, time, weather, chat, email, calendar, sms.
        """
        client, _ = client_with_engine
        
        # Get list of modalities
        modalities_response = client.get("/environment/modalities")
        modalities = modalities_response.json()["modalities"]
        
        # Expected modalities
        expected_modalities = {"location", "time", "weather", "chat", "email", "calendar", "sms"}
        assert set(modalities) == expected_modalities
        
        # For each modality, get its state
        for modality in modalities:
            response = client.get(f"/environment/modalities/{modality}")
            
            # Verify each returns 200 status
            assert response.status_code == 200, f"Failed for modality: {modality}"
            
            # Verify each has correct structure
            data = response.json()
            assert "modality_type" in data
            assert "current_time" in data
            assert "state" in data
            assert data["modality_type"] == modality
            assert isinstance(data["state"], dict)
            
            # Verify state has modality_type field matching the modality
            assert data["state"]["modality_type"] == modality
    
    def test_get_modality_state_invalid_modality(self, client_with_engine):
        """Test that GET /environment/modalities/{name} returns 404 for invalid modality.
        
        Verifies error handling for non-existent modality names.
        """
        client, _ = client_with_engine
        
        # Try to get state for non-existent modality
        response = client.get("/environment/modalities/nonexistent")
        
        # Verify returns 404
        assert response.status_code == 404
        
        # Verify error message mentions modality not found
        error_detail = response.json()["detail"]
        assert "modality" in error_detail.lower()
        assert "not found" in error_detail.lower() or "nonexistent" in error_detail.lower()
    
    def test_get_modality_state_reflects_changes(self, client_with_engine):
        """Test that modality state reflects changes after event execution.
        
        Creates and executes an event that modifies a modality, then verifies
        the state endpoint reflects the change.
        """
        client, _ = client_with_engine
        
        # Get initial location state
        initial_response = client.get("/environment/modalities/location")
        assert initial_response.status_code == 200
        initial_state = initial_response.json()["state"]
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create and execute location update event
        new_latitude = 51.5074
        new_longitude = -0.1278
        new_address = "London, UK"
        
        event_response = client.post(
            "/events/immediate",
            json={
                "modality": "location",
                "data": location_event_data(
                    latitude=new_latitude,
                    longitude=new_longitude,
                    address=new_address,
                ),
            },
        )
        assert event_response.status_code == 200
        
        # Advance time to execute the event
        advance_response = client.post("/simulator/time/advance", json={"seconds": 1})
        assert advance_response.status_code == 200
        
        # Get updated location state
        updated_response = client.get("/environment/modalities/location")
        assert updated_response.status_code == 200
        updated_state = updated_response.json()["state"]
        
        # Verify state changed appropriately
        assert updated_state["current_latitude"] == new_latitude
        assert updated_state["current_longitude"] == new_longitude
        assert updated_state["current_address"] == new_address
        
        # Verify it's different from initial state
        assert updated_state["current_latitude"] != initial_state["current_latitude"]
    
    def test_get_modality_state_includes_current_time(self, client_with_engine):
        """Test that modality state includes current simulator time.
        
        Verifies that the response includes temporal context so clients
        know "when" the state is from.
        """
        client, _ = client_with_engine
        
        # Get current time from /simulator/time
        time_response = client.get("/simulator/time")
        assert time_response.status_code == 200
        simulator_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Get modality state
        modality_response = client.get("/environment/modalities/location")
        assert modality_response.status_code == 200
        modality_data = modality_response.json()
        
        # Verify current_time matches simulator time (within 1 second tolerance)
        modality_time = datetime.fromisoformat(modality_data["current_time"])
        time_diff = abs((modality_time - simulator_time).total_seconds())
        assert time_diff < 1
    
    def test_get_modality_state_more_efficient_than_full_state(self, client_with_engine):
        """Test that modality state endpoint returns only requested modality.
        
        Verifies that this endpoint is more efficient than fetching the full
        environment state when only one modality is needed.
        """
        client, _ = client_with_engine
        
        # Get full environment state
        full_response = client.get("/environment/state")
        assert full_response.status_code == 200
        full_data = full_response.json()
        
        # Get single modality state
        single_response = client.get("/environment/modalities/email")
        assert single_response.status_code == 200
        single_data = single_response.json()
        
        # Verify modality response only contains one modality's data
        assert "state" in single_data
        assert "modality_type" in single_data
        assert single_data["modality_type"] == "email"
        
        # Verify the state data structure matches
        # Compare specific fields rather than entire dicts to avoid timezone format differences
        email_state_full = full_data["modalities"]["email"]
        email_state_single = single_data["state"]
        
        assert email_state_single["emails"] == email_state_full["emails"]
        assert email_state_single["threads"] == email_state_full["threads"]
        assert email_state_single["drafts"] == email_state_full["drafts"]
        assert email_state_single["labels"] == email_state_full["labels"]
        assert email_state_single["folders"] == email_state_full["folders"]
        
        # Verify full state has all 7 modalities while single has just one
        assert len(full_data["modalities"]) == 7
        assert single_data["modality_type"] == "email"
        assert single_data["state"]["modality_type"] == "email"
