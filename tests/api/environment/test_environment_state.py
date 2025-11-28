"""Integration tests for environment state retrieval endpoints.

This module tests the GET /environment/state endpoint, which allows clients to:
- Get a complete snapshot of the current environment state
- View all modality states at once
- See the current simulator time
- Get summary information about each modality

Following patterns from API_TESTING_GUIDELINES.md.
"""

from datetime import datetime, timedelta

from tests.api.helpers import (
    make_event_request,
    location_event_data,
)


class TestGetEnvironmentState:
    """Tests for GET /environment/state endpoint."""
    
    def test_get_state_returns_complete_snapshot(self, client_with_engine):
        """Test that GET /environment/state returns all modality states.
        
        Verifies that the endpoint returns:
        - Current simulator time
        - Dictionary of all modality states
        - Summary list with brief info for each modality
        """
        client, _ = client_with_engine
        
        # Get environment state
        response = client.get("/environment/state")
        
        # Verify response structure
        assert response.status_code == 200
        data = response.json()
        
        # Verify all top-level fields exist
        assert "current_time" in data
        assert "modalities" in data
        assert "summary" in data
        
        # Verify current_time is valid ISO format
        current_time = datetime.fromisoformat(data["current_time"])
        assert current_time is not None
        assert current_time.tzinfo is not None  # Should have timezone
        
        # Verify modalities is a dict
        assert isinstance(data["modalities"], dict)
        
        # Verify all implemented modalities are present
        expected_modalities = {"location", "time", "weather", "chat", "email", "calendar", "sms"}
        assert set(data["modalities"].keys()) == expected_modalities
        
        # Verify summary is a list
        assert isinstance(data["summary"], list)
        assert len(data["summary"]) == len(expected_modalities)
        
        # Verify each summary has correct structure
        for summary in data["summary"]:
            assert "modality_type" in summary
            assert "state_summary" in summary
            assert isinstance(summary["modality_type"], str)
            assert isinstance(summary["state_summary"], str)
    
    def test_get_state_reflects_modality_changes(self, client_with_engine):
        """Test that GET /environment/state reflects state changes after events.
        
        Creates and executes a location event, then verifies the environment state
        reflects the change.
        """
        client, _ = client_with_engine
        
        # Get initial state
        initial_response = client.get("/environment/state")
        initial_data = initial_response.json()
        initial_location = initial_data["modalities"]["location"]
        
        # Get current time and create location update event
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        new_latitude = 40.7128
        new_longitude = -74.0060
        
        # Create immediate event to update location
        event_response = client.post(
            "/events/immediate",
            json={
                "modality": "location",
                "data": location_event_data(
                    latitude=new_latitude,
                    longitude=new_longitude,
                    address="New York, NY",
                ),
            },
        )
        assert event_response.status_code == 200
        
        # Advance time by 1 second to execute the event
        advance_response = client.post("/simulator/time/advance", json={"seconds": 1})
        assert advance_response.status_code == 200
        
        # Get updated state
        updated_response = client.get("/environment/state")
        updated_data = updated_response.json()
        updated_location = updated_data["modalities"]["location"]
        
        # Verify location state changed
        assert updated_location["current_latitude"] == new_latitude
        assert updated_location["current_longitude"] == new_longitude
        assert updated_location["current_address"] == "New York, NY"
        
        # Verify it's different from initial state
    def test_get_state_includes_all_registered_modalities(self, client_with_engine):
        """Test that GET /environment/state includes all modalities in the environment.
        
        Verifies that the response includes states for all modalities registered
        in the environment, even if they haven't been modified yet.
        """
        client, _ = client_with_engine
        
        # Get environment state
        response = client.get("/environment/state")
        assert response.status_code == 200
        data = response.json()
        
        # fresh_engine creates environment with all implemented modalities
        expected_modalities = {"location", "time", "weather", "chat", "email", "calendar", "sms"}
        
        # Verify all expected modalities are present
        for modality in expected_modalities:
            assert modality in data["modalities"], f"Missing modality: {modality}"
        
        # Verify no extra modalities
        assert set(data["modalities"].keys()) == expected_modalities
        
        # Verify modalities dict and summary list have same count
        modality_count = len(data["modalities"])
        summary_count = len(data["summary"])
        assert modality_count == summary_count
        assert modality_count == len(expected_modalities)
        
        # Verify summary has entry for each modality in modalities dict
        summary_types = {s["modality_type"] for s in data["summary"]}
        modality_keys = set(data["modalities"].keys())
        assert summary_types == modality_keys
    
    def test_get_state_returns_current_time(self, client_with_engine):
        """Test that GET /environment/state returns correct current simulator time.
        
        Verifies that:
        - current_time field is present
        - Time matches the simulator's current time
        - Time format is ISO 8601
        """
        client, _ = client_with_engine
        
        # Get current time from /simulator/time
        time_response = client.get("/simulator/time")
        assert time_response.status_code == 200
        time_data = time_response.json()
        simulator_time = datetime.fromisoformat(time_data["current_time"])
        
        # Get environment state
        env_response = client.get("/environment/state")
        assert env_response.status_code == 200
        env_data = env_response.json()
        env_time = datetime.fromisoformat(env_data["current_time"])
        
        # Verify times match (should be within 1 second)
        time_diff = abs((env_time - simulator_time).total_seconds())
        assert time_diff < 1
        
        # Verify time is valid ISO 8601 format with timezone
        assert env_data["current_time"].endswith(("Z", "+00:00"))
        assert env_time.tzinfo is not None
    
    def test_get_state_time_changes_after_advance(self, client_with_engine):
        """Test that GET /environment/state reflects time changes.
        
        Advances simulator time and verifies that the environment state
        snapshot reflects the new time.
        """
        client, _ = client_with_engine
        
        # Get initial state
        initial_response = client.get("/environment/state")
        assert initial_response.status_code == 200
        initial_data = initial_response.json()
        initial_time = datetime.fromisoformat(initial_data["current_time"])
        
        # Advance time by 3600 seconds (1 hour)
        advance_seconds = 3600
        advance_response = client.post("/simulator/time/advance", json={"seconds": advance_seconds})
        assert advance_response.status_code == 200
        
        # Get updated state
        updated_response = client.get("/environment/state")
        assert updated_response.status_code == 200
        updated_data = updated_response.json()
        updated_time = datetime.fromisoformat(updated_data["current_time"])
        
        # Verify time increased by expected amount
        time_delta = (updated_time - initial_time).total_seconds()
        assert abs(time_delta - advance_seconds) < 1
    
    def test_get_state_summary_has_correct_structure(self, client_with_engine):
        """Test that GET /environment/state summary field has correct structure.
        
        Verifies that each summary entry contains:
        - modality_type: string
        - state_summary: string
        """
        client, _ = client_with_engine
        
        # Get environment state
        response = client.get("/environment/state")
        assert response.status_code == 200
        data = response.json()
        
        # Verify summary is a list
        assert isinstance(data["summary"], list)
        assert len(data["summary"]) > 0
        
        # For each summary entry, verify structure
        for summary in data["summary"]:
            # Verify required fields exist
            assert "modality_type" in summary
            assert "state_summary" in summary
            
            # Verify field types
            assert isinstance(summary["modality_type"], str)
            assert isinstance(summary["state_summary"], str)
            
            # Verify modality_type matches a key in modalities dict
            assert summary["modality_type"] in data["modalities"]
            
            # Verify state_summary is non-empty
            assert len(summary["state_summary"]) > 0
