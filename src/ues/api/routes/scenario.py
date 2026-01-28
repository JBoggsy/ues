"""API routes for scenario save/load functionality.

These endpoints allow exporting and importing simulation state,
enabling scenarios to be saved to files and restored later.

Export endpoints return JSON representations of:
- Environment state only
- Event queue only
- Complete scenario (environment + events + metadata)

Import endpoints accept JSON data and load it into the simulation:
- Environment import with options for handling historic events
- Event import with merge/replace options
- Complete scenario import

All endpoints require authentication via X-API-Key header.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from ues.api.auth import Permissions, require_permission
from ues.api.dependencies import SimulationEngineDep
from ues.api.models import (
    ExportedEnvironmentData,
    ExportedEventQueueData,
    ExportedScenarioData,
    ExportedTimeState,
    ExportEnvironmentResponse,
    ExportEventsResponse,
    ExportScenarioResponse,
    LoadedScenarioMetadata,
    LoadEnvironmentRequest,
    LoadEnvironmentResponse,
    LoadEventsRequest,
    LoadEventsResponse,
    LoadScenarioRequest,
    LoadScenarioResponse,
    ScenarioMetadataModel,
)
from ues.models.api_key import APIKey
from ues.models.event import EventStatus
from ues.models.scenario import Scenario

# Create router for scenario endpoints
router = APIRouter(
    prefix="/scenario",
    tags=["scenario"],
)


# ===== Export Endpoints =====


@router.get("/export/environment", response_model=ExportEnvironmentResponse)
async def export_environment(
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.SCENARIO_EXPORT))],
) -> ExportEnvironmentResponse:
    """Export current environment state as JSON.

    Creates a serialized snapshot of the current environment state,
    including simulator time and all modality states. The exported
    data can later be imported using POST /scenario/import/environment.

    Args:
        engine: The SimulationEngine instance (injected by FastAPI).

    Returns:
        ExportEnvironmentResponse with environment data and summary.

    Requires:
        Permission: scenario:export

    Example response:
        {
            "environment": {
                "time_state": {...},
                "modality_states": {
                    "weather": {...},
                    "email": {...},
                    ...
                }
            },
            "modalities_exported": ["weather", "email", "sms", "chat", ...]
        }
    """
    # Get exported data from engine
    env_data = engine.export_environment()

    # Extract modality list
    modality_list = list(env_data.get("modality_states", {}).keys())

    # Build typed response
    return ExportEnvironmentResponse(
        environment=ExportedEnvironmentData(
            time_state=ExportedTimeState(**env_data["time_state"]),
            modality_states=env_data["modality_states"],
        ),
        modalities_exported=modality_list,
    )


@router.get("/export/events", response_model=ExportEventsResponse)
async def export_events(
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.SCENARIO_EXPORT))],
) -> ExportEventsResponse:
    """Export current event queue as JSON.

    Creates a serialized snapshot of the current event queue,
    including pending, executed, and failed events. The exported
    data can later be imported using POST /scenario/import/events.

    Args:
        engine: The SimulationEngine instance (injected by FastAPI).

    Returns:
        ExportEventsResponse with event queue data and statistics.

    Requires:
        Permission: scenario:export

    Example response:
        {
            "events": {
                "events": [
                    {"event_id": "...", "scheduled_time": "...", ...},
                    ...
                ]
            },
            "total_events": 10,
            "pending_events": 5,
            "executed_events": 4
        }
    """
    # Get exported data from engine
    events_data = engine.export_event_queue()

    # Count events by status
    events_list = events_data.get("events", [])
    total = len(events_list)
    pending = sum(1 for e in events_list if e.get("status") == EventStatus.PENDING.value)
    executed = sum(1 for e in events_list if e.get("status") == EventStatus.EXECUTED.value)

    # Build typed response
    return ExportEventsResponse(
        events=ExportedEventQueueData(events=events_list),
        total_events=total,
        pending_events=pending,
        executed_events=executed,
    )


@router.get("/export/full", response_model=ExportScenarioResponse)
async def export_full_scenario(
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.SCENARIO_EXPORT))],
    author: str | None = None,
    description: str | None = None,
) -> ExportScenarioResponse:
    """Export complete scenario with metadata.

    Creates a complete scenario snapshot including:
    - Metadata (UES version, creation timestamp, author, description)
    - Environment state (time + all modalities)
    - Event queue (all events)

    The exported scenario can later be imported using
    POST /scenario/import/full.

    Args:
        engine: The SimulationEngine instance (injected by FastAPI).
        author: Optional author name for scenario metadata.
        description: Optional description for scenario metadata.

    Returns:
        ExportScenarioResponse with complete scenario.

    Requires:
        Permission: scenario:export

    Example response:
        {
            "scenario": {
                "metadata": {
                    "ues_version": "0.1.0",
                    "scenario_version": "1",
                    "created_at": "2025-01-01T00:00:00Z",
                    "author": "Developer",
                    "description": "Test scenario"
                },
                "environment": {...},
                "events": {...}
            }
        }
    """
    # Get scenario from engine
    scenario: Scenario = engine.export_scenario(author=author, description=description)

    # Convert to API response models
    return ExportScenarioResponse(
        scenario=ExportedScenarioData(
            metadata=ScenarioMetadataModel(
                ues_version=scenario.metadata.ues_version,
                scenario_version=scenario.metadata.scenario_version,
                created_at=scenario.metadata.created_at,
                author=scenario.metadata.author,
                description=scenario.metadata.description,
            ),
            environment=ExportedEnvironmentData(
                time_state=ExportedTimeState(**scenario.environment["time_state"]),
                modality_states=scenario.environment["modality_states"],
            ),
            events=ExportedEventQueueData(events=scenario.events["events"]),
        )
    )


# ===== Import Endpoints =====


@router.post("/import/environment", response_model=LoadEnvironmentResponse)
async def import_environment(
    request: LoadEnvironmentRequest,
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.SCENARIO_IMPORT))],
) -> LoadEnvironmentResponse:
    """Import environment state from JSON.

    Replaces the current environment state with the provided data.
    The simulation must be stopped before importing.

    Historic events (events scheduled before the new environment time)
    can be handled in different ways:
    - "ignore": Leave in queue (they will never execute)
    - "delete": Remove from queue
    - "apply": Execute immediately against loaded state

    The undo stack is cleared when loading an environment.

    Args:
        request: Import request with environment data and options.
        engine: The SimulationEngine instance (injected by FastAPI).

    Returns:
        LoadEnvironmentResponse with load results and warnings.

    Requires:
        Permission: scenario:import

    Raises:
        HTTPException 409: If simulation is running.
        HTTPException 400: If strict_modalities=True and unknown modality found.
        HTTPException 422: If request data is invalid.
    """
    try:
        # Convert typed request model back to dict for engine
        env_data = request.data.model_dump(mode="json")

        result = engine.load_environment(
            data=env_data,
            historic_event_handling=request.historic_event_handling,
            strict_modalities=request.strict_modalities,
        )

        return LoadEnvironmentResponse(
            success=result["success"],
            modalities_loaded=result["modalities_loaded"],
            modalities_skipped=result["modalities_skipped"],
            warnings=result["warnings"],
            historic_events_count=result["historic_events_count"],
            historic_events_action=result["historic_events_action"],
        )
    except RuntimeError as e:
        # Simulation is running
        raise HTTPException(
            status_code=409,
            detail=str(e),
        )
    except ValueError as e:
        # Validation error (e.g., unknown modality in strict mode)
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.post("/import/events", response_model=LoadEventsResponse)
async def import_events(
    request: LoadEventsRequest,
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.SCENARIO_IMPORT))],
) -> LoadEventsResponse:
    """Import event queue from JSON.

    Replaces or merges the current event queue with the provided data.
    The simulation must be stopped before importing.

    When merge=True, loaded events are added to the existing queue.
    When merge=False (default), the entire queue is replaced.

    The undo stack is cleared when replacing (not when merging).

    Args:
        request: Import request with event data and options.
        engine: The SimulationEngine instance (injected by FastAPI).

    Returns:
        LoadEventsResponse with load results.

    Requires:
        Permission: scenario:import

    Raises:
        HTTPException 409: If simulation is running.
        HTTPException 422: If request data is invalid.
    """
    try:
        # Convert typed request model back to dict for engine
        events_data = request.data.model_dump(mode="json")

        result = engine.load_event_queue(
            data=events_data,
            merge=request.merge,
        )

        return LoadEventsResponse(
            success=result["success"],
            events_loaded=result["events_loaded"],
            events_merged=result["events_merged"],
            previous_events=result["previous_events"],
            historic_events_warning=result["historic_events_warning"],
            historic_event_count=result["historic_event_count"],
        )
    except RuntimeError as e:
        # Simulation is running
        raise HTTPException(
            status_code=409,
            detail=str(e),
        )
    except ValueError as e:
        # Validation error
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.post("/import/full", response_model=LoadScenarioResponse)
async def import_full_scenario(
    request: LoadScenarioRequest,
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.SCENARIO_IMPORT))],
) -> LoadScenarioResponse:
    """Import complete scenario (environment + events).

    Replaces both the environment and event queue with the provided
    scenario data. The simulation must be stopped before importing.

    The undo stack is always cleared when loading a scenario.

    Args:
        request: Import request with scenario data and options.
        engine: The SimulationEngine instance (injected by FastAPI).

    Returns:
        LoadScenarioResponse with comprehensive load results.

    Requires:
        Permission: scenario:import

    Raises:
        HTTPException 409: If simulation is running.
        HTTPException 400: If strict_modalities=True and unknown modality found.
        HTTPException 422: If request data is invalid.
    """
    try:
        # Convert typed request model to Scenario object
        scenario_data = request.scenario.model_dump(mode="json")

        # Create Scenario from dict (handles metadata, environment, events)
        scenario = Scenario.from_dict(scenario_data)

        result = engine.load_scenario(
            scenario=scenario,
            strict_modalities=request.strict_modalities,
        )

        # Build metadata summary for response
        metadata = LoadedScenarioMetadata(
            ues_version=result["scenario_metadata"]["ues_version"],
            scenario_version=result["scenario_metadata"]["scenario_version"],
            created_at=result["scenario_metadata"]["created_at"],
            author=result["scenario_metadata"].get("author"),
            description=result["scenario_metadata"].get("description"),
        )

        return LoadScenarioResponse(
            success=result["success"],
            environment_loaded=result["environment_loaded"],
            events_loaded=result["events_loaded"],
            modalities_loaded=result["modalities_loaded"],
            modalities_skipped=result["modalities_skipped"],
            warnings=result["warnings"],
            scenario_metadata=metadata,
        )
    except RuntimeError as e:
        # Simulation is running
        raise HTTPException(
            status_code=409,
            detail=str(e),
        )
    except ValueError as e:
        # Validation error (e.g., unknown modality in strict mode)
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
