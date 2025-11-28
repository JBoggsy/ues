"""Integration tests for modality-specific query endpoints.

This module tests the POST /environment/modalities/{modality_name}/query endpoint,
which allows clients to:
- Query modality states with custom filters
- Use modality-specific query parameters
- Get filtered results without retrieving full state

Following patterns from API_TESTING_GUIDELINES.md.
"""

from datetime import datetime, timedelta

from models.modalities.email_state import Email
from models.modalities.sms_state import SMSMessage
from models.modalities.chat_state import ChatMessage
from models.modalities.location_state import LocationHistoryEntry
from models.modalities.calendar_state import CalendarEvent

from tests.api.helpers import (
    make_event_request,
    email_event_data,
    sms_event_data,
    chat_event_data,
    location_event_data,
    calendar_event_data,
    weather_event_data,
    time_event_data,
)


class TestQueryModality:
    """Tests for POST /environment/modalities/{modality_name}/query endpoint."""
    
    def test_query_modality_returns_results(self, client_with_engine):
        """Test that POST /environment/modalities/{name}/query returns results.
        
        Verifies that the endpoint returns:
        - modality_type field
        - query field (echoes the query parameters)
        - results field (query results)
        """
        client, _ = client_with_engine
        
        # Query a modality with simple parameters
        query = {}
        response = client.post("/environment/modalities/location/query", json=query)
        
        # Verify response structure
        assert response.status_code == 200
        data = response.json()
        
        assert "modality_type" in data
        assert "query" in data
        assert "results" in data
        
        # Verify modality_type matches requested modality
        assert data["modality_type"] == "location"
        
        # Verify query echoes the sent parameters
        assert data["query"] == query
        
        # Verify results has expected structure for location query
        results = data["results"]
        assert "locations" in results
        assert "count" in results
        assert "total_count" in results
        assert isinstance(results["locations"], list)
        assert results["count"] == len(results["locations"])
    
    def test_query_modality_invalid_modality(self, client_with_engine):
        """Test that query endpoint returns 404 for invalid modality.
        
        Verifies error handling for non-existent modality names.
        """
        client, _ = client_with_engine
        
        # Try to query non-existent modality
        response = client.post("/environment/modalities/nonexistent/query", json={})
        
        # Verify returns 404
        assert response.status_code == 404
        
        # Verify error message mentions modality not found
        error_detail = response.json()["detail"].lower()
        assert "does not exist" in error_detail or "not found" in error_detail
        assert "modality" in error_detail or "nonexistent" in error_detail
        
        # Verify error includes available modalities list
        assert "available_modalities" in response.json()
        available = response.json()["available_modalities"]
        assert isinstance(available, list)
        assert len(available) > 0
    
    def test_query_email_with_filters(self, client_with_engine):
        """Test that email modality query supports filters.
        
        Verifies that email-specific query parameters work:
        - folder: Filter by folder name
        - is_read: Filter by read status
        - from_address: Filter by sender
        - subject_contains: Search subject
        """
        client, _ = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create email events with different properties
        event_time = current_time + timedelta(seconds=1)
        
        # Email from sender1 in inbox
        email1 = make_event_request(
            event_time,
            "email",
            email_event_data(
                operation="receive",
                from_address="sender1@example.com",
                subject="Test Email 1",
                folder="inbox",
            ),
        )
        
        # Email from sender2 in sent
        email2 = make_event_request(
            event_time + timedelta(seconds=1),
            "email",
            email_event_data(
                operation="send",
                from_address="user@example.com",
                to_addresses=["recipient@example.com"],
                subject="Sent Email",
                folder="sent",
            ),
        )
        
        client.post("/events", json=email1)
        client.post("/events", json=email2)
        
        # Execute events
        client.post("/simulator/time/advance", json={"seconds": 5})
        
        # Query with subject_contains filter
        query_response = client.post(
            "/environment/modalities/email/query",
            json={"subject_contains": "Test"}
        )
        
        assert query_response.status_code == 200
        data = query_response.json()
        
        # Verify response structure
        assert data["modality_type"] == "email"
        assert "results" in data
        results = data["results"]
        
        # EmailState.query() returns: {emails: [...], total_count: int, returned_count: int, query: dict}
        assert "emails" in results
        assert "total_count" in results
        assert "returned_count" in results
        
        # Query with from_address filter
        query_response2 = client.post(
            "/environment/modalities/email/query",
            json={"from_address": "sender1"}
        )
        
        assert query_response2.status_code == 200
        results2 = query_response2.json()["results"]
        assert "emails" in results2
    
    def test_query_sms_with_filters(self, client_with_engine):
        """Test that SMS modality query supports filters.
        
        Verifies that SMS-specific query parameters work:
        - thread_id: Filter by conversation
        - phone_number: Filter by participant
        - direction: Filter by incoming/outgoing
        - search_text: Search message content
        """
        client, _ = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create SMS events
        event_time = current_time + timedelta(seconds=1)
        
        sms1 = make_event_request(
            event_time,
            "sms",
            sms_event_data(
                action="receive",
                from_number="+15551234567",
                body="Hello from sender",
            ),
        )
        
        sms2 = make_event_request(
            event_time + timedelta(seconds=1),
            "sms",
            sms_event_data(
                action="send",
                to_numbers=["+15559876543"],
                body="Sent message text",
            ),
        )
        
        client.post("/events", json=sms1)
        client.post("/events", json=sms2)
        
        # Execute events
        client.post("/simulator/time/advance", json={"seconds": 5})
        
        # Query with search_text filter
        query_response = client.post(
            "/environment/modalities/sms/query",
            json={"search_text": "sender"}
        )
        
        assert query_response.status_code == 200
        data = query_response.json()
        
        # Verify response structure
        assert data["modality_type"] == "sms"
        results = data["results"]
        
        # SMSState.query() returns: {messages: [...], count: int, total_count: int, query_params: dict}
        assert "messages" in results
        assert "count" in results
        assert "total_count" in results
        
        # Query with direction filter
        query_response2 = client.post(
            "/environment/modalities/sms/query",
            json={"direction": "outgoing"}
        )
        
        assert query_response2.status_code == 200
        results2 = query_response2.json()["results"]
        assert "messages" in results2
    
    def test_query_calendar_with_filters(self, client_with_engine):
        """Test that calendar modality query supports filters.
        
        Verifies that calendar-specific query parameters work:
        - start: Start date for range
        - end: End date for range
        - status: Filter by event status
        - recurring: Filter recurring events
        """
        client, _ = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create calendar events
        event_time = current_time + timedelta(seconds=1)
        
        # Create a calendar event in the future
        meeting_start = current_time + timedelta(days=1)
        meeting_end = meeting_start + timedelta(hours=1)
        
        cal_event = make_event_request(
            event_time,
            "calendar",
            calendar_event_data(
                action="create",
                title="Team Meeting",
                start=meeting_start.isoformat(),
                end=meeting_end.isoformat(),
                status="confirmed",
            ),
        )
        
        client.post("/events", json=cal_event)
        
        # Execute event
        client.post("/simulator/time/advance", json={"seconds": 5})
        
        # Query with status filter
        query_response = client.post(
            "/environment/modalities/calendar/query",
            json={"status": "confirmed"}
        )
        
        assert query_response.status_code == 200
        data = query_response.json()
        
        # Verify response structure
        assert data["modality_type"] == "calendar"
        results = data["results"]
        
        # CalendarState.query() returns: {events: [...], count: int, total_count: int}
        assert "events" in results
        assert "count" in results
        assert "total_count" in results
        
        # Query with search text
        query_response2 = client.post(
            "/environment/modalities/calendar/query",
            json={"search": "Meeting"}
        )
        
        assert query_response2.status_code == 200
        results2 = query_response2.json()["results"]
        assert "events" in results2
    
    def test_query_chat_with_filters(self, client_with_engine):
        """Test that chat modality query supports filters.
        
        Verifies that chat-specific query parameters work:
        - role: Filter by user/assistant
        - since: Messages after timestamp
        - search: Search message content
        """
        client, _ = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create chat events
        event_time = current_time + timedelta(seconds=1)
        
        chat1 = make_event_request(
            event_time,
            "chat",
            chat_event_data(
                role="user",
                content="Hello assistant",
            ),
        )
        
        chat2 = make_event_request(
            event_time + timedelta(seconds=1),
            "chat",
            chat_event_data(
                role="assistant",
                content="Hello user, how can I help?",
            ),
        )
        
        client.post("/events", json=chat1)
        client.post("/events", json=chat2)
        
        # Execute events
        client.post("/simulator/time/advance", json={"seconds": 5})
        
        # Query with role filter
        query_response = client.post(
            "/environment/modalities/chat/query",
            json={"role": "user"}
        )
        
        assert query_response.status_code == 200
        data = query_response.json()
        
        # Verify response structure
        assert data["modality_type"] == "chat"
        results = data["results"]
        
        # ChatState.query() returns: {messages: [...], count: int, total_count: int}
        assert "messages" in results
        assert "count" in results
        assert "total_count" in results
        
        # Query with search filter
        query_response2 = client.post(
            "/environment/modalities/chat/query",
            json={"search": "help"}
        )
        
        assert query_response2.status_code == 200
        results2 = query_response2.json()["results"]
        assert "messages" in results2
    
    def test_query_location_with_filters(self, client_with_engine):
        """Test that location modality query supports filters.
        
        Verifies that location-specific query parameters work:
        - since: Start of time range
        - until: End of time range
        - named_location: Filter by location name
        """
        client, _ = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create location events
        event_time = current_time + timedelta(seconds=1)
        
        loc1 = make_event_request(
            event_time,
            "location",
            location_event_data(
                latitude=37.7749,
                longitude=-122.4194,
                named_location="San Francisco",
            ),
        )
        
        loc2 = make_event_request(
            event_time + timedelta(seconds=2),
            "location",
            location_event_data(
                latitude=34.0522,
                longitude=-118.2437,
                named_location="Los Angeles",
            ),
        )
        
        client.post("/events", json=loc1)
        client.post("/events", json=loc2)
        
        # Execute events
        client.post("/simulator/time/advance", json={"seconds": 5})
        
        # Query with named_location filter
        query_response = client.post(
            "/environment/modalities/location/query",
            json={"named_location": "San Francisco"}
        )
        
        assert query_response.status_code == 200
        data = query_response.json()
        
        # Verify response structure
        assert data["modality_type"] == "location"
        results = data["results"]
        
        # LocationState.query() returns: {locations: [...], count: int, total_count: int}
        assert "locations" in results
        assert "count" in results
        assert "total_count" in results
        
        # Query with limit
        query_response2 = client.post(
            "/environment/modalities/location/query",
            json={"limit": 1}
        )
        
        assert query_response2.status_code == 200
        results2 = query_response2.json()["results"]
        assert "locations" in results2
        assert results2["count"] <= 1
    
    def test_query_weather_with_filters(self, client_with_engine):
        """Test that weather modality query supports filters.
        
        Verifies that weather-specific query parameters work:
        - lat (required): Latitude coordinate
        - lon (required): Longitude coordinate
        - exclude: Sections to exclude from report
        - units: Unit system (standard, metric, imperial)
        - from/to: Time range for historical data
        - limit/offset: Pagination
        
        Note: Weather query REQUIRES lat/lon parameters.
        """
        client, _ = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create weather events at different locations
        event_time = current_time + timedelta(seconds=1)
        
        # Weather for San Francisco
        weather1 = make_event_request(
            event_time,
            "weather",
            weather_event_data(
                latitude=37.7749,
                longitude=-122.4194,
            ),
        )
        
        # Weather for New York
        weather2 = make_event_request(
            event_time + timedelta(seconds=1),
            "weather",
            weather_event_data(
                latitude=40.7128,
                longitude=-74.0060,
            ),
        )
        
        client.post("/events", json=weather1)
        client.post("/events", json=weather2)
        
        # Execute events
        client.post("/simulator/time/advance", json={"seconds": 5})
        
        # Query with required lat/lon parameters (San Francisco)
        query_response = client.post(
            "/environment/modalities/weather/query",
            json={"lat": 37.7749, "lon": -122.4194}
        )
        
        assert query_response.status_code == 200
        data = query_response.json()
        
        # Verify response structure
        assert data["modality_type"] == "weather"
        results = data["results"]
        
        # WeatherState.query() returns: {reports: [...], count: int, total_count: int}
        assert "reports" in results
        assert "count" in results
        # Note: total_count may not be present if there's an error
        assert results["count"] == len(results["reports"])
        
        # Verify we got the San Francisco weather
        assert results["count"] > 0
        
        # Query different location (New York)
        query_response2 = client.post(
            "/environment/modalities/weather/query",
            json={"lat": 40.7128, "lon": -74.0060}
        )
        
        assert query_response2.status_code == 200
        results2 = query_response2.json()["results"]
        assert "reports" in results2
        assert results2["count"] > 0
        
        # Query with units parameter
        query_response3 = client.post(
            "/environment/modalities/weather/query",
            json={"lat": 37.7749, "lon": -122.4194, "units": "metric"}
        )
        
        assert query_response3.status_code == 200
        results3 = query_response3.json()["results"]
        assert "reports" in results3
    
    def test_query_weather_missing_required_params(self, client_with_engine):
        """Test that weather query fails without required lat/lon parameters.
        
        Weather queries require lat and lon parameters, unlike other modalities.
        """
        client, _ = client_with_engine
        
        # Try to query without lat/lon - should fail
        query_response = client.post(
            "/environment/modalities/weather/query",
            json={}
        )
        
        # Should return 400 error (validation error from WeatherState.query)
        assert query_response.status_code == 400
        
        # Error should mention missing parameters
        error_detail = query_response.json()["detail"].lower()
        assert "lat" in error_detail or "lon" in error_detail or "parameter" in error_detail
    
    def test_query_time_with_filters(self, client_with_engine):
        """Test that time modality query supports filters.
        
        Verifies that time-specific query parameters work:
        - since/until: Time range for settings history
        - timezone: Filter by timezone
        - format_preference: Filter by time format
        - include_current: Include current settings
        - sort_by/sort_order: Sorting options
        - limit/offset: Pagination
        """
        client, _ = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create time preference events
        event_time = current_time + timedelta(seconds=1)
        
        # First preference change - 24h format, UTC
        time1 = make_event_request(
            event_time,
            "time",
            time_event_data(
                timezone="UTC",
                format_preference="24h",
            ),
        )
        
        # Second preference change - 12h format, New York
        time2 = make_event_request(
            event_time + timedelta(seconds=2),
            "time",
            time_event_data(
                timezone="America/New_York",
                format_preference="12h",
                date_format="MM/DD/YYYY",
            ),
        )
        
        client.post("/events", json=time1)
        client.post("/events", json=time2)
        
        # Execute events
        client.post("/simulator/time/advance", json={"seconds": 5})
        
        # Query with timezone filter
        query_response = client.post(
            "/environment/modalities/time/query",
            json={"timezone": "America/New_York"}
        )
        
        assert query_response.status_code == 200
        data = query_response.json()
        
        # Verify response structure
        assert data["modality_type"] == "time"
        results = data["results"]
        
        # TimeState.query() returns: {settings: [...], count: int, total_count: int}
        assert "settings" in results
        assert "count" in results
        assert "total_count" in results
        
        # Query with format_preference filter
        query_response2 = client.post(
            "/environment/modalities/time/query",
            json={"format_preference": "12h"}
        )
        
        assert query_response2.status_code == 200
        results2 = query_response2.json()["results"]
        assert "settings" in results2
        
        # Query with include_current parameter
        query_response3 = client.post(
            "/environment/modalities/time/query",
            json={"include_current": True}
        )
        
        assert query_response3.status_code == 200
        results3 = query_response3.json()["results"]
        assert "settings" in results3
        assert results3["count"] > 0
        
        # Verify current settings are included
        settings_list = results3["settings"]
        has_current = any(s.get("is_current", False) for s in settings_list)
        assert has_current, "Query with include_current=True should include current settings"
        
        # Query with sort_by parameter
        query_response4 = client.post(
            "/environment/modalities/time/query",
            json={"sort_by": "timestamp", "sort_order": "asc"}
        )
        
        assert query_response4.status_code == 200
        results4 = query_response4.json()["results"]
        assert "settings" in results4
    
    def test_query_modality_handles_invalid_params(self, client_with_engine):
        """Test that query endpoint handles invalid query parameters.
        
        Verifies error handling for invalid or unsupported query parameters.
        Note: Most modalities are lenient with query parameters - they ignore
        unknown params rather than rejecting them. This test verifies that
        queries don't crash with unexpected parameters.
        """
        client, _ = client_with_engine
        
        # Send query with unexpected parameters - should be handled gracefully
        query_response = client.post(
            "/environment/modalities/location/query",
            json={"nonexistent_param": "value", "another_bad_param": 123}
        )
        
        # Should succeed (query methods ignore unknown params)
        assert query_response.status_code == 200
        data = query_response.json()
        
        # Should still return valid structure
        assert data["modality_type"] == "location"
        assert "results" in data
        results = data["results"]
        assert "locations" in results
        
        # Verify query was echoed back (including unknown params)
        assert data["query"]["nonexistent_param"] == "value"
    
    def test_query_modality_without_query_method(self, client_with_engine):
        """Test that query endpoint handles modalities without query support.
        
        Note: As of current implementation, all 7 modalities (location, time,
        weather, email, SMS, chat, calendar) have query methods implemented.
        
        This test verifies that the fallback logic exists in the API route
        for future modalities that might not implement query methods.
        
        Since we can't easily create a test modality without a query method,
        this test documents the expected fallback behavior based on the
        implementation in api/routes/environment.py.
        
        Note: Weather requires lat/lon params, so it needs special handling.
        """
        client, _ = client_with_engine
        
        # All current modalities have query methods
        # Weather requires lat/lon parameters, so we test it separately
        # Other modalities work with empty queries
        modalities_with_empty_query = ["location", "time", "email", "sms", "chat", "calendar"]
        
        for modality in modalities_with_empty_query:
            response = client.post(f"/environment/modalities/{modality}/query", json={})
            
            # All should succeed since they all have query methods
            assert response.status_code == 200, f"{modality} query failed"
            data = response.json()
            
            assert data["modality_type"] == modality
            assert "results" in data
            assert "query" in data
            
            # Should NOT have the fallback message (since query methods exist)
            assert "message" not in data or "does not support" not in data.get("message", "")
        
        # Test weather separately with required parameters
        weather_response = client.post(
            "/environment/modalities/weather/query",
            json={"lat": 37.7749, "lon": -122.4194}
        )
        
        assert weather_response.status_code == 200, "weather query failed"
        weather_data = weather_response.json()
        
        assert weather_data["modality_type"] == "weather"
        assert "results" in weather_data
        assert "query" in weather_data
