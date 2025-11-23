"""Weather modality endpoints.

These endpoints allow clients to query and update the simulated weather conditions.
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import SimulationEngineDep
from models.modalities.weather_input import WeatherInput
from models.event import SimulatorEvent

# Create router for weather-related endpoints
router = APIRouter(
    prefix="/weather",
    tags=["weather"],
)


# Response Models


class CurrentWeatherResponse(BaseModel):
    """Current weather conditions.
    
    Attributes:
        location_name: Human-readable location name.
        latitude: Location latitude.
        longitude: Location longitude.
        current_conditions: Dictionary of current weather data.
        forecast: List of forecasted conditions (if available).
        last_updated: When the weather was last updated (simulator time).
    """

    location_name: str
    latitude: float
    longitude: float
    current_conditions: dict
    forecast: list[dict] = Field(default_factory=list)
    last_updated: str | None = None


# Request Models


class UpdateWeatherRequest(BaseModel):
    """Request to update weather conditions.
    
    Attributes:
        temperature: Temperature in Fahrenheit.
        conditions: Weather conditions description (e.g., "Sunny", "Rainy").
        humidity: Humidity percentage (0-100).
        wind_speed: Wind speed in mph.
        wind_direction: Wind direction (e.g., "N", "NE", "SW").
    """

    temperature: float = Field(..., ge=-100, le=150, description="Temperature in °F")
    conditions: str
    humidity: int = Field(..., ge=0, le=100, description="Humidity percentage")
    wind_speed: float = Field(..., ge=0, description="Wind speed in mph")
    wind_direction: str


# Route Handlers


@router.get("/current", response_model=CurrentWeatherResponse)
async def get_current_weather(engine: SimulationEngineDep):
    """Get the current weather conditions.
    
    Returns the simulated weather state including current conditions
    and any available forecast data.
    
    Args:
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        Current weather conditions and forecast.
    
    Raises:
        HTTPException: If weather modality is not available (500).
    """
    env = engine.environment
    
    if "weather" not in env.modality_states:
        raise HTTPException(
            status_code=500,
            detail="Weather modality not initialized in environment",
        )
    
    weather_state = env.modality_states["weather"]
    
    # If no locations tracked yet, return empty response
    if not weather_state.locations:
        return CurrentWeatherResponse(
            location_name="No location tracked",
            latitude=0.0,
            longitude=0.0,
            current_conditions={},
            forecast=[],
            last_updated=weather_state.last_updated.isoformat(),
        )
    
    # Get the first location (for simplicity)
    location_key = list(weather_state.locations.keys())[0]
    location_state = weather_state.locations[location_key]
    
    return CurrentWeatherResponse(
        location_name=f"Location ({location_state.latitude:.2f}, {location_state.longitude:.2f})",
        latitude=location_state.latitude,
        longitude=location_state.longitude,
        current_conditions=location_state.current_report.model_dump()
        if location_state.current_report
        else {},
        forecast=[],  # Simplified - not exposing full forecast structure yet
        last_updated=weather_state.last_updated.isoformat(),
    )


@router.post("/update", response_model=CurrentWeatherResponse)
async def update_weather(request: UpdateWeatherRequest, engine: SimulationEngineDep):
    """Update the current weather conditions.
    
    Creates an immediate weather update event that modifies the simulated
    weather conditions. This is useful for testing how an AI assistant
    responds to weather changes.
    
    Args:
        request: The new weather conditions to set.
        engine: The SimulationEngine instance (injected by FastAPI).
    
    Returns:
        The updated weather state.
    
    Raises:
        HTTPException: If the update fails.
    """
    try:
        # Create a simple weather report
        # For a complete implementation, we'd use the full WeatherInput/WeatherReport structure
        # For now, just return a simplified response showing this would work
        
        raise HTTPException(
            status_code=501,
            detail="Weather updates not yet fully implemented - requires complete WeatherReport structure",
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update weather: {str(e)}",
        )
