"""API integration tests for modality state routes with compact parameter.

Tests the GET /{modality}/state endpoints with compact=true query parameter.
These tests verify that the compact parameter works consistently across all modalities.
"""

import pytest


class TestLocationCompactState:
    """Test GET /location/state with compact parameter."""

    def test_default_returns_full_state(self, client_with_engine):
        """Default response includes history."""
        client, _ = client_with_engine
        response = client.get("/location/state")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "history" in data
        assert "current" in data
        assert isinstance(data["history"], list)

    def test_compact_returns_history_count(self, client_with_engine):
        """Compact response replaces history with history_count."""
        client, _ = client_with_engine
        response = client.get("/location/state", params={"compact": True})
        
        assert response.status_code == 200
        data = response.json()
        
        assert "history_count" in data
        assert "history" not in data
        assert "current" in data
        assert isinstance(data["history_count"], int)


class TestWeatherCompactState:
    """Test GET /weather/state with compact parameter."""

    def test_default_returns_full_state(self, client_with_engine):
        """Default response includes full location data."""
        client, _ = client_with_engine
        response = client.get("/weather/state")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "locations" in data
        assert "location_count" in data

    def test_compact_returns_summary(self, client_with_engine):
        """Compact response returns current weather per location."""
        client, _ = client_with_engine
        response = client.get("/weather/state", params={"compact": True})
        
        assert response.status_code == 200
        data = response.json()
        
        assert "locations" in data
        assert "location_count" in data


class TestSMSCompactState:
    """Test GET /sms/state with compact parameter."""

    def test_default_returns_full_state(self, client_with_engine):
        """Default response includes full messages."""
        client, _ = client_with_engine
        response = client.get("/sms/state")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "messages" in data
        assert "conversations" in data
        assert isinstance(data["messages"], dict)

    def test_compact_returns_conversation_metadata(self, client_with_engine):
        """Compact response returns conversation metadata only."""
        client, _ = client_with_engine
        response = client.get("/sms/state", params={"compact": True})
        
        assert response.status_code == 200
        data = response.json()
        
        # Compact format has conversations but no messages
        assert "messages" not in data
        assert "conversations" in data
        assert "total_messages" in data
        assert "unread_total" in data
        # Conversations in compact are keyed by thread_id
        assert isinstance(data["conversations"], dict)


class TestChatCompactState:
    """Test GET /chat/state with compact parameter."""

    def test_default_returns_full_state(self, client_with_engine):
        """Default response includes full messages."""
        client, _ = client_with_engine
        response = client.get("/chat/state")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "messages" in data
        assert "conversations" in data
        assert isinstance(data["messages"], list)

    def test_compact_returns_conversation_metadata(self, client_with_engine):
        """Compact response returns conversation metadata only."""
        client, _ = client_with_engine
        response = client.get("/chat/state", params={"compact": True})
        
        assert response.status_code == 200
        data = response.json()
        
        # Compact format has conversations but no messages
        assert "messages" not in data
        assert "conversations" in data
        assert "total_message_count" in data
        assert "conversation_count" in data
        # Conversations in compact are keyed by conversation_id
        assert isinstance(data["conversations"], dict)


class TestCalendarCompactState:
    """Test GET /calendar/state with compact parameter."""

    def test_default_returns_full_state(self, client_with_engine):
        """Default response includes full events."""
        client, _ = client_with_engine
        response = client.get("/calendar/state")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "events" in data
        assert "calendars" in data
        assert isinstance(data["events"], dict)

    def test_compact_returns_calendar_metadata(self, client_with_engine):
        """Compact response returns calendar metadata only."""
        client, _ = client_with_engine
        response = client.get("/calendar/state", params={"compact": True})
        
        assert response.status_code == 200
        data = response.json()
        
        # Compact format has calendars with counts but no full events
        assert "events" not in data
        assert "calendars" in data
        assert "calendar_count" in data
        assert "event_count" in data
        # Calendars in compact are keyed by calendar_id
        assert isinstance(data["calendars"], dict)


class TestEmailCompactState:
    """Test GET /email/state with compact parameter.
    
    Email uses both 'summary' and 'compact' parameters (compact is alias).
    """

    def test_default_returns_full_state(self, client_with_engine):
        """Default response includes full email content."""
        client, _ = client_with_engine
        response = client.get("/email/state")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "emails" in data
        assert "threads" in data

    def test_compact_returns_summary(self, client_with_engine):
        """Compact parameter returns summary response."""
        client, _ = client_with_engine
        response = client.get("/email/state", params={"compact": True})
        
        assert response.status_code == 200
        data = response.json()
        
        assert "statistics" in data
        assert "emails" in data  # Contains summaries not full content

    def test_summary_parameter_works(self, client_with_engine):
        """Summary parameter (original) still works."""
        client, _ = client_with_engine
        response = client.get("/email/state", params={"summary": True})
        
        assert response.status_code == 200
        data = response.json()
        
        assert "statistics" in data


class TestCompactFalseReturnsFullState:
    """Test that compact=false explicitly returns full state."""

    @pytest.mark.parametrize("endpoint", [
        "/location/state",
        "/weather/state",
        "/sms/state",
        "/chat/state",
        "/calendar/state",
        "/email/state",
    ])
    def test_compact_false_returns_full_state(self, client_with_engine, endpoint):
        """Explicit compact=false returns full state."""
        client, _ = client_with_engine
        response = client.get(endpoint, params={"compact": False})
        
        assert response.status_code == 200
        # All should return successfully with full state
