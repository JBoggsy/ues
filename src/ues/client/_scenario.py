"""Scenario save/load sub-client for the UES API.

This module provides ScenarioClient and AsyncScenarioClient for interacting
with the scenario import/export endpoints (/scenario/*).

This is an internal module. Import from `client` instead.
"""

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from ues.client._base import AsyncBaseClient, BaseClient

if TYPE_CHECKING:
    from ues.client._http import AsyncHTTPClient, HTTPClient


# =============================================================================
# Response Models
# =============================================================================


class ExportedTimeState(BaseModel):
    """Serialized SimulatorTime state.
    
    Attributes:
        current_time: Current simulator time (ISO format).
        time_scale: Time multiplier for auto-advance.
        is_paused: Whether simulation is paused.
        auto_advance: Whether auto-advance is enabled.
        last_wall_time_update: Last wall-clock update time (ISO format).
    """

    current_time: str
    time_scale: float
    is_paused: bool
    auto_advance: bool
    last_wall_time_update: str


class ExportedEnvironmentData(BaseModel):
    """Structure of exported environment data.
    
    Attributes:
        time_state: Serialized SimulatorTime state.
        modality_states: Dict mapping modality_type to serialized state data.
    """

    time_state: ExportedTimeState
    modality_states: dict[str, dict[str, Any]]


class ExportedEventQueueData(BaseModel):
    """Structure of exported event queue data.
    
    Attributes:
        events: List of serialized SimulatorEvent dictionaries.
    """

    events: list[dict[str, Any]]


class ScenarioMetadata(BaseModel):
    """Metadata for a saved scenario.
    
    Attributes:
        ues_version: UES version that created this scenario.
        scenario_version: Schema version for file format.
        created_at: When scenario was created (ISO format).
        author: Author name or identifier.
        description: Human-readable description.
    """

    ues_version: str
    scenario_version: str
    created_at: str
    author: str | None = None
    description: str | None = None


class ExportedScenarioData(BaseModel):
    """Complete scenario structure for export.
    
    Attributes:
        metadata: Scenario metadata.
        environment: Serialized environment.
        events: Serialized event queue.
    """

    metadata: ScenarioMetadata
    environment: ExportedEnvironmentData
    events: ExportedEventQueueData


# --- Export Response Models ---


class ExportEnvironmentResponse(BaseModel):
    """Response for environment export endpoint.
    
    Attributes:
        environment: Serialized environment data.
        modalities_exported: List of modality types included in export.
    """

    environment: ExportedEnvironmentData
    modalities_exported: list[str]


class ExportEventsResponse(BaseModel):
    """Response for event queue export endpoint.
    
    Attributes:
        events: Serialized event queue data.
        total_events: Total number of events exported.
        pending_events: Number of pending events.
        executed_events: Number of executed events.
    """

    events: ExportedEventQueueData
    total_events: int
    pending_events: int
    executed_events: int


class ExportScenarioResponse(BaseModel):
    """Response for full scenario export endpoint.
    
    Attributes:
        scenario: Complete serialized scenario with metadata.
    """

    scenario: ExportedScenarioData


# --- Import Response Models ---


class LoadEnvironmentResponse(BaseModel):
    """Response for environment import endpoint.
    
    Attributes:
        success: Whether the load operation succeeded.
        modalities_loaded: List of modality types that were successfully loaded.
        modalities_skipped: List of modality types that were skipped (unknown types).
        warnings: Warning messages about the load operation.
        historic_events_count: Number of existing events scheduled before loaded environment time.
        historic_events_action: How historic events were handled ('ignore', 'delete', or 'apply').
    """

    success: bool
    modalities_loaded: list[str]
    modalities_skipped: list[str]
    warnings: list[str]
    historic_events_count: int
    historic_events_action: str


class LoadEventsResponse(BaseModel):
    """Response for event queue import endpoint.
    
    Attributes:
        success: Whether the load operation succeeded.
        events_loaded: Total number of events in the loaded data.
        events_merged: Number of events actually added (when merge=True).
        previous_events: Number of events in queue before load.
        historic_events_warning: True if any loaded events are scheduled before current time.
        historic_event_count: Number of events scheduled before current simulator time.
    """

    success: bool
    events_loaded: int
    events_merged: int
    previous_events: int
    historic_events_warning: bool
    historic_event_count: int


class LoadedScenarioMetadata(BaseModel):
    """Summary of loaded scenario metadata.
    
    Attributes:
        ues_version: UES version from loaded scenario.
        scenario_version: Schema version from loaded scenario.
        created_at: When scenario was created (ISO format).
        author: Author from loaded scenario.
        description: Description from loaded scenario.
    """

    ues_version: str
    scenario_version: str
    created_at: str
    author: str | None = None
    description: str | None = None


class LoadScenarioResponse(BaseModel):
    """Response for full scenario import endpoint.
    
    Attributes:
        success: Whether the load operation succeeded.
        environment_loaded: Whether environment was successfully loaded.
        events_loaded: Number of events loaded from scenario.
        modalities_loaded: List of modality types that were successfully loaded.
        modalities_skipped: List of modality types that were skipped (unknown types).
        warnings: Warning messages about the load operation.
        scenario_metadata: Metadata from the loaded scenario.
    """

    success: bool
    environment_loaded: bool
    events_loaded: int
    modalities_loaded: list[str]
    modalities_skipped: list[str]
    warnings: list[str]
    scenario_metadata: LoadedScenarioMetadata


# =============================================================================
# Synchronous ScenarioClient
# =============================================================================


class ScenarioClient(BaseClient):
    """Synchronous client for scenario save/load endpoints (/scenario/*).
    
    This client provides methods for exporting and importing simulation state:
    - Environment state (time + all modalities)
    - Event queue (scheduled/executed events)
    - Complete scenarios (environment + events + metadata)
    
    Example:
        with UESClient() as client:
            # Export current state
            scenario = client.scenario.export_full(
                author="Test Author",
                description="Test scenario",
            )
            
            # Save to file
            with open("scenario.json", "w") as f:
                json.dump(scenario.scenario.model_dump(), f)
            
            # Later, load it back
            with open("scenario.json") as f:
                data = json.load(f)
            result = client.scenario.import_full(data)
            print(f"Loaded {result.events_loaded} events")
    """

    _BASE_PATH = "/scenario"

    def export_environment(self) -> ExportEnvironmentResponse:
        """Export current environment state.
        
        Creates a serialized snapshot of the current environment state,
        including simulator time and all modality states.
        
        Returns:
            ExportEnvironmentResponse with environment data and modality list.
        
        Raises:
            APIError: If the request fails.
        """
        data = self._get(f"{self._BASE_PATH}/export/environment")
        return ExportEnvironmentResponse(**data)

    def export_events(self) -> ExportEventsResponse:
        """Export current event queue.
        
        Creates a serialized snapshot of the current event queue,
        including pending, executed, and failed events.
        
        Returns:
            ExportEventsResponse with event data and statistics.
        
        Raises:
            APIError: If the request fails.
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
            ExportScenarioResponse with complete scenario.
        
        Raises:
            APIError: If the request fails.
        """
        params = {}
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
        historic_event_handling: str = "ignore",
        strict_modalities: bool = False,
    ) -> LoadEnvironmentResponse:
        """Import environment state from exported data.
        
        Replaces the current environment state with the provided data.
        The simulation must be stopped before importing.
        
        Historic events (events scheduled before the new environment time)
        can be handled in different ways:
        - "ignore": Leave in queue (they will never execute)
        - "delete": Remove from queue
        - "apply": Execute immediately against loaded state
        
        Args:
            data: Environment data dict (from export_environment() or file).
            historic_event_handling: How to handle existing events scheduled
                before the loaded environment's time.
            strict_modalities: If True, raise error on unknown modality types.
        
        Returns:
            LoadEnvironmentResponse with load results.
        
        Raises:
            ConflictError: If simulation is running.
            ValidationError: If strict_modalities=True and unknown modality found.
            APIError: If the request fails.
        """
        response = self._post(
            f"{self._BASE_PATH}/import/environment",
            json={
                "data": data,
                "historic_event_handling": historic_event_handling,
                "strict_modalities": strict_modalities,
            },
        )
        return LoadEnvironmentResponse(**response)

    def import_events(
        self,
        data: dict[str, Any],
        merge: bool = False,
    ) -> LoadEventsResponse:
        """Import event queue from exported data.
        
        Replaces or merges the current event queue with the provided data.
        The simulation must be stopped before importing.
        
        Args:
            data: Event queue data dict (from export_events() or file).
            merge: If True, add loaded events to existing queue.
                If False (default), replace all events.
        
        Returns:
            LoadEventsResponse with load results.
        
        Raises:
            ConflictError: If simulation is running.
            APIError: If the request fails.
        """
        response = self._post(
            f"{self._BASE_PATH}/import/events",
            json={
                "data": data,
                "merge": merge,
            },
        )
        return LoadEventsResponse(**response)

    def import_full(
        self,
        scenario: dict[str, Any],
        strict_modalities: bool = False,
    ) -> LoadScenarioResponse:
        """Import complete scenario (environment + events).
        
        Replaces both the environment and event queue with the provided
        scenario data. The simulation must be stopped before importing.
        
        Args:
            scenario: Complete scenario data dict (from export_full() or file).
            strict_modalities: If True, raise error on unknown modality types.
        
        Returns:
            LoadScenarioResponse with comprehensive load results.
        
        Raises:
            ConflictError: If simulation is running.
            ValidationError: If strict_modalities=True and unknown modality found.
            APIError: If the request fails.
        """
        response = self._post(
            f"{self._BASE_PATH}/import/full",
            json={
                "scenario": scenario,
                "strict_modalities": strict_modalities,
            },
        )
        return LoadScenarioResponse(**response)


# =============================================================================
# Asynchronous AsyncScenarioClient
# =============================================================================


class AsyncScenarioClient(AsyncBaseClient):
    """Asynchronous client for scenario save/load endpoints (/scenario/*).
    
    This client provides async methods for exporting and importing simulation state:
    - Environment state (time + all modalities)
    - Event queue (scheduled/executed events)
    - Complete scenarios (environment + events + metadata)
    
    Example:
        async with AsyncUESClient() as client:
            # Export current state
            scenario = await client.scenario.export_full(
                author="Test Author",
                description="Test scenario",
            )
            
            # Save to file
            with open("scenario.json", "w") as f:
                json.dump(scenario.scenario.model_dump(), f)
            
            # Later, load it back
            with open("scenario.json") as f:
                data = json.load(f)
            result = await client.scenario.import_full(data)
            print(f"Loaded {result.events_loaded} events")
    """

    _BASE_PATH = "/scenario"

    async def export_environment(self) -> ExportEnvironmentResponse:
        """Export current environment state.
        
        Creates a serialized snapshot of the current environment state,
        including simulator time and all modality states.
        
        Returns:
            ExportEnvironmentResponse with environment data and modality list.
        
        Raises:
            APIError: If the request fails.
        """
        data = await self._get(f"{self._BASE_PATH}/export/environment")
        return ExportEnvironmentResponse(**data)

    async def export_events(self) -> ExportEventsResponse:
        """Export current event queue.
        
        Creates a serialized snapshot of the current event queue,
        including pending, executed, and failed events.
        
        Returns:
            ExportEventsResponse with event data and statistics.
        
        Raises:
            APIError: If the request fails.
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
            ExportScenarioResponse with complete scenario.
        
        Raises:
            APIError: If the request fails.
        """
        params = {}
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
        historic_event_handling: str = "ignore",
        strict_modalities: bool = False,
    ) -> LoadEnvironmentResponse:
        """Import environment state from exported data.
        
        Replaces the current environment state with the provided data.
        The simulation must be stopped before importing.
        
        Historic events (events scheduled before the new environment time)
        can be handled in different ways:
        - "ignore": Leave in queue (they will never execute)
        - "delete": Remove from queue
        - "apply": Execute immediately against loaded state
        
        Args:
            data: Environment data dict (from export_environment() or file).
            historic_event_handling: How to handle existing events scheduled
                before the loaded environment's time.
            strict_modalities: If True, raise error on unknown modality types.
        
        Returns:
            LoadEnvironmentResponse with load results.
        
        Raises:
            ConflictError: If simulation is running.
            ValidationError: If strict_modalities=True and unknown modality found.
            APIError: If the request fails.
        """
        response = await self._post(
            f"{self._BASE_PATH}/import/environment",
            json={
                "data": data,
                "historic_event_handling": historic_event_handling,
                "strict_modalities": strict_modalities,
            },
        )
        return LoadEnvironmentResponse(**response)

    async def import_events(
        self,
        data: dict[str, Any],
        merge: bool = False,
    ) -> LoadEventsResponse:
        """Import event queue from exported data.
        
        Replaces or merges the current event queue with the provided data.
        The simulation must be stopped before importing.
        
        Args:
            data: Event queue data dict (from export_events() or file).
            merge: If True, add loaded events to existing queue.
                If False (default), replace all events.
        
        Returns:
            LoadEventsResponse with load results.
        
        Raises:
            ConflictError: If simulation is running.
            APIError: If the request fails.
        """
        response = await self._post(
            f"{self._BASE_PATH}/import/events",
            json={
                "data": data,
                "merge": merge,
            },
        )
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
            scenario: Complete scenario data dict (from export_full() or file).
            strict_modalities: If True, raise error on unknown modality types.
        
        Returns:
            LoadScenarioResponse with comprehensive load results.
        
        Raises:
            ConflictError: If simulation is running.
            ValidationError: If strict_modalities=True and unknown modality found.
            APIError: If the request fails.
        """
        response = await self._post(
            f"{self._BASE_PATH}/import/full",
            json={
                "scenario": scenario,
                "strict_modalities": strict_modalities,
            },
        )
        return LoadScenarioResponse(**response)
