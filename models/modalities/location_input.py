"""Location input model."""

from datetime import datetime
from typing import Optional

from pydantic import Field, field_validator

from models.base_input import ModalityInput


class LocationInput(ModalityInput):
    """Input for updating user location.

    Represents a location change event, containing geographic coordinates,
    human-readable address, and optional metadata like location names or accuracy.

    Args:
        modality_type: Always "location" for this input type.
        timestamp: When this location update logically occurred (simulator time).
        input_id: Unique identifier for this specific location update.
        latitude: Latitude coordinate in decimal degrees (-90 to 90).
        longitude: Longitude coordinate in decimal degrees (-180 to 180).
        address: Human-readable address or location description.
        named_location: Optional semantic name for the location (e.g., "Home", "Office", "Gym").
        altitude: Optional altitude in meters above sea level.
        accuracy: Optional accuracy radius in meters.
        speed: Optional speed in meters per second.
        bearing: Optional bearing/heading in degrees (0-360, where 0 is North).
    """

    modality_type: str = Field(default="location", frozen=True)
    latitude: float = Field(
        description="Latitude coordinate in decimal degrees (-90 to 90)"
    )
    longitude: float = Field(
        description="Longitude coordinate in decimal degrees (-180 to 180)"
    )
    address: Optional[str] = Field(
        default=None, description="Human-readable address or location description"
    )
    named_location: Optional[str] = Field(
        default=None,
        description="Semantic name for the location (e.g., 'Home', 'Office')",
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
        default=None, description="Bearing/heading in degrees (0-360, 0=North)"
    )

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value: float) -> float:
        """Validate latitude is within valid range.

        Args:
            value: Latitude value to validate.

        Returns:
            The validated latitude value.

        Raises:
            ValueError: If latitude is outside valid range.
        """
        if not -90 <= value <= 90:
            raise ValueError(f"Latitude must be between -90 and 90, got {value}")
        return value

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value: float) -> float:
        """Validate longitude is within valid range.

        Args:
            value: Longitude value to validate.

        Returns:
            The validated longitude value.

        Raises:
            ValueError: If longitude is outside valid range.
        """
        if not -180 <= value <= 180:
            raise ValueError(f"Longitude must be between -180 and 180, got {value}")
        return value

    @field_validator("accuracy")
    @classmethod
    def validate_accuracy(cls, value: Optional[float]) -> Optional[float]:
        """Validate accuracy is non-negative if provided.

        Args:
            value: Accuracy value to validate.

        Returns:
            The validated accuracy value.

        Raises:
            ValueError: If accuracy is negative.
        """
        if value is not None and value < 0:
            raise ValueError(f"Accuracy must be non-negative, got {value}")
        return value

    @field_validator("speed")
    @classmethod
    def validate_speed(cls, value: Optional[float]) -> Optional[float]:
        """Validate speed is non-negative if provided.

        Args:
            value: Speed value to validate.

        Returns:
            The validated speed value.

        Raises:
            ValueError: If speed is negative.
        """
        if value is not None and value < 0:
            raise ValueError(f"Speed must be non-negative, got {value}")
        return value

    @field_validator("bearing")
    @classmethod
    def validate_bearing(cls, value: Optional[float]) -> Optional[float]:
        """Validate bearing is within valid range if provided.

        Args:
            value: Bearing value to validate.

        Returns:
            The validated bearing value.

        Raises:
            ValueError: If bearing is outside valid range.
        """
        if value is not None and not 0 <= value <= 360:
            raise ValueError(f"Bearing must be between 0 and 360, got {value}")
        return value

    def validate_input(self) -> None:
        """Perform modality-specific validation beyond Pydantic field validation.

        For LocationInput, all validation is handled by Pydantic field validators.
        This method is provided for consistency with the base class interface.

        Raises:
            ValueError: Never raised (all validation in field validators).
        """
        pass

    def get_affected_entities(self) -> list[str]:
        """Return list of entity IDs affected by this input.

        For location updates, we consider the user's location as a single entity.
        If a named_location is provided, we also track it as an affected entity
        to enable queries like "show all times I was at Office".

        Returns:
            List containing "user_location" and optionally the named_location.
        """
        entities = ["user_location"]
        if self.named_location:
            entities.append(f"location:{self.named_location}")
        return entities

    def get_summary(self) -> str:
        """Return human-readable one-line summary of this input.

        Examples:
            - "Moved to 123 Main St, NYC (40.7128, -74.0060)"
            - "At Office: 456 Work Ave (40.7589, -73.9851)"
            - "Location update: (34.0522, -118.2437)"

        Returns:
            Brief description of the location update for logging/UI display.
        """
        if self.named_location and self.address:
            return f"At {self.named_location}: {self.address} ({self.latitude}, {self.longitude})"
        elif self.address:
            return f"Moved to {self.address} ({self.latitude}, {self.longitude})"
        elif self.named_location:
            return f"At {self.named_location} ({self.latitude}, {self.longitude})"
        else:
            return f"Location update: ({self.latitude}, {self.longitude})"

    def should_merge_with(self, other: "ModalityInput") -> bool:
        """Determine if this input should be merged with another input.

        Location updates within 1 second of each other are considered duplicate
        position updates and can be merged to avoid clutter. Only merge if they
        have the same named_location (or both lack one).

        Args:
            other: Another input to compare against.

        Returns:
            True if inputs should be merged (same location within 1 second).
        """
        if not isinstance(other, LocationInput):
            return False

        time_diff = abs((self.timestamp - other.timestamp).total_seconds())
        same_named_location = self.named_location == other.named_location

        return time_diff <= 1.0 and same_named_location
