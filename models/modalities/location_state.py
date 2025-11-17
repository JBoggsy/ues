"""Location state model."""

from models.base_state import ModalityState


class LocationState(ModalityState):
    """Current user location state.

    Args:
        current_lat: Current latitude coordinate.
        current_long: Current longitude coordinate.
        current_address: Current human-readable address.
        current_named_location: Current location name if applicable.
        location_history: Optional history of recent locations.
    """

    pass
