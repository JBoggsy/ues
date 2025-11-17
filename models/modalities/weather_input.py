"""Weather input model."""

from models.base_input import ModalityInput


class WeatherInput(ModalityInput):
    """Input for updating weather data.

    Args:
        temperature: Temperature in degrees.
        temperature_unit: Unit for temperature (C/F).
        conditions: Weather conditions (sunny, cloudy, rainy, etc.).
        humidity: Humidity percentage.
        wind_speed: Wind speed.
        forecast: Optional forecast data for upcoming periods.
    """

    pass
