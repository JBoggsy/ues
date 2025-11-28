"""Integration tests for GET /location/state endpoint."""

from datetime import datetime, timezone


class TestGetLocationState:
    """Tests for GET /location/state endpoint."""

    def test_returns_correct_structure(self, client_with_engine):
        """Test that GET /location/state returns response with correct structure.
        
        Per LocationStateResponse model, response should include:
        - modality_type: "location"
        - last_updated: ISO format timestamp
        - update_count: integer
        - current: dict with location data
        - history: list of location entries
        """
        client, engine = client_with_engine
        
        response = client.get("/location/state")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "modality_type" in data
        assert data["modality_type"] == "location"
        assert "last_updated" in data
        assert "update_count" in data
        assert isinstance(data["update_count"], int)
        assert "current" in data
        assert isinstance(data["current"], dict)
        assert "history" in data
        assert isinstance(data["history"], list)

    def test_returns_initial_location(self, client_with_engine):
        """Test that state has initial location from test fixture.
        
        Note: The fresh_engine fixture initializes LocationState with default
        coordinates (San Francisco: 37.7749, -122.4194) for consistent testing.
        """
        client, engine = client_with_engine
        
        response = client.get("/location/state")
        
        assert response.status_code == 200
        data = response.json()
        
        # Fixture sets initial location (San Francisco)
        assert data["current"]["latitude"] == 37.7749
        assert data["current"]["longitude"] == -122.4194
        # No updates have been made yet via the API
        assert data["update_count"] == 0
        assert data["history"] == []

    def test_reflects_location_update(self, client_with_engine):
        """Test that state shows updated location after update action."""
        client, engine = client_with_engine
        
        # Update location
        update_response = client.post(
            "/location/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "address": "New York, NY",
            },
        )
        assert update_response.status_code == 200
        
        # Check state reflects update
        state_response = client.get("/location/state")
        assert state_response.status_code == 200
        
        data = state_response.json()
        assert data["update_count"] == 1
        assert data["current"]["latitude"] == 40.7128
        assert data["current"]["longitude"] == -74.0060
        assert data["current"]["address"] == "New York, NY"

    def test_includes_location_history(self, client_with_engine):
        """Test that state includes location history after multiple updates.
        
        Note: Fixture initializes with San Francisco location, which becomes
        first history entry when we update location.
        """
        client, engine = client_with_engine
        
        # First update - moves initial SF location to history
        client.post(
            "/location/update",
            json={"latitude": 40.7128, "longitude": -74.0060, "named_location": "Office"},
        )
        
        # Second update - moves Office to history
        client.post(
            "/location/update",
            json={"latitude": 34.0522, "longitude": -118.2437, "named_location": "Home"},
        )
        
        state_response = client.get("/location/state")
        data = state_response.json()
        
        assert data["update_count"] == 2
        assert data["current"]["latitude"] == 34.0522
        assert data["current"]["longitude"] == -118.2437
        assert data["current"]["named_location"] == "Home"
        
        # History should contain initial SF and Office locations (2 entries)
        assert len(data["history"]) == 2
        # First history entry is initial SF location
        assert data["history"][0]["latitude"] == 37.7749
        assert data["history"][0]["longitude"] == -122.4194
        # Second history entry is Office
        assert data["history"][1]["latitude"] == 40.7128
        assert data["history"][1]["longitude"] == -74.0060
        assert data["history"][1]["named_location"] == "Office"

    def test_includes_named_locations(self, client_with_engine):
        """Test that state includes named location when set."""
        client, engine = client_with_engine
        
        client.post(
            "/location/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "named_location": "Work",
                "address": "123 Business Ave",
            },
        )
        
        state_response = client.get("/location/state")
        data = state_response.json()
        
        assert data["current"]["named_location"] == "Work"
        assert data["current"]["address"] == "123 Business Ave"

    def test_last_updated_changes_with_updates(self, client_with_engine):
        """Test that last_updated timestamp changes when location is updated."""
        client, engine = client_with_engine
        
        # Advance simulator time first to ensure a time difference
        client.post("/simulator/time/advance", json={"seconds": 60})
        
        # Get time before update
        time_response = client.get("/simulator/time")
        before_update_time = datetime.fromisoformat(
            time_response.json()["current_time"].replace("Z", "+00:00")
        )
        
        # Update location
        client.post(
            "/location/update",
            json={"latitude": 40.7128, "longitude": -74.0060},
        )
        
        # Get updated state
        updated_response = client.get("/location/state")
        updated_time = datetime.fromisoformat(
            updated_response.json()["last_updated"].replace("Z", "+00:00")
        )
        
        # last_updated should be at or after the time before update
        assert updated_time >= before_update_time

    def test_includes_all_optional_metadata(self, client_with_engine):
        """Test that state includes all optional metadata fields when provided."""
        client, engine = client_with_engine
        
        client.post(
            "/location/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "address": "New York, NY",
                "named_location": "Office",
                "altitude": 10.5,
                "accuracy": 5.0,
                "speed": 1.5,
                "bearing": 90.0,
            },
        )
        
        state_response = client.get("/location/state")
        data = state_response.json()
        
        current = data["current"]
        assert current["latitude"] == 40.7128
        assert current["longitude"] == -74.0060
        assert current["address"] == "New York, NY"
        assert current["named_location"] == "Office"
        assert current["altitude"] == 10.5
        assert current["accuracy"] == 5.0
        assert current["speed"] == 1.5
        assert current["bearing"] == 90.0
