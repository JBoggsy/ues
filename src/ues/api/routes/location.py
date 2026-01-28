"""Location modality endpoints.

Provides REST API access to user location state and operations.
Supports updating location coordinates and querying location history.
"""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationError

from ues.api.broadcast import broadcast_event
from ues.api.dependencies import SimulationEngineDep
from ues.api.models import ModalityActionResponse
from ues.api.utils import create_immediate_event
from ues.api.websocket import WSEventType
from ues.models.modalities.location_input import LocationInput
from ues.models.modalities.location_state import LocationState

router = APIRouter(
    prefix="/location",
    tags=["location"],
)


# Request Models


class UpdateLocationRequest(BaseModel):
    """Request to update the user's current location with coordinates.

    Args:
        latitude: Latitude coordinate in decimal degrees (-90 to 90).
        longitude: Longitude coordinate in decimal degrees (-180 to 180).
        address: Optional human-readable address or location description.
        named_location: Optional semantic name (e.g., "Home", "Office", "Gym").
        altitude: Optional altitude in meters above sea level.
        accuracy: Optional accuracy radius in meters.
        speed: Optional speed in meters per second.
        bearing: Optional bearing/heading in degrees (0-360, 0=North).
    """

    latitude: float = Field(description="Latitude coordinate (-90 to 90)")
    longitude: float = Field(description="Longitude coordinate (-180 to 180)")
    address: Optional[str] = Field(default=None, description="Human-readable address")
    named_location: Optional[str] = Field(
        default=None, description="Semantic location name"
    )
    altitude: Optional[float] = Field(
        default=None, description="Altitude in meters above sea level"
    )
    accuracy: Optional[float] = Field(
        default=None, description="Accuracy radius in meters"
    )
    speed: Optional[float] = Field(
        default=None, description="Speed in meters per second"
    )
    bearing: Optional[float] = Field(
        default=None, description="Bearing/heading in degrees (0-360)"
    )


class LocationQueryRequest(BaseModel):
    """Request to query location history.

    Args:
        since: Optional start time filter (ISO format datetime).
        until: Optional end time filter (ISO format datetime).
        named_location: Optional filter by semantic location name.
        limit: Optional maximum number of results to return.
        offset: Optional number of results to skip for pagination.
        include_current: Whether to include current location (default: True).
        sort_by: Field to sort by ("timestamp", "latitude", "longitude").
        sort_order: Sort order ("asc" or "desc").
    """

    since: Optional[datetime] = Field(
        default=None, description="Return locations after this time"
    )
    until: Optional[datetime] = Field(
        default=None, description="Return locations before this time"
    )
    named_location: Optional[str] = Field(
        default=None, description="Filter by semantic location name"
    )
    limit: Optional[int] = Field(
        default=None, description="Maximum number of results", ge=1
    )
    offset: Optional[int] = Field(default=0, description="Results to skip", ge=0)
    include_current: bool = Field(
        default=True, description="Include current location in results"
    )
    sort_by: str = Field(
        default="timestamp", description="Field to sort by"
    )
    sort_order: str = Field(
        default="desc", description="Sort order (asc or desc)"
    )


# Response Models


class LocationStateResponse(BaseModel):
    """Response containing current location state.

    Args:
        modality_type: Always "location".
        last_updated: ISO format timestamp of last update.
        update_count: Number of location updates.
        current: Current location data.
        history: List of recent location history entries.
    """

    modality_type: str = Field(description="Modality type identifier")
    last_updated: str = Field(description="ISO format timestamp of last update")
    update_count: int = Field(description="Number of location updates")
    current: dict[str, Any] = Field(description="Current location data")
    history: list[dict[str, Any]] = Field(description="Recent location history")


class LocationCompactStateResponse(BaseModel):
    """Compact response containing current location state without history.

    Used when compact=true query parameter is set. Optimized for LLM context.

    Args:
        modality_type: Always "location".
        last_updated: ISO format timestamp of last update.
        update_count: Number of location updates.
        current: Current location data.
        history_count: Number of entries in location history (not included).
    """

    modality_type: str = Field(description="Modality type identifier")
    last_updated: str = Field(description="ISO format timestamp of last update")
    update_count: int = Field(description="Number of location updates")
    current: dict[str, Any] = Field(description="Current location data")
    history_count: int = Field(description="Number of history entries (history not included)")


class LocationQueryResponse(BaseModel):
    """Response containing location query results.

    Args:
        locations: List of location entries matching the query.
        count: Number of locations returned (after pagination).
        total_count: Total matching locations (before pagination).
    """

    locations: list[dict[str, Any]] = Field(description="Matching location entries")
    count: int = Field(description="Number of locations returned")
    total_count: int = Field(description="Total matching locations")


# Route Handlers


@router.get("/state")
async def get_location_state(
    engine: SimulationEngineDep,
    compact: bool = False,
) -> LocationStateResponse | LocationCompactStateResponse:
    """Get current location state.

    Returns a snapshot of the user's current location and optionally
    location history.

    Args:
        engine: The simulation engine dependency.
        compact: If True, return compact state without history.
            Optimized for LLM context and quick status checks.

    Returns:
        LocationStateResponse: Full state including history (default).
        LocationCompactStateResponse: Compact state without history (if compact=True).
    """
    location_state = engine.environment.get_state("location")

    if not isinstance(location_state, LocationState):
        raise HTTPException(
            status_code=500,
            detail="Location state not properly initialized",
        )

    # Return compact snapshot if requested
    if compact:
        snapshot = location_state.get_snapshot()
        return LocationCompactStateResponse(**snapshot)

    # Use model_dump for complete state (includes history)
    state_data = location_state.model_dump(mode="json")
    
    # Transform to response format expected by LocationStateResponse
    return LocationStateResponse(
        modality_type=state_data["modality_type"],
        last_updated=state_data["last_updated"],
        update_count=state_data["update_count"],
        current={
            "latitude": state_data["current_latitude"],
            "longitude": state_data["current_longitude"],
            "address": state_data.get("current_address"),
            "named_location": state_data.get("current_named_location"),
            "altitude": state_data.get("current_altitude"),
            "accuracy": state_data.get("current_accuracy"),
            "speed": state_data.get("current_speed"),
            "bearing": state_data.get("current_bearing"),
        },
        history=state_data["location_history"],
    )


@router.post("/query", response_model=LocationQueryResponse)
async def query_location_history(
    request: LocationQueryRequest, engine: SimulationEngineDep
):
    """Query location history with filters.

    Allows filtering and searching through the user's location history
    based on time range, semantic location names, and other criteria.

    Args:
        request: Query parameters including filters and pagination options.
        engine: The simulation engine dependency.

    Returns:
        LocationQueryResponse: Matching location entries with pagination info.
    """
    location_state = engine.environment.get_state("location")

    if not isinstance(location_state, LocationState):
        raise HTTPException(
            status_code=500,
            detail="Location state not properly initialized",
        )

    query_params = request.model_dump(exclude_unset=True)
    result = location_state.query(query_params)

    return LocationQueryResponse(**result)


@router.post("/update", response_model=ModalityActionResponse)
async def update_location(request: UpdateLocationRequest, engine: SimulationEngineDep):
    """Update the user's current location.

    Creates an immediate event that updates the user's location with the
    provided coordinates and optional metadata. The previous location is
    automatically added to the location history.

    Args:
        request: Location update data including coordinates and metadata.
        engine: The simulation engine dependency.

    Returns:
        ModalityActionResponse: Confirmation of the location update with event ID.

    Raises:
        HTTPException: If the location update fails validation or execution.
    """
    try:
        # Convert request to LocationInput
        location_input = LocationInput(
            timestamp=engine.environment.time_state.current_time,
            latitude=request.latitude,
            longitude=request.longitude,
            address=request.address,
            named_location=request.named_location,
            altitude=request.altitude,
            accuracy=request.accuracy,
            speed=request.speed,
            bearing=request.bearing,
        )

        event = create_immediate_event(
            engine=engine,
            modality="location",
            data=location_input,
            priority=100,
        )

        # Broadcast location updated event
        await broadcast_event(WSEventType.LOCATION_UPDATED, {
            "latitude": request.latitude,
            "longitude": request.longitude,
            "address": request.address,
        })

        return ModalityActionResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            status="executed",
            message=f"Location updated to ({request.latitude}, {request.longitude})",
            modality="location",
        )
    except ValidationError as e:
        # Pydantic validation failed (e.g., lat/lon out of range)
        raise HTTPException(
            status_code=422,
            detail=f"Invalid location data: {str(e)}",
        )
    except ValueError as e:
        # Business logic error (after validation passes)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid location data: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update location: {str(e)}",
        )
