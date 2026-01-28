"""Integration tests for scenario export/import API endpoints.

These tests verify that the scenario save/load API endpoints:
- Export environment, events, and full scenarios correctly
- Import environment, events, and full scenarios correctly
- Handle error conditions (running simulation, invalid data, etc.)
- Properly integrate with SimulationEngine methods
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from ues.api.auth import initialize_api_key_registry, shutdown_api_key_registry
from ues.api.dependencies import get_simulation_engine
from ues.main import app
from ues.models.event import EventStatus, SimulatorEvent
from tests.fixtures.core.events import create_simulator_event
from tests.fixtures.modalities.email import create_email_input


# ============ Fixtures ============


@pytest.fixture
def client_without_start(fresh_engine):
    """Provide a TestClient with a fresh SimulationEngine that is NOT started.
    
    Scenario import requires the simulation to be stopped, so this fixture
    does NOT start the simulation.
    
    Yields:
        A tuple of (TestClient, SimulationEngine) for testing.
    """
    app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
    admin_secret, _ = initialize_api_key_registry()
    client = TestClient(app)
    client.headers["X-API-Key"] = admin_secret
    
    yield client, fresh_engine
    
    # Cleanup: Stop simulation if running and clear dependency overrides
    try:
        if fresh_engine.is_running:
            client.post("/simulation/stop")
    except Exception:
        pass
    
    shutdown_api_key_registry()
    app.dependency_overrides.clear()


@pytest.fixture
def client_with_stopped_simulation(fresh_engine):
    """Provide a TestClient with simulation explicitly stopped.
    
    Yields:
        A tuple of (TestClient, SimulationEngine) for testing.
    """
    app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
    admin_secret, _ = initialize_api_key_registry()
    client = TestClient(app)
    client.headers["X-API-Key"] = admin_secret
    
    # Ensure engine is not running
    assert not fresh_engine.is_running
    
    yield client, fresh_engine
    
    shutdown_api_key_registry()
    app.dependency_overrides.clear()


@pytest.fixture
def client_with_running_simulation(fresh_engine):
    """Provide a TestClient with simulation explicitly started.
    
    This is used to test error cases where import should fail.
    
    Yields:
        A tuple of (TestClient, SimulationEngine) for testing.
    """
    app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
    admin_secret, _ = initialize_api_key_registry()
    client = TestClient(app)
    client.headers["X-API-Key"] = admin_secret
    
    # Start simulation
    response = client.post("/simulation/start", json={"auto_advance": False})
    assert response.status_code == 200
    
    yield client, fresh_engine
    
    # Cleanup
    try:
        client.post("/simulation/stop")
    except Exception:
        pass
    
    shutdown_api_key_registry()
    app.dependency_overrides.clear()


# ============ Export Environment Tests ============


class TestExportEnvironment:
    """Tests for GET /scenario/export/environment endpoint."""

    def test_export_environment_returns_200(self, client_with_stopped_simulation):
        """Test that export environment returns a successful response."""
        client, engine = client_with_stopped_simulation
        
        response = client.get("/scenario/export/environment")
        
        assert response.status_code == 200

    def test_export_environment_includes_time_state(self, client_with_stopped_simulation):
        """Test that exported environment includes time_state."""
        client, engine = client_with_stopped_simulation
        
        response = client.get("/scenario/export/environment")
        data = response.json()
        
        assert "environment" in data
        assert "time_state" in data["environment"]
        assert "current_time" in data["environment"]["time_state"]

    def test_export_environment_includes_modality_states(self, client_with_stopped_simulation):
        """Test that exported environment includes modality_states."""
        client, engine = client_with_stopped_simulation
        
        response = client.get("/scenario/export/environment")
        data = response.json()
        
        assert "modality_states" in data["environment"]
        # Check that we have some modalities
        assert len(data["environment"]["modality_states"]) > 0

    def test_export_environment_includes_modalities_exported_list(
        self, client_with_stopped_simulation
    ):
        """Test that response includes list of exported modalities."""
        client, engine = client_with_stopped_simulation
        
        response = client.get("/scenario/export/environment")
        data = response.json()
        
        assert "modalities_exported" in data
        assert isinstance(data["modalities_exported"], list)
        # Should match keys in modality_states
        assert set(data["modalities_exported"]) == set(
            data["environment"]["modality_states"].keys()
        )

    def test_export_environment_modalities_match_engine_state(
        self, client_with_stopped_simulation
    ):
        """Test that exported modalities match what's in the engine."""
        client, engine = client_with_stopped_simulation
        
        response = client.get("/scenario/export/environment")
        data = response.json()
        
        # Check that all engine modalities are exported
        engine_modalities = set(engine.environment.modality_states.keys())
        exported_modalities = set(data["modalities_exported"])
        
        assert engine_modalities == exported_modalities


# ============ Export Events Tests ============


class TestExportEvents:
    """Tests for GET /scenario/export/events endpoint."""

    def test_export_events_returns_200(self, client_with_stopped_simulation):
        """Test that export events returns a successful response."""
        client, engine = client_with_stopped_simulation
        
        response = client.get("/scenario/export/events")
        
        assert response.status_code == 200

    def test_export_events_includes_events_list(self, client_with_stopped_simulation):
        """Test that exported data includes events list."""
        client, engine = client_with_stopped_simulation
        
        response = client.get("/scenario/export/events")
        data = response.json()
        
        assert "events" in data
        assert "events" in data["events"]
        assert isinstance(data["events"]["events"], list)

    def test_export_events_includes_counts(self, client_with_stopped_simulation):
        """Test that response includes event counts."""
        client, engine = client_with_stopped_simulation
        
        response = client.get("/scenario/export/events")
        data = response.json()
        
        assert "total_events" in data
        assert "pending_events" in data
        assert "executed_events" in data

    def test_export_events_empty_queue(self, client_with_stopped_simulation):
        """Test export with empty event queue."""
        client, engine = client_with_stopped_simulation
        
        response = client.get("/scenario/export/events")
        data = response.json()
        
        assert data["total_events"] == 0
        assert data["pending_events"] == 0
        assert data["executed_events"] == 0
        assert data["events"]["events"] == []

    def test_export_events_with_pending_events(self, client_with_stopped_simulation):
        """Test export with pending events in queue."""
        client, engine = client_with_stopped_simulation
        
        # Add a pending event
        future_time = engine.environment.time_state.current_time + timedelta(hours=1)
        event = create_simulator_event(
            scheduled_time=future_time,
            data=create_email_input(
                timestamp=future_time,
                subject="Test Email",
                body_text="Test body",
            ),
        )
        engine.event_queue.add_event(event)
        
        response = client.get("/scenario/export/events")
        data = response.json()
        
        assert data["total_events"] == 1
        assert data["pending_events"] == 1
        assert data["executed_events"] == 0
        assert len(data["events"]["events"]) == 1


# ============ Export Full Scenario Tests ============


class TestExportFullScenario:
    """Tests for GET /scenario/export/full endpoint."""

    def test_export_full_scenario_returns_200(self, client_with_stopped_simulation):
        """Test that export full scenario returns a successful response."""
        client, engine = client_with_stopped_simulation
        
        response = client.get("/scenario/export/full")
        
        assert response.status_code == 200

    def test_export_full_scenario_includes_metadata(self, client_with_stopped_simulation):
        """Test that exported scenario includes metadata."""
        client, engine = client_with_stopped_simulation
        
        response = client.get("/scenario/export/full")
        data = response.json()
        
        assert "scenario" in data
        assert "metadata" in data["scenario"]
        assert "ues_version" in data["scenario"]["metadata"]
        assert "scenario_version" in data["scenario"]["metadata"]
        assert "created_at" in data["scenario"]["metadata"]

    def test_export_full_scenario_includes_environment(self, client_with_stopped_simulation):
        """Test that exported scenario includes environment."""
        client, engine = client_with_stopped_simulation
        
        response = client.get("/scenario/export/full")
        data = response.json()
        
        assert "environment" in data["scenario"]
        assert "time_state" in data["scenario"]["environment"]
        assert "modality_states" in data["scenario"]["environment"]

    def test_export_full_scenario_includes_events(self, client_with_stopped_simulation):
        """Test that exported scenario includes events."""
        client, engine = client_with_stopped_simulation
        
        response = client.get("/scenario/export/full")
        data = response.json()
        
        assert "events" in data["scenario"]
        assert "events" in data["scenario"]["events"]

    def test_export_full_scenario_with_author(self, client_with_stopped_simulation):
        """Test export with author parameter."""
        client, engine = client_with_stopped_simulation
        
        response = client.get("/scenario/export/full", params={"author": "Test Author"})
        data = response.json()
        
        assert data["scenario"]["metadata"]["author"] == "Test Author"

    def test_export_full_scenario_with_description(self, client_with_stopped_simulation):
        """Test export with description parameter."""
        client, engine = client_with_stopped_simulation
        
        response = client.get(
            "/scenario/export/full",
            params={"description": "Test description for scenario"},
        )
        data = response.json()
        
        assert data["scenario"]["metadata"]["description"] == "Test description for scenario"

    def test_export_full_scenario_with_author_and_description(
        self, client_with_stopped_simulation
    ):
        """Test export with both author and description."""
        client, engine = client_with_stopped_simulation
        
        response = client.get(
            "/scenario/export/full",
            params={"author": "Developer", "description": "Regression test scenario"},
        )
        data = response.json()
        
        assert data["scenario"]["metadata"]["author"] == "Developer"
        assert data["scenario"]["metadata"]["description"] == "Regression test scenario"


# ============ Import Environment Tests ============


class TestImportEnvironment:
    """Tests for POST /scenario/import/environment endpoint."""

    def test_import_environment_returns_200(self, client_with_stopped_simulation):
        """Test that import environment returns a successful response."""
        client, engine = client_with_stopped_simulation
        
        # First export the environment
        export_response = client.get("/scenario/export/environment")
        exported_data = export_response.json()
        
        # Then import it back
        response = client.post(
            "/scenario/import/environment",
            json={"data": exported_data["environment"]},
        )
        
        assert response.status_code == 200

    def test_import_environment_success_fields(self, client_with_stopped_simulation):
        """Test that import response includes expected fields."""
        client, engine = client_with_stopped_simulation
        
        export_response = client.get("/scenario/export/environment")
        exported_data = export_response.json()
        
        response = client.post(
            "/scenario/import/environment",
            json={"data": exported_data["environment"]},
        )
        data = response.json()
        
        assert data["success"] is True
        assert "modalities_loaded" in data
        assert "modalities_skipped" in data
        assert "warnings" in data
        assert "historic_events_count" in data
        assert "historic_events_action" in data

    def test_import_environment_fails_when_running(self, client_with_running_simulation):
        """Test that import fails with 409 when simulation is running."""
        client, engine = client_with_running_simulation
        
        # Export while stopped (need to stop first)
        client.post("/simulation/stop")
        export_response = client.get("/scenario/export/environment")
        exported_data = export_response.json()
        
        # Start again
        client.post("/simulation/start", json={})
        
        # Try to import - should fail
        response = client.post(
            "/scenario/import/environment",
            json={"data": exported_data["environment"]},
        )
        
        assert response.status_code == 409
        assert "running" in response.json()["detail"].lower()

    def test_import_environment_historic_event_handling_ignore(
        self, client_with_stopped_simulation
    ):
        """Test import with historic_event_handling='ignore'."""
        client, engine = client_with_stopped_simulation
        
        # Add an event before current time (will become historic after import)
        past_time = engine.environment.time_state.current_time - timedelta(hours=1)
        event = create_simulator_event(
            scheduled_time=past_time,
            data=create_email_input(
                timestamp=past_time,
                subject="Old Email",
            ),
        )
        engine.event_queue.add_event(event)
        
        # Export and import with time in future (making original event historic)
        export_response = client.get("/scenario/export/environment")
        exported_data = export_response.json()
        
        response = client.post(
            "/scenario/import/environment",
            json={
                "data": exported_data["environment"],
                "historic_event_handling": "ignore",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["historic_events_action"] == "ignore"

    def test_import_environment_historic_event_handling_delete(
        self, client_with_stopped_simulation
    ):
        """Test import with historic_event_handling='delete'."""
        client, engine = client_with_stopped_simulation
        
        # Add events that will become historic
        past_time = engine.environment.time_state.current_time - timedelta(hours=1)
        event = create_simulator_event(
            scheduled_time=past_time,
            data=create_email_input(
                timestamp=past_time,
                subject="Old Email",
            ),
        )
        engine.event_queue.add_event(event)
        
        # Export environment
        export_response = client.get("/scenario/export/environment")
        exported_data = export_response.json()
        
        initial_event_count = len(engine.event_queue.events)
        
        response = client.post(
            "/scenario/import/environment",
            json={
                "data": exported_data["environment"],
                "historic_event_handling": "delete",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["historic_events_action"] == "delete"

    def test_import_environment_invalid_historic_event_handling(
        self, client_with_stopped_simulation
    ):
        """Test import with invalid historic_event_handling value returns 422."""
        client, engine = client_with_stopped_simulation
        
        export_response = client.get("/scenario/export/environment")
        exported_data = export_response.json()
        
        response = client.post(
            "/scenario/import/environment",
            json={
                "data": exported_data["environment"],
                "historic_event_handling": "invalid_value",
            },
        )
        
        assert response.status_code == 422  # Validation error


# ============ Import Events Tests ============


class TestImportEvents:
    """Tests for POST /scenario/import/events endpoint."""

    def test_import_events_returns_200(self, client_with_stopped_simulation):
        """Test that import events returns a successful response."""
        client, engine = client_with_stopped_simulation
        
        export_response = client.get("/scenario/export/events")
        exported_data = export_response.json()
        
        response = client.post(
            "/scenario/import/events",
            json={"data": exported_data["events"]},
        )
        
        assert response.status_code == 200

    def test_import_events_success_fields(self, client_with_stopped_simulation):
        """Test that import response includes expected fields."""
        client, engine = client_with_stopped_simulation
        
        export_response = client.get("/scenario/export/events")
        exported_data = export_response.json()
        
        response = client.post(
            "/scenario/import/events",
            json={"data": exported_data["events"]},
        )
        data = response.json()
        
        assert data["success"] is True
        assert "events_loaded" in data
        assert "events_merged" in data
        assert "previous_events" in data
        assert "historic_events_warning" in data
        assert "historic_event_count" in data

    def test_import_events_fails_when_running(self, client_with_running_simulation):
        """Test that import fails with 409 when simulation is running."""
        client, engine = client_with_running_simulation
        
        # Export while stopped
        client.post("/simulation/stop")
        export_response = client.get("/scenario/export/events")
        exported_data = export_response.json()
        
        # Start again
        client.post("/simulation/start", json={})
        
        response = client.post(
            "/scenario/import/events",
            json={"data": exported_data["events"]},
        )
        
        assert response.status_code == 409

    def test_import_events_replace_mode(self, client_with_stopped_simulation):
        """Test import with merge=False replaces all events."""
        client, engine = client_with_stopped_simulation
        
        # Add some events
        future_time = engine.environment.time_state.current_time + timedelta(hours=1)
        event = create_simulator_event(
            scheduled_time=future_time,
            data=create_email_input(
                timestamp=future_time,
                subject="Original Email",
            ),
        )
        engine.event_queue.add_event(event)
        
        # Import empty event queue with merge=False (replace)
        response = client.post(
            "/scenario/import/events",
            json={"data": {"events": []}, "merge": False},
        )
        data = response.json()
        
        assert response.status_code == 200
        assert data["previous_events"] == 1
        assert data["events_loaded"] == 0
        # After replace with empty, queue should be empty
        assert len(engine.event_queue.events) == 0

    def test_import_events_merge_mode(self, client_with_stopped_simulation):
        """Test import with merge=True adds events to existing queue."""
        client, engine = client_with_stopped_simulation
        
        # Add an event
        future_time = engine.environment.time_state.current_time + timedelta(hours=1)
        event = create_simulator_event(
            scheduled_time=future_time,
            data=create_email_input(
                timestamp=future_time,
                subject="Original Email",
            ),
        )
        engine.event_queue.add_event(event)
        initial_count = len(engine.event_queue.events)
        
        # Export current events
        export_response = client.get("/scenario/export/events")
        exported_data = export_response.json()
        
        # Import with merge=True
        response = client.post(
            "/scenario/import/events",
            json={"data": exported_data["events"], "merge": True},
        )
        data = response.json()
        
        assert response.status_code == 200
        assert data["previous_events"] == initial_count
        # Merge adds events (with new IDs)
        assert data["events_merged"] > 0


# ============ Import Full Scenario Tests ============


class TestImportFullScenario:
    """Tests for POST /scenario/import/full endpoint."""

    def test_import_full_scenario_returns_200(self, client_with_stopped_simulation):
        """Test that import full scenario returns a successful response."""
        client, engine = client_with_stopped_simulation
        
        export_response = client.get("/scenario/export/full")
        exported_data = export_response.json()
        
        response = client.post(
            "/scenario/import/full",
            json={"scenario": exported_data["scenario"]},
        )
        
        assert response.status_code == 200

    def test_import_full_scenario_success_fields(self, client_with_stopped_simulation):
        """Test that import response includes expected fields."""
        client, engine = client_with_stopped_simulation
        
        export_response = client.get("/scenario/export/full")
        exported_data = export_response.json()
        
        response = client.post(
            "/scenario/import/full",
            json={"scenario": exported_data["scenario"]},
        )
        data = response.json()
        
        assert data["success"] is True
        assert "environment_loaded" in data
        assert "events_loaded" in data
        assert "modalities_loaded" in data
        assert "modalities_skipped" in data
        assert "warnings" in data
        assert "scenario_metadata" in data

    def test_import_full_scenario_fails_when_running(self, client_with_running_simulation):
        """Test that import fails with 409 when simulation is running."""
        client, engine = client_with_running_simulation
        
        client.post("/simulation/stop")
        export_response = client.get("/scenario/export/full")
        exported_data = export_response.json()
        
        client.post("/simulation/start", json={})
        
        response = client.post(
            "/scenario/import/full",
            json={"scenario": exported_data["scenario"]},
        )
        
        assert response.status_code == 409

    def test_import_full_scenario_metadata_returned(self, client_with_stopped_simulation):
        """Test that imported scenario metadata is returned in response."""
        client, engine = client_with_stopped_simulation
        
        export_response = client.get(
            "/scenario/export/full",
            params={"author": "Test Author", "description": "Test Description"},
        )
        exported_data = export_response.json()
        
        response = client.post(
            "/scenario/import/full",
            json={"scenario": exported_data["scenario"]},
        )
        data = response.json()
        
        assert data["scenario_metadata"]["author"] == "Test Author"
        assert data["scenario_metadata"]["description"] == "Test Description"

    def test_import_full_scenario_strict_modalities_false(
        self, client_with_stopped_simulation
    ):
        """Test import with strict_modalities=False (default)."""
        client, engine = client_with_stopped_simulation
        
        export_response = client.get("/scenario/export/full")
        exported_data = export_response.json()
        
        response = client.post(
            "/scenario/import/full",
            json={"scenario": exported_data["scenario"], "strict_modalities": False},
        )
        
        assert response.status_code == 200


# ============ Round-Trip Tests ============


class TestScenarioRoundTrip:
    """Tests verifying export -> import -> export produces consistent data."""

    def test_environment_round_trip(self, client_with_stopped_simulation):
        """Test that environment data survives export/import/export cycle."""
        client, engine = client_with_stopped_simulation
        
        # First export
        first_export = client.get("/scenario/export/environment")
        first_data = first_export.json()
        
        # Import
        client.post(
            "/scenario/import/environment",
            json={"data": first_data["environment"]},
        )
        
        # Second export
        second_export = client.get("/scenario/export/environment")
        second_data = second_export.json()
        
        # Compare key structural elements (not timestamps which might differ)
        assert set(first_data["modalities_exported"]) == set(
            second_data["modalities_exported"]
        )
        assert set(first_data["environment"]["modality_states"].keys()) == set(
            second_data["environment"]["modality_states"].keys()
        )

    def test_events_round_trip(self, client_with_stopped_simulation):
        """Test that events data survives export/import/export cycle."""
        client, engine = client_with_stopped_simulation
        
        # Add some events
        future_time = engine.environment.time_state.current_time + timedelta(hours=1)
        event = create_simulator_event(
            scheduled_time=future_time,
            data=create_email_input(
                timestamp=future_time,
                subject="Round Trip Test",
            ),
        )
        engine.event_queue.add_event(event)
        
        # First export
        first_export = client.get("/scenario/export/events")
        first_data = first_export.json()
        
        # Import
        client.post(
            "/scenario/import/events",
            json={"data": first_data["events"]},
        )
        
        # Second export
        second_export = client.get("/scenario/export/events")
        second_data = second_export.json()
        
        # Event counts should match (events regenerate IDs but count is same)
        assert first_data["total_events"] == second_data["total_events"]
        assert first_data["pending_events"] == second_data["pending_events"]

    def test_full_scenario_round_trip(self, client_with_stopped_simulation):
        """Test that full scenario survives export/import/export cycle."""
        client, engine = client_with_stopped_simulation
        
        # First export
        first_export = client.get(
            "/scenario/export/full",
            params={"author": "Original Author", "description": "Original Description"},
        )
        first_data = first_export.json()
        
        # Import
        client.post(
            "/scenario/import/full",
            json={"scenario": first_data["scenario"]},
        )
        
        # Second export (metadata will differ - new created_at)
        second_export = client.get("/scenario/export/full")
        second_data = second_export.json()
        
        # Environment and event structure should be consistent
        assert set(first_data["scenario"]["environment"]["modality_states"].keys()) == set(
            second_data["scenario"]["environment"]["modality_states"].keys()
        )
