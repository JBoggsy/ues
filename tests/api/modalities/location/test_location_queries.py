"""Integration tests for POST /location/query endpoint."""

from datetime import timedelta


class TestPostLocationQuery:
    """Tests for POST /location/query endpoint."""

    def test_query_returns_correct_structure(self, client_with_engine):
        """Test that query returns response with correct structure.
        
        Per LocationQueryResponse model, response should include:
        - locations: list of location entries
        - count: number of locations returned (after pagination)
        - total_count: total matching locations (before pagination)
        """
        client, engine = client_with_engine
        
        response = client.post("/location/query", json={})
        
        assert response.status_code == 200
        data = response.json()
        
        assert "locations" in data
        assert isinstance(data["locations"], list)
        assert "count" in data
        assert isinstance(data["count"], int)
        assert "total_count" in data
        assert isinstance(data["total_count"], int)

    def test_query_returns_current_location(self, client_with_engine):
        """Test that query with no filters returns current location when include_current=True.
        
        Note: Fixture initializes with SF location, which is moved to history when updated.
        """
        client, engine = client_with_engine
        
        # Update to a new location (SF moves to history)
        client.post(
            "/location/update",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "named_location": "Office",
            },
        )
        
        # Query with default include_current=True
        response = client.post("/location/query", json={})
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have current (Office) + history (SF) = 2 locations
        assert data["count"] == 2
        
        # Find the current location
        current_locations = [loc for loc in data["locations"] if loc.get("is_current")]
        assert len(current_locations) == 1
        
        current = current_locations[0]
        assert current["latitude"] == 40.7128
        assert current["longitude"] == -74.0060
        assert current["is_current"] is True

    def test_query_excludes_current_when_disabled(self, client_with_engine):
        """Test that query can exclude current location with include_current=False.
        
        Note: Fixture provides initial SF location. When we update, SF moves to history.
        """
        client, engine = client_with_engine
        
        # Update to new location (SF becomes history)
        client.post(
            "/location/update",
            json={"latitude": 40.7128, "longitude": -74.0060},
        )
        
        # Query with include_current=False
        response = client.post("/location/query", json={"include_current": False})
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have just the history (SF location)
        assert data["count"] == 1
        # Verify it's the history entry, not current
        assert data["locations"][0]["is_current"] is False
        assert data["locations"][0]["latitude"] == 37.7749

    def test_query_location_history(self, client_with_engine):
        """Test querying location history after multiple updates.
        
        Note: Fixture provides initial SF location which becomes history on first update.
        """
        client, engine = client_with_engine
        
        # Create multiple location updates
        client.post(
            "/location/update",
            json={"latitude": 40.7128, "longitude": -74.0060, "named_location": "Office"},
        )
        client.post(
            "/location/update",
            json={"latitude": 34.0522, "longitude": -118.2437, "named_location": "Home"},
        )
        
        response = client.post("/location/query", json={})
        
        assert response.status_code == 200
        data = response.json()
        
        # Should include: current (Home), history (Office, SF) = 3 locations
        assert data["count"] == 3
        
        # Check all locations are present
        named_locations = [loc.get("named_location") for loc in data["locations"]]
        assert "Home" in named_locations
        assert "Office" in named_locations
        # SF doesn't have a named_location, check by coordinates
        sf_found = any(
            loc["latitude"] == 37.7749 and loc["longitude"] == -122.4194
            for loc in data["locations"]
        )
        assert sf_found

    def test_filter_by_time_range_since(self, client_with_engine):
        """Test filtering location history by since parameter."""
        client, engine = client_with_engine
        
        # First location
        client.post(
            "/location/update",
            json={"latitude": 40.7128, "longitude": -74.0060, "named_location": "First"},
        )
        
        # Get the timestamp after first update
        time_response = client.get("/simulator/time")
        middle_time = time_response.json()["current_time"]
        
        # Advance time
        client.post("/simulator/time/advance", json={"seconds": 60})
        
        # Second location
        client.post(
            "/location/update",
            json={"latitude": 34.0522, "longitude": -118.2437, "named_location": "Second"},
        )
        
        # Query with since filter (should only get Second)
        response = client.post("/location/query", json={"since": middle_time})
        
        assert response.status_code == 200
        data = response.json()
        
        # Should only include locations at or after middle_time
        assert data["count"] >= 1
        # The current location "Second" should be included
        assert any(loc.get("named_location") == "Second" for loc in data["locations"])

    def test_filter_by_named_location(self, client_with_engine):
        """Test filtering for specific named location."""
        client, engine = client_with_engine
        
        # Create multiple locations with different names
        client.post(
            "/location/update",
            json={"latitude": 40.7128, "longitude": -74.0060, "named_location": "Office"},
        )
        client.post(
            "/location/update",
            json={"latitude": 34.0522, "longitude": -118.2437, "named_location": "Home"},
        )
        client.post(
            "/location/update",
            json={"latitude": 40.7128, "longitude": -74.0060, "named_location": "Office"},
        )
        
        # Filter by named_location
        response = client.post("/location/query", json={"named_location": "Office"})
        
        assert response.status_code == 200
        data = response.json()
        
        # Current is Office, plus one Office in history (Home is in between)
        assert data["count"] == 2
        assert all(loc.get("named_location") == "Office" for loc in data["locations"])

    def test_pagination_with_limit(self, client_with_engine):
        """Test pagination using limit parameter.
        
        Note: Fixture provides initial SF location, so we have 5 updates + 1 initial = 6 total.
        """
        client, engine = client_with_engine
        
        # Create multiple locations (5 updates)
        for i in range(5):
            client.post(
                "/location/update",
                json={
                    "latitude": 40.0 + i * 0.1,
                    "longitude": -74.0,
                    "named_location": f"Location{i}",
                },
            )
        
        response = client.post("/location/query", json={"limit": 3})
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return only 3 locations
        assert data["count"] == 3
        # Total count should reflect all matching locations (5 updates + 1 initial = 6)
        assert data["total_count"] == 6

    def test_pagination_with_offset(self, client_with_engine):
        """Test pagination using offset parameter.
        
        Note: Fixture provides initial SF location, so we have 5 updates + 1 initial = 6 total.
        """
        client, engine = client_with_engine
        
        # Create multiple locations (5 updates)
        for i in range(5):
            client.post(
                "/location/update",
                json={
                    "latitude": 40.0 + i * 0.1,
                    "longitude": -74.0,
                    "named_location": f"Location{i}",
                },
            )
        
        response = client.post("/location/query", json={"offset": 2, "limit": 2})
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return 2 locations after skipping 2
        assert data["count"] == 2
        assert data["total_count"] == 6

    def test_sort_by_timestamp_desc(self, client_with_engine):
        """Test sorting location history by timestamp descending (default).
        
        Note: Fixture provides initial SF location which becomes first history entry.
        """
        client, engine = client_with_engine
        
        # Create locations with time advancement between them
        client.post(
            "/location/update",
            json={"latitude": 40.0, "longitude": -74.0, "named_location": "First"},
        )
        client.post("/simulator/time/advance", json={"seconds": 1})
        
        client.post(
            "/location/update",
            json={"latitude": 41.0, "longitude": -74.0, "named_location": "Second"},
        )
        client.post("/simulator/time/advance", json={"seconds": 1})
        
        client.post(
            "/location/update",
            json={"latitude": 42.0, "longitude": -74.0, "named_location": "Third"},
        )
        
        response = client.post(
            "/location/query", json={"sort_by": "timestamp", "sort_order": "desc"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # With desc order, most recent (Third) should come first
        # Filter to only named locations to check order
        names = [loc.get("named_location") for loc in data["locations"] if loc.get("named_location")]
        assert names[0] == "Third"
        # Third, Second, First should be in that order
        assert names == ["Third", "Second", "First"]

    def test_sort_by_timestamp_asc(self, client_with_engine):
        """Test sorting location history by timestamp ascending."""
        client, engine = client_with_engine
        
        # Create locations with time advancement between them
        client.post(
            "/location/update",
            json={"latitude": 40.0, "longitude": -74.0, "named_location": "First"},
        )
        client.post("/simulator/time/advance", json={"seconds": 1})
        
        client.post(
            "/location/update",
            json={"latitude": 41.0, "longitude": -74.0, "named_location": "Second"},
        )
        client.post("/simulator/time/advance", json={"seconds": 1})
        
        client.post(
            "/location/update",
            json={"latitude": 42.0, "longitude": -74.0, "named_location": "Third"},
        )
        
        response = client.post(
            "/location/query", json={"sort_by": "timestamp", "sort_order": "asc"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # With asc order, oldest (First) should come first
        names = [loc.get("named_location") for loc in data["locations"]]
        assert names[0] == "First"

    def test_empty_results_when_no_matches(self, client_with_engine):
        """Test that query returns empty results when filters match nothing."""
        client, engine = client_with_engine
        
        # Set a location
        client.post(
            "/location/update",
            json={"latitude": 40.7128, "longitude": -74.0060, "named_location": "Office"},
        )
        
        # Query for non-existent named location
        response = client.post("/location/query", json={"named_location": "Nonexistent"})
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["count"] == 0
        assert data["total_count"] == 0
        assert data["locations"] == []

    def test_empty_results_when_no_location_set(self, client_with_engine):
        """Test that query returns initial location from fixture.
        
        Note: The fresh_engine fixture initializes LocationState with default
        San Francisco coordinates, so there's always an initial location.
        """
        client, engine = client_with_engine
        
        response = client.post("/location/query", json={})
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have the initial SF location
        assert data["count"] == 1
        assert data["locations"][0]["latitude"] == 37.7749
        assert data["locations"][0]["longitude"] == -122.4194

    def test_combined_filters(self, client_with_engine):
        """Test query with multiple filters combined."""
        client, engine = client_with_engine
        
        # Create several locations
        client.post(
            "/location/update",
            json={"latitude": 40.7128, "longitude": -74.0060, "named_location": "Office"},
        )
        client.post(
            "/location/update",
            json={"latitude": 34.0522, "longitude": -118.2437, "named_location": "Home"},
        )
        client.post(
            "/location/update",
            json={"latitude": 40.7128, "longitude": -74.0060, "named_location": "Office"},
        )
        
        # Query with limit and named_location filter
        response = client.post(
            "/location/query",
            json={"named_location": "Office", "limit": 1},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["count"] == 1
        assert data["total_count"] == 2  # There are 2 Office locations
        assert data["locations"][0]["named_location"] == "Office"
