"""Unit tests for the WeatherClient and AsyncWeatherClient.

This module tests the weather modality sub-client that provides methods for
getting weather state, querying weather data, and updating weather conditions.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from client._weather import (
    AsyncWeatherClient,
    WeatherClient,
    WeatherQueryResponse,
    WeatherStateResponse,
)
from client.models import ModalityActionResponse


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


class TestWeatherQueryResponse:
    """Tests for the WeatherQueryResponse model."""

    def test_instantiation(self):
        """Test creating a WeatherQueryResponse."""
        response = WeatherQueryResponse(
            reports=[
                {
                    "lat": 40.7128,
                    "lon": -74.0060,
                    "timezone": "America/New_York",
                    "current": {
                        "dt": 1705315200,
                        "temp": 45.0,
                        "humidity": 60,
                    },
                },
            ],
            count=1,
            total_count=1,
        )
        assert response.count == 1
        assert response.total_count == 1
        assert len(response.reports) == 1

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
                    "current": {"temp": 45.0},
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

    def test_query_real_weather(self):
        """Test querying real weather data."""
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
            real=True,
        )

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["real"] is True

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
                    "current": {"temp": 45.0},
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
