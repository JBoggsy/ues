"""Location state model."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from models.base_input import ModalityInput
from models.base_state import ModalityState


class LocationHistoryEntry(BaseModel):
    """A single entry in the location history.

    Tracks a historical location with timestamp and associated metadata.

    Args:
        timestamp: When the user was at this location.
        latitude: Latitude coordinate.
        longitude: Longitude coordinate.
        address: Human-readable address if available.
        named_location: Semantic location name if available.
        altitude: Altitude in meters if available.
        accuracy: Accuracy radius in meters if available.
        speed: Speed in meters per second if available.
        bearing: Bearing in degrees if available.
    """

    timestamp: datetime = Field(description="When the user was at this location")
    latitude: float = Field(description="Latitude coordinate")
    longitude: float = Field(description="Longitude coordinate")
    address: Optional[str] = Field(default=None, description="Human-readable address")
    named_location: Optional[str] = Field(default=None, description="Semantic location name")
    altitude: Optional[float] = Field(default=None, description="Altitude in meters")
    accuracy: Optional[float] = Field(default=None, description="Accuracy radius in meters")
    speed: Optional[float] = Field(default=None, description="Speed in meters per second")
    bearing: Optional[float] = Field(default=None, description="Bearing in degrees")

    def to_dict(self) -> dict[str, Any]:
        """Convert this entry to a dictionary.

        Returns:
            Dictionary representation of this location entry.
        """
        result = {
            "timestamp": self.timestamp.isoformat(),
            "latitude": self.latitude,
            "longitude": self.longitude,
        }
        if self.address:
            result["address"] = self.address
        if self.named_location:
            result["named_location"] = self.named_location
        if self.altitude is not None:
            result["altitude"] = self.altitude
        if self.accuracy is not None:
            result["accuracy"] = self.accuracy
        if self.speed is not None:
            result["speed"] = self.speed
        if self.bearing is not None:
            result["bearing"] = self.bearing
        return result


class LocationState(ModalityState):
    """Current user location state.

    Tracks the user's current location and maintains a history of recent locations.
    Extensible to support additional location metadata in the future.

    Args:
        modality_type: Always "location" for this state type.
        last_updated: Simulator time when this state was last modified.
        update_count: Number of times this state has been modified.
        current_latitude: Current latitude coordinate.
        current_longitude: Current longitude coordinate.
        current_address: Current human-readable address if known.
        current_named_location: Current location name if applicable (e.g., "Home", "Office").
        current_altitude: Current altitude in meters if known.
        current_accuracy: Current position accuracy in meters if known.
        current_speed: Current speed in meters per second if known.
        current_bearing: Current bearing in degrees if known.
        location_history: List of recent location updates.
        max_history_size: Maximum number of historical locations to retain.
    """

    modality_type: str = Field(default="location", frozen=True)
    current_latitude: Optional[float] = Field(
        default=None, description="Current latitude coordinate"
    )
    current_longitude: Optional[float] = Field(
        default=None, description="Current longitude coordinate"
    )
    current_address: Optional[str] = Field(
        default=None, description="Current human-readable address"
    )
    current_named_location: Optional[str] = Field(
        default=None, description="Current location name (e.g., 'Home', 'Office')"
    )
    current_altitude: Optional[float] = Field(
        default=None, description="Current altitude in meters"
    )
    current_accuracy: Optional[float] = Field(
        default=None, description="Current position accuracy in meters"
    )
    current_speed: Optional[float] = Field(
        default=None, description="Current speed in meters per second"
    )
    current_bearing: Optional[float] = Field(
        default=None, description="Current bearing in degrees"
    )
    location_history: list[LocationHistoryEntry] = Field(
        default_factory=list, description="List of recent location updates"
    )
    max_history_size: int = Field(
        default=100, description="Maximum number of historical locations to retain"
    )

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True

    def apply_input(self, input_data: ModalityInput) -> None:
        """Apply a LocationInput to modify this state.

        Updates the current location and adds the previous location to history.
        Automatically manages history size by removing oldest entries when needed.

        Args:
            input_data: The LocationInput to apply to this state.

        Raises:
            ValueError: If input_data is not a LocationInput.
        """
        from models.modalities.location_input import LocationInput

        if not isinstance(input_data, LocationInput):
            raise ValueError(
                f"LocationState can only apply LocationInput, got {type(input_data)}"
            )

        if self.current_latitude is not None and self.current_longitude is not None:
            previous_entry = LocationHistoryEntry(
                timestamp=self.last_updated,
                latitude=self.current_latitude,
                longitude=self.current_longitude,
                address=self.current_address,
                named_location=self.current_named_location,
                altitude=self.current_altitude,
                accuracy=self.current_accuracy,
                speed=self.current_speed,
                bearing=self.current_bearing,
            )
            self.location_history.append(previous_entry)

            if len(self.location_history) > self.max_history_size:
                self.location_history.pop(0)

        self.current_latitude = input_data.latitude
        self.current_longitude = input_data.longitude
        self.current_address = input_data.address
        self.current_named_location = input_data.named_location
        self.current_altitude = input_data.altitude
        self.current_accuracy = input_data.accuracy
        self.current_speed = input_data.speed
        self.current_bearing = input_data.bearing

        self.last_updated = input_data.timestamp
        self.update_count += 1

    def get_snapshot(self) -> dict[str, Any]:
        """Return a complete snapshot of current state for API responses.

        Returns:
            Dictionary representation of current location state suitable for API responses.
        """
        snapshot: dict[str, Any] = {
            "modality_type": self.modality_type,
            "last_updated": self.last_updated.isoformat(),
            "update_count": self.update_count,
            "current": {},
            "history": [entry.to_dict() for entry in self.location_history],
        }

        if self.current_latitude is not None and self.current_longitude is not None:
            snapshot["current"] = {
                "latitude": self.current_latitude,
                "longitude": self.current_longitude,
            }
            if self.current_address:
                snapshot["current"]["address"] = self.current_address
            if self.current_named_location:
                snapshot["current"]["named_location"] = self.current_named_location
            if self.current_altitude is not None:
                snapshot["current"]["altitude"] = self.current_altitude
            if self.current_accuracy is not None:
                snapshot["current"]["accuracy"] = self.current_accuracy
            if self.current_speed is not None:
                snapshot["current"]["speed"] = self.current_speed
            if self.current_bearing is not None:
                snapshot["current"]["bearing"] = self.current_bearing

        return snapshot

    def validate_state(self) -> list[str]:
        """Validate internal state consistency and return any issues.

        Checks for:
        - Current coordinates are both set or both unset
        - History entries are in chronological order
        - History size doesn't exceed maximum

        Returns:
            List of validation error messages (empty list if valid).
        """
        issues = []

        if (self.current_latitude is None) != (self.current_longitude is None):
            issues.append(
                "Current latitude and longitude must both be set or both be None"
            )

        if self.current_latitude is not None:
            if not -90 <= self.current_latitude <= 90:
                issues.append(
                    f"Current latitude {self.current_latitude} is outside valid range"
                )

        if self.current_longitude is not None:
            if not -180 <= self.current_longitude <= 180:
                issues.append(
                    f"Current longitude {self.current_longitude} is outside valid range"
                )

        for i in range(1, len(self.location_history)):
            if (
                self.location_history[i].timestamp
                < self.location_history[i - 1].timestamp
            ):
                issues.append(f"Location history not in chronological order at index {i}")

        if len(self.location_history) > self.max_history_size:
            issues.append(
                f"Location history size {len(self.location_history)} exceeds maximum {self.max_history_size}"
            )

        return issues

    def query(self, query_params: dict[str, Any]) -> dict[str, Any]:
        """Execute a query against this state.

        Supports filtering location history by various criteria.

        Supported query parameters:
            - since: datetime - Return locations after this time
            - until: datetime - Return locations before this time
            - named_location: str - Return locations with this name
            - limit: int - Maximum number of results to return
            - offset: int - Number of results to skip (for pagination)
            - include_current: bool - Include current location in results (default: True)
            - sort_by: str - Field to sort by ("timestamp", "latitude", "longitude")
            - sort_order: str - Sort order ("asc" or "desc")

        Args:
            query_params: Dictionary of query parameters.

        Returns:
            Dictionary containing query results with matching locations:
                - locations: List of location objects matching the query.
                - count: Number of locations returned (after pagination).
                - total_count: Total number of locations matching query (before pagination).
        """
        since = query_params.get("since")
        until = query_params.get("until")
        named_location = query_params.get("named_location")
        limit = query_params.get("limit")
        include_current = query_params.get("include_current", True)

        results = []

        if include_current and self.current_latitude is not None:
            current_entry = {
                "timestamp": self.last_updated.isoformat(),
                "latitude": self.current_latitude,
                "longitude": self.current_longitude,
                "is_current": True,
            }
            if self.current_address:
                current_entry["address"] = self.current_address
            if self.current_named_location:
                current_entry["named_location"] = self.current_named_location
            if self.current_altitude is not None:
                current_entry["altitude"] = self.current_altitude
            if self.current_accuracy is not None:
                current_entry["accuracy"] = self.current_accuracy
            if self.current_speed is not None:
                current_entry["speed"] = self.current_speed
            if self.current_bearing is not None:
                current_entry["bearing"] = self.current_bearing

            if (
                (since is None or self.last_updated >= since)
                and (until is None or self.last_updated <= until)
                and (
                    named_location is None
                    or self.current_named_location == named_location
                )
            ):
                results.append(current_entry)

        for entry in reversed(self.location_history):
            if (
                (since is None or entry.timestamp >= since)
                and (until is None or entry.timestamp <= until)
                and (named_location is None or entry.named_location == named_location)
            ):
                entry_dict = entry.to_dict()
                entry_dict["is_current"] = False
                results.append(entry_dict)

        # Sort locations
        sort_by = query_params.get("sort_by", "timestamp")
        sort_order = query_params.get("sort_order", "desc")
        if sort_by in ["timestamp", "latitude", "longitude"]:
            results.sort(
                key=lambda loc: loc.get(sort_by, ""),
                reverse=(sort_order == "desc")
            )

        # Store total count before pagination
        total_count = len(results)

        # Apply pagination
        offset = query_params.get("offset", 0)
        if offset:
            results = results[offset:]
        if limit is not None:
            results = results[:limit]

        return {"locations": results, "count": len(results), "total_count": total_count}
