"""Unit tests for the WeatherClient and AsyncWeatherClient.

This module tests the weather modality sub-client that provides methods for
getting weather state, querying weather data, and updating weather conditions.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from ues.client._weather import (
    AsyncWeatherClient,
    CurrentWeather,
    DailyFeelsLike,
    DailyForecast,
    DailyTemperature,
    HourlyForecast,
    MinutelyForecast,
    WeatherAlert,
    WeatherClient,
    WeatherCompactStateResponse,
    WeatherCondition,
    WeatherQueryResponse,
    WeatherReport,
    WeatherStateResponse,
)
from ues.client.models import ModalityActionResponse


# =============================================================================
# Typed Weather Model Tests
# =============================================================================


class TestWeatherCondition:
    """Tests for the WeatherCondition model."""

    def test_instantiation(self):
        """Test creating a WeatherCondition."""
        condition = WeatherCondition(
            id=800,
            main="Clear",
            description="clear sky",
            icon="01d",
        )
        assert condition.id == 800
        assert condition.main == "Clear"
        assert condition.description == "clear sky"
        assert condition.icon == "01d"


class TestCurrentWeather:
    """Tests for the CurrentWeather model."""

    def test_instantiation(self):
        """Test creating a CurrentWeather with all fields."""
        weather = CurrentWeather(
            dt=1705315200,
            sunrise=1705294800,
            sunset=1705330800,
            temp=280.0,
            feels_like=277.5,
            pressure=1013,
            humidity=60,
            dew_point=272.0,
            uvi=1.5,
            clouds=10,
            visibility=10000,
            wind_speed=5.0,
            wind_deg=180,
            wind_gust=8.5,
            weather=[
                WeatherCondition(
                    id=800, main="Clear", description="clear sky", icon="01d"
                )
            ],
        )
        assert weather.dt == 1705315200
        assert weather.temp == 280.0
        assert weather.wind_gust == 8.5
        assert len(weather.weather) == 1

    def test_instantiation_without_optional(self):
        """Test creating CurrentWeather without optional wind_gust."""
        weather = CurrentWeather(
            dt=1705315200,
            sunrise=1705294800,
            sunset=1705330800,
            temp=280.0,
            feels_like=277.5,
            pressure=1013,
            humidity=60,
            dew_point=272.0,
            uvi=1.5,
            clouds=10,
            visibility=10000,
            wind_speed=5.0,
            wind_deg=180,
            weather=[
                WeatherCondition(
                    id=800, main="Clear", description="clear sky", icon="01d"
                )
            ],
        )
        assert weather.wind_gust is None


class TestMinutelyForecast:
    """Tests for the MinutelyForecast model."""

    def test_instantiation(self):
        """Test creating a MinutelyForecast."""
        forecast = MinutelyForecast(dt=1705315200, precipitation=0.5)
        assert forecast.dt == 1705315200
        assert forecast.precipitation == 0.5


class TestHourlyForecast:
    """Tests for the HourlyForecast model."""

    def test_instantiation(self):
        """Test creating an HourlyForecast with all fields."""
        forecast = HourlyForecast(
            dt=1705315200,
            temp=280.0,
            feels_like=277.5,
            pressure=1013,
            humidity=60,
            dew_point=272.0,
            uvi=1.5,
            clouds=10,
            visibility=10000,
            wind_speed=5.0,
            wind_deg=180,
            wind_gust=8.5,
            weather=[
                WeatherCondition(
                    id=800, main="Clear", description="clear sky", icon="01d"
                )
            ],
            pop=0.2,
            rain={"1h": 0.5},
            snow=None,
        )
        assert forecast.pop == 0.2
        assert forecast.rain == {"1h": 0.5}
        assert forecast.snow is None

    def test_instantiation_minimal(self):
        """Test creating HourlyForecast without optional fields."""
        forecast = HourlyForecast(
            dt=1705315200,
            temp=280.0,
            feels_like=277.5,
            pressure=1013,
            humidity=60,
            dew_point=272.0,
            uvi=1.5,
            clouds=10,
            wind_speed=5.0,
            wind_deg=180,
            weather=[
                WeatherCondition(
                    id=800, main="Clear", description="clear sky", icon="01d"
                )
            ],
            pop=0.0,
        )
        assert forecast.visibility is None
        assert forecast.wind_gust is None
        assert forecast.rain is None


class TestDailyTemperature:
    """Tests for the DailyTemperature model."""

    def test_instantiation(self):
        """Test creating a DailyTemperature."""
        temp = DailyTemperature(
            day=285.0, min=278.0, max=288.0,
            night=280.0, eve=283.0, morn=279.0,
        )
        assert temp.day == 285.0
        assert temp.min == 278.0
        assert temp.max == 288.0


class TestDailyFeelsLike:
    """Tests for the DailyFeelsLike model."""

    def test_instantiation(self):
        """Test creating a DailyFeelsLike."""
        feels = DailyFeelsLike(day=283.0, night=278.0, eve=281.0, morn=277.0)
        assert feels.day == 283.0
        assert feels.night == 278.0


class TestDailyForecast:
    """Tests for the DailyForecast model."""

    def test_instantiation(self):
        """Test creating a DailyForecast with all fields."""
        forecast = DailyForecast(
            dt=1705315200,
            sunrise=1705294800,
            sunset=1705330800,
            moonrise=1705310000,
            moonset=1705350000,
            moon_phase=0.5,
            summary="Partly cloudy",
            temp=DailyTemperature(
                day=285.0, min=278.0, max=288.0,
                night=280.0, eve=283.0, morn=279.0,
            ),
            feels_like=DailyFeelsLike(
                day=283.0, night=278.0, eve=281.0, morn=277.0,
            ),
            pressure=1013,
            humidity=60,
            dew_point=272.0,
            wind_speed=5.0,
            wind_deg=180,
            wind_gust=8.5,
            weather=[
                WeatherCondition(
                    id=802, main="Clouds",
                    description="scattered clouds", icon="03d",
                )
            ],
            clouds=40,
            pop=0.3,
            rain=1.5,
            snow=None,
            uvi=3.0,
        )
        assert forecast.summary == "Partly cloudy"
        assert forecast.temp.max == 288.0
        assert forecast.feels_like.day == 283.0
        assert forecast.rain == 1.5

    def test_instantiation_minimal(self):
        """Test creating DailyForecast without optional fields."""
        forecast = DailyForecast(
            dt=1705315200,
            sunrise=1705294800,
            sunset=1705330800,
            moonrise=1705310000,
            moonset=1705350000,
            moon_phase=0.5,
            temp=DailyTemperature(
                day=285.0, min=278.0, max=288.0,
                night=280.0, eve=283.0, morn=279.0,
            ),
            feels_like=DailyFeelsLike(
                day=283.0, night=278.0, eve=281.0, morn=277.0,
            ),
            pressure=1013,
            humidity=60,
            dew_point=272.0,
            wind_speed=5.0,
            wind_deg=180,
            weather=[
                WeatherCondition(
                    id=800, main="Clear", description="clear sky", icon="01d",
                )
            ],
            clouds=10,
            pop=0.0,
            uvi=3.0,
        )
        assert forecast.summary is None
        assert forecast.wind_gust is None
        assert forecast.rain is None
        assert forecast.snow is None


class TestWeatherAlert:
    """Tests for the WeatherAlert model."""

    def test_instantiation(self):
        """Test creating a WeatherAlert."""
        alert = WeatherAlert(
            sender_name="NWS",
            event="Winter Storm Warning",
            start=1705315200,
            end=1705401600,
            description="Heavy snow expected.",
            tags=["Snow", "Winter"],
        )
        assert alert.sender_name == "NWS"
        assert alert.event == "Winter Storm Warning"
        assert len(alert.tags) == 2

    def test_instantiation_default_tags(self):
        """Test WeatherAlert with default empty tags."""
        alert = WeatherAlert(
            sender_name="NWS",
            event="Heat Advisory",
            start=1705315200,
            end=1705401600,
            description="Extreme heat expected.",
        )
        assert alert.tags == []


class TestWeatherReport:
    """Tests for the WeatherReport model."""

    def test_instantiation_minimal(self):
        """Test creating a WeatherReport with only required fields."""
        report = WeatherReport(
            lat=40.7128,
            lon=-74.0060,
            timezone="America/New_York",
            timezone_offset=-18000,
        )
        assert report.lat == 40.7128
        assert report.lon == -74.0060
        assert report.timezone == "America/New_York"
        assert report.timezone_offset == -18000
        assert report.current is None
        assert report.minutely is None
        assert report.hourly is None
        assert report.daily is None
        assert report.alerts is None

    def test_instantiation_with_current(self):
        """Test creating a WeatherReport with current weather."""
        report = WeatherReport(
            lat=40.7128,
            lon=-74.0060,
            timezone="America/New_York",
            timezone_offset=-18000,
            current=CurrentWeather(
                dt=1705315200,
                sunrise=1705294800,
                sunset=1705330800,
                temp=280.0,
                feels_like=277.5,
                pressure=1013,
                humidity=60,
                dew_point=272.0,
                uvi=1.5,
                clouds=10,
                visibility=10000,
                wind_speed=5.0,
                wind_deg=180,
                weather=[
                    WeatherCondition(
                        id=800, main="Clear",
                        description="clear sky", icon="01d",
                    )
                ],
            ),
        )
        assert report.current is not None
        assert report.current.temp == 280.0



# =============================================================================
# Response Model Tests
# =============================================================================


class TestWeatherStateResponse:
    """Tests for the WeatherStateResponse model."""

    def test_instantiation(self):
        """Test creating a WeatherStateResponse."""
        response = WeatherStateResponse(
            modality_type="weather",
            last_updated="2025-01-15T10:00:00+00:00",
            update_count=3,
            locations={
                "40.71,-74.01": {
                    "lat": 40.7128,
                    "lon": -74.0060,
                    "timezone": "America/New_York",
                    "current": {
                        "dt": 1705315200,
                        "temp": 45.0,
                        "humidity": 60,
                        "weather": [{"id": 800, "main": "Clear", "description": "clear sky"}],
                    },
                },
            },
            location_count=1,
        )
        assert response.modality_type == "weather"
        assert response.update_count == 3
        assert response.location_count == 1
        assert "40.71,-74.01" in response.locations

    def test_instantiation_empty_locations(self):
        """Test WeatherStateResponse with no locations."""
        response = WeatherStateResponse(
            modality_type="weather",
            last_updated="2025-01-15T10:00:00+00:00",
            update_count=0,
            locations={},
            location_count=0,
        )
        assert response.locations == {}
        assert response.location_count == 0

    def test_no_default_modality_type(self):
        """Test that modality_type has no default and must be provided."""
        with pytest.raises(Exception):
            WeatherStateResponse(
                last_updated="2025-01-15T10:00:00+00:00",
                update_count=0,
                locations={},
                location_count=0,
            )


class TestWeatherQueryResponse:
    """Tests for the WeatherQueryResponse model."""

    def test_instantiation(self):
        """Test creating a WeatherQueryResponse with typed WeatherReport objects."""
        report = WeatherReport(
            lat=40.7128,
            lon=-74.0060,
            timezone="America/New_York",
            timezone_offset=-18000,
            current=CurrentWeather(
                dt=1705315200,
                sunrise=1705294800,
                sunset=1705330800,
                temp=280.0,
                feels_like=277.5,
                pressure=1013,
                humidity=60,
                dew_point=272.0,
                uvi=1.5,
                clouds=10,
                visibility=10000,
                wind_speed=5.0,
                wind_deg=180,
                weather=[
                    WeatherCondition(
                        id=800, main="Clear",
                        description="clear sky", icon="01d",
                    )
                ],
            ),
        )
        response = WeatherQueryResponse(
            reports=[report],
            count=1,
            total_count=1,
        )
        assert response.count == 1
        assert response.total_count == 1
        assert len(response.reports) == 1
        assert isinstance(response.reports[0], WeatherReport)
        assert response.reports[0].lat == 40.7128

    def test_instantiation_from_dict(self):
        """Test creating a WeatherQueryResponse from dict data (as from JSON)."""
        response = WeatherQueryResponse(
            reports=[
                {
                    "lat": 40.7128,
                    "lon": -74.0060,
                    "timezone": "America/New_York",
                    "timezone_offset": -18000,
                },
            ],
            count=1,
            total_count=1,
        )
        assert len(response.reports) == 1
        assert isinstance(response.reports[0], WeatherReport)

    def test_instantiation_with_error(self):
        """Test WeatherQueryResponse with an error message."""
        response = WeatherQueryResponse(
            reports=[],
            count=0,
            total_count=0,
            error="No weather data available for the specified location",
        )
        assert response.error is not None
        assert "No weather data" in response.error

    def test_instantiation_defaults(self):
        """Test WeatherQueryResponse defaults."""
        response = WeatherQueryResponse(
            reports=[],
            count=0,
        )
        assert response.total_count == 0
        assert response.error is None


# =============================================================================
# WeatherClient Tests
# =============================================================================


class TestWeatherClientGetState:
    """Tests for WeatherClient.get_state() method."""

    def test_get_state(self):
        """Test getting weather state."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "modality_type": "weather",
            "last_updated": "2025-01-15T10:00:00+00:00",
            "update_count": 3,
            "locations": {
                "40.71,-74.01": {
                    "lat": 40.7128,
                    "lon": -74.0060,
                    "timezone": "America/New_York",
                    "current": {"temp": 45.0},
                },
            },
            "location_count": 1,
        }

        client = WeatherClient(mock_http)
        result = client.get_state()

        mock_http.get.assert_called_once_with("/weather/state", params=None)
        assert isinstance(result, WeatherStateResponse)
        assert result.location_count == 1

    def test_get_state_compact(self):
        """Test getting compact weather state."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "modality_type": "weather",
            "last_updated": "2025-01-15T10:00:00+00:00",
            "update_count": 5,
            "location_count": 2,
            "locations": {
                "40.71,-74.01": {
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "last_updated": "2025-01-15T10:00:00+00:00",
                    "current_report": {"temp": 45.0},
                    "report_count": 3,
                },
                "34.05,-118.24": {
                    "latitude": 34.0522,
                    "longitude": -118.2437,
                    "last_updated": "2025-01-15T09:00:00+00:00",
                    "current_report": None,
                    "report_count": 0,
                },
            },
        }

        client = WeatherClient(mock_http)
        result = client.get_state(compact=True)

        mock_http.get.assert_called_once_with("/weather/state", params={"compact": True})
        assert isinstance(result, WeatherCompactStateResponse)
        assert result.location_count == 2
        assert result.update_count == 5
        assert "40.71,-74.01" in result.locations
        assert "34.05,-118.24" in result.locations

    def test_get_state_compact_false_returns_full(self):
        """Test that compact=False returns full state (default behavior)."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "modality_type": "weather",
            "last_updated": "2025-01-15T10:00:00+00:00",
            "update_count": 0,
            "locations": {},
            "location_count": 0,
        }

        client = WeatherClient(mock_http)
        result = client.get_state(compact=False)

        mock_http.get.assert_called_once_with("/weather/state", params=None)
        assert isinstance(result, WeatherStateResponse)


class TestWeatherClientQuery:
    """Tests for WeatherClient.query() method."""

    def test_query_minimal(self):
        """Test querying weather with minimal parameters."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "reports": [
                {
                    "lat": 40.7128,
                    "lon": -74.0060,
                    "timezone": "America/New_York",
                    "timezone_offset": -18000,
                },
            ],
            "count": 1,
            "total_count": 1,
        }

        client = WeatherClient(mock_http)
        result = client.query(lat=40.7128, lon=-74.0060)

        mock_http.post.assert_called_once()
        call_args = mock_http.post.call_args
        assert call_args[0][0] == "/weather/query"
        assert call_args[1]["json"]["lat"] == 40.7128
        assert call_args[1]["json"]["lon"] == -74.0060
        assert isinstance(result, WeatherQueryResponse)
        assert result.count == 1

    def test_query_with_exclude(self):
        """Test querying weather with exclude sections."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "reports": [],
            "count": 0,
            "total_count": 0,
        }

        client = WeatherClient(mock_http)
        result = client.query(
            lat=40.7128,
            lon=-74.0060,
            exclude=["minutely", "hourly", "alerts"],
        )

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["exclude"] == ["minutely", "hourly", "alerts"]

    def test_query_with_units(self):
        """Test querying weather with different unit systems."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "reports": [],
            "count": 0,
            "total_count": 0,
        }

        client = WeatherClient(mock_http)
        result = client.query(
            lat=40.7128,
            lon=-74.0060,
            units="imperial",
        )

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["units"] == "imperial"

    def test_query_with_time_range(self):
        """Test querying weather with time range."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "reports": [],
            "count": 0,
            "total_count": 0,
        }

        client = WeatherClient(mock_http)
        result = client.query(
            lat=40.7128,
            lon=-74.0060,
            from_time=1705315200,
            to_time=1705401600,
        )

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["from_time"] == 1705315200
        assert call_args[1]["json"]["to_time"] == 1705401600

    def test_query_with_pagination(self):
        """Test querying weather with pagination."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "reports": [],
            "count": 0,
            "total_count": 100,
        }

        client = WeatherClient(mock_http)
        result = client.query(
            lat=40.7128,
            lon=-74.0060,
            limit=10,
            offset=20,
        )

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["limit"] == 10
        assert call_args[1]["json"]["offset"] == 20


class TestWeatherClientUpdate:
    """Tests for WeatherClient.update() method."""

    def test_update(self):
        """Test updating weather for a location."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Weather updated",
            "modality": "weather",
        }

        client = WeatherClient(mock_http)
        result = client.update(
            latitude=40.7128,
            longitude=-74.0060,
            report={
                "lat": 40.7128,
                "lon": -74.0060,
                "timezone": "America/New_York",
                "current": {
                    "dt": 1705315200,
                    "temp": 45.0,
                    "humidity": 60,
                    "weather": [{"id": 800, "main": "Clear", "description": "clear sky"}],
                },
            },
        )

        mock_http.post.assert_called_once()
        call_args = mock_http.post.call_args
        assert call_args[0][0] == "/weather/update"
        assert call_args[1]["json"]["latitude"] == 40.7128
        assert call_args[1]["json"]["longitude"] == -74.0060
        assert call_args[1]["json"]["report"]["timezone"] == "America/New_York"
        assert isinstance(result, ModalityActionResponse)

    def test_update_with_forecast(self):
        """Test updating weather with full forecast data."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Weather updated",
            "modality": "weather",
        }

        client = WeatherClient(mock_http)
        result = client.update(
            latitude=40.7128,
            longitude=-74.0060,
            report={
                "lat": 40.7128,
                "lon": -74.0060,
                "timezone": "America/New_York",
                "current": {
                    "dt": 1705315200,
                    "temp": 45.0,
                    "humidity": 60,
                    "weather": [{"id": 800, "main": "Clear"}],
                },
                "hourly": [
                    {"dt": 1705318800, "temp": 46.0},
                    {"dt": 1705322400, "temp": 47.0},
                ],
                "daily": [
                    {"dt": 1705315200, "temp": {"min": 40.0, "max": 50.0}},
                ],
                "alerts": [],
            },
        )

        call_args = mock_http.post.call_args
        assert "hourly" in call_args[1]["json"]["report"]
        assert "daily" in call_args[1]["json"]["report"]

    def test_update_with_typed_report(self):
        """Test updating weather using a WeatherReport model instance."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Weather updated",
            "modality": "weather",
        }

        report = WeatherReport(
            lat=40.7128,
            lon=-74.0060,
            timezone="America/New_York",
            timezone_offset=-18000,
            current=CurrentWeather(
                dt=1705315200,
                sunrise=1705294800,
                sunset=1705330800,
                temp=280.0,
                feels_like=277.5,
                pressure=1013,
                humidity=60,
                dew_point=272.0,
                uvi=1.5,
                clouds=10,
                visibility=10000,
                wind_speed=5.0,
                wind_deg=180,
                weather=[
                    WeatherCondition(
                        id=800, main="Clear",
                        description="clear sky", icon="01d",
                    )
                ],
            ),
        )

        client = WeatherClient(mock_http)
        result = client.update(
            latitude=40.7128,
            longitude=-74.0060,
            report=report,
        )

        call_args = mock_http.post.call_args
        report_data = call_args[1]["json"]["report"]
        assert report_data["lat"] == 40.7128
        assert report_data["timezone"] == "America/New_York"
        assert report_data["current"]["temp"] == 280.0
        assert isinstance(result, ModalityActionResponse)


# =============================================================================
# AsyncWeatherClient Tests
# =============================================================================


class TestAsyncWeatherClientGetState:
    """Tests for AsyncWeatherClient.get_state() method."""

    async def test_get_state(self):
        """Test getting weather state asynchronously."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "modality_type": "weather",
            "last_updated": "2025-01-15T10:00:00+00:00",
            "update_count": 3,
            "locations": {},
            "location_count": 0,
        }

        client = AsyncWeatherClient(mock_http)
        result = await client.get_state()

        mock_http.get.assert_called_once_with("/weather/state", params=None)
        assert isinstance(result, WeatherStateResponse)

    async def test_get_state_compact(self):
        """Test getting compact weather state asynchronously."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "modality_type": "weather",
            "last_updated": "2025-01-15T10:00:00+00:00",
            "update_count": 1,
            "location_count": 0,
            "locations": {},
        }

        client = AsyncWeatherClient(mock_http)
        result = await client.get_state(compact=True)

        mock_http.get.assert_called_once_with("/weather/state", params={"compact": True})
        assert isinstance(result, WeatherCompactStateResponse)
        assert result.update_count == 1


class TestAsyncWeatherClientQuery:
    """Tests for AsyncWeatherClient.query() method."""

    async def test_query(self):
        """Test querying weather asynchronously."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "reports": [
                {
                    "lat": 40.7128,
                    "lon": -74.0060,
                    "timezone": "America/New_York",
                    "timezone_offset": -18000,
                },
            ],
            "count": 1,
            "total_count": 1,
        }

        client = AsyncWeatherClient(mock_http)
        result = await client.query(lat=40.7128, lon=-74.0060)

        mock_http.post.assert_called_once()
        assert isinstance(result, WeatherQueryResponse)


class TestAsyncWeatherClientUpdate:
    """Tests for AsyncWeatherClient.update() method."""

    async def test_update(self):
        """Test updating weather asynchronously."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Weather updated",
            "modality": "weather",
        }

        client = AsyncWeatherClient(mock_http)
        result = await client.update(
            latitude=40.7128,
            longitude=-74.0060,
            report={
                "lat": 40.7128,
                "lon": -74.0060,
                "timezone": "America/New_York",
                "current": {"temp": 45.0},
            },
        )

        assert isinstance(result, ModalityActionResponse)
