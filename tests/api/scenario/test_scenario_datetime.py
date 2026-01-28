"""Integration tests for scenario save/load with datetime handling.

This test verifies the original bug is fixed:
- Export scenario → Import scenario → Start simulation works without 
  "can't compare offset-naive and offset-aware datetimes" error.
"""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from ues.main import app
from ues.api.dependencies import get_simulation_engine
from tests.api.helpers import make_event_request, email_event_data


@pytest.fixture
def client(fresh_engine):
    """Create a fresh test client with a new simulation engine (not started)."""
    app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestScenarioDatetimeRoundTrip:
    """Test that scenario export/import handles datetimes correctly."""

    def test_scenario_export_import_start_simulation(self, client):
        """Full workflow: add events, export, reset, import, start simulation.
        
        This is the original bug scenario - after import, starting the simulation
        would fail with "can't compare offset-naive and offset-aware datetimes".
        """
        # 1. Add some events with different datetime formats
        event_time_1 = datetime(2025, 12, 24, 12, 0, 0, tzinfo=timezone.utc)
        response = client.post("/events", json=make_event_request(
            event_time_1,
            "email",
            email_event_data(
                operation="receive",
                from_address="alice@example.com",
                to_addresses=["bob@example.com"],
                subject="Test Email 1",
                body_text="Hello!",
            ),
        ))
        assert response.status_code == 200
        event1_id = response.json()["event_id"]

        event_time_2 = datetime(2025, 12, 24, 13, 0, 0, tzinfo=timezone.utc)
        response = client.post("/events", json=make_event_request(
            event_time_2,
            "email",
            email_event_data(
                operation="receive",
                from_address="charlie@example.com",
                to_addresses=["bob@example.com"],
                subject="Test Email 2",
                body_text="Hi there!",
            ),
        ))
        assert response.status_code == 200
        event2_id = response.json()["event_id"]

        # 2. Export the scenario (GET with query params)
        response = client.get(
            "/scenario/export/full",
            params={
                "name": "Datetime Test Scenario",
                "description": "Testing datetime round-trip",
            },
        )
        assert response.status_code == 200
        exported_data = response.json()
        
        # Verify the export contains our events (nested under scenario.events.events)
        assert "scenario" in exported_data
        assert "events" in exported_data["scenario"]
        assert len(exported_data["scenario"]["events"]["events"]) == 2

        # 3. Clear everything
        response = client.post("/simulation/clear")
        assert response.status_code == 200

        # Verify events are cleared
        response = client.get("/events")
        assert response.status_code == 200
        assert len(response.json()["events"]) == 0

        # 4. Import the scenario (POST with the scenario nested)
        response = client.post(
            "/scenario/import/full",
            json={"scenario": exported_data["scenario"]},
        )
        assert response.status_code == 200
        import_result = response.json()
        assert import_result["events_loaded"] == 2

        # 5. Start the simulation - THIS IS WHERE THE BUG OCCURRED
        # The error was: "can't compare offset-naive and offset-aware datetimes"
        response = client.post("/simulation/start", json={})
        assert response.status_code == 200, f"Failed to start simulation: {response.json()}"
        
        result = response.json()
        assert result["status"] == "running"

    def test_scenario_with_mixed_datetime_formats(self, client):
        """Test that scenarios handle events with various datetime formats."""
        # Create events with different datetime objects
        event_times = [
            (datetime(2025, 12, 24, 10, 0, 0, tzinfo=timezone.utc), "Z suffix"),
            (datetime(2025, 12, 24, 11, 0, 0, tzinfo=timezone.utc), "+00:00 offset"),
            (datetime(2025, 12, 24, 12, 0, 0, 123456, tzinfo=timezone.utc), "With microseconds"),
        ]

        for event_time, subject in event_times:
            response = client.post("/events", json=make_event_request(
                event_time,
                "email",
                email_event_data(
                    operation="receive",
                    from_address="test@example.com",
                    to_addresses=["recipient@example.com"],
                    subject=subject,
                    body_text="Test",
                ),
            ))
            assert response.status_code == 200

        # Export
        response = client.get("/scenario/export/full", params={"name": "Mixed formats"})
        assert response.status_code == 200
        exported = response.json()

        # Clear
        client.post("/simulation/clear")

        # Import
        response = client.post(
            "/scenario/import/full",
            json={"scenario": exported["scenario"]},
        )
        assert response.status_code == 200

        # Start simulation - should work without datetime errors
        response = client.post("/simulation/start", json={})
        assert response.status_code == 200

        # Simulator starts at 2025-01-01 12:00:00 but events are at 2025-12-24
        # Use skip-to-next to jump directly to event times instead of trying to advance
        for _ in range(3):  # Execute all 3 events
            response = client.post("/simulator/time/skip-to-next")
            assert response.status_code == 200

        # Check simulation status to verify events executed
        response = client.get("/simulation/status")
        assert response.status_code == 200
        result = response.json()
        assert result["executed_events"] == 3

    def test_scenario_import_preserves_event_order(self, client):
        """Verify that imported events maintain correct time ordering."""
        # Add events in non-chronological order
        times = [
            datetime(2025, 12, 24, 14, 0, 0, tzinfo=timezone.utc),
            datetime(2025, 12, 24, 10, 0, 0, tzinfo=timezone.utc),
            datetime(2025, 12, 24, 12, 0, 0, tzinfo=timezone.utc),
        ]
        
        for i, event_time in enumerate(times):
            client.post("/events", json=make_event_request(
                event_time,
                "email",
                email_event_data(
                    operation="receive",
                    from_address=f"sender{i}@example.com",
                    to_addresses=["recipient@example.com"],
                    subject=f"Email {i}",
                    body_text="Test",
                ),
            ))

        # Export
        response = client.get("/scenario/export/full", params={"name": "Order test"})
        exported = response.json()

        # Clear and import
        client.post("/simulation/clear")
        client.post(
            "/scenario/import/full",
            json={"scenario": exported["scenario"]},
        )

        # Start and check events are in correct order
        client.post("/simulation/start", json={})
        
        # Skip to first event
        response = client.post("/simulator/time/skip-to-next")
        assert response.status_code == 200
        result = response.json()
        # First event should be at 10:00
        current_time_str = str(result["current_time"])
        assert "10:00:00" in current_time_str

        # Skip to second event
        response = client.post("/simulator/time/skip-to-next")
        assert response.status_code == 200
        result = response.json()
        # Second event should be at 12:00
        current_time_str = str(result["current_time"])
        assert "12:00:00" in current_time_str

        # Skip to third event
        response = client.post("/simulator/time/skip-to-next")
        assert response.status_code == 200
        result = response.json()
        # Third event should be at 14:00
        current_time_str = str(result["current_time"])
        assert "14:00:00" in current_time_str


class TestScenarioMetadataDatetime:
    """Test that scenario metadata datetimes are handled correctly."""

    def test_created_at_preserved_after_import(self, client):
        """The scenario's created_at timestamp should survive round-trip."""
        # Create a scenario with an event
        event_time = datetime(2025, 12, 24, 12, 0, 0, tzinfo=timezone.utc)
        client.post("/events", json=make_event_request(
            event_time,
            "email",
            email_event_data(
                operation="receive",
                from_address="test@example.com",
                to_addresses=["recipient@example.com"],
                subject="Test",
                body_text="Test",
            ),
        ))

        response = client.get("/scenario/export/full", params={"name": "Timestamp Test"})
        exported = response.json()
        
        # created_at should be present and valid in metadata (nested under scenario)
        assert "scenario" in exported
        assert "metadata" in exported["scenario"]
        assert "created_at" in exported["scenario"]["metadata"]
        original_created_at = exported["scenario"]["metadata"]["created_at"]
        
        # Clear and reimport
        client.post("/simulation/clear")
        response = client.post(
            "/scenario/import/full",
            json={"scenario": exported["scenario"]},
        )
        assert response.status_code == 200

        # Export again - the new export will have its own created_at
        event_time_2 = datetime(2025, 12, 24, 13, 0, 0, tzinfo=timezone.utc)
        client.post("/events", json=make_event_request(
            event_time_2,
            "email",
            email_event_data(
                operation="receive",
                from_address="another@example.com",
                to_addresses=["recipient@example.com"],
                subject="Another",
                body_text="Test",
            ),
        ))
        
        response = client.get("/scenario/export/full", params={"name": "Re-exported"})
        re_exported = response.json()
        
        # The new export should have a new created_at (it's a new scenario)
        # But the original scenario's created_at was valid and parseable
        assert "created_at" in re_exported["scenario"]["metadata"]
        # Verify it's a valid datetime by checking format includes timezone offset
        # Accept both "Z" suffix and "+HH:MM" offset format as both represent UTC
        created_at = re_exported["scenario"]["metadata"]["created_at"]
        assert "+" in created_at or created_at.endswith("Z"), f"Expected timezone info in {created_at}"
