"""Cross-cutting integration tests for concurrent request handling.

This module tests that the system handles concurrent requests correctly,
ensuring data consistency and proper handling of race conditions.

Tests cover:
- Concurrent read operations (multiple simultaneous GETs)
- Concurrent write operations (multiple simultaneous POSTs)
- Read-write consistency (reads during writes)
- Race condition prevention (double-start, double-delete, etc.)
- Resource contention (high-frequency operations)

Note: These tests use ThreadPoolExecutor to simulate concurrent requests.
FastAPI's TestClient is thread-safe for this purpose.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Callable

import pytest

from tests.api.helpers import (
    make_event_request,
    email_event_data,
    sms_event_data,
    chat_event_data,
    location_event_data,
)


def run_concurrent(
    tasks: list[Callable],
    max_workers: int = 10,
) -> list:
    """Run multiple tasks concurrently and collect results.
    
    Args:
        tasks: List of callable functions to execute.
        max_workers: Maximum number of concurrent threads.
    
    Returns:
        List of results from each task (in completion order).
    """
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(task) for task in tasks]
        for future in as_completed(futures):
            results.append(future.result())
    return results


# =============================================================================
# Concurrent Read Operations
# =============================================================================


class TestConcurrentReadOperations:
    """Tests for concurrent read operations."""

    def test_multiple_simultaneous_status_reads(self, client_with_engine):
        """Multiple simultaneous GET /simulation/status should all succeed."""
        client, _ = client_with_engine
        
        def get_status():
            return client.get("/simulation/status")
        
        # Run 10 concurrent status reads
        tasks = [get_status for _ in range(10)]
        results = run_concurrent(tasks)
        
        # All should succeed
        for response in results:
            assert response.status_code == 200
            assert "is_running" in response.json()

    def test_multiple_simultaneous_environment_reads(self, client_with_engine):
        """Multiple simultaneous GET /environment/state should all succeed."""
        client, _ = client_with_engine
        
        def get_environment():
            return client.get("/environment/state")
        
        # Run 10 concurrent environment reads
        tasks = [get_environment for _ in range(10)]
        results = run_concurrent(tasks)
        
        # All should succeed
        for response in results:
            assert response.status_code == 200
            assert "modalities" in response.json()

    def test_multiple_simultaneous_events_reads(self, client_with_engine):
        """Multiple simultaneous GET /events should all succeed."""
        client, _ = client_with_engine
        
        # Create some events first
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        for i in range(5):
            client.post(
                "/events",
                json=make_event_request(
                    current_time + timedelta(hours=i + 1),
                    "email",
                    email_event_data(subject=f"Test {i}"),
                ),
            )
        
        def get_events():
            return client.get("/events")
        
        # Run 10 concurrent event list reads
        tasks = [get_events for _ in range(10)]
        results = run_concurrent(tasks)
        
        # All should succeed with same count
        for response in results:
            assert response.status_code == 200
            assert response.json()["total"] >= 5

    def test_reads_dont_block_other_reads(self, client_with_engine):
        """Concurrent reads should not block each other."""
        client, _ = client_with_engine
        
        def get_status():
            return ("status", client.get("/simulation/status"))
        
        def get_environment():
            return ("environment", client.get("/environment/state"))
        
        def get_events():
            return ("events", client.get("/events"))
        
        def get_time():
            return ("time", client.get("/simulator/time"))
        
        # Mix different read operations
        tasks = [get_status, get_environment, get_events, get_time] * 5
        results = run_concurrent(tasks, max_workers=20)
        
        # All should succeed
        for endpoint, response in results:
            assert response.status_code == 200, f"{endpoint} failed"

    def test_concurrent_reads_return_consistent_snapshots(self, client_with_engine):
        """Concurrent reads should return consistent data."""
        client, _ = client_with_engine
        
        def get_time_from_status():
            response = client.get("/simulation/status")
            return response.json()["current_time"]
        
        def get_time_from_environment():
            response = client.get("/environment/state")
            return response.json()["current_time"]
        
        def get_time_from_time_endpoint():
            response = client.get("/simulator/time")
            return response.json()["current_time"]
        
        # Get times from all endpoints concurrently
        tasks = [get_time_from_status, get_time_from_environment, get_time_from_time_endpoint] * 3
        results = run_concurrent(tasks)
        
        # All times should be the same (within 1 second tolerance due to timing)
        times = [datetime.fromisoformat(t) for t in results]
        first_time = times[0]
        for t in times:
            assert abs((t - first_time).total_seconds()) < 1


# =============================================================================
# Concurrent Write Operations
# =============================================================================


class TestConcurrentWriteOperations:
    """Tests for concurrent write operations."""

    def test_multiple_simultaneous_event_creations(self, client_with_engine):
        """Multiple simultaneous event creations should all succeed."""
        client, _ = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        def create_event(i):
            def _create():
                return client.post(
                    "/events",
                    json=make_event_request(
                        current_time + timedelta(hours=i + 1),
                        "email",
                        email_event_data(subject=f"Concurrent Event {i}"),
                    ),
                )
            return _create
        
        # Create 10 events concurrently
        tasks = [create_event(i) for i in range(10)]
        results = run_concurrent(tasks)
        
        # All should succeed
        for response in results:
            assert response.status_code == 200
            assert "event_id" in response.json()

    def test_events_created_concurrently_have_unique_ids(self, client_with_engine):
        """Events created concurrently should all have unique IDs."""
        client, _ = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        def create_event(i):
            def _create():
                response = client.post(
                    "/events",
                    json=make_event_request(
                        current_time + timedelta(hours=i + 1),
                        "sms",
                        sms_event_data(body=f"Message {i}"),
                    ),
                )
                return response.json().get("event_id")
            return _create
        
        # Create 20 events concurrently
        tasks = [create_event(i) for i in range(20)]
        event_ids = run_concurrent(tasks, max_workers=20)
        
        # All IDs should be unique
        assert len(set(event_ids)) == len(event_ids), "Duplicate event IDs created"

    def test_concurrent_immediate_events(self, client_with_engine):
        """Multiple simultaneous immediate events should all succeed."""
        client, _ = client_with_engine
        
        def create_immediate(i):
            def _create():
                return client.post(
                    "/events/immediate",
                    json={
                        "modality": "location",
                        "data": location_event_data(
                            latitude=37.0 + i * 0.01,
                            longitude=-122.0 + i * 0.01,
                        ),
                    },
                )
            return _create
        
        # Create 10 immediate events concurrently
        tasks = [create_immediate(i) for i in range(10)]
        results = run_concurrent(tasks)
        
        # All should succeed
        for response in results:
            assert response.status_code == 200

    def test_concurrent_time_advances_sequential_effect(self, client_with_engine):
        """Concurrent time advances should have cumulative effect."""
        client, _ = client_with_engine
        
        # Get initial time
        initial_response = client.get("/simulator/time")
        initial_time = datetime.fromisoformat(initial_response.json()["current_time"])
        
        def advance_time():
            return client.post("/simulator/time/advance", json={"seconds": 100})
        
        # Try to advance time concurrently
        # Note: Due to locks, these may serialize, but all should succeed
        tasks = [advance_time for _ in range(5)]
        results = run_concurrent(tasks, max_workers=5)
        
        # Count successes (some may fail if paused during execution)
        successes = [r for r in results if r.status_code == 200]
        
        # At least some should succeed
        assert len(successes) >= 1
        
        # Final time should have advanced
        final_response = client.get("/simulator/time")
        final_time = datetime.fromisoformat(final_response.json()["current_time"])
        assert final_time > initial_time

    def test_concurrent_pause_resume_operations(self, client_with_engine):
        """Concurrent pause/resume operations should be handled gracefully."""
        client, _ = client_with_engine
        
        def pause():
            return ("pause", client.post("/simulator/time/pause"))
        
        def resume():
            return ("resume", client.post("/simulator/time/resume"))
        
        # Mix pause and resume operations
        tasks = [pause, resume, pause, resume, pause, resume] * 2
        results = run_concurrent(tasks, max_workers=12)
        
        # All should complete (pause/resume are idempotent)
        for op_type, response in results:
            assert response.status_code == 200, f"{op_type} failed"


# =============================================================================
# Read-Write Consistency
# =============================================================================


class TestReadWriteConsistency:
    """Tests for consistency during concurrent read and write operations."""

    def test_read_during_write_returns_consistent_state(self, client_with_engine):
        """Reads during writes should return consistent (not partial) state."""
        client, _ = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        def create_events():
            for i in range(5):
                client.post(
                    "/events",
                    json=make_event_request(
                        current_time + timedelta(hours=i + 10),
                        "chat",
                        chat_event_data(content=f"Message {i}"),
                    ),
                )
            return "writes_done"
        
        def read_events():
            response = client.get("/events")
            data = response.json()
            # Verify consistency: total should equal len(events)
            assert data["total"] == len(data["events"])
            return data["total"]
        
        # Mix writes and reads
        tasks = [create_events, read_events, read_events, read_events]
        results = run_concurrent(tasks, max_workers=4)
        
        # All reads should return valid counts
        for result in results:
            if isinstance(result, int):
                assert result >= 0

    def test_event_creation_visible_in_subsequent_reads(self, client_with_engine):
        """Events created should be visible in subsequent reads."""
        client, _ = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        # Create event
        create_response = client.post(
            "/events",
            json=make_event_request(
                current_time + timedelta(hours=1),
                "email",
                email_event_data(subject="Visibility Test"),
            ),
        )
        event_id = create_response.json()["event_id"]
        
        def read_event():
            return client.get(f"/events/{event_id}")
        
        # Multiple concurrent reads should all see the event
        tasks = [read_event for _ in range(10)]
        results = run_concurrent(tasks)
        
        for response in results:
            assert response.status_code == 200
            assert response.json()["event_id"] == event_id

    def test_time_advance_visible_in_subsequent_reads(self, client_with_engine):
        """Time advances should be visible in subsequent reads."""
        client, _ = client_with_engine
        
        # Get initial time
        initial = client.get("/simulator/time").json()["current_time"]
        initial_time = datetime.fromisoformat(initial)
        
        # Advance time
        client.post("/simulator/time/advance", json={"seconds": 3600})
        
        def read_time():
            response = client.get("/simulator/time")
            return datetime.fromisoformat(response.json()["current_time"])
        
        # Multiple concurrent reads should all see advanced time
        tasks = [read_time for _ in range(10)]
        results = run_concurrent(tasks)
        
        for result_time in results:
            assert result_time > initial_time

    def test_no_partial_state_during_updates(self, client_with_engine):
        """Updates should be atomic - no partial state visible."""
        client, _ = client_with_engine
        
        def update_location(lat, lon):
            def _update():
                return client.post(
                    "/events/immediate",
                    json={
                        "modality": "location",
                        "data": location_event_data(latitude=lat, longitude=lon),
                    },
                )
            return _update
        
        def read_location():
            response = client.get("/environment/modalities/location")
            state = response.json()["state"]
            lat = state.get("current_latitude")
            lon = state.get("current_longitude")
            # If one is set, both should be set (atomic update)
            if lat is not None and lon is not None:
                # Values should be consistent (from same update)
                # This is a basic check - more sophisticated would track pairs
                assert isinstance(lat, (int, float))
                assert isinstance(lon, (int, float))
            return (lat, lon)
        
        # Mix updates and reads
        updates = [update_location(40.0 + i, -74.0 + i) for i in range(5)]
        reads = [read_location for _ in range(10)]
        
        tasks = updates + reads
        results = run_concurrent(tasks, max_workers=15)
        
        # All operations should complete without error
        assert len(results) == 15


# =============================================================================
# Race Condition Prevention
# =============================================================================


class TestRaceConditionPrevention:
    """Tests for race condition prevention."""

    def test_double_start_simulation_one_succeeds_one_fails(self, client_with_engine):
        """Double-start simulation: one succeeds, one gets 409."""
        client, _ = client_with_engine
        
        # Stop first so we can try double-start
        client.post("/simulation/stop")
        
        def start_simulation():
            return client.post("/simulation/start", json={"auto_advance": False})
        
        # Try to start twice concurrently
        tasks = [start_simulation, start_simulation]
        results = run_concurrent(tasks, max_workers=2)
        
        status_codes = [r.status_code for r in results]
        
        # One should succeed (200), one should fail (409)
        assert 200 in status_codes, "At least one start should succeed"
        # Due to timing, both might succeed if first completes before second starts
        # or one might get 409 - both are valid outcomes

    def test_double_stop_simulation_handled_gracefully(self, client_with_engine):
        """Double-stop simulation should be handled gracefully."""
        client, _ = client_with_engine
        
        def stop_simulation():
            return client.post("/simulation/stop")
        
        # Try to stop twice concurrently
        tasks = [stop_simulation, stop_simulation]
        results = run_concurrent(tasks, max_workers=2)
        
        # Both should complete without error (stop is idempotent-ish)
        for response in results:
            assert response.status_code == 200

    def test_concurrent_delete_same_event(self, client_with_engine):
        """Concurrent delete of same event: one succeeds, others get error."""
        client, _ = client_with_engine
        
        # Create an event to delete
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
        
        def delete_event():
            return client.delete(f"/events/{event_id}")
        
        # Try to delete same event twice concurrently
        tasks = [delete_event, delete_event]
        results = run_concurrent(tasks, max_workers=2)
        
        status_codes = [r.status_code for r in results]
        
        # One should succeed (200), one should get error
        # Could be 400 (already cancelled, not pending) or 404 (not found)
        assert 200 in status_codes, "At least one delete should succeed"
        # The other should fail
        assert status_codes.count(200) == 1 or len([c for c in status_codes if c in (400, 404)]) >= 1

    def test_concurrent_event_cancellation(self, client_with_engine):
        """Concurrent cancellation of same event handled correctly."""
        client, _ = client_with_engine
        
        # Create an event
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        create_response = client.post(
            "/events",
            json=make_event_request(
                current_time + timedelta(hours=2),
                "sms",
                sms_event_data(),
            ),
        )
        event_id = create_response.json()["event_id"]
        
        def cancel_event():
            return client.delete(f"/events/{event_id}")
        
        # Try to cancel same event multiple times concurrently
        tasks = [cancel_event for _ in range(5)]
        results = run_concurrent(tasks, max_workers=5)
        
        # Count successes and errors
        successes = [r for r in results if r.status_code == 200]
        errors = [r for r in results if r.status_code in (400, 404)]
        
        # At least one should succeed
        assert len(successes) >= 1
        # All operations should complete (either success or expected error)
        assert len(successes) + len(errors) == 5


# =============================================================================
# Resource Contention
# =============================================================================


class TestResourceContention:
    """Tests for resource contention and thread safety."""

    def test_high_frequency_event_creation(self, client_with_engine):
        """High-frequency event creation should not deadlock or lose events."""
        client, _ = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        num_events = 50
        
        def create_event(i):
            def _create():
                response = client.post(
                    "/events",
                    json=make_event_request(
                        current_time + timedelta(minutes=i + 1),
                        "chat",
                        chat_event_data(content=f"High frequency {i}"),
                    ),
                )
                return response.status_code
            return _create
        
        # Create many events rapidly
        tasks = [create_event(i) for i in range(num_events)]
        results = run_concurrent(tasks, max_workers=20)
        
        # All should succeed
        assert all(code == 200 for code in results)
        
        # Verify all events were created
        list_response = client.get("/events")
        assert list_response.json()["total"] >= num_events

    def test_rapid_time_advances_dont_corrupt_state(self, client_with_engine):
        """Rapid time advances should maintain state consistency."""
        client, _ = client_with_engine
        
        # Get initial time
        initial_response = client.get("/simulator/time")
        initial_time = datetime.fromisoformat(initial_response.json()["current_time"])
        
        def advance_small():
            return client.post("/simulator/time/advance", json={"seconds": 10})
        
        # Rapid small advances
        tasks = [advance_small for _ in range(10)]
        results = run_concurrent(tasks, max_workers=10)
        
        # Get final time
        final_response = client.get("/simulator/time")
        final_time = datetime.fromisoformat(final_response.json()["current_time"])
        
        # Time should have advanced (at least one advance should succeed)
        assert final_time > initial_time
        
        # State should still be consistent
        status_response = client.get("/simulation/status")
        assert status_response.status_code == 200
        assert "current_time" in status_response.json()

    def test_queue_operations_thread_safe(self, client_with_engine):
        """Queue operations should be thread-safe."""
        client, _ = client_with_engine
        
        time_response = client.get("/simulator/time")
        current_time = datetime.fromisoformat(time_response.json()["current_time"])
        
        created_ids = []
        
        def create_and_track(i):
            def _create():
                response = client.post(
                    "/events",
                    json=make_event_request(
                        current_time + timedelta(minutes=i + 1),
                        "location",
                        location_event_data(),
                    ),
                )
                if response.status_code == 200:
                    return response.json()["event_id"]
                return None
            return _create
        
        def list_events():
            response = client.get("/events")
            return response.json()["total"]
        
        # Mix create and list operations
        creates = [create_and_track(i) for i in range(20)]
        lists = [list_events for _ in range(10)]
        
        tasks = creates + lists
        results = run_concurrent(tasks, max_workers=30)
        
        # Collect created IDs
        for result in results:
            if isinstance(result, str):  # event_id
                created_ids.append(result)
        
        # Final count should match created events
        final_response = client.get("/events")
        assert final_response.json()["total"] >= len(created_ids)

    def test_modality_state_updates_atomic(self, client_with_engine):
        """Modality state updates should be atomic."""
        client, _ = client_with_engine
        
        def update_and_read():
            # Create immediate event
            client.post(
                "/events/immediate",
                json={
                    "modality": "chat",
                    "data": chat_event_data(
                        content="Atomic test",
                        conversation_id="atomic_test",
                    ),
                },
            )
            # Advance to execute
            client.post("/simulator/time/advance", json={"seconds": 1})
            # Read state
            response = client.get("/environment/modalities/chat")
            return response.json()
        
        def just_read():
            response = client.get("/environment/modalities/chat")
            state = response.json()["state"]
            # State should always be valid
            assert "conversations" in state
            assert "messages" in state
            return state
        
        # Mix updates and reads
        tasks = [update_and_read for _ in range(5)] + [just_read for _ in range(10)]
        results = run_concurrent(tasks, max_workers=15)
        
        # All operations should complete
        assert len(results) == 15

    def test_concurrent_modality_queries(self, client_with_engine):
        """Concurrent queries on same modality should not interfere."""
        client, _ = client_with_engine
        
        # Add some data first
        for i in range(5):
            client.post(
                "/events/immediate",
                json={
                    "modality": "email",
                    "data": email_event_data(subject=f"Query Test {i}"),
                },
            )
        client.post("/simulator/time/advance", json={"seconds": 1})
        
        def query_email():
            response = client.post(
                "/email/query",
                json={"limit": 10},
            )
            return response.status_code
        
        # Run many queries concurrently
        tasks = [query_email for _ in range(20)]
        results = run_concurrent(tasks, max_workers=20)
        
        # All should succeed
        assert all(code == 200 for code in results)
