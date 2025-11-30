"""Integration tests for location action endpoints."""


class TestPostLocationUpdate:
    """Tests for POST /location/update endpoint."""

    def test_update_location_succeeds(self, client_with_engine):
        """Test updating location creates event successfully.
        
        Per ModalityActionResponse model, response should include:
        - event_id: unique identifier
        - scheduled_time: when event was scheduled
        - status: execution status
        - message: description of action
        - modality: "location"
        """
        client, engine = client_with_engine
        
        response = client.post(
            "/location/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "event_id" in data
        assert "scheduled_time" in data
        assert data["modality"] == "location"
        assert data["status"] == "executed"

    def test_update_with_coordinates_only(self, client_with_engine):
        """Test updating location with only required lat/lon coordinates."""
        client, engine = client_with_engine
        
        response = client.post(
            "/location/update",
            json={
                "latitude": 37.7749,
                "longitude": -122.4194,
            },
        )
        
        assert response.status_code == 200
        
        # Verify state was updated
        state = client.get("/location/state").json()
        assert state["current"]["latitude"] == 37.7749
        assert state["current"]["longitude"] == -122.4194

    def test_update_with_named_location(self, client_with_engine):
        """Test updating location with named location (semantic label)."""
        client, engine = client_with_engine
        
        response = client.post(
            "/location/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "named_location": "Office",
            },
        )
        
        assert response.status_code == 200
        
        state = client.get("/location/state").json()
        assert state["current"]["named_location"] == "Office"

    def test_update_with_address(self, client_with_engine):
        """Test updating location with human-readable address."""
        client, engine = client_with_engine
        
        response = client.post(
            "/location/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "address": "123 Broadway, New York, NY 10006",
            },
        )
        
        assert response.status_code == 200
        
        state = client.get("/location/state").json()
        assert state["current"]["address"] == "123 Broadway, New York, NY 10006"

    def test_update_with_altitude(self, client_with_engine):
        """Test updating location with altitude metadata."""
        client, engine = client_with_engine
        
        response = client.post(
            "/location/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "altitude": 100.5,
            },
        )
        
        assert response.status_code == 200
        
        state = client.get("/location/state").json()
        assert state["current"]["altitude"] == 100.5

    def test_update_with_accuracy(self, client_with_engine):
        """Test updating location with GPS accuracy radius."""
        client, engine = client_with_engine
        
        response = client.post(
            "/location/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "accuracy": 10.0,
            },
        )
        
        assert response.status_code == 200
        
        state = client.get("/location/state").json()
        assert state["current"]["accuracy"] == 10.0

    def test_update_with_speed_and_bearing(self, client_with_engine):
        """Test updating location with movement metadata (speed and bearing)."""
        client, engine = client_with_engine
        
        response = client.post(
            "/location/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "speed": 15.6,  # meters per second (~35 mph)
                "bearing": 45.0,  # Northeast
            },
        )
        
        assert response.status_code == 200
        
        state = client.get("/location/state").json()
        assert state["current"]["speed"] == 15.6
        assert state["current"]["bearing"] == 45.0

    def test_update_with_all_metadata(self, client_with_engine):
        """Test updating location with all optional metadata fields."""
        client, engine = client_with_engine
        
        response = client.post(
            "/location/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "address": "New York, NY",
                "named_location": "Office",
                "altitude": 50.0,
                "accuracy": 5.0,
                "speed": 0.0,
                "bearing": 180.0,
            },
        )
        
        assert response.status_code == 200
        
        state = client.get("/location/state").json()
        current = state["current"]
        assert current["latitude"] == 40.7128
        assert current["longitude"] == -74.0060
        assert current["address"] == "New York, NY"
        assert current["named_location"] == "Office"
        assert current["altitude"] == 50.0
        assert current["accuracy"] == 5.0
        assert current["speed"] == 0.0
        assert current["bearing"] == 180.0

    def test_update_validates_required_fields(self, client_with_engine):
        """Test that missing required fields returns 422 error."""
        client, engine = client_with_engine
        
        # Missing both latitude and longitude
        response = client.post("/location/update", json={})
        assert response.status_code == 422
        
        # Missing longitude
        response = client.post("/location/update", json={"latitude": 40.7128})
        assert response.status_code == 422
        
        # Missing latitude
        response = client.post("/location/update", json={"longitude": -74.0060})
        assert response.status_code == 422

    def test_update_validates_latitude_range(self, client_with_engine):
        """Test that latitude outside valid range (-90 to 90) returns error.
        
        Note: Per LocationInput field_validator, latitude must be -90 to 90.
        Pydantic validators may return 400 (business logic) or 422 (validation).
        The route catches ValueError and returns 400.
        """
        client, engine = client_with_engine
        
        # Latitude too high
        response = client.post(
            "/location/update",
            json={"latitude": 91.0, "longitude": -74.0060},
        )
        assert response.status_code == 422
        assert "latitude" in response.json()["detail"].lower()
        
        # Latitude too low
        response = client.post(
            "/location/update",
            json={"latitude": -91.0, "longitude": -74.0060},
        )
        assert response.status_code == 422

    def test_update_validates_longitude_range(self, client_with_engine):
        """Test that longitude outside valid range (-180 to 180) returns error.
        
        Note: Per LocationInput field_validator, longitude must be -180 to 180.
        """
        client, engine = client_with_engine
        
        # Longitude too high
        response = client.post(
            "/location/update",
            json={"latitude": 40.7128, "longitude": 181.0},
        )
        assert response.status_code == 422
        assert "longitude" in response.json()["detail"].lower()
        
        # Longitude too low
        response = client.post(
            "/location/update",
            json={"latitude": 40.7128, "longitude": -181.0},
        )
        assert response.status_code == 422

    def test_update_accepts_boundary_coordinates(self, client_with_engine):
        """Test that boundary coordinate values are accepted."""
        client, engine = client_with_engine
        
        # Max latitude
        response = client.post(
            "/location/update",
            json={"latitude": 90.0, "longitude": 0.0},
        )
        assert response.status_code == 200
        
        # Min latitude
        response = client.post(
            "/location/update",
            json={"latitude": -90.0, "longitude": 0.0},
        )
        assert response.status_code == 200
        
        # Max longitude
        response = client.post(
            "/location/update",
            json={"latitude": 0.0, "longitude": 180.0},
        )
        assert response.status_code == 200
        
        # Min longitude
        response = client.post(
            "/location/update",
            json={"latitude": 0.0, "longitude": -180.0},
        )
        assert response.status_code == 200

    def test_state_reflects_location_update(self, client_with_engine):
        """Test that state shows new location immediately after update action."""
        client, engine = client_with_engine
        
        # Update location
        update_response = client.post(
            "/location/update",
            json={
                "latitude": 51.5074,
                "longitude": -0.1278,
                "named_location": "London Office",
            },
        )
        assert update_response.status_code == 200
        
        # State should immediately reflect the update
        state_response = client.get("/location/state")
        data = state_response.json()
        
        assert data["update_count"] == 1
        assert data["current"]["latitude"] == 51.5074
        assert data["current"]["longitude"] == -0.1278
        assert data["current"]["named_location"] == "London Office"

    def test_location_history_preserves_previous(self, client_with_engine):
        """Test that location history includes previous locations after updates.
        
        Note: Fixture initializes with SF location (37.7749, -122.4194) which
        becomes first history entry when we make the first update.
        """
        client, engine = client_with_engine
        
        # First location update (SF moves to history)
        client.post(
            "/location/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "named_location": "New York",
            },
        )
        
        # Second location update (New York moves to history)
        client.post(
            "/location/update",
            json={
                "latitude": 51.5074,
                "longitude": -0.1278,
                "named_location": "London",
            },
        )
        
        # Third location update (London moves to history)
        client.post(
            "/location/update",
            json={
                "latitude": 35.6762,
                "longitude": 139.6503,
                "named_location": "Tokyo",
            },
        )
        
        state = client.get("/location/state").json()
        
        # Current should be Tokyo
        assert state["current"]["named_location"] == "Tokyo"
        
        # History should contain: initial SF, New York, London (3 entries)
        assert len(state["history"]) == 3
        
        # Verify history contains our locations (order: SF, New York, London)
        assert state["history"][0]["latitude"] == 37.7749  # Initial SF
        assert state["history"][1]["named_location"] == "New York"
        assert state["history"][2]["named_location"] == "London"

    def test_message_includes_coordinates(self, client_with_engine):
        """Test that response message includes the updated coordinates."""
        client, engine = client_with_engine
        
        response = client.post(
            "/location/update",
            json={"latitude": 40.7128, "longitude": -74.0060},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "40.7128" in data["message"]
        assert "-74.006" in data["message"]

    def test_multiple_updates_increment_count(self, client_with_engine):
        """Test that multiple location updates increment update_count correctly."""
        client, engine = client_with_engine
        
        for i in range(3):
            client.post(
                "/location/update",
                json={"latitude": 40.0 + i, "longitude": -74.0},
            )
        
        state = client.get("/location/state").json()
        assert state["update_count"] == 3

    def test_update_with_zero_speed(self, client_with_engine):
        """Test updating location with zero speed (stationary)."""
        client, engine = client_with_engine
        
        response = client.post(
            "/location/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "speed": 0.0,
            },
        )
        
        assert response.status_code == 200
        
        state = client.get("/location/state").json()
        assert state["current"]["speed"] == 0.0

    def test_update_with_bearing_zero(self, client_with_engine):
        """Test updating location with bearing=0 (North)."""
        client, engine = client_with_engine
        
        response = client.post(
            "/location/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "bearing": 0.0,
            },
        )
        
        assert response.status_code == 200
        
        state = client.get("/location/state").json()
        assert state["current"]["bearing"] == 0.0

    def test_update_with_bearing_360(self, client_with_engine):
        """Test updating location with bearing=360 (also North)."""
        client, engine = client_with_engine
        
        response = client.post(
            "/location/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "bearing": 360.0,
            },
        )
        
        assert response.status_code == 200
        
        state = client.get("/location/state").json()
        assert state["current"]["bearing"] == 360.0
