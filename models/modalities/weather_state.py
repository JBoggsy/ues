"""Weather state model."""

from models.base_state import ModalityState


class WeatherState(ModalityState):
    """Current weather state.

    Args:
        current_temperature: Current temperature.
        temperature_unit: Unit for temperature (C/F).
        current_conditions: Current weather conditions.
        current_humidity: Current humidity percentage.
        current_wind_speed: Current wind speed.
        forecast: Forecast data for upcoming periods.
    """

    pass
