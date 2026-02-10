"""Weather modality endpoints.

Provides REST API access to weather state and operations.
Supports querying weather data for multiple locations with optional filtering
and unit conversion.

All endpoints require authentication via X-API-Key header.
"""

from typing import Annotated, Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError

from ues.api.auth import Permissions, require_permission
from ues.api.broadcast import broadcast_event
from ues.api.dependencies import SimulationEngineDep
from ues.api.models import ModalityActionResponse
from ues.api.utils import create_immediate_event
from ues.api.websocket import WSEventType
from ues.models.api_key import APIKey
from ues.models.modalities.weather_input import WeatherInput, WeatherReport
from ues.models.modalities.weather_state import WeatherState

router = APIRouter(
    prefix="/weather",
    tags=["weather"],
)


# Request Models


class UpdateWeatherRequest(BaseModel):
    """Request to update weather conditions for a location.

    Args:
        latitude: Location latitude in decimal degrees (-90 to 90).
        longitude: Location longitude in decimal degrees (-180 to 180).
        report: Complete weather report conforming to OpenWeather API format.
    """

    latitude: float = Field(description="Location latitude (-90 to 90)")
    longitude: float = Field(description="Location longitude (-180 to 180)")
    report: WeatherReport = Field(description="Complete weather report")


class WeatherQueryRequest(BaseModel):
    """Request to query weather data for a location.

    Args:
        lat: Location latitude to query (required).
        lon: Location longitude to query (required).
        exclude: List of sections to exclude (current, minutely, hourly, daily, alerts).
        units: Unit system (standard, metric, imperial) - default: standard.
        from_time: Unix timestamp - return all reports since this time.
        to_time: Unix timestamp - return reports up to this time (requires from_time).
        limit: Maximum number of reports to return.
        offset: Number of reports to skip (for pagination).
    """

    lat: float = Field(description="Location latitude to query")
    lon: float = Field(description="Location longitude to query")
    exclude: Optional[list[str]] = Field(
        default=None,
        description="Sections to exclude (current, minutely, hourly, daily, alerts)",
    )
    units: Literal["standard", "metric", "imperial"] = Field(
        default="standard", description="Unit system"
    )
    from_time: Optional[int] = Field(
        default=None, description="Return reports since this Unix timestamp"
    )
    to_time: Optional[int] = Field(
        default=None, description="Return reports up to this Unix timestamp"
    )
    limit: Optional[int] = Field(default=None, description="Maximum reports to return", ge=1)
    offset: Optional[int] = Field(default=0, description="Reports to skip", ge=0)


# Response Models


class WeatherStateResponse(BaseModel):
    """Response containing complete weather state.

    Args:
        modality_type: Always "weather".
        last_updated: ISO format timestamp of last update.
        update_count: Number of weather updates.
        locations: Dict mapping location keys to weather data.
        location_count: Number of tracked locations.
    """

    modality_type: str = Field(description="Modality type identifier")
    last_updated: str = Field(description="ISO format timestamp of last update")
    update_count: int = Field(description="Number of weather updates")
    locations: dict[str, Any] = Field(description="Weather data for tracked locations")
    location_count: int = Field(description="Number of tracked locations")


class WeatherCompactStateResponse(BaseModel):
    """Compact response containing weather state without full history.

    Used when compact=true query parameter is set. Optimized for LLM context.

    Args:
        modality_type: Always "weather".
        last_updated: ISO format timestamp of last update.
        update_count: Number of weather updates.
        location_count: Number of tracked locations.
        locations: Dict with current weather per location (no history).
    """

    modality_type: str = Field(description="Modality type identifier")
    last_updated: str = Field(description="ISO format timestamp of last update")
    update_count: int = Field(description="Number of weather updates")
    location_count: int = Field(description="Number of tracked locations")
    locations: dict[str, Any] = Field(description="Current weather per location (no history)")


class WeatherQueryResponse(BaseModel):
    """Response containing weather query results.

    Args:
        reports: List of WeatherReport objects matching the query.
        count: Number of reports returned (after pagination).
        total_count: Total matching reports (before pagination).
        error: Optional error message if no data available.
    """

    reports: list[WeatherReport] = Field(description="Matching weather reports")
    count: int = Field(description="Number of reports returned")
    total_count: int = Field(default=0, description="Total matching reports")
    error: Optional[str] = Field(default=None, description="Error message if applicable")


# Route Handlers


@router.get("/state")
async def get_weather_state(
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.WEATHER_STATE))],
    compact: bool = False,
) -> WeatherStateResponse | WeatherCompactStateResponse:
    """Get current weather state for all tracked locations.

    Returns a snapshot of the weather state including all tracked
    locations and their current weather conditions.

    Args:
        engine: The simulation engine dependency.
        compact: If True, return compact state without full history.
            Optimized for LLM context and quick status checks.

    Returns:
        WeatherStateResponse: Full state including history (default).
        WeatherCompactStateResponse: Compact state without history (if compact=True).
    
    Requires:
        Permission: weather:state
    """
    weather_state = engine.environment.get_state("weather")

    if not isinstance(weather_state, WeatherState):
        raise HTTPException(
            status_code=500,
            detail="Weather state not properly initialized",
        )

    # Return compact snapshot if requested
    if compact:
        snapshot = weather_state.get_snapshot()
        return WeatherCompactStateResponse(**snapshot)

    # Use model_dump for complete state (includes history)
    state_data = weather_state.model_dump(mode="json")
    return WeatherStateResponse(
        modality_type=state_data["modality_type"],
        last_updated=state_data["last_updated"],
        update_count=state_data["update_count"],
        locations=state_data["locations"],
        location_count=len(state_data["locations"]),
    )


@router.post("/query", response_model=WeatherQueryResponse)
async def query_weather(
    request: WeatherQueryRequest,
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.WEATHER_QUERY))],
):
    """Query weather data for a specific location with filters.

    Supports querying simulated weather history with filtering by time range,
    excluded sections, and unit conversion.

    Args:
        request: Query parameters including location, filters, and options.
        engine: The simulation engine dependency.

    Returns:
        WeatherQueryResponse: Matching weather reports with pagination info.

    Raises:
        HTTPException: If query parameters are invalid or query fails.
    
    Requires:
        Permission: weather:query
    """
    weather_state = engine.environment.get_state("weather")

    if not isinstance(weather_state, WeatherState):
        raise HTTPException(
            status_code=500,
            detail="Weather state not properly initialized",
        )

    try:
        query_params = request.model_dump(exclude_unset=True)
        result = weather_state.query(query_params)

        # Convert dict reports to WeatherReport objects
        reports = []
        for report_dict in result.get("reports", []):
            reports.append(WeatherReport(**report_dict))

        return WeatherQueryResponse(
            reports=reports,
            count=result.get("count", 0),
            total_count=result.get("total_count", result.get("count", 0)),
            error=result.get("error"),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid query parameters: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query weather: {str(e)}",
        )


@router.post("/update", response_model=ModalityActionResponse)
async def update_weather(
    request: UpdateWeatherRequest,
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.WEATHER_UPDATE))],
):
    """Update weather conditions for a location.

    Creates an immediate event that updates the weather for the specified
    location. The weather report should conform to OpenWeather API format.

    Args:
        request: Weather update data including location and complete report.
        engine: The simulation engine dependency.

    Returns:
        ModalityActionResponse: Confirmation of the weather update with event ID.

    Raises:
        HTTPException: If the weather update fails validation or execution.
    
    Requires:
        Permission: weather:update
    """
    try:
        # Convert request to WeatherInput
        weather_input = WeatherInput(
            timestamp=engine.environment.time_state.current_time,
            latitude=request.latitude,
            longitude=request.longitude,
            report=request.report,
        )

        event = create_immediate_event(
            engine=engine,
            modality="weather",
            data=weather_input,
            priority=100,
        )

        # Broadcast weather update via WebSocket
        await broadcast_event(
            WSEventType.WEATHER_UPDATED,
            {
                "latitude": request.latitude,
                "longitude": request.longitude,
                "event_id": event.event_id,
            },
        )

        return ModalityActionResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            status=event.status.value,
            message=(
                f"Weather updated for location ({request.latitude}, {request.longitude})"
                if not event.error_message
                else f"Failed to update weather: {event.error_message}"
            ),
            modality="weather",
        )
    except ValidationError as e:
        # Pydantic validation failed (e.g., lat/lon out of range)
        raise HTTPException(
            status_code=422,
            detail=f"Invalid weather data: {str(e)}",
        )
    except ValueError as e:
        # Business logic error (after validation passes)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid weather data: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update weather: {str(e)}",
        )
