"""Weather modality sub-client for the UES API.

This module provides WeatherClient and AsyncWeatherClient for interacting with
the weather modality endpoints (/weather/*).

This is an internal module. Import from `client` instead.
"""

from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field

from client._base import AsyncBaseClient, BaseClient
from client.models import ModalityActionResponse

if TYPE_CHECKING:
    from client._http import AsyncHTTPClient, HTTPClient


# Type aliases for weather fields
UnitSystem = Literal["standard", "metric", "imperial"]
ExcludeSection = Literal["current", "minutely", "hourly", "daily", "alerts"]


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

    modality_type: str = "weather"
    last_updated: str
    update_count: int
    locations: dict[str, Any]
    location_count: int


class WeatherQueryResponse(BaseModel):
    """Response model for weather query endpoint.
    
    Attributes:
        reports: List of weather report objects matching the query.
        count: Number of reports returned (after pagination).
        total_count: Total matching reports (before pagination).
        error: Optional error message if no data available.
    """

    reports: list[dict[str, Any]]
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

    def get_state(self) -> WeatherStateResponse:
        """Get the current weather state for all tracked locations.
        
        Returns a complete snapshot of the weather state including all tracked
        locations and their current weather conditions.
        
        Returns:
            Complete weather state with all locations and their data.
        
        Raises:
            APIError: If the request fails.
        """
        data = self._get(f"{self._BASE_PATH}/state")
        return WeatherStateResponse(**data)

    def query(
        self,
        lat: float,
        lon: float,
        exclude: list[ExcludeSection] | None = None,
        units: UnitSystem = "standard",
        from_time: int | None = None,
        to_time: int | None = None,
        real: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> WeatherQueryResponse:
        """Query weather data for a specific location with filters.
        
        Supports querying simulated weather history or real-time weather from
        OpenWeather API. Can filter by time range, exclude sections, and convert
        units.
        
        Args:
            lat: Location latitude to query (required).
            lon: Location longitude to query (required).
            exclude: List of sections to exclude ("current", "minutely", 
                "hourly", "daily", "alerts").
            units: Unit system ("standard", "metric", or "imperial").
            from_time: Unix timestamp - return all reports since this time.
            to_time: Unix timestamp - return reports up to this time 
                (requires from_time).
            real: If True, query OpenWeather API instead of simulated data.
            limit: Maximum number of reports to return.
            offset: Number of reports to skip (for pagination).
        
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
        if real:
            request_data["real"] = real
        if limit is not None:
            request_data["limit"] = limit
        if offset != 0:
            request_data["offset"] = offset
        
        data = self._post(f"{self._BASE_PATH}/query", json=request_data)
        
        # Convert WeatherReport objects back to dicts if needed
        reports = data.get("reports", [])
        if reports and hasattr(reports[0], "model_dump"):
            reports = [r.model_dump() for r in reports]
        
        return WeatherQueryResponse(
            reports=reports,
            count=data.get("count", 0),
            total_count=data.get("total_count", data.get("count", 0)),
            error=data.get("error"),
        )

    def update(
        self,
        latitude: float,
        longitude: float,
        report: dict[str, Any],
    ) -> ModalityActionResponse:
        """Update weather conditions for a location.
        
        Creates an immediate event that updates the weather for the specified
        location. The weather report should conform to OpenWeather API format.
        
        Args:
            latitude: Location latitude in decimal degrees (-90 to 90).
            longitude: Location longitude in decimal degrees (-180 to 180).
            report: Complete weather report conforming to OpenWeather API format.
                Should include at minimum: lat, lon, timezone, and current conditions.
        
        Returns:
            Action response with event ID and execution status.
        
        Raises:
            ValidationError: If coordinates are out of range or report is invalid.
            APIError: If the request fails.
        """
        request_data: dict[str, Any] = {
            "latitude": latitude,
            "longitude": longitude,
            "report": report,
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

    async def get_state(self) -> WeatherStateResponse:
        """Get the current weather state for all tracked locations.
        
        Returns a complete snapshot of the weather state including all tracked
        locations and their current weather conditions.
        
        Returns:
            Complete weather state with all locations and their data.
        
        Raises:
            APIError: If the request fails.
        """
        data = await self._get(f"{self._BASE_PATH}/state")
        return WeatherStateResponse(**data)

    async def query(
        self,
        lat: float,
        lon: float,
        exclude: list[ExcludeSection] | None = None,
        units: UnitSystem = "standard",
        from_time: int | None = None,
        to_time: int | None = None,
        real: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> WeatherQueryResponse:
        """Query weather data for a specific location with filters.
        
        Supports querying simulated weather history or real-time weather from
        OpenWeather API. Can filter by time range, exclude sections, and convert
        units.
        
        Args:
            lat: Location latitude to query (required).
            lon: Location longitude to query (required).
            exclude: List of sections to exclude ("current", "minutely", 
                "hourly", "daily", "alerts").
            units: Unit system ("standard", "metric", or "imperial").
            from_time: Unix timestamp - return all reports since this time.
            to_time: Unix timestamp - return reports up to this time 
                (requires from_time).
            real: If True, query OpenWeather API instead of simulated data.
            limit: Maximum number of reports to return.
            offset: Number of reports to skip (for pagination).
        
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
        if real:
            request_data["real"] = real
        if limit is not None:
            request_data["limit"] = limit
        if offset != 0:
            request_data["offset"] = offset
        
        data = await self._post(f"{self._BASE_PATH}/query", json=request_data)
        
        # Convert WeatherReport objects back to dicts if needed
        reports = data.get("reports", [])
        if reports and hasattr(reports[0], "model_dump"):
            reports = [r.model_dump() for r in reports]
        
        return WeatherQueryResponse(
            reports=reports,
            count=data.get("count", 0),
            total_count=data.get("total_count", data.get("count", 0)),
            error=data.get("error"),
        )

    async def update(
        self,
        latitude: float,
        longitude: float,
        report: dict[str, Any],
    ) -> ModalityActionResponse:
        """Update weather conditions for a location.
        
        Creates an immediate event that updates the weather for the specified
        location. The weather report should conform to OpenWeather API format.
        
        Args:
            latitude: Location latitude in decimal degrees (-90 to 90).
            longitude: Location longitude in decimal degrees (-180 to 180).
            report: Complete weather report conforming to OpenWeather API format.
                Should include at minimum: lat, lon, timezone, and current conditions.
        
        Returns:
            Action response with event ID and execution status.
        
        Raises:
            ValidationError: If coordinates are out of range or report is invalid.
            APIError: If the request fails.
        """
        request_data: dict[str, Any] = {
            "latitude": latitude,
            "longitude": longitude,
            "report": report,
        }
        
        data = await self._post(f"{self._BASE_PATH}/update", json=request_data)
        return ModalityActionResponse(**data)
