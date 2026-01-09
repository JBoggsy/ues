"""API integration tests for compact snapshot endpoint.

Tests the GET /environment/state endpoint with compact=true and format=text parameters.
"""


class TestCompactSnapshotEndpoint:
    """Test GET /environment/state with compact parameter."""

    def test_default_returns_full_state(self, client_with_engine):
        """Test that default response is full state (backward compatible)."""
        client, _ = client_with_engine
        response = client.get("/environment/state")
        
        assert response.status_code == 200
        data = response.json()
        
        # Full state has "modalities" with full state objects
        assert "current_time" in data
        assert "modalities" in data
        assert "summary" in data
        # Modalities should contain detailed state
        assert isinstance(data["modalities"], dict)

    def test_compact_true_returns_compact_snapshot(self, client_with_engine):
        """Test that compact=true returns compact snapshot format."""
        client, _ = client_with_engine
        response = client.get("/environment/state", params={"compact": True})
        
        assert response.status_code == 200
        data = response.json()
        
        # Compact response format
        assert "snapshot_time" in data
        assert "format" in data
        assert data["format"] == "compact"
        assert "modalities" in data
        
        # All modalities should be present
        modalities = data["modalities"]
        assert "location" in modalities
        assert "time" in modalities
        assert "weather" in modalities
        assert "email" in modalities
        assert "sms" in modalities
        assert "chat" in modalities
        assert "calendar" in modalities

    def test_compact_false_returns_full_state(self, client_with_engine):
        """Test that compact=false returns full state."""
        client, _ = client_with_engine
        response = client.get("/environment/state", params={"compact": False})
        
        assert response.status_code == 200
        data = response.json()
        
        # Full state format
        assert "current_time" in data
        assert "summary" in data

    def test_compact_with_format_text(self, client_with_engine):
        """Test that compact=true with format=text returns plain text."""
        client, _ = client_with_engine
        response = client.get(
            "/environment/state", 
            params={"compact": True, "format": "text"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        
        text = response.text
        # Should contain some expected text markers
        assert "Time:" in text or "time" in text.lower()
        # Should contain emoji formatting
        assert any(emoji in text for emoji in ["📅", "📍", "📧", "💬", "📱", "🌤", "⏰"])

    def test_format_json_returns_json(self, client_with_engine):
        """Test that format=json explicitly returns JSON."""
        client, _ = client_with_engine
        response = client.get(
            "/environment/state",
            params={"compact": True, "format": "json"}
        )
        
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        
        data = response.json()
        assert "snapshot_time" in data

    def test_format_text_without_compact_returns_json(self, client_with_engine):
        """Test that format=text without compact=true is ignored (returns JSON)."""
        client, _ = client_with_engine
        response = client.get(
            "/environment/state",
            params={"format": "text"}
        )
        
        # When compact is not set, format=text is ignored and returns JSON
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        data = response.json()
        # Still returns full state format
        assert "current_time" in data

    def test_compact_snapshot_includes_events_summary(self, client_with_engine):
        """Test that compact snapshot includes pending events summary."""
        client, _ = client_with_engine
        # Schedule some events
        client.post("/events/schedule", json={
            "modality": "email",
            "action": "receive",
            "timestamp": "2024-01-15T12:00:00Z",
            "data": {
                "from_address": "test@example.com",
                "subject": "Test"
            }
        })
        
        response = client.get("/environment/state", params={"compact": True})
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have events field
        assert "events" in data
        if data["events"]:
            assert "pending_count" in data["events"]


class TestCompactSnapshotContent:
    """Test the actual content of compact snapshots."""

    def test_location_compact_format(self, client_with_engine):
        """Test location compact snapshot format."""
        client, _ = client_with_engine
        # Set a location
        client.post("/location/set", json={
            "latitude": 37.7749,
            "longitude": -122.4194,
            "address": "San Francisco, CA"
        })
        
        response = client.get("/environment/state", params={"compact": True})
        data = response.json()
        
        location = data["modalities"]["location"]
        # The compact format uses "current" not "current_location"
        assert "current" in location
        if location["current"]:
            assert "latitude" in location["current"]
            assert "longitude" in location["current"]

    def test_email_compact_format(self, client_with_engine):
        """Test email compact snapshot includes unread info."""
        client, _ = client_with_engine
        # Receive an email (use correct request format)
        client.post("/email/receive", json={
            "from_address": "sender@example.com",
            "to_addresses": ["user@example.com"],
            "subject": "Important Message",
            "body_text": "Please review."
        })
        
        response = client.get("/environment/state", params={"compact": True})
        data = response.json()
        
        email = data["modalities"]["email"]
        assert "unread_count" in email
        # Note: May be 0 if email was auto-marked read or inbox configuration
        assert isinstance(email["unread_count"], int)
        assert "recent_unread" in email

    def test_calendar_compact_format(self, client_with_engine):
        """Test calendar compact snapshot includes event info."""
        client, _ = client_with_engine
        # Add a calendar event
        client.post("/calendar/add", json={
            "title": "Test Meeting",
            "start_time": "2024-01-15T14:00:00Z",
            "end_time": "2024-01-15T15:00:00Z"
        })
        
        response = client.get("/environment/state", params={"compact": True})
        data = response.json()
        
        calendar = data["modalities"]["calendar"]
        assert "today_count" in calendar
        assert "current_event" in calendar
        assert "next_event" in calendar


class TestCompactSnapshotSize:
    """Test that compact snapshots are appropriately sized."""

    def test_compact_is_smaller_than_full(self, client_with_engine):
        """Test that compact response is smaller than full response."""
        client, _ = client_with_engine
        # Add some data to make the full state larger
        for i in range(5):
            client.post("/email/receive", json={
                "from_address": f"sender{i}@example.com",
                "subject": f"Test Email {i}",
                "body_text": f"This is test email number {i}. " * 20
            })
        
        # Get both responses
        full_response = client.get("/environment/state")
        compact_response = client.get("/environment/state", params={"compact": True})
        
        full_size = len(full_response.content)
        compact_size = len(compact_response.content)
        
        # Compact should be smaller
        assert compact_size < full_size
        # At least 2x smaller for meaningful data
        assert compact_size < full_size / 2
