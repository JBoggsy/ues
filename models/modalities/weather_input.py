"""Weather input model."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from models.base_input import ModalityInput


class WeatherCondition(BaseModel):
    """A single weather condition descriptor.

    Represents a weather condition as defined by the OpenWeather API.

    Args:
        id: Weather condition id (e.g., 800 for clear sky).
        main: Group of weather parameters (Rain, Snow, Clouds, etc.).
        description: Weather condition description (e.g., "light rain").
        icon: Weather icon id (e.g., "01d" for day clear sky).
    """

    id: int = Field(description="Weather condition id")
    main: str = Field(description="Group of weather parameters")
    description: str = Field(description="Weather condition description")
    icon: str = Field(description="Weather icon id")


class CurrentWeather(BaseModel):
    """Current weather conditions.

    Args:
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

    dt: int = Field(description="Current time, Unix timestamp")
    sunrise: int = Field(description="Sunrise time, Unix timestamp")
    sunset: int = Field(description="Sunset time, Unix timestamp")
    temp: float = Field(description="Temperature")
    feels_like: float = Field(description="Feels like temperature")
    pressure: int = Field(description="Atmospheric pressure, hPa")
    humidity: int = Field(description="Humidity percentage")
    dew_point: float = Field(description="Dew point temperature")
    uvi: float = Field(description="UV index")
    clouds: int = Field(description="Cloudiness percentage")
    visibility: int = Field(description="Visibility in meters")
    wind_speed: float = Field(description="Wind speed")
    wind_deg: int = Field(description="Wind direction in degrees")
    wind_gust: Optional[float] = Field(default=None, description="Wind gust speed")
    weather: list[WeatherCondition] = Field(description="Weather conditions")


class MinutelyForecast(BaseModel):
    """Minute-by-minute precipitation forecast.

    Args:
        dt: Time of forecast, Unix timestamp (UTC).
        precipitation: Precipitation volume in mm.
    """

    dt: int = Field(description="Time of forecast, Unix timestamp")
    precipitation: float = Field(description="Precipitation volume in mm")


class HourlyForecast(BaseModel):
    """Hourly weather forecast.

    Args:
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

    dt: int = Field(description="Time of forecast, Unix timestamp")
    temp: float = Field(description="Temperature")
    feels_like: float = Field(description="Feels like temperature")
    pressure: int = Field(description="Atmospheric pressure, hPa")
    humidity: int = Field(description="Humidity percentage")
    dew_point: float = Field(description="Dew point temperature")
    uvi: float = Field(description="UV index")
    clouds: int = Field(description="Cloudiness percentage")
    visibility: Optional[int] = Field(default=None, description="Visibility in meters")
    wind_speed: float = Field(description="Wind speed")
    wind_deg: int = Field(description="Wind direction in degrees")
    wind_gust: Optional[float] = Field(default=None, description="Wind gust speed")
    weather: list[WeatherCondition] = Field(description="Weather conditions")
    pop: float = Field(description="Probability of precipitation")
    rain: Optional[dict[str, float]] = Field(
        default=None, description="Rain volume in mm"
    )
    snow: Optional[dict[str, float]] = Field(
        default=None, description="Snow volume in mm"
    )


class DailyTemperature(BaseModel):
    """Daily temperature breakdown.

    Args:
        day: Day temperature.
        min: Minimum daily temperature.
        max: Maximum daily temperature.
        night: Night temperature.
        eve: Evening temperature.
        morn: Morning temperature.
    """

    day: float = Field(description="Day temperature")
    min: float = Field(description="Minimum daily temperature")
    max: float = Field(description="Maximum daily temperature")
    night: float = Field(description="Night temperature")
    eve: float = Field(description="Evening temperature")
    morn: float = Field(description="Morning temperature")


class DailyFeelsLike(BaseModel):
    """Daily feels like temperature breakdown.

    Args:
        day: Day feels like temperature.
        night: Night feels like temperature.
        eve: Evening feels like temperature.
        morn: Morning feels like temperature.
    """

    day: float = Field(description="Day feels like temperature")
    night: float = Field(description="Night feels like temperature")
    eve: float = Field(description="Evening feels like temperature")
    morn: float = Field(description="Morning feels like temperature")


class DailyForecast(BaseModel):
    """Daily weather forecast.

    Args:
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

    dt: int = Field(description="Time of forecast, Unix timestamp")
    sunrise: int = Field(description="Sunrise time, Unix timestamp")
    sunset: int = Field(description="Sunset time, Unix timestamp")
    moonrise: int = Field(description="Moonrise time, Unix timestamp")
    moonset: int = Field(description="Moonset time, Unix timestamp")
    moon_phase: float = Field(description="Moon phase (0-1)")
    summary: Optional[str] = Field(default=None, description="Human-readable summary")
    temp: DailyTemperature = Field(description="Temperature breakdown")
    feels_like: DailyFeelsLike = Field(description="Feels like temperature breakdown")
    pressure: int = Field(description="Atmospheric pressure, hPa")
    humidity: int = Field(description="Humidity percentage")
    dew_point: float = Field(description="Dew point temperature")
    wind_speed: float = Field(description="Wind speed")
    wind_deg: int = Field(description="Wind direction in degrees")
    wind_gust: Optional[float] = Field(default=None, description="Wind gust speed")
    weather: list[WeatherCondition] = Field(description="Weather conditions")
    clouds: int = Field(description="Cloudiness percentage")
    pop: float = Field(description="Probability of precipitation")
    rain: Optional[float] = Field(default=None, description="Rain volume in mm")
    snow: Optional[float] = Field(default=None, description="Snow volume in mm")
    uvi: float = Field(description="UV index")


class WeatherAlert(BaseModel):
    """Weather alert information.

    Args:
        sender_name: Name of the alert source.
        event: Alert event name.
        start: Alert start time, Unix timestamp.
        end: Alert end time, Unix timestamp.
        description: Alert description.
        tags: List of alert tags.
    """

    sender_name: str = Field(description="Name of the alert source")
    event: str = Field(description="Alert event name")
    start: int = Field(description="Alert start time, Unix timestamp")
    end: int = Field(description="Alert end time, Unix timestamp")
    description: str = Field(description="Alert description")
    tags: list[str] = Field(default_factory=list, description="List of alert tags")


class WeatherReport(BaseModel):
    """Complete weather report for a location.

    Conforms to the OpenWeather One Call API format.

    Args:
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

    lat: float = Field(description="Location latitude")
    lon: float = Field(description="Location longitude")
    timezone: str = Field(description="Timezone identifier")
    timezone_offset: int = Field(description="Timezone offset in seconds from UTC")
    current: Optional[CurrentWeather] = Field(
        default=None, description="Current weather conditions"
    )
    minutely: Optional[list[MinutelyForecast]] = Field(
        default=None, description="Minute-by-minute forecast"
    )
    hourly: Optional[list[HourlyForecast]] = Field(
        default=None, description="Hourly forecast"
    )
    daily: Optional[list[DailyForecast]] = Field(
        default=None, description="Daily forecast"
    )
    alerts: Optional[list[WeatherAlert]] = Field(
        default=None, description="Weather alerts"
    )


class WeatherInput(ModalityInput):
    """Input for updating weather at a location.

    Represents a weather update event for a specific location. Unlike location and time
    modalities, weather supports multiple locations simultaneously.

    Args:
        modality_type: Always "weather" for this input type.
        timestamp: When this weather update logically occurred (simulator time).
        input_id: Unique identifier for this specific weather update.
        latitude: Location latitude in decimal degrees (-90 to 90).
        longitude: Location longitude in decimal degrees (-180 to 180).
        report: Complete weather report conforming to OpenWeather API format.
    """

    modality_type: str = Field(default="weather", frozen=True)
    latitude: float = Field(
        description="Location latitude in decimal degrees (-90 to 90)"
    )
    longitude: float = Field(
        description="Location longitude in decimal degrees (-180 to 180)"
    )
    report: WeatherReport = Field(
        description="Complete weather report conforming to OpenWeather API format"
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

    def validate_input(self) -> None:
        """Perform modality-specific validation beyond Pydantic field validation.

        Validates that the report coordinates match the input coordinates and that
        the report contains valid data.

        Raises:
            ValueError: If report coordinates don't match or report is invalid.
        """
        if abs(self.report.lat - self.latitude) > 0.01:
            raise ValueError(
                f"Report latitude {self.report.lat} doesn't match input latitude {self.latitude}"
            )
        if abs(self.report.lon - self.longitude) > 0.01:
            raise ValueError(
                f"Report longitude {self.report.lon} doesn't match input longitude {self.longitude}"
            )

    def get_affected_entities(self) -> list[str]:
        """Return list of entity IDs affected by this input.

        For weather updates, we track the location as the affected entity.

        Returns:
            List containing the location identifier.
        """
        return [f"weather_location:{self.latitude:.4f},{self.longitude:.4f}"]

    def get_summary(self) -> str:
        """Return human-readable one-line summary of this input.

        Examples:
            - "Weather at (40.7128, -74.0060): Cloudy, 72°F"
            - "Weather at (34.0522, -118.2437): Clear sky, 85°F"

        Returns:
            Brief description of the weather update for logging/UI display.
        """
        if self.report.current and self.report.current.weather:
            condition = self.report.current.weather[0].description
            temp_k = self.report.current.temp
            temp_f = (temp_k - 273.15) * 9 / 5 + 32
            return f"Weather at ({self.latitude:.4f}, {self.longitude:.4f}): {condition.capitalize()}, {temp_f:.0f}°F"
        else:
            return f"Weather update at ({self.latitude:.4f}, {self.longitude:.4f})"

    def should_merge_with(self, other: "ModalityInput") -> bool:
        """Determine if this input should be merged with another input.

        Weather updates should not be merged as each represents a distinct
        weather state change that should be tracked separately.

        Args:
            other: Another input to compare against.

        Returns:
            Always False for weather inputs.
        """
        return False