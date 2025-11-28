"""Weather modality endpoints.

Provides REST API access to weather state and operations.
Supports querying weather data for multiple locations with optional filtering
and unit conversion. Also supports real-time weather queries via OpenWeather API.
"""

from typing import Any, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import SimulationEngineDep
from api.models import ModalityActionResponse
from api.utils import create_immediate_event
from models.modalities.weather_input import WeatherInput, WeatherReport
from models.modalities.weather_state import WeatherState

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
        real: If True, query OpenWeather API instead of simulated data.
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
    real: bool = Field(
        default=False, description="Query OpenWeather API for real weather data"
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


@router.get("/state", response_model=WeatherStateResponse)
async def get_weather_state(engine: SimulationEngineDep):
    """Get current weather state for all tracked locations.

    Returns a complete snapshot of the weather state including all tracked
    locations and their current weather conditions.

    Returns:
        WeatherStateResponse: Complete weather state with all locations.
    """
    weather_state = engine.environment.get_state("weather")

    if not isinstance(weather_state, WeatherState):
        raise HTTPException(
            status_code=500,
            detail="Weather state not properly initialized",
        )

    snapshot = weather_state.get_snapshot()
    return WeatherStateResponse(**snapshot)


@router.post("/query", response_model=WeatherQueryResponse)
async def query_weather(request: WeatherQueryRequest, engine: SimulationEngineDep):
    """Query weather data for a specific location with filters.

    Supports querying simulated weather history or real-time weather from
    OpenWeather API. Can filter by time range, exclude sections, and convert units.

    Args:
        request: Query parameters including location, filters, and options.
        engine: The simulation engine dependency.

    Returns:
        WeatherQueryResponse: Matching weather reports with pagination info.

    Raises:
        HTTPException: If query parameters are invalid or query fails.
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
async def update_weather(request: UpdateWeatherRequest, engine: SimulationEngineDep):
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

        return ModalityActionResponse(
            event_id=event.event_id,
            scheduled_time=event.scheduled_time,
            status="executed",
            message=f"Weather updated for location ({request.latitude}, {request.longitude})",
            modality="weather",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid weather data: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update weather: {str(e)}",
        )
