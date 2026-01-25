"""Scenario import/export sub-client for the UES API.

This module provides ScenarioClient and AsyncScenarioClient for interacting
with the scenario endpoints (/scenario/*) for saving and loading simulation state.

This is an internal module. Import from `client` instead.

Example:
    Synchronous usage::
    
        from client import UESClient
        
        with UESClient() as client:
            # Export complete scenario
            scenario = client.scenario.export_full(
                author="Developer",
                description="Test scenario for email workflow",
            )
            
            # Save to file
            client.scenario.save_to_file("my-scenario.ues-scenario.json")
            
            # Later, load it back
            result = client.scenario.load_from_file("my-scenario.ues-scenario.json")
            print(f"Loaded {result.events_loaded} events")
    
    Asynchronous usage::
    
        from client import AsyncUESClient
        
        async with AsyncUESClient() as client:
            scenario = await client.scenario.export_full()
            await client.scenario.save_to_file("backup.ues-scenario.json")
"""

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field

from client._base import AsyncBaseClient, BaseClient

if TYPE_CHECKING:
    from client._http import AsyncHTTPClient, HTTPClient


# Export response models


class ExportedTimeState(BaseModel):
    """Exported time state data.
    
    Attributes:
        current_time: Current simulator time.
        time_scale: Time multiplier.
        is_paused: Whether time is paused.
        auto_advance: Whether auto-advance is enabled.
        last_wall_time_update: Last wall-clock update time.
    """
    
    current_time: datetime
    time_scale: float
    is_paused: bool
    auto_advance: bool
    last_wall_time_update: datetime | None = None


class ExportedEnvironmentData(BaseModel):
    """Exported environment state data.
    
    Attributes:
        time_state: Time state snapshot.
        modality_states: Dict of modality states keyed by modality type.
    """
    
    time_state: ExportedTimeState
    modality_states: dict[str, Any]


class ExportEnvironmentResponse(BaseModel):
    """Response model for environment export.
    
    Attributes:
        environment: The exported environment data.
        modalities_exported: List of modality types that were exported.
    """
    
    environment: ExportedEnvironmentData
    modalities_exported: list[str]


class ExportedEventQueueData(BaseModel):
    """Exported event queue data.
    
    Attributes:
        events: List of event dictionaries.
    """
    
    events: list[dict[str, Any]]


class ExportEventsResponse(BaseModel):
    """Response model for event queue export.
    
    Attributes:
        events: The exported event queue data.
        total_events: Total number of events.
        pending_events: Number of pending events.
        executed_events: Number of executed events.
    """
    
    events: ExportedEventQueueData
    total_events: int
    pending_events: int
    executed_events: int


class ScenarioMetadata(BaseModel):
    """Scenario metadata.
    
    Attributes:
        ues_version: UES version that created the scenario.
        scenario_version: Scenario format version.
        created_at: When the scenario was exported.
        author: Optional author name.
        description: Optional scenario description.
    """
    
    ues_version: str
    scenario_version: str
    created_at: datetime
    author: str | None = None
    description: str | None = None


class ExportedScenarioData(BaseModel):
    """Complete exported scenario data.
    
    Attributes:
        metadata: Scenario metadata.
        environment: Environment state.
        events: Event queue.
    """
    
    metadata: ScenarioMetadata
    environment: ExportedEnvironmentData
    events: ExportedEventQueueData


class ExportScenarioResponse(BaseModel):
    """Response model for full scenario export.
    
    Attributes:
        scenario: The complete exported scenario.
    """
    
    scenario: ExportedScenarioData


# Import response models


class LoadEnvironmentResponse(BaseModel):
    """Response model for environment import.
    
    Attributes:
        success: Whether the import succeeded.
        modalities_loaded: List of modalities that were loaded.
        modalities_skipped: List of modalities that were skipped.
        warnings: Any warnings generated during import.
        historic_events_count: Number of historic events found.
        historic_events_action: How historic events were handled.
    """
    
    success: bool
    modalities_loaded: list[str]
    modalities_skipped: list[str]
    warnings: list[str]
    historic_events_count: int
    historic_events_action: str


class LoadEventsResponse(BaseModel):
    """Response model for event queue import.
    
    Attributes:
        success: Whether the import succeeded.
        events_loaded: Number of events loaded.
        events_merged: Whether events were merged (vs replaced).
        previous_events: Number of events before import.
        historic_events_warning: Whether historic events were detected.
        historic_event_count: Number of historic events found.
    """
    
    success: bool
    events_loaded: int
    events_merged: bool
    previous_events: int
    historic_events_warning: bool
    historic_event_count: int


class LoadedScenarioMetadata(BaseModel):
    """Metadata from a loaded scenario.
    
    Attributes:
        ues_version: UES version that created the scenario.
        scenario_version: Scenario format version.
        created_at: When the scenario was exported.
        author: Author name if present.
        description: Description if present.
    """
    
    ues_version: str
    scenario_version: str
    created_at: datetime
    author: str | None = None
    description: str | None = None


class LoadScenarioResponse(BaseModel):
    """Response model for full scenario import.
    
    Attributes:
        success: Whether the import succeeded.
        environment_loaded: Whether environment was loaded.
        events_loaded: Number of events loaded.
        modalities_loaded: List of modalities that were loaded.
        modalities_skipped: List of modalities that were skipped.
        warnings: Any warnings generated during import.
        scenario_metadata: Metadata from the loaded scenario.
    """
    
    success: bool
    environment_loaded: bool
    events_loaded: int
    modalities_loaded: list[str]
    modalities_skipped: list[str]
    warnings: list[str]
    scenario_metadata: LoadedScenarioMetadata


# Synchronous ScenarioClient


class ScenarioClient(BaseClient):
    """Synchronous client for scenario import/export endpoints (/scenario/*).
    
    Provides methods for saving and loading simulation state. Scenarios can
    be exported as complete snapshots (environment + events + metadata) or
    as individual components.
    
    The simulation must be stopped before importing.
    
    Example:
        with UESClient() as client:
            # Export complete scenario
            scenario = client.scenario.export_full(
                author="QA Team",
                description="Email workflow test fixture",
            )
            
            # Save to file for later use
            client.scenario.save_to_file(
                "fixtures/email-workflow.ues-scenario.json",
                author="QA Team",
                description="Email workflow test fixture",
            )
            
            # Reset and reload
            client.simulation.clear()
            result = client.scenario.load_from_file(
                "fixtures/email-workflow.ues-scenario.json"
            )
            print(f"Loaded {result.events_loaded} events")
            
            # Export just environment (without events)
            env_data = client.scenario.export_environment()
            
            # Import environment with historic event handling
            client.scenario.import_environment(
                data=env_data.environment.model_dump(),
                historic_event_handling="delete",
            )
    """
    
    _BASE_PATH = "/scenario"
    
    def export_environment(self) -> ExportEnvironmentResponse:
        """Export current environment state as JSON.
        
        Creates a serialized snapshot of the current environment state,
        including simulator time and all modality states.
        
        Returns:
            Export response with environment data and list of exported modalities.
        
        Raises:
            APIError: If the export fails.
        
        Example:
            env = client.scenario.export_environment()
            print(f"Exported: {env.modalities_exported}")
        """
        data = self._get(f"{self._BASE_PATH}/export/environment")
        return ExportEnvironmentResponse(**data)
    
    def export_events(self) -> ExportEventsResponse:
        """Export current event queue as JSON.
        
        Creates a serialized snapshot of the current event queue,
        including pending, executed, and failed events.
        
        Returns:
            Export response with event data and statistics.
        
        Raises:
            APIError: If the export fails.
        
        Example:
            events = client.scenario.export_events()
            print(f"Total: {events.total_events}, Pending: {events.pending_events}")
        """
        data = self._get(f"{self._BASE_PATH}/export/events")
        return ExportEventsResponse(**data)
    
    def export_full(
        self,
        author: str | None = None,
        description: str | None = None,
    ) -> ExportScenarioResponse:
        """Export complete scenario with metadata.
        
        Creates a complete scenario snapshot including:
        - Metadata (UES version, creation timestamp, author, description)
        - Environment state (time + all modalities)
        - Event queue (all events)
        
        Args:
            author: Optional author name for scenario metadata.
            description: Optional description for scenario metadata.
        
        Returns:
            Complete exported scenario.
        
        Raises:
            APIError: If the export fails.
        
        Example:
            scenario = client.scenario.export_full(
                author="Developer",
                description="Integration test fixture",
            )
            print(f"Version: {scenario.scenario.metadata.ues_version}")
        """
        params: dict[str, Any] = {}
        if author is not None:
            params["author"] = author
        if description is not None:
            params["description"] = description
        
        data = self._get(
            f"{self._BASE_PATH}/export/full",
            params=params if params else None,
        )
        return ExportScenarioResponse(**data)
    
    def import_environment(
        self,
        data: dict[str, Any],
        historic_event_handling: Literal["ignore", "delete", "apply"] = "ignore",
        strict_modalities: bool = False,
    ) -> LoadEnvironmentResponse:
        """Import environment state from JSON.
        
        Replaces the current environment state with the provided data.
        The simulation must be stopped before importing.
        
        Historic events (scheduled before the new environment time) can be
        handled in different ways:
        - "ignore": Leave in queue (they will never execute)
        - "delete": Remove from queue
        - "apply": Execute immediately against loaded state
        
        The undo stack is cleared when loading an environment.
        
        Args:
            data: Environment data dict (must have "time_state" and "modality_states").
            historic_event_handling: How to handle events scheduled before new time.
            strict_modalities: If True, fail on unknown modality types.
        
        Returns:
            Import results including loaded/skipped modalities and warnings.
        
        Raises:
            ConflictError: If simulation is running.
            ValidationError: If data is invalid or (with strict_modalities) unknown modality.
            APIError: If the import fails.
        
        Example:
            result = client.scenario.import_environment(
                data=env_export.environment.model_dump(),
                historic_event_handling="delete",
            )
            print(f"Loaded: {result.modalities_loaded}")
        """
        request_data = {
            "data": data,
            "historic_event_handling": historic_event_handling,
            "strict_modalities": strict_modalities,
        }
        
        response = self._post(f"{self._BASE_PATH}/import/environment", json=request_data)
        return LoadEnvironmentResponse(**response)
    
    def import_events(
        self,
        data: dict[str, Any],
        merge: bool = False,
    ) -> LoadEventsResponse:
        """Import event queue from JSON.
        
        Replaces or merges the current event queue with the provided data.
        The simulation must be stopped before importing.
        
        When merge=True, loaded events are added to the existing queue.
        When merge=False (default), the entire queue is replaced.
        
        The undo stack is cleared when replacing (not when merging).
        
        Args:
            data: Event queue data dict (must have "events" list).
            merge: If True, add to existing queue; if False, replace entirely.
        
        Returns:
            Import results including event counts and merge status.
        
        Raises:
            ConflictError: If simulation is running.
            ValidationError: If data is invalid.
            APIError: If the import fails.
        
        Example:
            # Replace all events
            result = client.scenario.import_events(
                data=events_export.events.model_dump()
            )
            
            # Merge with existing
            result = client.scenario.import_events(
                data={"events": new_events},
                merge=True,
            )
        """
        request_data = {
            "data": data,
            "merge": merge,
        }
        
        response = self._post(f"{self._BASE_PATH}/import/events", json=request_data)
        return LoadEventsResponse(**response)
    
    def import_full(
        self,
        scenario: dict[str, Any],
        strict_modalities: bool = False,
    ) -> LoadScenarioResponse:
        """Import complete scenario (environment + events).
        
        Replaces both the environment and event queue with the provided
        scenario data. The simulation must be stopped before importing.
        
        The undo stack is always cleared when loading a scenario.
        
        Args:
            scenario: Complete scenario dict (must have "metadata", "environment", "events").
            strict_modalities: If True, fail on unknown modality types.
        
        Returns:
            Comprehensive import results.
        
        Raises:
            ConflictError: If simulation is running.
            ValidationError: If scenario is invalid or (with strict) unknown modality.
            APIError: If the import fails.
        
        Example:
            result = client.scenario.import_full(
                scenario=scenario_export.scenario.model_dump()
            )
            print(f"Loaded {result.events_loaded} events")
        """
        request_data = {
            "scenario": scenario,
            "strict_modalities": strict_modalities,
        }
        
        response = self._post(f"{self._BASE_PATH}/import/full", json=request_data)
        return LoadScenarioResponse(**response)
    
    # Convenience file I/O methods
    
    def save_to_file(
        self,
        filepath: str,
        author: str | None = None,
        description: str | None = None,
    ) -> None:
        """Export scenario and save to a file.
        
        Convenience method that exports the complete scenario and writes
        it to the specified file path as JSON.
        
        Args:
            filepath: Path to save the scenario file.
            author: Optional author name for metadata.
            description: Optional description for metadata.
        
        Raises:
            APIError: If the export fails.
            IOError: If the file cannot be written.
        
        Example:
            client.scenario.save_to_file(
                "fixtures/test-scenario.ues-scenario.json",
                author="Test Suite",
                description="Pre-configured email inbox state",
            )
        """
        scenario = self.export_full(author=author, description=description)
        
        with open(filepath, "w", encoding="utf-8") as f:
            # Use model_dump with mode="json" for proper serialization
            json.dump(
                scenario.model_dump(mode="json"),
                f,
                indent=2,
                ensure_ascii=False,
            )
    
    def load_from_file(
        self,
        filepath: str,
        strict_modalities: bool = False,
    ) -> LoadScenarioResponse:
        """Load scenario from a file.
        
        Convenience method that reads a scenario file and imports it.
        
        Args:
            filepath: Path to the scenario file.
            strict_modalities: If True, fail on unknown modality types.
        
        Returns:
            Import results.
        
        Raises:
            ConflictError: If simulation is running.
            FileNotFoundError: If the file doesn't exist.
            json.JSONDecodeError: If the file is not valid JSON.
            ValidationError: If the scenario data is invalid.
            APIError: If the import fails.
        
        Example:
            result = client.scenario.load_from_file(
                "fixtures/test-scenario.ues-scenario.json"
            )
            print(f"Loaded scenario by {result.scenario_metadata.author}")
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Handle both wrapped and unwrapped formats
        # (export_full returns {"scenario": {...}}, but file might just have the scenario)
        if "scenario" in data:
            scenario = data["scenario"]
        else:
            scenario = data
        
        return self.import_full(scenario=scenario, strict_modalities=strict_modalities)


# Asynchronous AsyncScenarioClient


class AsyncScenarioClient(AsyncBaseClient):
    """Asynchronous client for scenario import/export endpoints (/scenario/*).
    
    Provides async methods for saving and loading simulation state.
    
    Example:
        async with AsyncUESClient() as client:
            scenario = await client.scenario.export_full(author="Developer")
            await client.scenario.save_to_file("backup.ues-scenario.json")
    """
    
    _BASE_PATH = "/scenario"
    
    async def export_environment(self) -> ExportEnvironmentResponse:
        """Export current environment state as JSON.
        
        Creates a serialized snapshot of the current environment state,
        including simulator time and all modality states.
        
        Returns:
            Export response with environment data and list of exported modalities.
        
        Raises:
            APIError: If the export fails.
        """
        data = await self._get(f"{self._BASE_PATH}/export/environment")
        return ExportEnvironmentResponse(**data)
    
    async def export_events(self) -> ExportEventsResponse:
        """Export current event queue as JSON.
        
        Creates a serialized snapshot of the current event queue,
        including pending, executed, and failed events.
        
        Returns:
            Export response with event data and statistics.
        
        Raises:
            APIError: If the export fails.
        """
        data = await self._get(f"{self._BASE_PATH}/export/events")
        return ExportEventsResponse(**data)
    
    async def export_full(
        self,
        author: str | None = None,
        description: str | None = None,
    ) -> ExportScenarioResponse:
        """Export complete scenario with metadata.
        
        Creates a complete scenario snapshot including:
        - Metadata (UES version, creation timestamp, author, description)
        - Environment state (time + all modalities)
        - Event queue (all events)
        
        Args:
            author: Optional author name for scenario metadata.
            description: Optional description for scenario metadata.
        
        Returns:
            Complete exported scenario.
        
        Raises:
            APIError: If the export fails.
        """
        params: dict[str, Any] = {}
        if author is not None:
            params["author"] = author
        if description is not None:
            params["description"] = description
        
        data = await self._get(
            f"{self._BASE_PATH}/export/full",
            params=params if params else None,
        )
        return ExportScenarioResponse(**data)
    
    async def import_environment(
        self,
        data: dict[str, Any],
        historic_event_handling: Literal["ignore", "delete", "apply"] = "ignore",
        strict_modalities: bool = False,
    ) -> LoadEnvironmentResponse:
        """Import environment state from JSON.
        
        Replaces the current environment state with the provided data.
        The simulation must be stopped before importing.
        
        Args:
            data: Environment data dict.
            historic_event_handling: How to handle events scheduled before new time.
            strict_modalities: If True, fail on unknown modality types.
        
        Returns:
            Import results including loaded/skipped modalities and warnings.
        
        Raises:
            ConflictError: If simulation is running.
            ValidationError: If data is invalid.
            APIError: If the import fails.
        """
        request_data = {
            "data": data,
            "historic_event_handling": historic_event_handling,
            "strict_modalities": strict_modalities,
        }
        
        response = await self._post(f"{self._BASE_PATH}/import/environment", json=request_data)
        return LoadEnvironmentResponse(**response)
    
    async def import_events(
        self,
        data: dict[str, Any],
        merge: bool = False,
    ) -> LoadEventsResponse:
        """Import event queue from JSON.
        
        Replaces or merges the current event queue with the provided data.
        The simulation must be stopped before importing.
        
        Args:
            data: Event queue data dict (must have "events" list).
            merge: If True, add to existing queue; if False, replace entirely.
        
        Returns:
            Import results including event counts and merge status.
        
        Raises:
            ConflictError: If simulation is running.
            ValidationError: If data is invalid.
            APIError: If the import fails.
        """
        request_data = {
            "data": data,
            "merge": merge,
        }
        
        response = await self._post(f"{self._BASE_PATH}/import/events", json=request_data)
        return LoadEventsResponse(**response)
    
    async def import_full(
        self,
        scenario: dict[str, Any],
        strict_modalities: bool = False,
    ) -> LoadScenarioResponse:
        """Import complete scenario (environment + events).
        
        Replaces both the environment and event queue with the provided
        scenario data. The simulation must be stopped before importing.
        
        Args:
            scenario: Complete scenario dict.
            strict_modalities: If True, fail on unknown modality types.
        
        Returns:
            Comprehensive import results.
        
        Raises:
            ConflictError: If simulation is running.
            ValidationError: If scenario is invalid.
            APIError: If the import fails.
        """
        request_data = {
            "scenario": scenario,
            "strict_modalities": strict_modalities,
        }
        
        response = await self._post(f"{self._BASE_PATH}/import/full", json=request_data)
        return LoadScenarioResponse(**response)
    
    # Convenience file I/O methods
    
    async def save_to_file(
        self,
        filepath: str,
        author: str | None = None,
        description: str | None = None,
    ) -> None:
        """Export scenario and save to a file.
        
        Convenience method that exports the complete scenario and writes
        it to the specified file path as JSON.
        
        Note: File I/O is synchronous but the export API call is async.
        
        Args:
            filepath: Path to save the scenario file.
            author: Optional author name for metadata.
            description: Optional description for metadata.
        
        Raises:
            APIError: If the export fails.
            IOError: If the file cannot be written.
        """
        scenario = await self.export_full(author=author, description=description)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(
                scenario.model_dump(mode="json"),
                f,
                indent=2,
                ensure_ascii=False,
            )
    
    async def load_from_file(
        self,
        filepath: str,
        strict_modalities: bool = False,
    ) -> LoadScenarioResponse:
        """Load scenario from a file.
        
        Convenience method that reads a scenario file and imports it.
        
        Note: File I/O is synchronous but the import API call is async.
        
        Args:
            filepath: Path to the scenario file.
            strict_modalities: If True, fail on unknown modality types.
        
        Returns:
            Import results.
        
        Raises:
            ConflictError: If simulation is running.
            FileNotFoundError: If the file doesn't exist.
            json.JSONDecodeError: If the file is not valid JSON.
            ValidationError: If the scenario data is invalid.
            APIError: If the import fails.
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Handle both wrapped and unwrapped formats
        if "scenario" in data:
            scenario = data["scenario"]
        else:
            scenario = data
        
        return await self.import_full(scenario=scenario, strict_modalities=strict_modalities)
