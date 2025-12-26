"""Unit tests for scenario API request/response models.

Tests the Pydantic models used for the scenario save/load API endpoints:
- Export response models (ExportEnvironmentResponse, ExportEventsResponse, ExportScenarioResponse)
- Import request models (LoadEnvironmentRequest, LoadEventsRequest, LoadScenarioRequest)
- Import response models (LoadEnvironmentResponse, LoadEventsResponse, LoadScenarioResponse)
- Data structure models (ExportedEnvironmentData, ExportedEventQueueData, etc.)

Test Organization:
- Data structure model validation
- Export response model validation
- Import request model validation
- Import response model validation
- Round-trip serialization tests
- Integration with actual SimulationEngine data
"""

from datetime import datetime, timezone, timedelta

import pytest
from pydantic import ValidationError

from api.models import (
    # Data structure models
    ExportedEnvironmentData,
    ExportedEventQueueData,
    ExportedScenarioData,
    ExportedTimeState,
    ScenarioMetadataModel,
    # Export response models
    ExportEnvironmentResponse,
    ExportEventsResponse,
    ExportScenarioResponse,
    # Import request models
    LoadEnvironmentRequest,
    LoadEventsRequest,
    LoadScenarioRequest,
    # Import response models
    LoadEnvironmentResponse,
    LoadEventsResponse,
    LoadScenarioResponse,
    LoadedScenarioMetadata,
)


# =============================================================================
# Test Data Fixtures
# =============================================================================


@pytest.fixture
def sample_time_state_dict():
    """Sample time state data as would be exported."""
    return {
        "current_time": "2025-06-15T12:00:00Z",
        "time_scale": 1.0,
        "is_paused": False,
        "auto_advance": False,
        "last_wall_time_update": "2025-06-15T12:00:00Z",
    }


@pytest.fixture
def sample_modality_states_dict():
    """Sample modality states as would be exported."""
    return {
        "location": {
            "modality_type": "location",
            "current_latitude": 37.7749,
            "current_longitude": -122.4194,
            "current_address": "San Francisco, CA",
            "last_updated": "2025-06-15T12:00:00Z",
        },
        "email": {
            "modality_type": "email",
            "inbox": [],
            "sent": [],
            "drafts": [],
            "trash": [],
            "last_updated": "2025-06-15T12:00:00Z",
        },
    }


@pytest.fixture
def sample_environment_data(sample_time_state_dict, sample_modality_states_dict):
    """Sample environment data as would be exported."""
    return {
        "time_state": sample_time_state_dict,
        "modality_states": sample_modality_states_dict,
    }


@pytest.fixture
def sample_events_list():
    """Sample events list as would be exported."""
    return [
        {
            "event_id": "event-123",
            "modality": "location",
            "scheduled_time": "2025-06-15T13:00:00Z",
            "created_at": "2025-06-15T12:00:00Z",
            "status": "pending",
            "priority": 0,
            "data": {
                "modality_type": "location",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "timestamp": "2025-06-15T13:00:00Z",
            },
        },
    ]


@pytest.fixture
def sample_event_queue_data(sample_events_list):
    """Sample event queue data as would be exported."""
    return {"events": sample_events_list}


@pytest.fixture
def sample_scenario_metadata():
    """Sample scenario metadata."""
    return {
        "ues_version": "0.1.0",
        "scenario_version": "1",
        "created_at": "2025-06-15T12:00:00Z",
        "author": "Test User",
        "description": "Test scenario for unit tests",
    }


@pytest.fixture
def sample_scenario_data(sample_scenario_metadata, sample_environment_data, sample_event_queue_data):
    """Complete sample scenario data."""
    return {
        "metadata": sample_scenario_metadata,
        "environment": sample_environment_data,
        "events": sample_event_queue_data,
    }


# =============================================================================
# Data Structure Models
# =============================================================================


class TestExportedTimeState:
    """Tests for ExportedTimeState model."""

    def test_valid_time_state(self, sample_time_state_dict):
        """Test creating valid time state model."""
        model = ExportedTimeState(**sample_time_state_dict)
        assert model.time_scale == 1.0
        assert model.is_paused is False
        assert model.auto_advance is False

    def test_missing_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            ExportedTimeState(current_time=datetime.now(timezone.utc))


class TestExportedEnvironmentData:
    """Tests for ExportedEnvironmentData model."""

    def test_valid_environment_data(self, sample_environment_data):
        """Test creating valid environment data model."""
        model = ExportedEnvironmentData(**sample_environment_data)
        assert "location" in model.modality_states
        assert "email" in model.modality_states
        assert model.time_state is not None

    def test_empty_modality_states(self, sample_time_state_dict):
        """Test environment with empty modality states."""
        model = ExportedEnvironmentData(
            time_state=sample_time_state_dict,
            modality_states={},
        )
        assert model.modality_states == {}

    def test_missing_time_state(self):
        """Test that time_state is required."""
        with pytest.raises(ValidationError) as exc_info:
            ExportedEnvironmentData(modality_states={})
        assert "time_state" in str(exc_info.value)


class TestExportedEventQueueData:
    """Tests for ExportedEventQueueData model."""

    def test_valid_event_queue_data(self, sample_event_queue_data):
        """Test creating valid event queue data model."""
        model = ExportedEventQueueData(**sample_event_queue_data)
        assert len(model.events) == 1

    def test_empty_events(self):
        """Test event queue with no events."""
        model = ExportedEventQueueData(events=[])
        assert model.events == []

    def test_missing_events_field(self):
        """Test that events field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ExportedEventQueueData()
        assert "events" in str(exc_info.value)


class TestScenarioMetadataModel:
    """Tests for ScenarioMetadataModel."""

    def test_valid_metadata(self, sample_scenario_metadata):
        """Test creating valid metadata model."""
        model = ScenarioMetadataModel(**sample_scenario_metadata)
        assert model.ues_version == "0.1.0"
        assert model.scenario_version == "1"
        assert model.author == "Test User"

    def test_optional_fields(self):
        """Test that author and description are optional."""
        model = ScenarioMetadataModel(
            ues_version="0.1.0",
            scenario_version="1",
            created_at=datetime.now(timezone.utc),
        )
        assert model.author is None
        assert model.description is None


class TestExportedScenarioData:
    """Tests for ExportedScenarioData model."""

    def test_valid_scenario_data(self, sample_scenario_data):
        """Test creating valid scenario data model."""
        model = ExportedScenarioData(**sample_scenario_data)
        assert model.metadata.ues_version == "0.1.0"
        assert "location" in model.environment.modality_states
        assert len(model.events.events) == 1

    def test_missing_required_fields(self):
        """Test that all top-level fields are required."""
        with pytest.raises(ValidationError):
            ExportedScenarioData(metadata={})


# =============================================================================
# Export Response Models
# =============================================================================


class TestExportEnvironmentResponse:
    """Tests for ExportEnvironmentResponse model."""

    def test_valid_response(self, sample_environment_data):
        """Test creating valid export environment response."""
        response = ExportEnvironmentResponse(
            environment=sample_environment_data,
            current_time=datetime.now(timezone.utc),
            modalities_exported=["location", "email"],
        )
        assert len(response.modalities_exported) == 2
        assert response.environment is not None

    def test_empty_modalities(self, sample_environment_data):
        """Test response with no modalities exported."""
        response = ExportEnvironmentResponse(
            environment={"time_state": sample_environment_data["time_state"], "modality_states": {}},
            current_time=datetime.now(timezone.utc),
            modalities_exported=[],
        )
        assert response.modalities_exported == []

    def test_serialization(self, sample_environment_data):
        """Test that response serializes to JSON."""
        response = ExportEnvironmentResponse(
            environment=sample_environment_data,
            modalities_exported=["location"],
        )
        json_data = response.model_dump(mode="json")
        assert isinstance(json_data, dict)
        assert "environment" in json_data


class TestExportEventsResponse:
    """Tests for ExportEventsResponse model."""

    def test_valid_response(self, sample_event_queue_data):
        """Test creating valid export events response."""
        response = ExportEventsResponse(
            events=sample_event_queue_data,
            total_events=10,
            pending_events=5,
            executed_events=5,
        )
        assert response.total_events == 10
        assert response.pending_events == 5

    def test_zero_counts(self):
        """Test response with zero event counts."""
        response = ExportEventsResponse(
            events={"events": []},
            total_events=0,
            pending_events=0,
            executed_events=0,
        )
        assert response.total_events == 0

    def test_negative_counts_rejected(self):
        """Test that negative counts are rejected."""
        with pytest.raises(ValidationError):
            ExportEventsResponse(
                events={"events": []},
                total_events=-1,
                pending_events=0,
                executed_events=0,
            )


class TestExportScenarioResponse:
    """Tests for ExportScenarioResponse model."""

    def test_valid_response(self, sample_scenario_data):
        """Test creating valid export scenario response."""
        response = ExportScenarioResponse(scenario=sample_scenario_data)
        assert response.scenario.metadata.ues_version == "0.1.0"

    def test_serialization(self, sample_scenario_data):
        """Test that response serializes to JSON."""
        response = ExportScenarioResponse(scenario=sample_scenario_data)
        json_data = response.model_dump(mode="json")
        assert "scenario" in json_data
        assert "metadata" in json_data["scenario"]


# =============================================================================
# Import Request Models
# =============================================================================


class TestLoadEnvironmentRequest:
    """Tests for LoadEnvironmentRequest model."""

    def test_valid_request_defaults(self, sample_environment_data):
        """Test request with default values."""
        request = LoadEnvironmentRequest(data=sample_environment_data)
        assert request.historic_event_handling == "ignore"
        assert request.strict_modalities is False

    def test_valid_request_custom_options(self, sample_environment_data):
        """Test request with custom options."""
        request = LoadEnvironmentRequest(
            data=sample_environment_data,
            historic_event_handling="delete",
            strict_modalities=True,
        )
        assert request.historic_event_handling == "delete"
        assert request.strict_modalities is True

    def test_all_historic_handling_options(self, sample_environment_data):
        """Test all valid historic event handling options."""
        for option in ["ignore", "delete", "apply"]:
            request = LoadEnvironmentRequest(
                data=sample_environment_data,
                historic_event_handling=option,
            )
            assert request.historic_event_handling == option

    def test_invalid_historic_handling_rejected(self, sample_environment_data):
        """Test that invalid historic_event_handling is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LoadEnvironmentRequest(
                data=sample_environment_data,
                historic_event_handling="invalid_option",
            )
        assert "historic_event_handling" in str(exc_info.value)


class TestLoadEventsRequest:
    """Tests for LoadEventsRequest model."""

    def test_valid_request_defaults(self, sample_event_queue_data):
        """Test request with default values."""
        request = LoadEventsRequest(data=sample_event_queue_data)
        assert request.merge is False

    def test_merge_true(self, sample_event_queue_data):
        """Test request with merge=True."""
        request = LoadEventsRequest(
            data=sample_event_queue_data,
            merge=True,
        )
        assert request.merge is True


class TestLoadScenarioRequest:
    """Tests for LoadScenarioRequest model."""

    def test_valid_request_defaults(self, sample_scenario_data):
        """Test request with default values."""
        request = LoadScenarioRequest(scenario=sample_scenario_data)
        assert request.strict_modalities is False

    def test_strict_modalities_true(self, sample_scenario_data):
        """Test request with strict_modalities=True."""
        request = LoadScenarioRequest(
            scenario=sample_scenario_data,
            strict_modalities=True,
        )
        assert request.strict_modalities is True


# =============================================================================
# Import Response Models
# =============================================================================


class TestLoadEnvironmentResponse:
    """Tests for LoadEnvironmentResponse model."""

    def test_valid_response(self):
        """Test creating valid load environment response."""
        response = LoadEnvironmentResponse(
            success=True,
            modalities_loaded=["location", "email"],
            modalities_skipped=["unknown_type"],
            warnings=["Warning about something"],
            historic_events_count=5,
            historic_events_action="ignore",
        )
        assert response.success is True
        assert len(response.modalities_loaded) == 2
        assert len(response.modalities_skipped) == 1
        assert response.historic_events_count == 5

    def test_empty_lists(self):
        """Test response with empty lists."""
        response = LoadEnvironmentResponse(
            success=True,
            modalities_loaded=[],
            modalities_skipped=[],
            warnings=[],
            historic_events_count=0,
            historic_events_action="ignore",
        )
        assert response.modalities_loaded == []

    def test_negative_historic_count_rejected(self):
        """Test that negative historic_events_count is rejected."""
        with pytest.raises(ValidationError):
            LoadEnvironmentResponse(
                success=True,
                modalities_loaded=[],
                modalities_skipped=[],
                warnings=[],
                historic_events_count=-1,
                historic_events_action="ignore",
            )


class TestLoadEventsResponse:
    """Tests for LoadEventsResponse model."""

    def test_valid_response_replace_mode(self):
        """Test response for replace mode (merge=False)."""
        response = LoadEventsResponse(
            success=True,
            events_loaded=10,
            events_merged=0,
            previous_events=5,
            historic_events_warning=False,
            historic_event_count=0,
        )
        assert response.events_loaded == 10
        assert response.events_merged == 0

    def test_valid_response_merge_mode(self):
        """Test response for merge mode (merge=True)."""
        response = LoadEventsResponse(
            success=True,
            events_loaded=10,
            events_merged=8,
            previous_events=5,
            historic_events_warning=True,
            historic_event_count=2,
        )
        assert response.events_merged == 8
        assert response.historic_events_warning is True


class TestLoadedScenarioMetadata:
    """Tests for LoadedScenarioMetadata model."""

    def test_valid_metadata(self):
        """Test creating valid loaded metadata."""
        metadata = LoadedScenarioMetadata(
            ues_version="0.1.0",
            scenario_version="1",
            created_at="2025-06-15T12:00:00Z",
            author="Test User",
            description="Test description",
        )
        assert metadata.ues_version == "0.1.0"
        assert metadata.created_at == "2025-06-15T12:00:00Z"

    def test_optional_fields_none(self):
        """Test that author and description can be None."""
        metadata = LoadedScenarioMetadata(
            ues_version="0.1.0",
            scenario_version="1",
            created_at="2025-06-15T12:00:00Z",
        )
        assert metadata.author is None
        assert metadata.description is None


class TestLoadScenarioResponse:
    """Tests for LoadScenarioResponse model."""

    def test_valid_response(self):
        """Test creating valid load scenario response."""
        response = LoadScenarioResponse(
            success=True,
            environment_loaded=True,
            events_loaded=5,
            modalities_loaded=["location", "email"],
            modalities_skipped=[],
            warnings=[],
            scenario_metadata=LoadedScenarioMetadata(
                ues_version="0.1.0",
                scenario_version="1",
                created_at="2025-06-15T12:00:00Z",
                author="Test User",
                description=None,
            ),
        )
        assert response.success is True
        assert response.environment_loaded is True
        assert response.scenario_metadata.author == "Test User"

    def test_with_warnings(self):
        """Test response with warnings."""
        response = LoadScenarioResponse(
            success=True,
            environment_loaded=True,
            events_loaded=5,
            modalities_loaded=["location"],
            modalities_skipped=["unknown"],
            warnings=[
                "Skipped unknown modality type: 'unknown'",
                "2 events scheduled before environment time",
            ],
            scenario_metadata=LoadedScenarioMetadata(
                ues_version="0.1.0",
                scenario_version="1",
                created_at="2025-06-15T12:00:00Z",
            ),
        )
        assert len(response.warnings) == 2
        assert "unknown" in response.modalities_skipped


# =============================================================================
# Integration Tests with Actual Data
# =============================================================================


class TestIntegrationWithSimulationEngine:
    """Integration tests using actual SimulationEngine export data."""

    def test_environment_data_from_engine(self):
        """Test that ExportedEnvironmentData works with actual engine export."""
        from tests.fixtures.core.environments import create_environment
        from models.simulation import SimulationEngine
        from models.queue import EventQueue

        # Create engine and export
        env = create_environment()
        engine = SimulationEngine(environment=env, event_queue=EventQueue())
        exported = engine.export_environment()

        # Should successfully create model from exported data
        model = ExportedEnvironmentData(**exported)
        assert "time_state" in exported
        assert model.time_state is not None

    def test_event_queue_data_from_engine(self):
        """Test that ExportedEventQueueData works with actual engine export."""
        from tests.fixtures.core.environments import create_environment
        from tests.fixtures.core.events import create_simulator_event
        from tests.fixtures.core.queues import create_event_queue
        from models.simulation import SimulationEngine

        # Create engine with events and export
        event = create_simulator_event(modality="location")
        queue = create_event_queue(events=[event])
        engine = SimulationEngine(
            environment=create_environment(),
            event_queue=queue,
        )
        exported = engine.export_event_queue()

        # Should successfully create model from exported data
        model = ExportedEventQueueData(**exported)
        assert len(model.events) == 1

    def test_scenario_data_from_engine(self):
        """Test that ExportedScenarioData works with actual engine export."""
        from tests.fixtures.core.environments import create_environment
        from models.simulation import SimulationEngine
        from models.queue import EventQueue

        # Create engine and export scenario
        engine = SimulationEngine(
            environment=create_environment(),
            event_queue=EventQueue(),
        )
        scenario = engine.export_scenario(author="Test", description="Test scenario")
        exported = scenario.to_dict()

        # Should successfully create model from exported data
        model = ExportedScenarioData(**exported)
        assert model.metadata.author == "Test"
        assert model.metadata.description == "Test scenario"

    def test_load_environment_response_matches_engine_result(self):
        """Test that LoadEnvironmentResponse matches actual engine.load_environment() result."""
        from tests.fixtures.core.environments import create_environment
        from models.simulation import SimulationEngine
        from models.queue import EventQueue

        # Create and export environment
        source_engine = SimulationEngine(
            environment=create_environment(),
            event_queue=EventQueue(),
        )
        exported = source_engine.export_environment()

        # Load into new engine
        target_engine = SimulationEngine(
            environment=create_environment(),
            event_queue=EventQueue(),
        )
        result = target_engine.load_environment(exported)

        # Should successfully create response from result
        response = LoadEnvironmentResponse(**result)
        assert response.success is True
        assert len(response.modalities_loaded) > 0

    def test_load_events_response_matches_engine_result(self):
        """Test that LoadEventsResponse matches actual engine.load_event_queue() result."""
        from tests.fixtures.core.environments import create_environment
        from tests.fixtures.core.events import create_simulator_event
        from tests.fixtures.core.queues import create_event_queue
        from models.simulation import SimulationEngine
        from models.queue import EventQueue

        # Create engine with events and export
        event = create_simulator_event(modality="location")
        queue = create_event_queue(events=[event])
        source_engine = SimulationEngine(
            environment=create_environment(),
            event_queue=queue,
        )
        exported = source_engine.export_event_queue()

        # Load into new engine
        target_engine = SimulationEngine(
            environment=create_environment(),
            event_queue=EventQueue(),
        )
        result = target_engine.load_event_queue(exported)

        # Should successfully create response from result
        response = LoadEventsResponse(**result)
        assert response.success is True
        assert response.events_loaded == 1

    def test_load_scenario_response_matches_engine_result(self):
        """Test that LoadScenarioResponse matches actual engine.load_scenario() result."""
        from tests.fixtures.core.environments import create_environment
        from models.simulation import SimulationEngine
        from models.queue import EventQueue
        from models.scenario import Scenario

        # Create and export scenario
        source_engine = SimulationEngine(
            environment=create_environment(),
            event_queue=EventQueue(),
        )
        scenario = source_engine.export_scenario(author="Test", description="Test")

        # Load into new engine
        target_engine = SimulationEngine(
            environment=create_environment(),
            event_queue=EventQueue(),
        )
        result = target_engine.load_scenario(scenario)

        # Should successfully create response from result
        response = LoadScenarioResponse(**result)
        assert response.success is True
        assert response.scenario_metadata.author == "Test"
