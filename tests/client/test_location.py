"""Unit tests for the LocationClient and AsyncLocationClient.

This module tests the location modality sub-client that provides methods for
getting location state, querying location history, and updating the user's location.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from client._location import (
    AsyncLocationClient,
    LocationClient,
    LocationQueryResponse,
    LocationStateResponse,
)
from client.models import ModalityActionResponse


# =============================================================================
# Response Model Tests
# =============================================================================


class TestLocationStateResponse:
    """Tests for the LocationStateResponse model."""

    def test_instantiation(self):
        """Test creating a LocationStateResponse."""
        response = LocationStateResponse(
            modality_type="location",
            last_updated="2025-01-15T10:00:00+00:00",
            update_count=5,
            current={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "address": "New York, NY",
                "named_location": "Office",
                "accuracy": 10.0,
                "altitude": 50.0,
                "speed": 0.0,
                "bearing": 0.0,
                "timestamp": "2025-01-15T10:00:00+00:00",
            },
            history=[
                {
                    "latitude": 40.7580,
                    "longitude": -73.9855,
                    "address": "Times Square, NY",
                    "timestamp": "2025-01-15T09:00:00+00:00",
                },
            ],
        )
        assert response.modality_type == "location"
        assert response.update_count == 5
        assert response.current["latitude"] == 40.7128
        assert len(response.history) == 1

    def test_instantiation_empty_history(self):
        """Test LocationStateResponse with empty history."""
        response = LocationStateResponse(
            modality_type="location",
            last_updated="2025-01-15T10:00:00+00:00",
            update_count=1,
            current={
                "latitude": 40.7128,
                "longitude": -74.0060,
            },
            history=[],
        )
        assert response.history == []


class TestLocationQueryResponse:
    """Tests for the LocationQueryResponse model."""

    def test_instantiation(self):
        """Test creating a LocationQueryResponse."""
        response = LocationQueryResponse(
            locations=[
                {
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "named_location": "Office",
                    "timestamp": "2025-01-15T10:00:00+00:00",
                },
                {
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "named_location": "Office",
                    "timestamp": "2025-01-14T10:00:00+00:00",
                },
            ],
            count=2,
            total_count=5,
        )
        assert response.count == 2
        assert response.total_count == 5
        assert len(response.locations) == 2


# =============================================================================
# LocationClient Tests
# =============================================================================


class TestLocationClientGetState:
    """Tests for LocationClient.get_state() method."""

    def test_get_state(self):
        """Test getting location state."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "modality_type": "location",
            "last_updated": "2025-01-15T10:00:00+00:00",
            "update_count": 5,
            "current": {
                "latitude": 40.7128,
                "longitude": -74.0060,
                "address": "New York, NY",
            },
            "history": [],
        }

        client = LocationClient(mock_http)
        result = client.get_state()

        mock_http.get.assert_called_once_with("/location/state", params=None)
        assert isinstance(result, LocationStateResponse)
        assert result.current["latitude"] == 40.7128


class TestLocationClientQuery:
    """Tests for LocationClient.query() method."""

    def test_query_no_filters(self):
        """Test querying location history with no filters."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "locations": [],
            "count": 0,
            "total_count": 0,
        }

        client = LocationClient(mock_http)
        result = client.query()

        mock_http.post.assert_called_once_with("/location/query", json={}, params=None)
        assert isinstance(result, LocationQueryResponse)

    def test_query_with_date_filters(self):
        """Test querying location history with date filters."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "locations": [],
            "count": 0,
            "total_count": 0,
        }

        client = LocationClient(mock_http)
        since = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
        until = datetime(2025, 1, 15, 0, 0, tzinfo=timezone.utc)
        result = client.query(since=since, until=until)

        call_args = mock_http.post.call_args
        assert "since" in call_args[1]["json"]
        assert "until" in call_args[1]["json"]

    def test_query_with_named_location(self):
        """Test querying location history by named location."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "locations": [
                {
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "named_location": "Office",
                    "timestamp": "2025-01-15T10:00:00+00:00",
                },
            ],
            "count": 1,
            "total_count": 1,
        }

        client = LocationClient(mock_http)
        result = client.query(named_location="Office")

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["named_location"] == "Office"

    def test_query_with_pagination(self):
        """Test querying location history with pagination."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "locations": [],
            "count": 0,
            "total_count": 100,
        }

        client = LocationClient(mock_http)
        result = client.query(limit=10, offset=20)

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["limit"] == 10
        assert call_args[1]["json"]["offset"] == 20

    def test_query_exclude_current(self):
        """Test querying with include_current=False."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "locations": [],
            "count": 0,
            "total_count": 0,
        }

        client = LocationClient(mock_http)
        result = client.query(include_current=False)

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["include_current"] is False

    def test_query_with_sort_options(self):
        """Test querying with sort options."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "locations": [],
            "count": 0,
            "total_count": 0,
        }

        client = LocationClient(mock_http)
        result = client.query(sort_by="named_location", sort_order="asc")

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["sort_by"] == "named_location"
        assert call_args[1]["json"]["sort_order"] == "asc"


class TestLocationClientUpdate:
    """Tests for LocationClient.update() method."""

    def test_update_minimal(self):
        """Test updating location with minimal parameters."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Location updated",
            "modality": "location",
        }

        client = LocationClient(mock_http)
        result = client.update(
            latitude=40.7128,
            longitude=-74.0060,
        )

        mock_http.post.assert_called_once()
        call_args = mock_http.post.call_args
        assert call_args[0][0] == "/location/update"
        assert call_args[1]["json"]["latitude"] == 40.7128
        assert call_args[1]["json"]["longitude"] == -74.0060
        assert isinstance(result, ModalityActionResponse)

    def test_update_with_all_options(self):
        """Test updating location with all options."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Location updated",
            "modality": "location",
        }

        client = LocationClient(mock_http)
        result = client.update(
            latitude=40.7128,
            longitude=-74.0060,
            address="350 5th Ave, New York, NY",
            named_location="Empire State Building",
            altitude=443.0,
            accuracy=5.0,
            speed=1.5,
            bearing=45.0,
        )

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["address"] == "350 5th Ave, New York, NY"
        assert call_args[1]["json"]["named_location"] == "Empire State Building"
        assert call_args[1]["json"]["altitude"] == 443.0
        assert call_args[1]["json"]["accuracy"] == 5.0
        assert call_args[1]["json"]["speed"] == 1.5
        assert call_args[1]["json"]["bearing"] == 45.0


# =============================================================================
# AsyncLocationClient Tests
# =============================================================================


class TestAsyncLocationClientGetState:
    """Tests for AsyncLocationClient.get_state() method."""

    async def test_get_state(self):
        """Test getting location state asynchronously."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "modality_type": "location",
            "last_updated": "2025-01-15T10:00:00+00:00",
            "update_count": 5,
            "current": {
                "latitude": 40.7128,
                "longitude": -74.0060,
            },
            "history": [],
        }

        client = AsyncLocationClient(mock_http)
        result = await client.get_state()

        mock_http.get.assert_called_once_with("/location/state", params=None)
        assert isinstance(result, LocationStateResponse)


class TestAsyncLocationClientQuery:
    """Tests for AsyncLocationClient.query() method."""

    async def test_query(self):
        """Test querying location history asynchronously."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "locations": [],
            "count": 0,
            "total_count": 0,
        }

        client = AsyncLocationClient(mock_http)
        result = await client.query(named_location="Home")

        mock_http.post.assert_called_once()
        assert isinstance(result, LocationQueryResponse)


class TestAsyncLocationClientUpdate:
    """Tests for AsyncLocationClient.update() method."""

    async def test_update(self):
        """Test updating location asynchronously."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "event_id": "evt-123",
            "scheduled_time": "2025-01-15T10:00:00+00:00",
            "status": "executed",
            "message": "Location updated",
            "modality": "location",
        }

        client = AsyncLocationClient(mock_http)
        result = await client.update(
            latitude=40.7128,
            longitude=-74.0060,
            named_location="Office",
        )

        assert isinstance(result, ModalityActionResponse)
