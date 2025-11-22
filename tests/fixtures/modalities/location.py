"""Fixtures for Location modality."""

from datetime import datetime, timezone

from models.modalities.location_input import LocationInput
from models.modalities.location_state import LocationState


def create_location_input(
    latitude: float = 37.7749,
    longitude: float = -122.4194,
    address: str | None = None,
    timestamp: datetime | None = None,
    **kwargs,
) -> LocationInput:
    """Create a LocationInput with sensible defaults.

    Args:
        latitude: Latitude coordinate (default: San Francisco).
        longitude: Longitude coordinate (default: San Francisco).
        address: Human-readable address.
        timestamp: When location update occurred (defaults to now).
        **kwargs: Additional fields to override.

    Returns:
        LocationInput instance ready for testing.
    """
    return LocationInput(
        latitude=latitude,
        longitude=longitude,
        address=address,
        timestamp=timestamp or datetime.now(timezone.utc),
        **kwargs,
    )


def create_location_state(
    current_latitude: float = 37.7749,
    current_longitude: float = -122.4194,
    current_address: str | None = None,
    last_updated: datetime | None = None,
    **kwargs,
) -> LocationState:
    """Create a LocationState with sensible defaults.

    Args:
        current_latitude: Current latitude (default: San Francisco).
        current_longitude: Current longitude (default: San Francisco).
        address: Human-readable address.
        last_updated: When state was last updated (defaults to now).
        **kwargs: Additional fields to override.

    Returns:
        LocationState instance ready for testing.
    """
    return LocationState(
        current_latitude=current_latitude,
        current_longitude=current_longitude,
        current_address=current_address,
        last_updated=last_updated or datetime.now(timezone.utc),
        **kwargs,
    )


# Pre-built location examples
HOME_LOCATION = create_location_input(
    latitude=37.7749,
    longitude=-122.4194,
    address="Home, San Francisco, CA",
    named_location="Home",
)

OFFICE_LOCATION = create_location_input(
    latitude=37.7849,
    longitude=-122.4094,
    address="Office, San Francisco, CA",
    named_location="Office",
)

GYM_LOCATION = create_location_input(
    latitude=37.7650,
    longitude=-122.4300,
    address="Gym, San Francisco, CA",
    named_location="Gym",
)

NYC_LOCATION = create_location_input(
    latitude=40.7128,
    longitude=-74.0060,
    address="New York, NY",
)

LONDON_LOCATION = create_location_input(
    latitude=51.5074,
    longitude=-0.1278,
    address="London, UK",
)

TOKYO_LOCATION = create_location_input(
    latitude=35.6762,
    longitude=139.6503,
    address="Tokyo, Japan",
)

WITH_ALTITUDE = create_location_input(
    latitude=39.7392,
    longitude=-104.9903,
    address="Denver, CO",
    altitude=1609.0,  # 1 mile above sea level
)

WITH_SPEED = create_location_input(
    latitude=37.7749,
    longitude=-122.4194,
    speed=15.0,  # 15 m/s (~34 mph)
    bearing=90.0,  # East
)

WITH_ACCURACY = create_location_input(
    latitude=37.7749,
    longitude=-122.4194,
    accuracy=10.0,  # 10 meter radius
)


# State examples
HOME_STATE = create_location_state(
    current_latitude=37.7749,
    current_longitude=-122.4194,
    current_address="Home, San Francisco, CA",
)

OFFICE_STATE = create_location_state(
    current_latitude=37.7849,
    current_longitude=-122.4094,
    current_address="Office, San Francisco, CA",
)


# Invalid examples for validation testing
INVALID_LOCATIONS = {
    "latitude_too_high": {
        "latitude": 100.0,
        "longitude": -122.4194,
        "timestamp": datetime.now(timezone.utc),
    },
    "latitude_too_low": {
        "latitude": -100.0,
        "longitude": -122.4194,
        "timestamp": datetime.now(timezone.utc),
    },
    "longitude_too_high": {
        "latitude": 37.7749,
        "longitude": 200.0,
        "timestamp": datetime.now(timezone.utc),
    },
    "longitude_too_low": {
        "latitude": 37.7749,
        "longitude": -200.0,
        "timestamp": datetime.now(timezone.utc),
    },
    "negative_accuracy": {
        "latitude": 37.7749,
        "longitude": -122.4194,
        "accuracy": -10.0,
        "timestamp": datetime.now(timezone.utc),
    },
}


# JSON fixtures for API testing
LOCATION_JSON_EXAMPLES = {
    "simple": {
        "modality_type": "location",
        "timestamp": "2025-01-15T10:30:00Z",
        "latitude": 37.7749,
        "longitude": -122.4194,
    },
    "with_address": {
        "modality_type": "location",
        "timestamp": "2025-01-15T14:00:00Z",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "address": "New York, NY",
        "named_location": "Office",
    },
    "with_metadata": {
        "modality_type": "location",
        "timestamp": "2025-01-15T16:00:00Z",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "address": "San Francisco, CA",
        "altitude": 50.0,
        "accuracy": 5.0,
        "speed": 10.0,
        "bearing": 180.0,
    },
}
