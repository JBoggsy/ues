"""Location input model."""

from models.base_input import ModalityInput


class LocationInput(ModalityInput):
    """Input for updating user location.

    Args:
        lat: Latitude coordinate.
        long: Longitude coordinate.
        address: Human-readable address.
        named_location: Optional name for the location (e.g., "Home", "Office").
    """

    pass
