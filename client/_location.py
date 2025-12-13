"""Location modality sub-client for the UES API.

This module provides LocationClient and AsyncLocationClient for interacting with
the location modality endpoints (/location/*).

This is an internal module. Import from `client` instead.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field

from client._base import AsyncBaseClient, BaseClient
from client.models import ModalityActionResponse

if TYPE_CHECKING:
    from client._http import AsyncHTTPClient, HTTPClient


# Response models for location endpoints


class LocationStateResponse(BaseModel):
    """Response model for location state endpoint.
    
    Attributes:
        modality_type: Always "location".
        last_updated: ISO format timestamp of last update.
        update_count: Number of location updates.
        current: Current location data.
        history: List of recent location history entries.
    """

    modality_type: str = "location"
    last_updated: str
    update_count: int
    current: dict[str, Any]
    history: list[dict[str, Any]]


class LocationQueryResponse(BaseModel):
    """Response model for location query endpoint.
    
    Attributes:
        locations: List of location entries matching the query.
        count: Number of locations returned (after pagination).
        total_count: Total matching locations (before pagination).
    """

    locations: list[dict[str, Any]]
    count: int
    total_count: int


# Synchronous LocationClient


class LocationClient(BaseClient):
    """Synchronous client for location modality endpoints (/location/*).
    
    This client provides methods for getting location state, querying location
    history, and updating the user's current location. The location includes
    coordinates, address information, and optional metadata like altitude,
    speed, and bearing.
    
    Example:
        with UESClient() as client:
            # Update location to specific coordinates
            client.location.update(
                latitude=40.7128,
                longitude=-74.0060,
                address="New York, NY",
                named_location="Office",
            )
            
            # Get current location state
            state = client.location.get_state()
            print(f"Current location: {state.current}")
            
            # Query location history
            history = client.location.query(
                named_location="Home",
                limit=10,
            )
            print(f"Found {history.total_count} visits to Home")
    """

    _BASE_PATH = "/location"

    def get_state(self) -> LocationStateResponse:
        """Get the current location state.
        
        Returns a complete snapshot of the user's current location and recent
        location history.
        
        Returns:
            Current location state including coordinates, address, metadata,
            and location history.
        
        Raises:
            APIError: If the request fails.
        """
        data = self._get(f"{self._BASE_PATH}/state")
        return LocationStateResponse(**data)

    def query(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        named_location: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        include_current: bool = True,
        sort_by: str = "timestamp",
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> LocationQueryResponse:
        """Query location history with filters.
        
        Allows filtering and searching through the user's location history
        based on time range, semantic location names, and other criteria.
        
        Args:
            since: Return locations after this time.
            until: Return locations before this time.
            named_location: Filter by semantic location name (e.g., "Home", "Office").
            limit: Maximum number of results to return.
            offset: Number of results to skip (for pagination).
            include_current: Whether to include current location in results.
            sort_by: Field to sort by (default: "timestamp").
            sort_order: Sort direction ("asc" or "desc", default: "desc").
        
        Returns:
            Matching location entries with pagination info.
        
        Raises:
            ValidationError: If query parameters are invalid.
            APIError: If the request fails.
        """
        # Build the request body, excluding None values and defaults
        request_data: dict[str, Any] = {}
        
        if since is not None:
            request_data["since"] = since.isoformat()
        if until is not None:
            request_data["until"] = until.isoformat()
        if named_location is not None:
            request_data["named_location"] = named_location
        if limit is not None:
            request_data["limit"] = limit
        if offset != 0:
            request_data["offset"] = offset
        if not include_current:
            request_data["include_current"] = include_current
        if sort_by != "timestamp":
            request_data["sort_by"] = sort_by
        if sort_order != "desc":
            request_data["sort_order"] = sort_order
        
        data = self._post(f"{self._BASE_PATH}/query", json=request_data)
        return LocationQueryResponse(**data)

    def update(
        self,
        latitude: float,
        longitude: float,
        address: str | None = None,
        named_location: str | None = None,
        altitude: float | None = None,
        accuracy: float | None = None,
        speed: float | None = None,
        bearing: float | None = None,
    ) -> ModalityActionResponse:
        """Update the user's current location.
        
        Creates an immediate event that updates the user's location with the
        provided coordinates and optional metadata. The previous location is
        automatically added to the location history.
        
        Args:
            latitude: Latitude coordinate in decimal degrees (-90 to 90).
            longitude: Longitude coordinate in decimal degrees (-180 to 180).
            address: Human-readable address or location description.
            named_location: Semantic name (e.g., "Home", "Office", "Gym").
            altitude: Altitude in meters above sea level.
            accuracy: Accuracy radius in meters.
            speed: Speed in meters per second.
            bearing: Bearing/heading in degrees (0-360, 0=North).
        
        Returns:
            Action response with event ID and execution status.
        
        Raises:
            ValidationError: If coordinates are out of range or other validation fails.
            APIError: If the request fails.
        """
        request_data: dict[str, Any] = {
            "latitude": latitude,
            "longitude": longitude,
        }
        
        if address is not None:
            request_data["address"] = address
        if named_location is not None:
            request_data["named_location"] = named_location
        if altitude is not None:
            request_data["altitude"] = altitude
        if accuracy is not None:
            request_data["accuracy"] = accuracy
        if speed is not None:
            request_data["speed"] = speed
        if bearing is not None:
            request_data["bearing"] = bearing
        
        data = self._post(f"{self._BASE_PATH}/update", json=request_data)
        return ModalityActionResponse(**data)


# Asynchronous AsyncLocationClient


class AsyncLocationClient(AsyncBaseClient):
    """Asynchronous client for location modality endpoints (/location/*).
    
    This client provides async methods for getting location state, querying
    location history, and updating the user's current location. The location
    includes coordinates, address information, and optional metadata like
    altitude, speed, and bearing.
    
    Example:
        async with AsyncUESClient() as client:
            # Update location to specific coordinates
            await client.location.update(
                latitude=40.7128,
                longitude=-74.0060,
                address="New York, NY",
                named_location="Office",
            )
            
            # Get current location state
            state = await client.location.get_state()
            print(f"Current location: {state.current}")
            
            # Query location history
            history = await client.location.query(
                named_location="Home",
                limit=10,
            )
            print(f"Found {history.total_count} visits to Home")
    """

    _BASE_PATH = "/location"

    async def get_state(self) -> LocationStateResponse:
        """Get the current location state.
        
        Returns a complete snapshot of the user's current location and recent
        location history.
        
        Returns:
            Current location state including coordinates, address, metadata,
            and location history.
        
        Raises:
            APIError: If the request fails.
        """
        data = await self._get(f"{self._BASE_PATH}/state")
        return LocationStateResponse(**data)

    async def query(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        named_location: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        include_current: bool = True,
        sort_by: str = "timestamp",
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> LocationQueryResponse:
        """Query location history with filters.
        
        Allows filtering and searching through the user's location history
        based on time range, semantic location names, and other criteria.
        
        Args:
            since: Return locations after this time.
            until: Return locations before this time.
            named_location: Filter by semantic location name (e.g., "Home", "Office").
            limit: Maximum number of results to return.
            offset: Number of results to skip (for pagination).
            include_current: Whether to include current location in results.
            sort_by: Field to sort by (default: "timestamp").
            sort_order: Sort direction ("asc" or "desc", default: "desc").
        
        Returns:
            Matching location entries with pagination info.
        
        Raises:
            ValidationError: If query parameters are invalid.
            APIError: If the request fails.
        """
        # Build the request body, excluding None values and defaults
        request_data: dict[str, Any] = {}
        
        if since is not None:
            request_data["since"] = since.isoformat()
        if until is not None:
            request_data["until"] = until.isoformat()
        if named_location is not None:
            request_data["named_location"] = named_location
        if limit is not None:
            request_data["limit"] = limit
        if offset != 0:
            request_data["offset"] = offset
        if not include_current:
            request_data["include_current"] = include_current
        if sort_by != "timestamp":
            request_data["sort_by"] = sort_by
        if sort_order != "desc":
            request_data["sort_order"] = sort_order
        
        data = await self._post(f"{self._BASE_PATH}/query", json=request_data)
        return LocationQueryResponse(**data)

    async def update(
        self,
        latitude: float,
        longitude: float,
        address: str | None = None,
        named_location: str | None = None,
        altitude: float | None = None,
        accuracy: float | None = None,
        speed: float | None = None,
        bearing: float | None = None,
    ) -> ModalityActionResponse:
        """Update the user's current location.
        
        Creates an immediate event that updates the user's location with the
        provided coordinates and optional metadata. The previous location is
        automatically added to the location history.
        
        Args:
            latitude: Latitude coordinate in decimal degrees (-90 to 90).
            longitude: Longitude coordinate in decimal degrees (-180 to 180).
            address: Human-readable address or location description.
            named_location: Semantic name (e.g., "Home", "Office", "Gym").
            altitude: Altitude in meters above sea level.
            accuracy: Accuracy radius in meters.
            speed: Speed in meters per second.
            bearing: Bearing/heading in degrees (0-360, 0=North).
        
        Returns:
            Action response with event ID and execution status.
        
        Raises:
            ValidationError: If coordinates are out of range or other validation fails.
            APIError: If the request fails.
        """
        request_data: dict[str, Any] = {
            "latitude": latitude,
            "longitude": longitude,
        }
        
        if address is not None:
            request_data["address"] = address
        if named_location is not None:
            request_data["named_location"] = named_location
        if altitude is not None:
            request_data["altitude"] = altitude
        if accuracy is not None:
            request_data["accuracy"] = accuracy
        if speed is not None:
            request_data["speed"] = speed
        if bearing is not None:
            request_data["bearing"] = bearing
        
        data = await self._post(f"{self._BASE_PATH}/update", json=request_data)
        return ModalityActionResponse(**data)
