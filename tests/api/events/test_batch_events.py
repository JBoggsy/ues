"""Integration tests for batch event creation endpoint.

This module tests the POST /events/batch endpoint for creating multiple events
in a single request.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status

from tests.api.helpers import (
    location_event_data,
    email_event_data,
    sms_event_data,
    chat_event_data,
)


class TestBatchEventsBasicSuccess:
    """Tests for successful batch event creation."""
    
    def test_create_batch_all_valid(self, client_with_engine):
        """Batch with all valid events returns 201 with all successes."""
        client, engine = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        future_time = current_time + timedelta(hours=1)
        
        response = client.post("/events/batch", json={
            "events": [
                {
                    "scheduled_time": future_time.isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=40.7128, longitude=-74.0060),
                },
                {
                    "scheduled_time": (future_time + timedelta(hours=1)).isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=34.0522, longitude=-118.2437),
                },
            ]
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["total_submitted"] == 2
        assert data["total_created"] == 2
        assert data["total_failed"] == 0
        assert len(data["events"]) == 2
        assert all(e["success"] for e in data["events"])
        assert all(e["event_id"] is not None for e in data["events"])

    def test_create_batch_single_event(self, client_with_engine):
        """Batch with single event works correctly."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        future_time = current_time + timedelta(hours=1)
        
        response = client.post("/events/batch", json={
            "events": [
                {
                    "scheduled_time": future_time.isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=40.7128, longitude=-74.0060),
                },
            ]
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["total_created"] == 1

    def test_create_batch_multiple_modalities(self, client_with_engine):
        """Batch can contain events for different modalities."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        future_time = current_time + timedelta(hours=1)
        
        response = client.post("/events/batch", json={
            "events": [
                {
                    "scheduled_time": future_time.isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=40.7128, longitude=-74.0060),
                },
                {
                    "scheduled_time": (future_time + timedelta(minutes=30)).isoformat(),
                    "modality": "email",
                    "data": email_event_data(
                        operation="receive",
                        from_address="test@example.com",
                        to_addresses=["user@example.com"],
                        subject="Test",
                        body_text="Hello",
                    ),
                },
                {
                    "scheduled_time": (future_time + timedelta(hours=1)).isoformat(),
                    "modality": "sms",
                    "data": sms_event_data(
                        operation="receive_message",
                        from_number="+1234567890",
                        to_numbers=["+0987654321"],
                        body="Test SMS",
                    ),
                },
            ]
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["total_created"] == 3
        
        # Verify all modalities are different
        modalities = {e["modality"] for e in client.get("/events").json()["events"][-3:]}
        assert len(modalities) == 3


class TestBatchEventsPartialSuccess:
    """Tests for partial success scenarios (207 Multi-Status)."""
    
    def test_create_batch_partial_success_past_time(self, client_with_engine):
        """Batch with some events in the past returns 207 with mixed results."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        future_time = current_time + timedelta(hours=1)
        past_time = current_time - timedelta(hours=1)
        
        response = client.post("/events/batch", json={
            "events": [
                {
                    "scheduled_time": future_time.isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=40.7128, longitude=-74.0060),
                },
                {
                    "scheduled_time": past_time.isoformat(),  # Invalid: past time
                    "modality": "location",
                    "data": location_event_data(latitude=34.0522, longitude=-118.2437),
                },
                {
                    "scheduled_time": (future_time + timedelta(hours=1)).isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=51.5074, longitude=-0.1278),
                },
            ]
        })
        
        assert response.status_code == status.HTTP_207_MULTI_STATUS
        data = response.json()
        assert data["total_submitted"] == 3
        assert data["total_created"] == 2
        assert data["total_failed"] == 1
        
        # Check individual results
        assert data["events"][0]["success"] is True
        assert data["events"][1]["success"] is False
        assert "past" in data["events"][1]["error"].lower()
        assert data["events"][2]["success"] is True

    def test_create_batch_invalid_modality(self, client_with_engine):
        """Invalid modality in batch causes that event to fail."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        future_time = current_time + timedelta(hours=1)
        
        response = client.post("/events/batch", json={
            "events": [
                {
                    "scheduled_time": future_time.isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=40.7128, longitude=-74.0060),
                },
                {
                    "scheduled_time": future_time.isoformat(),
                    "modality": "invalid_modality",
                    "data": {"some": "data"},
                },
            ]
        })
        
        assert response.status_code == status.HTTP_207_MULTI_STATUS
        data = response.json()
        assert data["total_created"] == 1
        assert data["total_failed"] == 1
        assert data["events"][0]["success"] is True
        assert data["events"][1]["success"] is False
        assert "unknown modality" in data["events"][1]["error"].lower()

    def test_create_batch_invalid_data(self, client_with_engine):
        """Invalid modality data causes that event to fail."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        future_time = current_time + timedelta(hours=1)
        
        response = client.post("/events/batch", json={
            "events": [
                {
                    "scheduled_time": future_time.isoformat(),
                    "modality": "location",
                    "data": {"action": "update", "latitude": 999},  # Invalid latitude
                },
            ]
        })
        
        assert response.status_code == status.HTTP_207_MULTI_STATUS
        data = response.json()
        assert data["total_failed"] == 1
        assert data["events"][0]["success"] is False

    def test_create_batch_all_failed(self, client_with_engine):
        """Batch where all events fail returns 207 with all failures."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        past_time = current_time - timedelta(hours=1)
        
        response = client.post("/events/batch", json={
            "events": [
                {
                    "scheduled_time": past_time.isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=40.0, longitude=-74.0),
                },
                {
                    "scheduled_time": (past_time - timedelta(hours=1)).isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=34.0, longitude=-118.0),
                },
            ]
        })
        
        assert response.status_code == status.HTTP_207_MULTI_STATUS
        data = response.json()
        assert data["total_created"] == 0
        assert data["total_failed"] == 2
        assert all(not e["success"] for e in data["events"])


class TestBatchEventsStrictMode:
    """Tests for stop_on_first_error (strict) mode."""
    
    def test_stop_on_first_error_aborts_on_invalid(self, client_with_engine):
        """stop_on_first_error=True aborts on first invalid event."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        future_time = current_time + timedelta(hours=1)
        past_time = current_time - timedelta(hours=1)
        
        response = client.post("/events/batch", json={
            "events": [
                {
                    "scheduled_time": future_time.isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=40.7128, longitude=-74.0060),
                },
                {
                    "scheduled_time": past_time.isoformat(),  # This will fail
                    "modality": "location",
                    "data": location_event_data(latitude=34.0522, longitude=-118.2437),
                },
                {
                    "scheduled_time": (future_time + timedelta(hours=1)).isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=51.5074, longitude=-0.1278),
                },
            ],
            "stop_on_first_error": True,
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()["detail"]
        assert data["failed_index"] == 1
        assert data["events_validated"] == 2
        assert data["total_events"] == 3
        assert "past" in data["detail"].lower()

    def test_stop_on_first_error_no_events_created(self, client_with_engine):
        """No events are created when stop_on_first_error fails."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        future_time = current_time + timedelta(hours=1)
        past_time = current_time - timedelta(hours=1)
        
        # Get initial event count
        initial_response = client.get("/events/summary")
        initial_count = initial_response.json()["total"]
        
        # Attempt batch with failure
        client.post("/events/batch", json={
            "events": [
                {
                    "scheduled_time": future_time.isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=40.7128, longitude=-74.0060),
                },
                {
                    "scheduled_time": past_time.isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=34.0522, longitude=-118.2437),
                },
            ],
            "stop_on_first_error": True,
        })
        
        # Verify no events were created
        final_response = client.get("/events/summary")
        assert final_response.json()["total"] == initial_count

    def test_stop_on_first_error_all_valid_creates_all(self, client_with_engine):
        """stop_on_first_error with all valid events creates all."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        future_time = current_time + timedelta(hours=1)
        
        response = client.post("/events/batch", json={
            "events": [
                {
                    "scheduled_time": future_time.isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=40.7128, longitude=-74.0060),
                },
                {
                    "scheduled_time": (future_time + timedelta(hours=1)).isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=34.0522, longitude=-118.2437),
                },
            ],
            "stop_on_first_error": True,
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["total_created"] == 2

    def test_stop_on_first_error_fails_immediately(self, client_with_engine):
        """stop_on_first_error fails at the first invalid event."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        past_time = current_time - timedelta(hours=1)
        
        response = client.post("/events/batch", json={
            "events": [
                {
                    "scheduled_time": past_time.isoformat(),  # First event is invalid
                    "modality": "location",
                    "data": location_event_data(latitude=40.0, longitude=-74.0),
                },
                {
                    "scheduled_time": (current_time + timedelta(hours=1)).isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=34.0, longitude=-118.0),
                },
            ],
            "stop_on_first_error": True,
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()["detail"]
        assert data["failed_index"] == 0
        assert data["events_validated"] == 1


class TestBatchEventsValidateOnly:
    """Tests for validate_only mode."""
    
    def test_validate_only_all_valid(self, client_with_engine):
        """validate_only=True returns validation results without creating."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        future_time = current_time + timedelta(hours=1)
        
        # Get initial event count
        initial_response = client.get("/events/summary")
        initial_count = initial_response.json()["total"]
        
        response = client.post("/events/batch", json={
            "events": [
                {
                    "scheduled_time": future_time.isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=40.7128, longitude=-74.0060),
                },
                {
                    "scheduled_time": (future_time + timedelta(hours=1)).isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=34.0522, longitude=-118.2437),
                },
            ],
            "validate_only": True,
        })
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["validation_only"] is True
        assert data["total_valid"] == 2
        assert data["total_invalid"] == 0
        assert all(e["valid"] for e in data["events"])
        
        # Verify no events were created
        final_response = client.get("/events/summary")
        assert final_response.json()["total"] == initial_count

    def test_validate_only_with_invalid(self, client_with_engine):
        """validate_only returns validation failures without creating."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        future_time = current_time + timedelta(hours=1)
        past_time = current_time - timedelta(hours=1)
        
        # Get initial event count
        initial_response = client.get("/events/summary")
        initial_count = initial_response.json()["total"]
        
        response = client.post("/events/batch", json={
            "events": [
                {
                    "scheduled_time": future_time.isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=40.7128, longitude=-74.0060),
                },
                {
                    "scheduled_time": past_time.isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=34.0522, longitude=-118.2437),
                },
                {
                    "scheduled_time": future_time.isoformat(),
                    "modality": "invalid_modality",
                    "data": {"some": "data"},
                },
            ],
            "validate_only": True,
        })
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_valid"] == 1
        assert data["total_invalid"] == 2
        assert data["events"][0]["valid"] is True
        assert data["events"][1]["valid"] is False
        assert data["events"][2]["valid"] is False
        
        # Verify no events were created
        final_response = client.get("/events/summary")
        assert final_response.json()["total"] == initial_count


class TestBatchEventsEdgeCases:
    """Tests for edge cases and validation."""
    
    def test_empty_batch_returns_400(self, client_with_engine):
        """Empty batch returns 400 error."""
        client, engine = client_with_engine
        
        response = client.post("/events/batch", json={"events": []})
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "at least one" in response.json()["detail"].lower()

    def test_batch_exceeds_limit_returns_400(self, client_with_engine):
        """Batch exceeding size limit returns 400 error."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        future_time = current_time + timedelta(hours=1)
        
        # Create 1001 events (exceeds default limit of 1000)
        events = [
            {
                "scheduled_time": (future_time + timedelta(minutes=i)).isoformat(),
                "modality": "location",
                "data": location_event_data(latitude=40.0, longitude=-74.0),
            }
            for i in range(1001)
        ]
        
        response = client.post("/events/batch", json={"events": events})
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "exceeds maximum" in response.json()["detail"].lower()

    def test_batch_at_limit_succeeds(self, client_with_engine):
        """Batch at exactly the size limit succeeds."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        future_time = current_time + timedelta(hours=1)
        
        # Create exactly 1000 events (at the limit)
        events = [
            {
                "scheduled_time": (future_time + timedelta(minutes=i)).isoformat(),
                "modality": "location",
                "data": location_event_data(latitude=40.0, longitude=-74.0),
            }
            for i in range(1000)
        ]
        
        response = client.post("/events/batch", json={"events": events})
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["total_created"] == 1000

    def test_batch_preserves_order(self, client_with_engine):
        """Response events maintain same order as request."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        future_time = current_time + timedelta(hours=1)
        
        response = client.post("/events/batch", json={
            "events": [
                {
                    "scheduled_time": (future_time + timedelta(hours=3)).isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=10.0, longitude=10.0),
                },
                {
                    "scheduled_time": (future_time + timedelta(hours=1)).isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=20.0, longitude=20.0),
                },
                {
                    "scheduled_time": (future_time + timedelta(hours=2)).isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=30.0, longitude=30.0),
                },
            ]
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        # Verify index order matches request order
        assert data["events"][0]["index"] == 0
        assert data["events"][1]["index"] == 1
        assert data["events"][2]["index"] == 2

    def test_batch_with_priorities(self, client_with_engine):
        """Batch events respect priority settings."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        future_time = current_time + timedelta(hours=1)
        
        response = client.post("/events/batch", json={
            "events": [
                {
                    "scheduled_time": future_time.isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=40.0, longitude=-74.0),
                    "priority": 10,
                },
                {
                    "scheduled_time": future_time.isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=34.0, longitude=-118.0),
                    "priority": 90,
                },
            ]
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify events were created with different priorities
        event_ids = [e["event_id"] for e in response.json()["events"]]
        assert len(event_ids) == 2
        assert all(eid is not None for eid in event_ids)

    def test_batch_with_metadata_and_agent_id(self, client_with_engine):
        """Batch events can include metadata and agent_id."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        future_time = current_time + timedelta(hours=1)
        
        response = client.post("/events/batch", json={
            "events": [
                {
                    "scheduled_time": future_time.isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=40.0, longitude=-74.0),
                    "metadata": {"source": "test", "batch": True},
                    "agent_id": "test-agent-001",
                },
            ]
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        event_id = response.json()["events"][0]["event_id"]
        
        # Verify event was created
        event_response = client.get(f"/events/{event_id}")
        assert event_response.status_code == status.HTTP_200_OK


class TestBatchEventsQueueIntegration:
    """Tests for batch events integration with event queue."""

    def test_batch_events_appear_in_queue(self, client_with_engine):
        """Batch-created events appear in event listing."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        future_time = current_time + timedelta(hours=1)
        
        batch_response = client.post("/events/batch", json={
            "events": [
                {
                    "scheduled_time": future_time.isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=40.0, longitude=-74.0),
                },
                {
                    "scheduled_time": (future_time + timedelta(hours=1)).isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=34.0, longitude=-118.0),
                },
            ]
        })
        
        event_ids = {e["event_id"] for e in batch_response.json()["events"]}
        
        # Verify events appear in listing
        list_response = client.get("/events", params={"status": "pending"})
        listed_ids = {e["event_id"] for e in list_response.json()["events"]}
        
        assert event_ids.issubset(listed_ids)

    def test_batch_events_execute_correctly(self, client_with_engine):
        """Batch-created events execute when time advances."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        future_time = current_time + timedelta(seconds=30)
        
        # Get initial executed count
        initial_summary = client.get("/events/summary").json()
        initial_executed = initial_summary["executed"]
        
        client.post("/events/batch", json={
            "events": [
                {
                    "scheduled_time": future_time.isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=40.7128, longitude=-74.0060),
                },
            ]
        })
        
        # Advance time past the event
        client.post("/simulator/time/advance", json={"seconds": 60})
        
        # Check event was executed
        summary = client.get("/events/summary").json()
        assert summary["executed"] >= initial_executed + 1

    def test_batch_events_update_summary(self, client_with_engine):
        """Batch-created events update event summary statistics."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        future_time = current_time + timedelta(hours=1)
        
        # Get initial summary
        initial_summary = client.get("/events/summary").json()
        initial_pending = initial_summary["pending"]
        initial_total = initial_summary["total"]
        
        # Create batch of 5 events
        client.post("/events/batch", json={
            "events": [
                {
                    "scheduled_time": (future_time + timedelta(minutes=i)).isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=40.0 + i, longitude=-74.0),
                }
                for i in range(5)
            ]
        })
        
        # Check summary updated
        final_summary = client.get("/events/summary").json()
        assert final_summary["pending"] == initial_pending + 5
        assert final_summary["total"] == initial_total + 5


class TestBatchEventsResponseDetails:
    """Tests for response format and content."""

    def test_response_includes_scheduled_time(self, client_with_engine):
        """Response includes scheduled_time for successful events."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        future_time = current_time + timedelta(hours=1)
        
        response = client.post("/events/batch", json={
            "events": [
                {
                    "scheduled_time": future_time.isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=40.0, longitude=-74.0),
                },
            ]
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        event_result = response.json()["events"][0]
        assert event_result["scheduled_time"] is not None
        
        # Verify the scheduled time matches what we requested
        scheduled = datetime.fromisoformat(event_result["scheduled_time"])
        assert abs((scheduled - future_time).total_seconds()) < 1

    def test_failed_events_have_null_ids(self, client_with_engine):
        """Failed events have null event_id and scheduled_time."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        past_time = current_time - timedelta(hours=1)
        
        response = client.post("/events/batch", json={
            "events": [
                {
                    "scheduled_time": past_time.isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=40.0, longitude=-74.0),
                },
            ]
        })
        
        assert response.status_code == status.HTTP_207_MULTI_STATUS
        event_result = response.json()["events"][0]
        assert event_result["success"] is False
        assert event_result["event_id"] is None
        assert event_result["scheduled_time"] is None
        assert event_result["error"] is not None

    def test_event_ids_are_unique(self, client_with_engine):
        """All created events have unique IDs."""
        client, engine = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        future_time = current_time + timedelta(hours=1)
        
        response = client.post("/events/batch", json={
            "events": [
                {
                    "scheduled_time": (future_time + timedelta(minutes=i)).isoformat(),
                    "modality": "location",
                    "data": location_event_data(latitude=40.0 + i, longitude=-74.0),
                }
                for i in range(10)
            ]
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        event_ids = [e["event_id"] for e in response.json()["events"]]
        assert len(event_ids) == len(set(event_ids))  # All unique
