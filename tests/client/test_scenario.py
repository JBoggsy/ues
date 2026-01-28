"""Unit tests for the ScenarioClient and AsyncScenarioClient.

This module tests the scenario save/load sub-client that provides methods for
exporting and importing simulation state.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from ues.client._scenario import (
    AsyncScenarioClient,
    ExportedEnvironmentData,
    ExportedEventQueueData,
    ExportedScenarioData,
    ExportedTimeState,
    ExportEnvironmentResponse,
    ExportEventsResponse,
    ExportScenarioResponse,
    LoadedScenarioMetadata,
    LoadEnvironmentResponse,
    LoadEventsResponse,
    LoadScenarioResponse,
    ScenarioClient,
    ScenarioMetadata,
)


# =============================================================================
# Response Model Tests
# =============================================================================


class TestExportedTimeState:
    """Tests for the ExportedTimeState model."""

    def test_instantiation(self):
        """Test creating an ExportedTimeState."""
        state = ExportedTimeState(
            current_time="2025-01-15T10:00:00+00:00",
            time_scale=1.0,
            is_paused=False,
            auto_advance=False,
            last_wall_time_update="2025-01-15T10:00:00+00:00",
        )
        assert state.current_time == "2025-01-15T10:00:00+00:00"
        assert state.time_scale == 1.0
        assert state.is_paused is False
        assert state.auto_advance is False


class TestExportedEnvironmentData:
    """Tests for the ExportedEnvironmentData model."""

    def test_instantiation(self):
        """Test creating an ExportedEnvironmentData."""
        time_state = ExportedTimeState(
            current_time="2025-01-15T10:00:00+00:00",
            time_scale=1.0,
            is_paused=False,
            auto_advance=False,
            last_wall_time_update="2025-01-15T10:00:00+00:00",
        )
        data = ExportedEnvironmentData(
            time_state=time_state,
            modality_states={"email": {"inbox": []}, "sms": {"threads": {}}},
        )
        assert data.time_state.current_time == "2025-01-15T10:00:00+00:00"
        assert len(data.modality_states) == 2


class TestExportedEventQueueData:
    """Tests for the ExportedEventQueueData model."""

    def test_instantiation_empty(self):
        """Test creating an ExportedEventQueueData with no events."""
        data = ExportedEventQueueData(events=[])
        assert data.events == []

    def test_instantiation_with_events(self):
        """Test creating an ExportedEventQueueData with events."""
        data = ExportedEventQueueData(
            events=[
                {"event_id": "evt-1", "modality": "email", "status": "pending"},
                {"event_id": "evt-2", "modality": "sms", "status": "executed"},
            ]
        )
        assert len(data.events) == 2


class TestScenarioMetadata:
    """Tests for the ScenarioMetadata model."""

    def test_instantiation_minimal(self):
        """Test creating ScenarioMetadata with required fields only."""
        metadata = ScenarioMetadata(
            ues_version="0.1.0",
            scenario_version="1",
            created_at="2025-01-15T10:00:00+00:00",
        )
        assert metadata.ues_version == "0.1.0"
        assert metadata.author is None
        assert metadata.description is None

    def test_instantiation_full(self):
        """Test creating ScenarioMetadata with all fields."""
        metadata = ScenarioMetadata(
            ues_version="0.1.0",
            scenario_version="1",
            created_at="2025-01-15T10:00:00+00:00",
            author="Test Author",
            description="Test scenario description",
        )
        assert metadata.author == "Test Author"
        assert metadata.description == "Test scenario description"


class TestExportEnvironmentResponse:
    """Tests for the ExportEnvironmentResponse model."""

    def test_instantiation(self):
        """Test creating an ExportEnvironmentResponse."""
        time_state = ExportedTimeState(
            current_time="2025-01-15T10:00:00+00:00",
            time_scale=1.0,
            is_paused=False,
            auto_advance=False,
            last_wall_time_update="2025-01-15T10:00:00+00:00",
        )
        env_data = ExportedEnvironmentData(
            time_state=time_state,
            modality_states={"email": {}, "sms": {}},
        )
        response = ExportEnvironmentResponse(
            environment=env_data,
            modalities_exported=["email", "sms"],
        )
        assert len(response.modalities_exported) == 2
        assert "email" in response.modalities_exported


class TestExportEventsResponse:
    """Tests for the ExportEventsResponse model."""

    def test_instantiation(self):
        """Test creating an ExportEventsResponse."""
        response = ExportEventsResponse(
            events=ExportedEventQueueData(events=[{"event_id": "evt-1"}]),
            total_events=10,
            pending_events=5,
            executed_events=4,
        )
        assert response.total_events == 10
        assert response.pending_events == 5
        assert response.executed_events == 4


class TestLoadEnvironmentResponse:
    """Tests for the LoadEnvironmentResponse model."""

    def test_instantiation_success(self):
        """Test LoadEnvironmentResponse for successful load."""
        response = LoadEnvironmentResponse(
            success=True,
            modalities_loaded=["email", "sms", "calendar"],
            modalities_skipped=[],
            warnings=[],
            historic_events_count=2,
            historic_events_action="ignore",
        )
        assert response.success is True
        assert len(response.modalities_loaded) == 3
        assert response.historic_events_action == "ignore"

    def test_instantiation_with_warnings(self):
        """Test LoadEnvironmentResponse with warnings."""
        response = LoadEnvironmentResponse(
            success=True,
            modalities_loaded=["email"],
            modalities_skipped=["unknown_modality"],
            warnings=["Unknown modality 'unknown_modality' skipped"],
            historic_events_count=0,
            historic_events_action="ignore",
        )
        assert len(response.modalities_skipped) == 1
        assert len(response.warnings) == 1


class TestLoadEventsResponse:
    """Tests for the LoadEventsResponse model."""

    def test_instantiation(self):
        """Test creating a LoadEventsResponse."""
        response = LoadEventsResponse(
            success=True,
            events_loaded=15,
            events_merged=10,
            previous_events=5,
            historic_events_warning=True,
            historic_event_count=3,
        )
        assert response.events_loaded == 15
        assert response.events_merged == 10
        assert response.historic_events_warning is True


class TestLoadScenarioResponse:
    """Tests for the LoadScenarioResponse model."""

    def test_instantiation(self):
        """Test creating a LoadScenarioResponse."""
        metadata = LoadedScenarioMetadata(
            ues_version="0.1.0",
            scenario_version="1",
            created_at="2025-01-15T10:00:00+00:00",
            author="Test Author",
            description="Test description",
        )
        response = LoadScenarioResponse(
            success=True,
            environment_loaded=True,
            events_loaded=10,
            modalities_loaded=["email", "sms"],
            modalities_skipped=[],
            warnings=[],
            scenario_metadata=metadata,
        )
        assert response.success is True
        assert response.environment_loaded is True
        assert response.events_loaded == 10
        assert response.scenario_metadata.author == "Test Author"


# =============================================================================
# ScenarioClient Tests
# =============================================================================


class TestScenarioClientExportEnvironment:
    """Tests for ScenarioClient.export_environment() method."""

    def test_export_environment(self):
        """Test exporting environment state."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "environment": {
                "time_state": {
                    "current_time": "2025-01-15T10:00:00+00:00",
                    "time_scale": 1.0,
                    "is_paused": False,
                    "auto_advance": False,
                    "last_wall_time_update": "2025-01-15T10:00:00+00:00",
                },
                "modality_states": {"email": {}, "sms": {}},
            },
            "modalities_exported": ["email", "sms"],
        }

        client = ScenarioClient(mock_http)
        result = client.export_environment()

        mock_http.get.assert_called_once_with("/scenario/export/environment", params=None)
        assert isinstance(result, ExportEnvironmentResponse)
        assert len(result.modalities_exported) == 2


class TestScenarioClientExportEvents:
    """Tests for ScenarioClient.export_events() method."""

    def test_export_events(self):
        """Test exporting event queue."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "events": {"events": [{"event_id": "evt-1"}, {"event_id": "evt-2"}]},
            "total_events": 2,
            "pending_events": 1,
            "executed_events": 1,
        }

        client = ScenarioClient(mock_http)
        result = client.export_events()

        mock_http.get.assert_called_once_with("/scenario/export/events", params=None)
        assert isinstance(result, ExportEventsResponse)
        assert result.total_events == 2


class TestScenarioClientExportFull:
    """Tests for ScenarioClient.export_full() method."""

    def test_export_full_minimal(self):
        """Test exporting full scenario without metadata."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "scenario": {
                "metadata": {
                    "ues_version": "0.1.0",
                    "scenario_version": "1",
                    "created_at": "2025-01-15T10:00:00+00:00",
                },
                "environment": {
                    "time_state": {
                        "current_time": "2025-01-15T10:00:00+00:00",
                        "time_scale": 1.0,
                        "is_paused": False,
                        "auto_advance": False,
                        "last_wall_time_update": "2025-01-15T10:00:00+00:00",
                    },
                    "modality_states": {},
                },
                "events": {"events": []},
            }
        }

        client = ScenarioClient(mock_http)
        result = client.export_full()

        mock_http.get.assert_called_once_with("/scenario/export/full", params=None)
        assert isinstance(result, ExportScenarioResponse)
        assert result.scenario.metadata.ues_version == "0.1.0"

    def test_export_full_with_metadata(self):
        """Test exporting full scenario with author and description."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "scenario": {
                "metadata": {
                    "ues_version": "0.1.0",
                    "scenario_version": "1",
                    "created_at": "2025-01-15T10:00:00+00:00",
                    "author": "Test Author",
                    "description": "Test description",
                },
                "environment": {
                    "time_state": {
                        "current_time": "2025-01-15T10:00:00+00:00",
                        "time_scale": 1.0,
                        "is_paused": False,
                        "auto_advance": False,
                        "last_wall_time_update": "2025-01-15T10:00:00+00:00",
                    },
                    "modality_states": {},
                },
                "events": {"events": []},
            }
        }

        client = ScenarioClient(mock_http)
        result = client.export_full(author="Test Author", description="Test description")

        mock_http.get.assert_called_once_with(
            "/scenario/export/full",
            params={"author": "Test Author", "description": "Test description"},
        )
        assert result.scenario.metadata.author == "Test Author"


class TestScenarioClientImportEnvironment:
    """Tests for ScenarioClient.import_environment() method."""

    def test_import_environment_default_options(self):
        """Test importing environment with default options."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "success": True,
            "modalities_loaded": ["email", "sms"],
            "modalities_skipped": [],
            "warnings": [],
            "historic_events_count": 0,
            "historic_events_action": "ignore",
        }

        client = ScenarioClient(mock_http)
        env_data = {
            "time_state": {
                "current_time": "2025-01-15T10:00:00+00:00",
                "time_scale": 1.0,
                "is_paused": False,
                "auto_advance": False,
                "last_wall_time_update": "2025-01-15T10:00:00+00:00",
            },
            "modality_states": {"email": {}, "sms": {}},
        }
        result = client.import_environment(data=env_data)

        mock_http.post.assert_called_once()
        call_args = mock_http.post.call_args
        assert call_args[0][0] == "/scenario/import/environment"
        assert call_args[1]["json"]["data"] == env_data
        assert call_args[1]["json"]["historic_event_handling"] == "ignore"
        assert call_args[1]["json"]["strict_modalities"] is False
        assert isinstance(result, LoadEnvironmentResponse)
        assert result.success is True

    def test_import_environment_with_options(self):
        """Test importing environment with custom options."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "success": True,
            "modalities_loaded": ["email"],
            "modalities_skipped": [],
            "warnings": [],
            "historic_events_count": 3,
            "historic_events_action": "delete",
        }

        client = ScenarioClient(mock_http)
        result = client.import_environment(
            data={"time_state": {}, "modality_states": {}},
            historic_event_handling="delete",
            strict_modalities=True,
        )

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["historic_event_handling"] == "delete"
        assert call_args[1]["json"]["strict_modalities"] is True


class TestScenarioClientImportEvents:
    """Tests for ScenarioClient.import_events() method."""

    def test_import_events_replace(self):
        """Test importing events with replace mode."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "success": True,
            "events_loaded": 5,
            "events_merged": 0,
            "previous_events": 10,
            "historic_events_warning": False,
            "historic_event_count": 0,
        }

        client = ScenarioClient(mock_http)
        events_data = {"events": [{"event_id": "evt-1"}]}
        result = client.import_events(data=events_data)

        mock_http.post.assert_called_once()
        call_args = mock_http.post.call_args
        assert call_args[0][0] == "/scenario/import/events"
        assert call_args[1]["json"]["data"] == events_data
        assert call_args[1]["json"]["merge"] is False
        assert result.events_loaded == 5
        assert result.previous_events == 10

    def test_import_events_merge(self):
        """Test importing events with merge mode."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "success": True,
            "events_loaded": 5,
            "events_merged": 5,
            "previous_events": 10,
            "historic_events_warning": False,
            "historic_event_count": 0,
        }

        client = ScenarioClient(mock_http)
        result = client.import_events(data={"events": []}, merge=True)

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["merge"] is True


class TestScenarioClientImportFull:
    """Tests for ScenarioClient.import_full() method."""

    def test_import_full_scenario(self):
        """Test importing a full scenario."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "success": True,
            "environment_loaded": True,
            "events_loaded": 10,
            "modalities_loaded": ["email", "sms"],
            "modalities_skipped": [],
            "warnings": [],
            "scenario_metadata": {
                "ues_version": "0.1.0",
                "scenario_version": "1",
                "created_at": "2025-01-15T10:00:00+00:00",
                "author": "Test Author",
                "description": "Test description",
            },
        }

        client = ScenarioClient(mock_http)
        scenario_data = {
            "metadata": {
                "ues_version": "0.1.0",
                "scenario_version": "1",
                "created_at": "2025-01-15T10:00:00+00:00",
            },
            "environment": {
                "time_state": {},
                "modality_states": {},
            },
            "events": {"events": []},
        }
        result = client.import_full(scenario=scenario_data)

        mock_http.post.assert_called_once()
        call_args = mock_http.post.call_args
        assert call_args[0][0] == "/scenario/import/full"
        assert call_args[1]["json"]["scenario"] == scenario_data
        assert call_args[1]["json"]["strict_modalities"] is False
        assert isinstance(result, LoadScenarioResponse)
        assert result.success is True
        assert result.events_loaded == 10

    def test_import_full_with_strict_modalities(self):
        """Test importing with strict modalities mode."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "success": True,
            "environment_loaded": True,
            "events_loaded": 0,
            "modalities_loaded": [],
            "modalities_skipped": [],
            "warnings": [],
            "scenario_metadata": {
                "ues_version": "0.1.0",
                "scenario_version": "1",
                "created_at": "2025-01-15T10:00:00+00:00",
            },
        }

        client = ScenarioClient(mock_http)
        result = client.import_full(scenario={}, strict_modalities=True)

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["strict_modalities"] is True


# =============================================================================
# AsyncScenarioClient Tests
# =============================================================================


class TestAsyncScenarioClientExportEnvironment:
    """Tests for AsyncScenarioClient.export_environment() method."""

    async def test_export_environment(self):
        """Test exporting environment state asynchronously."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "environment": {
                "time_state": {
                    "current_time": "2025-01-15T10:00:00+00:00",
                    "time_scale": 1.0,
                    "is_paused": False,
                    "auto_advance": False,
                    "last_wall_time_update": "2025-01-15T10:00:00+00:00",
                },
                "modality_states": {},
            },
            "modalities_exported": ["email"],
        }

        client = AsyncScenarioClient(mock_http)
        result = await client.export_environment()

        mock_http.get.assert_called_once_with("/scenario/export/environment", params=None)
        assert isinstance(result, ExportEnvironmentResponse)


class TestAsyncScenarioClientExportEvents:
    """Tests for AsyncScenarioClient.export_events() method."""

    async def test_export_events(self):
        """Test exporting events asynchronously."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "events": {"events": []},
            "total_events": 0,
            "pending_events": 0,
            "executed_events": 0,
        }

        client = AsyncScenarioClient(mock_http)
        result = await client.export_events()

        mock_http.get.assert_called_once_with("/scenario/export/events", params=None)
        assert isinstance(result, ExportEventsResponse)


class TestAsyncScenarioClientExportFull:
    """Tests for AsyncScenarioClient.export_full() method."""

    async def test_export_full(self):
        """Test exporting full scenario asynchronously."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "scenario": {
                "metadata": {
                    "ues_version": "0.1.0",
                    "scenario_version": "1",
                    "created_at": "2025-01-15T10:00:00+00:00",
                },
                "environment": {
                    "time_state": {
                        "current_time": "2025-01-15T10:00:00+00:00",
                        "time_scale": 1.0,
                        "is_paused": False,
                        "auto_advance": False,
                        "last_wall_time_update": "2025-01-15T10:00:00+00:00",
                    },
                    "modality_states": {},
                },
                "events": {"events": []},
            }
        }

        client = AsyncScenarioClient(mock_http)
        result = await client.export_full(author="Author")

        mock_http.get.assert_called_once_with(
            "/scenario/export/full",
            params={"author": "Author"},
        )
        assert isinstance(result, ExportScenarioResponse)


class TestAsyncScenarioClientImportEnvironment:
    """Tests for AsyncScenarioClient.import_environment() method."""

    async def test_import_environment(self):
        """Test importing environment asynchronously."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "success": True,
            "modalities_loaded": ["email"],
            "modalities_skipped": [],
            "warnings": [],
            "historic_events_count": 0,
            "historic_events_action": "ignore",
        }

        client = AsyncScenarioClient(mock_http)
        result = await client.import_environment(
            data={"time_state": {}, "modality_states": {}},
        )

        assert isinstance(result, LoadEnvironmentResponse)
        assert result.success is True


class TestAsyncScenarioClientImportEvents:
    """Tests for AsyncScenarioClient.import_events() method."""

    async def test_import_events(self):
        """Test importing events asynchronously."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "success": True,
            "events_loaded": 5,
            "events_merged": 0,
            "previous_events": 0,
            "historic_events_warning": False,
            "historic_event_count": 0,
        }

        client = AsyncScenarioClient(mock_http)
        result = await client.import_events(data={"events": []})

        assert isinstance(result, LoadEventsResponse)
        assert result.events_loaded == 5


class TestAsyncScenarioClientImportFull:
    """Tests for AsyncScenarioClient.import_full() method."""

    async def test_import_full(self):
        """Test importing full scenario asynchronously."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "success": True,
            "environment_loaded": True,
            "events_loaded": 10,
            "modalities_loaded": ["email"],
            "modalities_skipped": [],
            "warnings": [],
            "scenario_metadata": {
                "ues_version": "0.1.0",
                "scenario_version": "1",
                "created_at": "2025-01-15T10:00:00+00:00",
            },
        }

        client = AsyncScenarioClient(mock_http)
        result = await client.import_full(scenario={})

        assert isinstance(result, LoadScenarioResponse)
        assert result.success is True
        assert result.events_loaded == 10
