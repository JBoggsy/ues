"""Integration tests for POST /calendar/query endpoint."""

from datetime import datetime, timedelta, timezone


class TestPostCalendarQuery:
    """Tests for POST /calendar/query endpoint."""

    def test_query_with_no_filters_returns_all(self, client_with_engine):
        """Test that query with no filters returns all events."""
        client, engine = client_with_engine
        
        # Get current time via API
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create multiple events
        for i in range(3):
            start = current_time + timedelta(hours=i + 1)
            end = start + timedelta(hours=1)
            client.post(
                "/calendar/create",
                json={
                    "title": f"Event {i+1}",
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                },
            )
        
        # Query with no filters
        response = client.post("/calendar/query", json={})
        
        assert response.status_code == 200
        data = response.json()
        
        assert "events" in data
        assert "count" in data
        assert "total_count" in data
        assert data["count"] == 3
        assert data["total_count"] == 3

    def test_filter_by_date_range(self, client_with_engine):
        """Test filtering events by date range (start/end)."""
        client, engine = client_with_engine
        
        # Get current time via API
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create events at different times
        # Event 1: in 1 hour
        start1 = current_time + timedelta(hours=1)
        client.post("/calendar/create", json={
            "title": "Early Event",
            "start": start1.isoformat(),
            "end": (start1 + timedelta(hours=1)).isoformat(),
        })
        
        # Event 2: in 5 hours
        start2 = current_time + timedelta(hours=5)
        client.post("/calendar/create", json={
            "title": "Middle Event",
            "start": start2.isoformat(),
            "end": (start2 + timedelta(hours=1)).isoformat(),
        })
        
        # Event 3: in 10 hours
        start3 = current_time + timedelta(hours=10)
        client.post("/calendar/create", json={
            "title": "Late Event",
            "start": start3.isoformat(),
            "end": (start3 + timedelta(hours=1)).isoformat(),
        })
        
        # Query for events between 4 and 6 hours from now
        range_start = current_time + timedelta(hours=4)
        range_end = current_time + timedelta(hours=6)
        
        response = client.post("/calendar/query", json={
            "start": range_start.isoformat(),
            "end": range_end.isoformat(),
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Only the middle event should match
        assert data["count"] == 1
        assert data["events"][0]["title"] == "Middle Event"

    def test_filter_by_status_confirmed(self, client_with_engine):
        """Test filtering events by status='confirmed'."""
        client, engine = client_with_engine
        
        # Get current time via API
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create confirmed event
        start1 = current_time + timedelta(hours=1)
        client.post("/calendar/create", json={
            "title": "Confirmed Event",
            "start": start1.isoformat(),
            "end": (start1 + timedelta(hours=1)).isoformat(),
            "status": "confirmed",
        })
        
        # Create tentative event
        start2 = current_time + timedelta(hours=2)
        client.post("/calendar/create", json={
            "title": "Tentative Event",
            "start": start2.isoformat(),
            "end": (start2 + timedelta(hours=1)).isoformat(),
            "status": "tentative",
        })
        
        # Query for confirmed only
        response = client.post("/calendar/query", json={"status": "confirmed"})
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["count"] == 1
        assert data["events"][0]["title"] == "Confirmed Event"
        assert data["events"][0]["status"] == "confirmed"

    def test_filter_by_status_cancelled(self, client_with_engine):
        """Test filtering events by status='cancelled'."""
        client, engine = client_with_engine
        
        # Get current time via API
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create confirmed event
        start1 = current_time + timedelta(hours=1)
        client.post("/calendar/create", json={
            "title": "Active Event",
            "start": start1.isoformat(),
            "end": (start1 + timedelta(hours=1)).isoformat(),
            "status": "confirmed",
        })
        
        # Create cancelled event
        start2 = current_time + timedelta(hours=2)
        client.post("/calendar/create", json={
            "title": "Cancelled Event",
            "start": start2.isoformat(),
            "end": (start2 + timedelta(hours=1)).isoformat(),
            "status": "cancelled",
        })
        
        # Query for cancelled only
        response = client.post("/calendar/query", json={"status": "cancelled"})
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["count"] == 1
        assert data["events"][0]["title"] == "Cancelled Event"

    def test_filter_by_search_text(self, client_with_engine):
        """Test searching event titles and descriptions."""
        client, engine = client_with_engine
        
        # Get current time via API
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create events with different titles/descriptions
        start1 = current_time + timedelta(hours=1)
        client.post("/calendar/create", json={
            "title": "Team Standup",
            "description": "Daily sync meeting",
            "start": start1.isoformat(),
            "end": (start1 + timedelta(hours=1)).isoformat(),
        })
        
        start2 = current_time + timedelta(hours=2)
        client.post("/calendar/create", json={
            "title": "Project Planning",
            "description": "Quarterly planning session",
            "start": start2.isoformat(),
            "end": (start2 + timedelta(hours=1)).isoformat(),
        })
        
        # Search for "standup"
        response = client.post("/calendar/query", json={"search": "standup"})
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["count"] == 1
        assert data["events"][0]["title"] == "Team Standup"

    def test_filter_by_attendees(self, client_with_engine):
        """Test filtering events by attendee presence."""
        client, engine = client_with_engine
        
        # Get current time via API
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create event with attendees
        start1 = current_time + timedelta(hours=1)
        client.post("/calendar/create", json={
            "title": "Meeting with Attendees",
            "start": start1.isoformat(),
            "end": (start1 + timedelta(hours=1)).isoformat(),
            "attendees": [{"email": "attendee@example.com"}],
        })
        
        # Create event without attendees
        start2 = current_time + timedelta(hours=2)
        client.post("/calendar/create", json={
            "title": "Solo Event",
            "start": start2.isoformat(),
            "end": (start2 + timedelta(hours=1)).isoformat(),
        })
        
        # Query for events with attendees
        response = client.post("/calendar/query", json={"has_attendees": True})
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["count"] == 1
        assert data["events"][0]["title"] == "Meeting with Attendees"

    def test_filter_recurring_events(self, client_with_engine):
        """Test filtering for recurring vs one-time events."""
        client, engine = client_with_engine
        
        # Get current time via API
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create one-time event
        start1 = current_time + timedelta(hours=1)
        client.post("/calendar/create", json={
            "title": "One-time Event",
            "start": start1.isoformat(),
            "end": (start1 + timedelta(hours=1)).isoformat(),
        })
        
        # Create recurring event
        start2 = current_time + timedelta(hours=2)
        client.post("/calendar/create", json={
            "title": "Recurring Event",
            "start": start2.isoformat(),
            "end": (start2 + timedelta(hours=1)).isoformat(),
            "recurrence": {
                "frequency": "daily",
                "interval": 1,
                "end_type": "never",
            },
        })
        
        # Query for recurring events only
        response = client.post("/calendar/query", json={"recurring": True})
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["count"] == 1
        assert data["events"][0]["title"] == "Recurring Event"

    def test_pagination_with_limit(self, client_with_engine):
        """Test pagination using limit parameter."""
        client, engine = client_with_engine
        
        # Get current time via API
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create 5 events
        for i in range(5):
            start = current_time + timedelta(hours=i + 1)
            client.post("/calendar/create", json={
                "title": f"Event {i+1}",
                "start": start.isoformat(),
                "end": (start + timedelta(hours=1)).isoformat(),
            })
        
        # Query with limit of 2
        response = client.post("/calendar/query", json={"limit": 2})
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["count"] == 2
        assert data["total_count"] == 5

    def test_pagination_with_offset(self, client_with_engine):
        """Test pagination using offset parameter."""
        client, engine = client_with_engine
        
        # Get current time via API
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create 5 events with sequential titles
        for i in range(5):
            start = current_time + timedelta(hours=i + 1)
            client.post("/calendar/create", json={
                "title": f"Event {i+1}",
                "start": start.isoformat(),
                "end": (start + timedelta(hours=1)).isoformat(),
            })
        
        # Query with offset of 2
        response = client.post("/calendar/query", json={"offset": 2})
        
        assert response.status_code == 200
        data = response.json()
        
        # Should skip first 2, return remaining 3
        assert data["count"] == 3
        assert data["total_count"] == 5

    def test_sort_by_start_time(self, client_with_engine):
        """Test sorting events by start time."""
        client, engine = client_with_engine
        
        # Get current time via API
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create events in non-chronological order
        times_and_titles = [
            (3, "Third"),
            (1, "First"),
            (2, "Second"),
        ]
        
        for hours, title in times_and_titles:
            start = current_time + timedelta(hours=hours)
            client.post("/calendar/create", json={
                "title": title,
                "start": start.isoformat(),
                "end": (start + timedelta(hours=1)).isoformat(),
            })
        
        # Query sorted by start time ascending
        response = client.post("/calendar/query", json={
            "sort_by": "start",
            "sort_order": "asc",
        })
        
        assert response.status_code == 200
        data = response.json()
        
        titles = [e["title"] for e in data["events"]]
        assert titles == ["First", "Second", "Third"]
        
        # Query sorted descending
        response = client.post("/calendar/query", json={
            "sort_by": "start",
            "sort_order": "desc",
        })
        
        assert response.status_code == 200
        data = response.json()
        
        titles = [e["title"] for e in data["events"]]
        assert titles == ["Third", "Second", "First"]

    def test_combined_filters(self, client_with_engine):
        """Test query with multiple filters combined."""
        client, engine = client_with_engine
        
        # Get current time via API
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create diverse events
        # Event 1: confirmed, with attendees, in range
        start1 = current_time + timedelta(hours=2)
        client.post("/calendar/create", json={
            "title": "Target Meeting",
            "start": start1.isoformat(),
            "end": (start1 + timedelta(hours=1)).isoformat(),
            "status": "confirmed",
            "attendees": [{"email": "attendee@example.com"}],
        })
        
        # Event 2: confirmed, no attendees, in range
        start2 = current_time + timedelta(hours=3)
        client.post("/calendar/create", json={
            "title": "Solo Event",
            "start": start2.isoformat(),
            "end": (start2 + timedelta(hours=1)).isoformat(),
            "status": "confirmed",
        })
        
        # Event 3: tentative, with attendees, in range
        start3 = current_time + timedelta(hours=4)
        client.post("/calendar/create", json={
            "title": "Tentative Meeting",
            "start": start3.isoformat(),
            "end": (start3 + timedelta(hours=1)).isoformat(),
            "status": "tentative",
            "attendees": [{"email": "attendee2@example.com"}],
        })
        
        # Query with combined filters: confirmed + has_attendees
        response = client.post("/calendar/query", json={
            "status": "confirmed",
            "has_attendees": True,
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Only "Target Meeting" should match
        assert data["count"] == 1
        assert data["events"][0]["title"] == "Target Meeting"

    def test_empty_results_when_no_matches(self, client_with_engine):
        """Test that query returns empty results when filters match nothing."""
        client, engine = client_with_engine
        
        # Get current time via API
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create an event
        start = current_time + timedelta(hours=1)
        client.post("/calendar/create", json={
            "title": "Test Event",
            "start": start.isoformat(),
            "end": (start + timedelta(hours=1)).isoformat(),
            "status": "confirmed",
        })
        
        # Query for cancelled events (none exist)
        response = client.post("/calendar/query", json={"status": "cancelled"})
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["events"] == []
        assert data["count"] == 0
        assert data["total_count"] == 0
