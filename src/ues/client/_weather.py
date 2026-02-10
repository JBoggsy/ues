"""Weather modality sub-client for the UES API.

This module provides WeatherClient and AsyncWeatherClient for interacting with
the weather modality endpoints (/weather/*).

This is an internal module. Import from `client` instead.
"""

from typing import TYPE_CHECKING, Any, Literal, Optional

from pydantic import BaseModel, Field

from ues.client._base import AsyncBaseClient, BaseClient
from ues.client.models import ModalityActionResponse

if TYPE_CHECKING:
    from ues.client._http import AsyncHTTPClient, HTTPClient


# Type aliases for weather fields
UnitSystem = Literal["standard", "metric", "imperial"]
ExcludeSection = Literal["current", "minutely", "hourly", "daily", "alerts"]


# Typed weather data models (mirrors server's weather_input.py)


class WeatherCondition(BaseModel):
    """A single weather condition descriptor.

    Represents a weather condition as defined by the OpenWeather API.

    Attributes:
        id: Weather condition id (e.g., 800 for clear sky).
        main: Group of weather parameters (Rain, Snow, Clouds, etc.).
        description: Weather condition description (e.g., "light rain").
        icon: Weather icon id (e.g., "01d" for day clear sky).
    """

    id: int
    main: str
    description: str
    icon: str


class CurrentWeather(BaseModel):
    """Current weather conditions.

    Attributes:
        dt: Current time, Unix timestamp (UTC).
        sunrise: Sunrise time, Unix timestamp (UTC).
        sunset: Sunset time, Unix timestamp (UTC).
        temp: Temperature in Kelvin (standard units).
        feels_like: Temperature accounting for human perception.
        pressure: Atmospheric pressure on sea level, hPa.
        humidity: Humidity percentage.
        dew_point: Dew point temperature in Kelvin.
        uvi: UV index.
        clouds: Cloudiness percentage.
        visibility: Visibility in meters (max 10000).
        wind_speed: Wind speed in m/s (standard units).
        wind_deg: Wind direction in degrees.
        wind_gust: Wind gust speed in m/s.
        weather: List of weather condition objects.
    """

    dt: int
    sunrise: int
    sunset: int
    temp: float
    feels_like: float
    pressure: int
    humidity: int
    dew_point: float
    uvi: float
    clouds: int
    visibility: int
    wind_speed: float
    wind_deg: int
    wind_gust: Optional[float] = None
    weather: list[WeatherCondition]


class MinutelyForecast(BaseModel):
    """Minute-by-minute precipitation forecast.

    Attributes:
        dt: Time of forecast, Unix timestamp (UTC).
        precipitation: Precipitation volume in mm.
    """

    dt: int
    precipitation: float


class HourlyForecast(BaseModel):
    """Hourly weather forecast.

    Attributes:
        dt: Time of forecast, Unix timestamp (UTC).
        temp: Temperature.
        feels_like: Feels like temperature.
        pressure: Atmospheric pressure, hPa.
        humidity: Humidity percentage.
        dew_point: Dew point temperature.
        uvi: UV index.
        clouds: Cloudiness percentage.
        visibility: Visibility in meters.
        wind_speed: Wind speed.
        wind_deg: Wind direction in degrees.
        wind_gust: Wind gust speed.
        weather: Weather conditions.
        pop: Probability of precipitation (0-1).
        rain: Rain volume for last hour in mm.
        snow: Snow volume for last hour in mm.
    """

    dt: int
    temp: float
    feels_like: float
    pressure: int
    humidity: int
    dew_point: float
    uvi: float
    clouds: int
    visibility: Optional[int] = None
    wind_speed: float
    wind_deg: int
    wind_gust: Optional[float] = None
    weather: list[WeatherCondition]
    pop: float
    rain: Optional[dict[str, float]] = None
    snow: Optional[dict[str, float]] = None


class DailyTemperature(BaseModel):
    """Daily temperature breakdown.

    Attributes:
        day: Day temperature.
        min: Minimum daily temperature.
        max: Maximum daily temperature.
        night: Night temperature.
        eve: Evening temperature.
        morn: Morning temperature.
    """

    day: float
    min: float
    max: float
    night: float
    eve: float
    morn: float


class DailyFeelsLike(BaseModel):
    """Daily feels like temperature breakdown.

    Attributes:
        day: Day feels like temperature.
        night: Night feels like temperature.
        eve: Evening feels like temperature.
        morn: Morning feels like temperature.
    """

    day: float
    night: float
    eve: float
    morn: float


class DailyForecast(BaseModel):
    """Daily weather forecast.

    Attributes:
        dt: Time of forecast, Unix timestamp (UTC).
        sunrise: Sunrise time, Unix timestamp.
        sunset: Sunset time, Unix timestamp.
        moonrise: Moonrise time, Unix timestamp.
        moonset: Moonset time, Unix timestamp.
        moon_phase: Moon phase (0-1).
        summary: Human-readable summary.
        temp: Temperature breakdown.
        feels_like: Feels like temperature breakdown.
        pressure: Atmospheric pressure, hPa.
        humidity: Humidity percentage.
        dew_point: Dew point temperature.
        wind_speed: Wind speed.
        wind_deg: Wind direction in degrees.
        wind_gust: Wind gust speed.
        weather: Weather conditions.
        clouds: Cloudiness percentage.
        pop: Probability of precipitation.
        rain: Rain volume in mm.
        snow: Snow volume in mm.
        uvi: UV index.
    """

    dt: int
    sunrise: int
    sunset: int
    moonrise: int
    moonset: int
    moon_phase: float
    summary: Optional[str] = None
    temp: DailyTemperature
    feels_like: DailyFeelsLike
    pressure: int
    humidity: int
    dew_point: float
    wind_speed: float
    wind_deg: int
    wind_gust: Optional[float] = None
    weather: list[WeatherCondition]
    clouds: int
    pop: float
    rain: Optional[float] = None
    snow: Optional[float] = None
    uvi: float


class WeatherAlert(BaseModel):
    """Weather alert information.

    Attributes:
        sender_name: Name of the alert source.
        event: Alert event name.
        start: Alert start time, Unix timestamp.
        end: Alert end time, Unix timestamp.
        description: Alert description.
        tags: List of alert tags.
    """

    sender_name: str
    event: str
    start: int
    end: int
    description: str
    tags: list[str] = Field(default_factory=list)


class WeatherReport(BaseModel):
    """Complete weather report for a location.

    Conforms to the OpenWeather One Call API format.

    Attributes:
        lat: Location latitude.
        lon: Location longitude.
        timezone: Timezone identifier.
        timezone_offset: Timezone offset in seconds from UTC.
        current: Current weather conditions.
        minutely: Minute-by-minute forecast (optional).
        hourly: Hourly forecast (optional).
        daily: Daily forecast (optional).
        alerts: Weather alerts (optional).
    """

    lat: float
    lon: float
    timezone: str
    timezone_offset: int
    current: Optional[CurrentWeather] = None
    minutely: Optional[list[MinutelyForecast]] = None
    hourly: Optional[list[HourlyForecast]] = None
    daily: Optional[list[DailyForecast]] = None
    alerts: Optional[list[WeatherAlert]] = None


# Response models for weather endpoints


class WeatherStateResponse(BaseModel):
    """Response model for weather state endpoint.
    
    Attributes:
        modality_type: Always "weather".
        last_updated: ISO format timestamp of last update.
        update_count: Number of weather updates.
        locations: Dict mapping location keys to weather data.
        location_count: Number of tracked locations.
    """

    modality_type: str
    last_updated: str
    update_count: int
    locations: dict[str, Any]
    location_count: int


class WeatherCompactStateResponse(BaseModel):
    """Compact response model for weather state endpoint.

    Returned when ``compact=True`` is passed to ``get_state()``. Optimized
    for LLM context — includes current weather per location without full
    report history.

    Attributes:
        modality_type: Always "weather".
        last_updated: ISO format timestamp of last update.
        update_count: Number of weather updates.
        location_count: Number of tracked locations.
        locations: Current weather per location (no history).
    """

    modality_type: str
    last_updated: str
    update_count: int
    location_count: int
    locations: dict[str, Any]


class WeatherQueryResponse(BaseModel):
    """Response model for weather query endpoint.
    
    Attributes:
        reports: List of weather report objects matching the query.
        count: Number of reports returned (after pagination).
        total_count: Total matching reports (before pagination).
        error: Optional error message if no data available.
    """

    reports: list[WeatherReport]
    count: int
    total_count: int = 0
    error: str | None = None


# Synchronous WeatherClient


class WeatherClient(BaseClient):
    """Synchronous client for weather modality endpoints (/weather/*).
    
    This client provides methods for getting weather state, querying weather
    data for locations, and updating weather conditions. Weather data conforms
    to the OpenWeather API format and supports current conditions, forecasts,
    and alerts.
    
    Example:
        with UESClient() as client:
            # Update weather for a location
            client.weather.update(
                latitude=40.7128,
                longitude=-74.0060,
                report={
                    "lat": 40.7128,
                    "lon": -74.0060,
                    "timezone": "America/New_York",
                    "current": {
                        "dt": 1640000000,
                        "temp": 45.0,
                        "weather": [{"id": 800, "main": "Clear"}],
                    },
                },
            )
            
            # Get weather state
            state = client.weather.get_state()
            print(f"Tracking {state.location_count} locations")
            
            # Query weather for a location
            weather = client.weather.query(
                lat=40.7128,
                lon=-74.0060,
                units="imperial",
            )
            print(f"Found {weather.count} weather reports")
    """

    _BASE_PATH = "/weather"

    def get_state(
        self, compact: bool = False,
    ) -> WeatherStateResponse | WeatherCompactStateResponse:
        """Get the current weather state for all tracked locations.
        
        Returns a snapshot of the weather state. When ``compact=True``,
        returns a lightweight response with current weather per location
        but without full report history, optimized for LLM context windows.
        
        Args:
            compact: If True, return compact state without full history.
                Default is False (full state).
        
        Returns:
            Full weather state, or compact state if ``compact=True``.
        
        Raises:
            APIError: If the request fails.
        """
        params = {"compact": True} if compact else None
        data = self._get(f"{self._BASE_PATH}/state", params=params)
        if compact:
            return WeatherCompactStateResponse(**data)
        return WeatherStateResponse(**data)

    def query(
        self,
        lat: float,
        lon: float,
        exclude: list[ExcludeSection] | None = None,
        units: UnitSystem = "standard",
        from_time: int | None = None,
        to_time: int | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> WeatherQueryResponse:
        """Query weather data for a specific location with filters.
        
        Supports querying simulated weather history with filtering by time
        range, excluded sections, and unit conversion.
        
        Args:
            lat: Location latitude to query (required).
            lon: Location longitude to query (required).
            exclude: List of sections to exclude ("current", "minutely", 
                "hourly", "daily", "alerts").
            units: Unit system ("standard", "metric", or "imperial").
            from_time: Unix timestamp - return all reports since this time.
            to_time: Unix timestamp - return reports up to this time 
                (requires from_time).
            limit: Maximum number of reports to return (must be >= 1).
            offset: Number of reports to skip for pagination (must be >= 0).
        
        Returns:
            Matching weather reports with pagination info.
        
        Raises:
            ValidationError: If query parameters are invalid.
            APIError: If the request fails.
        """
        # Build the request body
        request_data: dict[str, Any] = {
            "lat": lat,
            "lon": lon,
        }
        
        if exclude is not None:
            request_data["exclude"] = exclude
        if units != "standard":
            request_data["units"] = units
        if from_time is not None:
            request_data["from_time"] = from_time
        if to_time is not None:
            request_data["to_time"] = to_time
        if limit is not None:
            request_data["limit"] = limit
        if offset != 0:
            request_data["offset"] = offset
        
        data = self._post(f"{self._BASE_PATH}/query", json=request_data)
        return WeatherQueryResponse(**data)

    def update(
        self,
        latitude: float,
        longitude: float,
        report: WeatherReport | dict[str, Any],
    ) -> ModalityActionResponse:
        """Update weather conditions for a location.
        
        Creates an immediate event that updates the weather for the specified
        location. The weather report should conform to OpenWeather API format.
        
        Args:
            latitude: Location latitude in decimal degrees (-90 to 90).
            longitude: Location longitude in decimal degrees (-180 to 180).
            report: Complete weather report conforming to OpenWeather API format.
                Can be a WeatherReport model or a raw dict. Should include at
                minimum: lat, lon, timezone, timezone_offset, and optionally
                current conditions, forecasts, and alerts.
        
        Returns:
            Action response with event ID and execution status.
        
        Raises:
            ValidationError: If coordinates are out of range or report is invalid.
            APIError: If the request fails.
        """
        report_data = (
            report.model_dump(mode="json") if isinstance(report, WeatherReport)
            else report
        )
        request_data: dict[str, Any] = {
            "latitude": latitude,
            "longitude": longitude,
            "report": report_data,
        }
        
        data = self._post(f"{self._BASE_PATH}/update", json=request_data)
        return ModalityActionResponse(**data)


# Asynchronous AsyncWeatherClient


class AsyncWeatherClient(AsyncBaseClient):
    """Asynchronous client for weather modality endpoints (/weather/*).
    
    This client provides async methods for getting weather state, querying
    weather data for locations, and updating weather conditions. Weather data
    conforms to the OpenWeather API format and supports current conditions,
    forecasts, and alerts.
    
    Example:
        async with AsyncUESClient() as client:
            # Update weather for a location
            await client.weather.update(
                latitude=40.7128,
                longitude=-74.0060,
                report={
                    "lat": 40.7128,
                    "lon": -74.0060,
                    "timezone": "America/New_York",
                    "current": {
                        "dt": 1640000000,
                        "temp": 45.0,
                        "weather": [{"id": 800, "main": "Clear"}],
                    },
                },
            )
            
            # Get weather state
            state = await client.weather.get_state()
            print(f"Tracking {state.location_count} locations")
            
            # Query weather for a location
            weather = await client.weather.query(
                lat=40.7128,
                lon=-74.0060,
                units="imperial",
            )
            print(f"Found {weather.count} weather reports")
    """

    _BASE_PATH = "/weather"

    async def get_state(
        self, compact: bool = False,
    ) -> WeatherStateResponse | WeatherCompactStateResponse:
        """Get the current weather state for all tracked locations.
        
        Returns a snapshot of the weather state. When ``compact=True``,
        returns a lightweight response with current weather per location
        but without full report history, optimized for LLM context windows.
        
        Args:
            compact: If True, return compact state without full history.
                Default is False (full state).
        
        Returns:
            Full weather state, or compact state if ``compact=True``.
        
        Raises:
            APIError: If the request fails.
        """
        params = {"compact": True} if compact else None
        data = await self._get(f"{self._BASE_PATH}/state", params=params)
        if compact:
            return WeatherCompactStateResponse(**data)
        return WeatherStateResponse(**data)

    async def query(
        self,
        lat: float,
        lon: float,
        exclude: list[ExcludeSection] | None = None,
        units: UnitSystem = "standard",
        from_time: int | None = None,
        to_time: int | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> WeatherQueryResponse:
        """Query weather data for a specific location with filters.
        
        Supports querying simulated weather history with filtering by time
        range, excluded sections, and unit conversion.
        
        Args:
            lat: Location latitude to query (required).
            lon: Location longitude to query (required).
            exclude: List of sections to exclude ("current", "minutely", 
                "hourly", "daily", "alerts").
            units: Unit system ("standard", "metric", or "imperial").
            from_time: Unix timestamp - return all reports since this time.
            to_time: Unix timestamp - return reports up to this time 
                (requires from_time).
            limit: Maximum number of reports to return (must be >= 1).
            offset: Number of reports to skip for pagination (must be >= 0).
        
        Returns:
            Matching weather reports with pagination info.
        
        Raises:
            ValidationError: If query parameters are invalid.
            APIError: If the request fails.
        """
        # Build the request body
        request_data: dict[str, Any] = {
            "lat": lat,
            "lon": lon,
        }
        
        if exclude is not None:
            request_data["exclude"] = exclude
        if units != "standard":
            request_data["units"] = units
        if from_time is not None:
            request_data["from_time"] = from_time
        if to_time is not None:
            request_data["to_time"] = to_time
        if limit is not None:
            request_data["limit"] = limit
        if offset != 0:
            request_data["offset"] = offset
        
        data = await self._post(f"{self._BASE_PATH}/query", json=request_data)
        return WeatherQueryResponse(**data)

    async def update(
        self,
        latitude: float,
        longitude: float,
        report: WeatherReport | dict[str, Any],
    ) -> ModalityActionResponse:
        """Update weather conditions for a location.
        
        Creates an immediate event that updates the weather for the specified
        location. The weather report should conform to OpenWeather API format.
        
        Args:
            latitude: Location latitude in decimal degrees (-90 to 90).
            longitude: Location longitude in decimal degrees (-180 to 180).
            report: Complete weather report conforming to OpenWeather API format.
                Can be a WeatherReport model or a raw dict. Should include at
                minimum: lat, lon, timezone, timezone_offset, and optionally
                current conditions, forecasts, and alerts.
        
        Returns:
            Action response with event ID and execution status.
        
        Raises:
            ValidationError: If coordinates are out of range or report is invalid.
            APIError: If the request fails.
        """
        report_data = (
            report.model_dump(mode="json") if isinstance(report, WeatherReport)
            else report
        )
        request_data: dict[str, Any] = {
            "latitude": latitude,
            "longitude": longitude,
            "report": report_data,
        }
        
        data = await self._post(f"{self._BASE_PATH}/update", json=request_data)
        return ModalityActionResponse(**data)
