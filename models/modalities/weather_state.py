"""Weather state model."""

import os
from copy import deepcopy
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from models.base_input import ModalityInput
from models.base_state import ModalityState
from models.modalities.weather_input import WeatherReport
from models.modalities.weather_input import WeatherInput


class WeatherReportHistoryEntry(BaseModel):
    """A single entry in the weather report history.

    Tracks a historical weather report with timestamp.

    Args:
        timestamp: When this weather report was recorded (simulator time).
        report: The complete weather report.
    """

    timestamp: datetime = Field(description="When this weather report was recorded")
    report: WeatherReport = Field(description="The complete weather report")

    def to_dict(self) -> dict[str, Any]:
        """Convert this entry to a dictionary.

        Returns:
            Dictionary representation of this report entry.
        """
        return {
            "timestamp": self.timestamp.isoformat(),
            "report": self.report.model_dump(),
        }


class WeatherLocationState(BaseModel):
    """State for a single weather location.

    Tracks weather data for one geographic location including current conditions
    and historical reports.

    Args:
        latitude: Location latitude.
        longitude: Location longitude.
        current_report: Current weather report.
        first_seen: When this location was first added.
        last_updated: When this location was last updated.
        update_count: Number of updates for this location.
        report_history: List of historical reports.
    """

    latitude: float = Field(description="Location latitude")
    longitude: float = Field(description="Location longitude")
    current_report: WeatherReport = Field(description="Current weather report")
    first_seen: datetime = Field(description="When this location was first added")
    last_updated: datetime = Field(description="When this location was last updated")
    update_count: int = Field(default=1, description="Number of updates for this location")
    report_history: list[WeatherReportHistoryEntry] = Field(
        default_factory=list, description="List of historical reports"
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert this location state to a dictionary.

        Returns:
            Dictionary representation of this location state.
        """
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "current_report": self.current_report.model_dump(),
            "first_seen": self.first_seen.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "update_count": self.update_count,
            "history_count": len(self.report_history),
        }


class WeatherState(ModalityState):
    """Current weather state.

    Tracks weather conditions at multiple locations with historical data.
    Supports both simulated weather updates and real weather queries via OpenWeather API.

    Args:
        modality_type: Always "weather" for this state type.
        last_updated: Simulator time when this state was last modified.
        update_count: Number of times this state has been modified.
        locations: Dict mapping location keys to WeatherLocationState objects.
        max_history_per_location: Maximum historical reports per location.
        openweather_api_key: Optional API key for real weather queries.
    """

    modality_type: str = Field(default="weather", frozen=True)
    locations: dict[str, WeatherLocationState] = Field(
        default_factory=dict, description="Weather data for tracked locations"
    )
    max_history_per_location: int = Field(
        default=100, description="Maximum historical reports per location"
    )
    openweather_api_key: Optional[str] = Field(
        default=None, description="OpenWeather API key for real weather queries"
    )

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True

    def __init__(self, **data):
        """Initialize weather state.

        Attempts to load OpenWeather API key from environment variable if not provided.

        Args:
            **data: Keyword arguments for Pydantic model initialization.
        """
        if "openweather_api_key" not in data or data["openweather_api_key"] is None:
            data["openweather_api_key"] = os.environ.get("OPENWEATHER_API_KEY")
        super().__init__(**data)

    def _get_location_key(self, lat: float, lon: float) -> str:
        """Normalize coordinates to a location key.

        Rounds coordinates to ~0.01 degrees (~1km precision) to prevent
        duplicate nearby locations.

        Args:
            lat: Latitude.
            lon: Longitude.

        Returns:
            Normalized location key string.
        """
        normalized_lat = round(lat, 2)
        normalized_lon = round(lon, 2)
        return f"{normalized_lat:.2f},{normalized_lon:.2f}"

    def apply_input(self, input_data: ModalityInput) -> None:
        """Apply a WeatherInput to modify this state.

        Updates weather for a location, creating location entry if new.
        Adds current report to history and sets new current report.
        Manages history size automatically.

        Args:
            input_data: The WeatherInput to apply to this state.

        Raises:
            ValueError: If input_data is not a WeatherInput.
        """
        if not isinstance(input_data, WeatherInput):
            raise ValueError(
                f"WeatherState can only apply WeatherInput, got {type(input_data)}"
            )

        location_key = self._get_location_key(input_data.latitude, input_data.longitude)

        if location_key in self.locations:
            location = self.locations[location_key]

            history_entry = WeatherReportHistoryEntry(
                timestamp=location.last_updated,
                report=location.current_report,
            )
            location.report_history.append(history_entry)

            if len(location.report_history) > self.max_history_per_location:
                location.report_history.pop(0)

            location.current_report = input_data.report
            location.last_updated = input_data.timestamp
            location.update_count += 1
        else:
            self.locations[location_key] = WeatherLocationState(
                latitude=input_data.latitude,
                longitude=input_data.longitude,
                current_report=input_data.report,
                first_seen=input_data.timestamp,
                last_updated=input_data.timestamp,
            )

        self.last_updated = input_data.timestamp
        self.update_count += 1

    def get_snapshot(self) -> dict[str, Any]:
        """Return a complete snapshot of current state for API responses.

        Returns:
            Dictionary representation of all locations and their current weather.
        """
        return {
            "modality_type": self.modality_type,
            "last_updated": self.last_updated.isoformat(),
            "update_count": self.update_count,
            "locations": {
                key: location.to_dict() for key, location in self.locations.items()
            },
            "location_count": len(self.locations),
        }

    def validate_state(self) -> list[str]:
        """Validate internal state consistency and return any issues.

        Checks for:
        - Location coordinate validity
        - History ordering (chronological)
        - History size limits

        Returns:
            List of validation error messages (empty list if valid).
        """
        issues = []

        for location_key, location in self.locations.items():
            if not -90 <= location.latitude <= 90:
                issues.append(
                    f"Location {location_key} has invalid latitude {location.latitude}"
                )
            if not -180 <= location.longitude <= 180:
                issues.append(
                    f"Location {location_key} has invalid longitude {location.longitude}"
                )

            for i in range(1, len(location.report_history)):
                if (
                    location.report_history[i].timestamp
                    < location.report_history[i - 1].timestamp
                ):
                    issues.append(
                        f"Location {location_key} history not in chronological order at index {i}"
                    )

            if len(location.report_history) > self.max_history_per_location:
                issues.append(
                    f"Location {location_key} history size {len(location.report_history)} "
                    f"exceeds maximum {self.max_history_per_location}"
                )

        return issues

    def _filter_report(
        self, report: WeatherReport, exclude: Optional[list[str]]
    ) -> WeatherReport:
        """Filter out excluded sections from a weather report.

        Args:
            report: The weather report to filter.
            exclude: List of sections to exclude (current, minutely, hourly, daily, alerts).

        Returns:
            Filtered weather report with excluded sections set to None.
        """
        if not exclude:
            return report

        filtered_report = deepcopy(report)

        if "current" in exclude:
            filtered_report.current = None
        if "minutely" in exclude:
            filtered_report.minutely = None
        if "hourly" in exclude:
            filtered_report.hourly = None
        if "daily" in exclude:
            filtered_report.daily = None
        if "alerts" in exclude:
            filtered_report.alerts = None

        return filtered_report

    def _convert_units(
        self, report: WeatherReport, units: Literal["standard", "metric", "imperial"]
    ) -> WeatherReport:
        """Convert weather report units.

        Weather is stored internally in standard units (Kelvin, m/s).
        This converts to requested units on query.

        Args:
            report: The weather report to convert.
            units: Target unit system (standard, metric, imperial).

        Returns:
            Weather report with converted units.
        """
        if units == "standard":
            return report

        converted_report = deepcopy(report)

        def convert_temp(temp_k: float) -> float:
            if units == "metric":
                return temp_k - 273.15
            else:
                return (temp_k - 273.15) * 9 / 5 + 32

        def convert_speed(speed_ms: float) -> float:
            if units == "imperial":
                return speed_ms * 2.23694
            return speed_ms

        if converted_report.current:
            converted_report.current.temp = convert_temp(converted_report.current.temp)
            converted_report.current.feels_like = convert_temp(
                converted_report.current.feels_like
            )
            converted_report.current.dew_point = convert_temp(
                converted_report.current.dew_point
            )
            converted_report.current.wind_speed = convert_speed(
                converted_report.current.wind_speed
            )
            if converted_report.current.wind_gust:
                converted_report.current.wind_gust = convert_speed(
                    converted_report.current.wind_gust
                )

        if converted_report.hourly:
            for hour in converted_report.hourly:
                hour.temp = convert_temp(hour.temp)
                hour.feels_like = convert_temp(hour.feels_like)
                hour.dew_point = convert_temp(hour.dew_point)
                hour.wind_speed = convert_speed(hour.wind_speed)
                if hour.wind_gust:
                    hour.wind_gust = convert_speed(hour.wind_gust)

        if converted_report.daily:
            for day in converted_report.daily:
                day.temp.day = convert_temp(day.temp.day)
                day.temp.min = convert_temp(day.temp.min)
                day.temp.max = convert_temp(day.temp.max)
                day.temp.night = convert_temp(day.temp.night)
                day.temp.eve = convert_temp(day.temp.eve)
                day.temp.morn = convert_temp(day.temp.morn)
                day.feels_like.day = convert_temp(day.feels_like.day)
                day.feels_like.night = convert_temp(day.feels_like.night)
                day.feels_like.eve = convert_temp(day.feels_like.eve)
                day.feels_like.morn = convert_temp(day.feels_like.morn)
                day.dew_point = convert_temp(day.dew_point)
                day.wind_speed = convert_speed(day.wind_speed)
                if day.wind_gust:
                    day.wind_gust = convert_speed(day.wind_gust)

        return converted_report

    def query_openweather_api(
        self,
        lat: float,
        lon: float,
        exclude: Optional[list[str]] = None,
        units: Literal["standard", "metric", "imperial"] = "standard",
    ) -> WeatherReport:
        """Query OpenWeather API for real weather data.

        Makes HTTP request to OpenWeather One Call API, parses response,
        creates WeatherInput, and applies it to state.

        Args:
            lat: Latitude to query.
            lon: Longitude to query.
            exclude: Sections to exclude from API query.
            units: Unit system to use (API returns data in these units).

        Returns:
            Weather report from OpenWeather API.

        Raises:
            ValueError: If API key is not configured.
            RuntimeError: If API request fails.
        """
        import requests

        from models.modalities.weather_input import WeatherInput

        if not self.openweather_api_key:
            raise ValueError(
                "OpenWeather API key not configured. Set OPENWEATHER_API_KEY environment variable."
            )

        url = "https://api.openweathermap.org/data/3.0/onecall"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.openweather_api_key,
            "units": "standard",
        }

        if exclude:
            params["exclude"] = ",".join(exclude)

        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            raise RuntimeError(
                f"OpenWeather API request failed: {response.status_code} {response.text}"
            )

        data = response.json()
        report = WeatherReport(**data)

        weather_input = WeatherInput(
            timestamp=datetime.now(),
            input_id=f"openweather_{lat}_{lon}_{datetime.now().timestamp()}",
            latitude=lat,
            longitude=lon,
            report=report,
        )

        self.apply_input(weather_input)

        return report

    def query(self, query_params: dict[str, Any]) -> dict[str, Any]:
        """Execute a query against this state.

        Supports filtering weather data by location, time range, and format options.
        Special case: real=true queries OpenWeather API and updates state.

        Supported query parameters:
            - lat (required): Latitude to query
            - lon (required): Longitude to query
            - exclude: List of sections to exclude (current, minutely, hourly, daily, alerts)
            - units: Unit system (standard, metric, imperial) - default: standard
            - from: Unix timestamp - return all reports since this time
            - to: Unix timestamp - return reports up to this time (requires from)
            - real: If True, query OpenWeather API instead of simulated data

        Args:
            query_params: Dictionary of query parameters.

        Returns:
            Dictionary containing weather reports matching the query.

        Raises:
            ValueError: If required parameters are missing or invalid.
        """
        if "lat" not in query_params or "lon" not in query_params:
            raise ValueError("Query must include 'lat' and 'lon' parameters")

        lat = float(query_params["lat"])
        lon = float(query_params["lon"])
        exclude = query_params.get("exclude")
        if exclude and isinstance(exclude, str):
            exclude = [s.strip() for s in exclude.split(",")]
        units = query_params.get("units", "standard")
        from_time = query_params.get("from")
        to_time = query_params.get("to")
        real = query_params.get("real", False)

        if real:
            report = self.query_openweather_api(lat, lon, exclude, units)
            filtered_report = self._filter_report(report, exclude)
            converted_report = self._convert_units(filtered_report, units)
            return {"reports": [converted_report.model_dump()], "count": 1}

        location_key = self._get_location_key(lat, lon)

        if location_key not in self.locations:
            return {"reports": [], "count": 0, "error": "No weather data for this location"}

        location = self.locations[location_key]
        reports = []

        if from_time:
            from_dt = datetime.fromtimestamp(from_time) if isinstance(from_time, (int, float)) else from_time

            for entry in location.report_history:
                if to_time:
                    to_dt = datetime.fromtimestamp(to_time) if isinstance(to_time, (int, float)) else to_time
                    if from_dt <= entry.timestamp <= to_dt:
                        filtered_report = self._filter_report(entry.report, exclude)
                        converted_report = self._convert_units(filtered_report, units)
                        reports.append(converted_report.model_dump())
                elif entry.timestamp >= from_dt:
                    filtered_report = self._filter_report(entry.report, exclude)
                    converted_report = self._convert_units(filtered_report, units)
                    reports.append(converted_report.model_dump())

            if (to_time is None or location.last_updated <= to_dt) and location.last_updated >= from_dt:
                filtered_report = self._filter_report(location.current_report, exclude)
                converted_report = self._convert_units(filtered_report, units)
                reports.append(converted_report.model_dump())
        else:
            filtered_report = self._filter_report(location.current_report, exclude)
            converted_report = self._convert_units(filtered_report, units)
            reports.append(converted_report.model_dump())

        return {"reports": reports, "count": len(reports)}
