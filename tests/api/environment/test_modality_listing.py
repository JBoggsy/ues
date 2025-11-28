"""Integration tests for modality listing endpoints.

This module tests the GET /environment/modalities endpoint, which allows clients to:
- Get a lightweight list of available modalities
- Check which modalities are present without fetching full state
- Get a count of total modalities

Following patterns from API_TESTING_GUIDELINES.md.
"""

from datetime import datetime, timedelta

from tests.api.helpers import make_event_request, location_event_data


class TestListModalities:
    """Tests for GET /environment/modalities endpoint."""
    
    def test_list_modalities_returns_all_types(self, client_with_engine):
        """Test that GET /environment/modalities returns all modality names.
        
        Verifies that the endpoint returns:
        - A list of modality names
        - The total count of modalities
        - All implemented modalities (location, time, weather, chat, email, calendar, sms)
        """
        client, _ = client_with_engine
        
        # Get modality list
        response = client.get("/environment/modalities")
        
        # Verify response structure
        assert response.status_code == 200
        data = response.json()
        
        assert "modalities" in data
        assert "count" in data
        
        # Verify modalities is a list
        assert isinstance(data["modalities"], list)
        
        # Verify count matches length of modalities list
        assert data["count"] == len(data["modalities"])
        
        # Verify all expected modality names are present
        expected_modalities = {"location", "time", "weather", "chat", "email", "calendar", "sms"}
        actual_modalities = set(data["modalities"])
        assert actual_modalities == expected_modalities
        
        # Verify exact count
        assert data["count"] == 7
    
    def test_list_modalities_matches_environment_state(self, client_with_engine):
        """Test that modality list matches modalities in environment state.
        
        Verifies consistency between /environment/modalities and
        /environment/state endpoints.
        """
        client, _ = client_with_engine
        
        # Get modality list
        list_response = client.get("/environment/modalities")
        assert list_response.status_code == 200
        list_data = list_response.json()
        
        # Get full environment state
        state_response = client.get("/environment/state")
        assert state_response.status_code == 200
        state_data = state_response.json()
        
        # Verify modalities list matches keys in state.modalities dict
        list_modalities = set(list_data["modalities"])
        state_modalities = set(state_data["modalities"].keys())
        assert list_modalities == state_modalities
        
        # Verify counts match
        assert list_data["count"] == len(state_data["modalities"])
        
        # Verify summary count also matches
        assert list_data["count"] == len(state_data["summary"])
    
    def test_list_modalities_count_is_accurate(self, client_with_engine):
        """Test that the count field accurately reflects the list length."""
        client, _ = client_with_engine
        
        # Get modality list
        response = client.get("/environment/modalities")
        assert response.status_code == 200
        data = response.json()
        
        # Verify count == len(modalities)
        assert data["count"] == len(data["modalities"])
        
        # Verify count is correct integer (not string or other type)
        assert isinstance(data["count"], int)
        assert data["count"] > 0
    
    def test_list_modalities_lightweight_response(self, client_with_engine):
        """Test that modality list response is lightweight.
        
        Verifies that this endpoint doesn't return full state data,
        only the list of modality names.
        """
        client, _ = client_with_engine
        
        # Get modality list
        response = client.get("/environment/modalities")
        assert response.status_code == 200
        data = response.json()
        
        # Verify response only contains modalities and count
        assert set(data.keys()) == {"modalities", "count"}
        
        # Verify modalities list contains only strings (names, not full state objects)
        for modality in data["modalities"]:
            assert isinstance(modality, str)
        
        # Compare response size - list should be much smaller than full state
        state_response = client.get("/environment/state")
        state_data = state_response.json()
        
        # Full state should have nested modality data
        assert "modalities" in state_data
        # Each modality in full state should be a dict with multiple fields
        for modality_name in data["modalities"]:
            assert isinstance(state_data["modalities"][modality_name], dict)
            assert len(state_data["modalities"][modality_name]) > 1
