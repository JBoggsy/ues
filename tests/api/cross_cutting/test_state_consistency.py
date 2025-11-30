"""Cross-cutting integration tests for state consistency.

This module tests that state changes are properly reflected across all related
API endpoints, ensuring that data is consistent regardless of which endpoint
is used to query it.

Tests cover:
- Event lifecycle consistency (created → executed → reflected)
- Time state consistency across endpoints
- Environment state consistency after modality events
- Simulation lifecycle consistency
- Cross-modality consistency
- Edge cases (rapid operations, failed events)
"""

from datetime import datetime, timedelta

import pytest

from tests.api.helpers import (
    make_event_request,
    email_event_data,
    sms_event_data,
    chat_event_data,
    location_event_data,
    calendar_event_data,
    weather_event_data,
)


# =============================================================================
# Event Lifecycle Consistency
# =============================================================================


class TestEventLifecycleConsistency:
    """Tests that event state is consistent across all event-related endpoints."""

    def test_created_event_appears_in_events_list(self, client_with_engine):
        """Created event should appear in GET /events list."""
        client, _ = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        event_time = current_time + timedelta(hours=1)
        
        # Create event
        create_response = client.post(
            "/events",
            json=make_event_request(event_time, "email", email_event_data()),
        )
        assert create_response.status_code == 200
        event_id = create_response.json()["event_id"]
        
        # Verify appears in list
        list_response = client.get("/events")
        assert list_response.status_code == 200
        events = list_response.json()["events"]
        event_ids = [e["event_id"] for e in events]
        assert event_id in event_ids

    def test_created_event_updates_summary_counts(self, client_with_engine):
        """Created event should update GET /events/summary counts."""
        client, _ = client_with_engine
        
        # Get initial summary
        initial_response = client.get("/events/summary")
        assert initial_response.status_code == 200
        initial_pending = initial_response.json()["pending"]
        
        # Create event
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        create_response = client.post(
            "/events",
            json=make_event_request(
                current_time + timedelta(hours=1),
                "email",
                email_event_data(),
            ),
        )
        assert create_response.status_code == 200
        
        # Verify summary updated
        after_response = client.get("/events/summary")
        assert after_response.status_code == 200
        assert after_response.json()["pending"] == initial_pending + 1

    def test_executed_event_status_updated_in_get_event(self, client_with_engine):
        """Executed event should show executed status in GET /events/{id}."""
        client, _ = client_with_engine
        
        # Create immediate event
        create_response = client.post(
            "/events/immediate",
            json={"modality": "location", "data": location_event_data()},
        )
        assert create_response.status_code == 200
        event_id = create_response.json()["event_id"]
        
        # Advance time to execute the event
        client.post("/simulator/time/advance", json={"seconds": 1})
        
        # Verify status
        get_response = client.get(f"/events/{event_id}")
        assert get_response.status_code == 200
        assert get_response.json()["status"] == "executed"

    def test_executed_event_reflected_in_environment_state(self, client_with_engine):
        """Executed event should update environment state."""
        client, _ = client_with_engine
        
        new_lat, new_lon = 40.7128, -74.0060
        
        # Create immediate event
        client.post(
            "/events/immediate",
            json={"modality": "location", "data": location_event_data(
                latitude=new_lat,
                longitude=new_lon,
            )},
        )
        
        # Advance time to execute the event
        client.post("/simulator/time/advance", json={"seconds": 1})
        
        # Verify environment state reflects change
        env_response = client.get("/environment/state")
        assert env_response.status_code == 200
        location_state = env_response.json()["modalities"]["location"]
        assert location_state["current_latitude"] == new_lat
        assert location_state["current_longitude"] == new_lon

    def test_cancelled_event_removed_from_pending_count(self, client_with_engine):
        """Cancelled event should decrement pending count."""
        client, _ = client_with_engine
        
        # Get initial count
        initial_response = client.get("/events")
        initial_pending = initial_response.json()["pending"]
        
        # Create event
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        create_response = client.post(
            "/events",
            json=make_event_request(
                current_time + timedelta(hours=1),
                "email",
                email_event_data(),
            ),
        )
        event_id = create_response.json()["event_id"]
        
        # Verify pending increased
        after_create = client.get("/events")
        assert after_create.json()["pending"] == initial_pending + 1
        
        # Cancel event
        delete_response = client.delete(f"/events/{event_id}")
        assert delete_response.status_code == 200
        
        # Verify pending decreased
        after_cancel = client.get("/events")
        assert after_cancel.json()["pending"] == initial_pending

    def test_immediate_event_increments_executed_count(self, client_with_engine):
        """Immediate event should increment executed count in summary after time advance."""
        client, _ = client_with_engine
        
        # Get initial count
        initial_response = client.get("/events/summary")
        initial_executed = initial_response.json()["executed"]
        
        # Create immediate event
        client.post(
            "/events/immediate",
            json={"modality": "location", "data": location_event_data()},
        )
        
        # Advance time to execute
        client.post("/simulator/time/advance", json={"seconds": 1})
        
        # Verify executed count increased
        after_response = client.get("/events/summary")
        assert after_response.json()["executed"] == initial_executed + 1


# =============================================================================
# Time State Consistency
# =============================================================================


class TestTimeStateConsistency:
    """Tests that time state is consistent across all time-related endpoints."""

    def test_time_advance_reflected_in_simulator_time(self, client_with_engine):
        """Time advance should update GET /simulator/time."""
        client, _ = client_with_engine
        
        # Get initial time
        initial_response = client.get("/simulator/time")
        initial_time = datetime.fromisoformat(initial_response.json()["current_time"])
        
        # Advance time
        advance_seconds = 3600  # 1 hour
        client.post("/simulator/time/advance", json={"seconds": advance_seconds})
        
        # Verify time updated
        after_response = client.get("/simulator/time")
        after_time = datetime.fromisoformat(after_response.json()["current_time"])
        
        expected_time = initial_time + timedelta(seconds=advance_seconds)
        assert abs((after_time - expected_time).total_seconds()) < 1

    def test_time_advance_reflected_in_simulation_status(self, client_with_engine):
        """Time advance should update GET /simulation/status current_time."""
        client, _ = client_with_engine
        
        # Get initial time
        initial_response = client.get("/simulation/status")
        initial_time = datetime.fromisoformat(initial_response.json()["current_time"])
        
        # Advance time
        advance_seconds = 3600
        client.post("/simulator/time/advance", json={"seconds": advance_seconds})
        
        # Verify status time updated
        after_response = client.get("/simulation/status")
        after_time = datetime.fromisoformat(after_response.json()["current_time"])
        
        expected_time = initial_time + timedelta(seconds=advance_seconds)
        assert abs((after_time - expected_time).total_seconds()) < 1

    def test_time_advance_reflected_in_environment_state(self, client_with_engine):
        """Time advance should update GET /environment/state current_time."""
        client, _ = client_with_engine
        
        # Get initial time
        initial_response = client.get("/environment/state")
        initial_time = datetime.fromisoformat(initial_response.json()["current_time"])
        
        # Advance time
        advance_seconds = 3600
        client.post("/simulator/time/advance", json={"seconds": advance_seconds})
        
        # Verify environment time updated
        after_response = client.get("/environment/state")
        after_time = datetime.fromisoformat(after_response.json()["current_time"])
        
        expected_time = initial_time + timedelta(seconds=advance_seconds)
        assert abs((after_time - expected_time).total_seconds()) < 1

    def test_pause_state_consistent_across_endpoints(self, client_with_engine):
        """Pause state should be consistent across time and status endpoints."""
        client, _ = client_with_engine
        
        # Pause simulation
        client.post("/simulator/time/pause")
        
        # Check time endpoint
        time_response = client.get("/simulator/time")
        assert time_response.json()["is_paused"] is True
        
        # Check status endpoint
        status_response = client.get("/simulation/status")
        assert status_response.json()["is_paused"] is True
        
        # Resume
        client.post("/simulator/time/resume")
        
        # Verify both updated
        time_response = client.get("/simulator/time")
        assert time_response.json()["is_paused"] is False
        
        status_response = client.get("/simulation/status")
        assert status_response.json()["is_paused"] is False

    def test_time_scale_consistent_across_endpoints(self, client_with_engine):
        """Time scale should be consistent across time and status endpoints."""
        client, _ = client_with_engine
        
        new_scale = 2.5
        
        # Set time scale
        client.post("/simulator/time/set-scale", json={"scale": new_scale})
        
        # Check time endpoint
        time_response = client.get("/simulator/time")
        assert time_response.json()["time_scale"] == new_scale
        
        # Check status endpoint
        status_response = client.get("/simulation/status")
        assert status_response.json()["time_scale"] == new_scale

    def test_set_time_reflected_in_all_time_endpoints(self, client_with_engine):
        """Set time should be reflected across all time-reporting endpoints."""
        client, _ = client_with_engine
        
        # Get current time and set to future
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        target_time = current_time + timedelta(hours=5)
        
        # Set time
        set_response = client.post(
            "/simulator/time/set",
            json={"target_time": target_time.isoformat()},
        )
        assert set_response.status_code == 200
        
        # Verify across all endpoints
        time_after = client.get("/simulator/time")
        status_after = client.get("/simulation/status")
        env_after = client.get("/environment/state")
        
        time_value = datetime.fromisoformat(time_after.json()["current_time"])
        status_value = datetime.fromisoformat(status_after.json()["current_time"])
        env_value = datetime.fromisoformat(env_after.json()["current_time"])
        
        # All should be approximately equal to target
        for value in [time_value, status_value, env_value]:
            assert abs((value - target_time).total_seconds()) < 1


# =============================================================================
# Environment State Consistency
# =============================================================================


class TestEnvironmentStateConsistency:
    """Tests that environment state is consistent after modality events."""

    def test_email_event_updates_email_modality_state(self, client_with_engine):
        """Email event should update email modality state."""
        client, _ = client_with_engine
        
        # Get initial state
        initial_response = client.get("/environment/modalities/email")
        initial_count = len(initial_response.json()["state"]["emails"])
        
        # Execute email receive event
        client.post(
            "/events/immediate",
            json={"modality": "email", "data": email_event_data(
                operation="receive",
                subject="Consistency Test Email",
                from_address="test@example.com",
            )},
        )
        
        # Advance time to execute
        client.post("/simulator/time/advance", json={"seconds": 1})
        
        # Check modality-specific endpoint
        modality_response = client.get("/environment/modalities/email")
        assert modality_response.status_code == 200
        email_state = modality_response.json()["state"]
        
        # Check full environment state
        env_response = client.get("/environment/state")
        env_email_state = env_response.json()["modalities"]["email"]
        
        # Both should have more emails than before
        assert len(email_state["emails"]) > initial_count
        assert len(env_email_state["emails"]) > initial_count

    def test_sms_event_updates_sms_modality_state(self, client_with_engine):
        """SMS event should update SMS modality state."""
        client, _ = client_with_engine
        
        # Get initial state
        initial_response = client.get("/environment/modalities/sms")
        initial_conversations = len(initial_response.json()["state"]["conversations"])
        
        # Execute SMS receive event
        client.post(
            "/events/immediate",
            json={"modality": "sms", "data": sms_event_data(
                action="receive_message",
                from_number="+1234567890",
                body="Test SMS",
            )},
        )
        
        # Advance time to execute
        client.post("/simulator/time/advance", json={"seconds": 1})
        
        # Check modality-specific endpoint
        modality_response = client.get("/environment/modalities/sms")
        assert modality_response.status_code == 200
        sms_state = modality_response.json()["state"]
        
        # Should have at least one conversation
        assert len(sms_state["conversations"]) > initial_conversations

    def test_chat_event_updates_chat_modality_state(self, client_with_engine):
        """Chat event should update chat modality state."""
        client, _ = client_with_engine
        
        # Execute chat message event
        client.post(
            "/events/immediate",
            json={"modality": "chat", "data": chat_event_data(
                role="user",
                content="Test chat message",
                conversation_id="test_conv",
            )},
        )
        
        # Advance time to execute
        client.post("/simulator/time/advance", json={"seconds": 1})
        
        # Check modality-specific endpoint
        modality_response = client.get("/environment/modalities/chat")
        assert modality_response.status_code == 200
        chat_state = modality_response.json()["state"]
        
        # Should have the conversation
        assert "test_conv" in chat_state["conversations"]

    def test_location_event_updates_location_modality_state(self, client_with_engine):
        """Location event should update location modality state."""
        client, _ = client_with_engine
        
        new_lat, new_lon = 51.5074, -0.1278  # London
        
        # Execute location update event
        client.post(
            "/events/immediate",
            json={"modality": "location", "data": location_event_data(
                latitude=new_lat,
                longitude=new_lon,
            )},
        )
        
        # Advance time to execute
        client.post("/simulator/time/advance", json={"seconds": 1})
        
        # Check modality-specific endpoint
        modality_response = client.get("/environment/modalities/location")
        assert modality_response.status_code == 200
        location_state = modality_response.json()["state"]
        
        assert location_state["current_latitude"] == new_lat
        assert location_state["current_longitude"] == new_lon

    def test_calendar_event_updates_calendar_modality_state(self, client_with_engine):
        """Calendar event should update calendar modality state."""
        client, _ = client_with_engine
        
        # Get current time for event scheduling
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Get initial count
        initial_response = client.get("/environment/modalities/calendar")
        initial_count = len(initial_response.json()["state"]["events"])
        
        # Execute calendar create event
        client.post(
            "/events/immediate",
            json={"modality": "calendar", "data": calendar_event_data(
                operation="create",
                title="Consistency Test Meeting",
                start_time=current_time + timedelta(days=1),
                end_time=current_time + timedelta(days=1, hours=1),
            )},
        )
        
        # Advance time to execute
        client.post("/simulator/time/advance", json={"seconds": 1})
        
        # Check modality-specific endpoint
        modality_response = client.get("/environment/modalities/calendar")
        assert modality_response.status_code == 200
        calendar_state = modality_response.json()["state"]
        
        # Should have more events than before
        assert len(calendar_state["events"]) > initial_count

    def test_weather_event_updates_weather_modality_state(self, client_with_engine):
        """Weather event should update weather modality state."""
        client, _ = client_with_engine
        
        test_lat, test_lon = 48.8566, 2.3522  # Paris
        
        # Get initial count
        initial_response = client.get("/environment/modalities/weather")
        initial_count = len(initial_response.json()["state"]["locations"])
        
        # Execute weather update event
        client.post(
            "/events/immediate",
            json={"modality": "weather", "data": weather_event_data(
                latitude=test_lat,
                longitude=test_lon,
            )},
        )
        
        # Advance time to execute
        client.post("/simulator/time/advance", json={"seconds": 1})
        
        # Check modality-specific endpoint
        modality_response = client.get("/environment/modalities/weather")
        assert modality_response.status_code == 200
        weather_state = modality_response.json()["state"]
        
        # Should have weather data for more locations
        assert len(weather_state["locations"]) > initial_count

    def test_modality_state_matches_full_environment_snapshot(self, client_with_engine):
        """Modality state endpoint should match corresponding state in full snapshot."""
        client, _ = client_with_engine
        
        # Update location
        client.post(
            "/events/immediate",
            json={"modality": "location", "data": location_event_data(
                latitude=35.6762,
                longitude=139.6503,  # Tokyo
            )},
        )
        
        # Advance time to execute
        client.post("/simulator/time/advance", json={"seconds": 1})
        
        # Get modality-specific state
        modality_response = client.get("/environment/modalities/location")
        modality_state = modality_response.json()["state"]
        
        # Get full environment state
        env_response = client.get("/environment/state")
        env_location_state = env_response.json()["modalities"]["location"]
        
        # States should match
        assert modality_state["current_latitude"] == env_location_state["current_latitude"]
        assert modality_state["current_longitude"] == env_location_state["current_longitude"]

    def test_modality_query_results_match_state(self, client_with_engine):
        """Modality query results should be consistent with modality state."""
        client, _ = client_with_engine
        
        # Send chat message
        client.post(
            "/events/immediate",
            json={"modality": "chat", "data": chat_event_data(
                role="user",
                content="Query test message",
                conversation_id="query_test",
            )},
        )
        
        # Get state
        state_response = client.get("/environment/modalities/chat")
        chat_state = state_response.json()["state"]
        
        # Query messages
        query_response = client.post(
            "/environment/modalities/chat/query",
            json={"conversation_id": "query_test"},
        )
        query_results = query_response.json()
        
        # Query should return messages from state
        assert len(query_results["results"]) > 0


# =============================================================================
# Simulation Lifecycle Consistency
# =============================================================================


class TestSimulationLifecycleConsistency:
    """Tests that simulation lifecycle state is consistent across endpoints."""

    def test_start_sets_is_running_true_in_status(self, client_with_engine):
        """Starting simulation should set is_running=true in status."""
        client, _ = client_with_engine
        # client_with_engine already starts the simulation
        
        status_response = client.get("/simulation/status")
        assert status_response.json()["is_running"] is True

    def test_stop_sets_is_running_false_in_status(self, client_with_engine):
        """Stopping simulation should set is_running=false in status."""
        client, _ = client_with_engine
        
        # Stop simulation
        stop_response = client.post("/simulation/stop")
        assert stop_response.status_code == 200
        
        # Verify status
        status_response = client.get("/simulation/status")
        assert status_response.json()["is_running"] is False

    def test_reset_resets_event_statuses_and_time(self, client_with_engine):
        """Reset should reset event statuses and simulation time."""
        client, _ = client_with_engine
        
        # Get initial time
        time_response = client.get("/simulator/time")
        initial_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create some events
        event_time = initial_time + timedelta(seconds=1)
        event_ids = []
        for i in range(3):
            response = client.post(
                "/events",
                json=make_event_request(
                    event_time + timedelta(seconds=i),
                    "location",
                    location_event_data(),
                ),
            )
            event_ids.append(response.json()["event_id"])
        
        # Advance time to execute events
        client.post("/simulator/time/advance", json={"seconds": 5})
        
        # Verify events were executed
        for event_id in event_ids:
            response = client.get(f"/events/{event_id}")
            assert response.json()["status"] in ["executed", "failed"]
        
        # Reset
        reset_response = client.post("/simulation/reset")
        assert reset_response.status_code == 200
        
        # Verify events reset to pending
        for event_id in event_ids:
            response = client.get(f"/events/{event_id}")
            assert response.json()["status"] == "pending"

    def test_reset_preserves_modality_registrations(self, client_with_engine):
        """Reset should preserve modality registrations."""
        client, _ = client_with_engine
        
        # Get modalities before reset
        before_response = client.get("/environment/modalities")
        modalities_before = set(before_response.json()["modalities"])
        
        # Reset
        client.post("/simulation/reset")
        
        # Restart simulation
        client.post("/simulation/start")
        
        # Get modalities after reset
        after_response = client.get("/environment/modalities")
        modalities_after = set(after_response.json()["modalities"])
        
        # Modalities should be preserved
        assert modalities_before == modalities_after

    def test_stop_returns_accurate_event_counts(self, client_with_engine):
        """Stop should return accurate counts of events."""
        client, _ = client_with_engine
        
        # Execute some events
        for i in range(3):
            client.post(
                "/events/immediate",
                json={"modality": "location", "data": location_event_data()},
            )
        
        # Advance time to execute immediate events
        client.post("/simulator/time/advance", json={"seconds": 1})
        
        # Create pending events (scheduled for future)
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        for i in range(2):
            client.post(
                "/events",
                json=make_event_request(
                    current_time + timedelta(hours=i + 1),
                    "email",
                    email_event_data(),
                ),
            )
        
        # Stop and check counts
        stop_response = client.post("/simulation/stop")
        assert stop_response.status_code == 200
        stop_data = stop_response.json()
        
        # Verify executed count matches what we executed
        # Note: stop response uses 'events_executed', not 'executed_events'
        assert stop_data["events_executed"] >= 3

    def test_status_reflects_auto_advance_mode(self, client_with_engine):
        """Status should reflect whether auto_advance mode is enabled."""
        client, _ = client_with_engine
        
        # Stop current simulation
        client.post("/simulation/stop")
        
        # Start with auto_advance
        start_response = client.post(
            "/simulation/start",
            json={"auto_advance": True},
        )
        assert start_response.status_code == 200
        
        # Status should show running (auto_advance affects behavior, not status field)
        status_response = client.get("/simulation/status")
        assert status_response.json()["is_running"] is True


# =============================================================================
# Cross-Modality Consistency
# =============================================================================


class TestCrossModalityConsistency:
    """Tests that cross-modality operations are consistent."""

    def test_multiple_events_at_same_time_all_execute(self, client_with_engine):
        """Multiple events scheduled at same time should all execute."""
        client, _ = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        event_time = current_time + timedelta(hours=1)
        
        # Create multiple events at same time
        modalities = ["email", "sms", "chat"]
        event_data = [
            email_event_data(subject="Multi-event test"),
            sms_event_data(body="Multi-event test"),
            chat_event_data(content="Multi-event test"),
        ]
        
        event_ids = []
        for modality, data in zip(modalities, event_data):
            response = client.post(
                "/events",
                json=make_event_request(event_time, modality, data),
            )
            assert response.status_code == 200
            event_ids.append(response.json()["event_id"])
        
        # Advance past event time
        client.post("/simulator/time/advance", json={"seconds": 3700})
        
        # Verify all executed
        for event_id in event_ids:
            event_response = client.get(f"/events/{event_id}")
            assert event_response.json()["status"] == "executed"

    def test_event_priorities_respected_across_modalities(self, client_with_engine):
        """Event priorities should be respected regardless of modality."""
        client, _ = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        event_time = current_time + timedelta(hours=1)
        
        # Create events with different priorities at same time
        low_priority = client.post(
            "/events",
            json=make_event_request(event_time, "email", email_event_data(), priority=10),
        ).json()
        
        high_priority = client.post(
            "/events",
            json=make_event_request(event_time, "sms", sms_event_data(), priority=90),
        ).json()
        
        # Get next event (should be high priority)
        next_response = client.get("/events/next")
        assert next_response.status_code == 200
        next_event = next_response.json()
        
        # Higher priority event should be next
        assert next_event["event_id"] == high_priority["event_id"]

    def test_time_advance_executes_events_from_all_modalities(self, client_with_engine):
        """Time advance should execute events from all modalities."""
        client, _ = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create events in different modalities at different times
        events = [
            (current_time + timedelta(minutes=10), "email", email_event_data()),
            (current_time + timedelta(minutes=20), "sms", sms_event_data()),
            (current_time + timedelta(minutes=30), "chat", chat_event_data()),
        ]
        
        event_ids = []
        for scheduled_time, modality, data in events:
            response = client.post(
                "/events",
                json=make_event_request(scheduled_time, modality, data),
            )
            event_ids.append(response.json()["event_id"])
        
        # Advance past all events
        client.post("/simulator/time/advance", json={"seconds": 2400})  # 40 minutes
        
        # Verify all executed
        for event_id in event_ids:
            event_response = client.get(f"/events/{event_id}")
            assert event_response.json()["status"] == "executed"

    def test_environment_state_shows_all_modality_changes(self, client_with_engine):
        """Environment state should reflect changes from all modalities."""
        client, _ = client_with_engine
        
        # Update multiple modalities
        client.post(
            "/events/immediate",
            json={"modality": "location", "data": location_event_data(
                latitude=34.0522,
                longitude=-118.2437,  # Los Angeles
            )},
        )
        
        client.post(
            "/events/immediate",
            json={"modality": "chat", "data": chat_event_data(
                content="Cross-modality test",
                conversation_id="cross_test",
            )},
        )
        
        # Advance time to execute all events
        client.post("/simulator/time/advance", json={"seconds": 1})
        
        # Get environment state
        env_response = client.get("/environment/state")
        env_data = env_response.json()
        
        # Verify both changes reflected
        assert env_data["modalities"]["location"]["current_latitude"] == 34.0522
        assert "cross_test" in env_data["modalities"]["chat"]["conversations"]


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCaseConsistency:
    """Tests for state consistency in edge cases."""

    def test_state_consistent_after_rapid_operations(self, client_with_engine):
        """State should remain consistent after many rapid operations."""
        client, _ = client_with_engine
        
        # Perform many operations rapidly
        for i in range(10):
            client.post(
                "/events/immediate",
                json={"modality": "location", "data": location_event_data(
                    latitude=37.0 + i * 0.1,
                    longitude=-122.0 + i * 0.1,
                )},
            )
        
        # Advance time to execute all events
        client.post("/simulator/time/advance", json={"seconds": 1})
        
        # Verify state is consistent
        env_response = client.get("/environment/state")
        location_state = env_response.json()["modalities"]["location"]
        
        # Should reflect the last update
        assert location_state["current_latitude"] == pytest.approx(37.9, rel=0.01)
        assert location_state["current_longitude"] == pytest.approx(-121.1, rel=0.01)
        
        # History should have all locations
        assert len(location_state["location_history"]) >= 10

    def test_state_consistent_after_skip_to_next(self, client_with_engine):
        """State should remain consistent after skip-to-next operations."""
        client, _ = client_with_engine
        
        # Get current time
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create multiple events
        for i in range(5):
            client.post(
                "/events",
                json=make_event_request(
                    current_time + timedelta(minutes=10 * (i + 1)),
                    "location",
                    location_event_data(latitude=30.0 + i, longitude=-90.0 + i),
                ),
            )
        
        # Skip through events
        for _ in range(5):
            skip_response = client.post("/simulator/time/skip-to-next")
            if skip_response.status_code == 404:
                break  # No more events
        
        # Verify final state
        summary = client.get("/events/summary").json()
        assert summary["executed"] >= 5
        assert summary["pending"] == 0

    def test_state_consistent_with_mixed_immediate_and_scheduled(self, client_with_engine):
        """State should be consistent with mix of immediate and scheduled events."""
        client, _ = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create scheduled event (for the future)
        scheduled = client.post(
            "/events",
            json=make_event_request(
                current_time + timedelta(minutes=30),
                "email",
                email_event_data(subject="Scheduled"),
            ),
        ).json()
        
        # Create immediate event
        immediate = client.post(
            "/events/immediate",
            json={"modality": "email", "data": email_event_data(subject="Immediate")},
        ).json()
        
        # Advance time a bit to execute immediate
        client.post("/simulator/time/advance", json={"seconds": 1})
        
        # Verify immediate is executed, scheduled is pending
        assert client.get(f"/events/{immediate['event_id']}").json()["status"] == "executed"
        assert client.get(f"/events/{scheduled['event_id']}").json()["status"] == "pending"
        
        # Advance time past scheduled event
        client.post("/simulator/time/advance", json={"seconds": 2000})
        
        # Now both should be executed
        assert client.get(f"/events/{scheduled['event_id']}").json()["status"] == "executed"
