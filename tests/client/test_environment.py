"""Unit tests for the EnvironmentClient and AsyncEnvironmentClient.

This module tests the environment state sub-client that provides methods for
querying the current state of the simulated environment, including all
modality states.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from client._environment import (
    AsyncEnvironmentClient,
    EnvironmentClient,
    EnvironmentStateResponse,
    ModalityListResponse,
    ModalitySummary,
    ValidationResponse,
)


# =============================================================================
# Response Model Tests
# =============================================================================


class TestModalitySummary:
    """Tests for the ModalitySummary model."""

    def test_instantiation(self):
        """Test creating a ModalitySummary."""
        summary = ModalitySummary(
            modality_type="email",
            state_summary="3 inbox, 5 sent, 0 drafts",
        )
        assert summary.modality_type == "email"
        assert summary.state_summary == "3 inbox, 5 sent, 0 drafts"


class TestEnvironmentStateResponse:
    """Tests for the EnvironmentStateResponse model."""

    def test_instantiation_with_all_fields(self):
        """Test creating an EnvironmentStateResponse with all fields."""
        summaries = [
            ModalitySummary(modality_type="email", state_summary="3 inbox"),
            ModalitySummary(modality_type="sms", state_summary="5 threads"),
        ]
        modalities = {
            "email": {"inbox": [], "sent": [], "drafts": []},
            "sms": {"threads": {}, "messages": []},
        }
        response = EnvironmentStateResponse(
            current_time="2025-01-15T10:00:00+00:00",
            modalities=modalities,
            summary=summaries,
        )
        assert response.current_time == "2025-01-15T10:00:00+00:00"
        assert len(response.modalities) == 2
        assert "email" in response.modalities
        assert len(response.summary) == 2

    def test_instantiation_with_empty_modalities(self):
        """Test EnvironmentStateResponse with no modalities."""
        response = EnvironmentStateResponse(
            current_time="2025-01-15T10:00:00+00:00",
            modalities={},
            summary=[],
        )
        assert response.modalities == {}
        assert response.summary == []

    def test_instantiation_modalities_required(self):
        """Test that modalities is a required field."""
        import pytest
        from pydantic import ValidationError as PydanticValidationError
        
        with pytest.raises(PydanticValidationError):
            EnvironmentStateResponse(
                current_time="2025-01-15T10:00:00+00:00",
                summary=[],
            )


class TestModalityListResponse:
    """Tests for the ModalityListResponse model."""

    def test_instantiation(self):
        """Test creating a ModalityListResponse."""
        response = ModalityListResponse(
            modalities=["email", "sms", "calendar", "chat", "location", "weather"],
            count=6,
        )
        assert response.modalities == ["email", "sms", "calendar", "chat", "location", "weather"]
        assert response.count == 6

    def test_instantiation_empty(self):
        """Test ModalityListResponse with no modalities."""
        response = ModalityListResponse(
            modalities=[],
            count=0,
        )
        assert response.modalities == []
        assert response.count == 0


class TestValidationResponse:
    """Tests for the ValidationResponse model."""

    def test_instantiation_valid(self):
        """Test ValidationResponse for valid environment."""
        response = ValidationResponse(
            valid=True,
            errors=[],
            checked_at=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
        )
        assert response.valid is True
        assert response.errors == []
        assert response.checked_at == datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc)

    def test_instantiation_invalid(self):
        """Test ValidationResponse for invalid environment."""
        response = ValidationResponse(
            valid=False,
            errors=[
                "Email inbox contains invalid message",
                "Calendar event references non-existent user",
            ],
            checked_at=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
        )
        assert response.valid is False
        assert len(response.errors) == 2

    def test_instantiation_with_default_errors(self):
        """Test that errors defaults to empty list."""
        response = ValidationResponse(
            valid=True,
            checked_at=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
        )
        assert response.errors == []


# =============================================================================
# EnvironmentClient Tests
# =============================================================================


class TestEnvironmentClientGetState:
    """Tests for EnvironmentClient.get_state() method."""

    def test_get_state(self):
        """Test getting complete environment state."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "current_time": "2025-01-15T10:00:00+00:00",
            "modalities": {
                "email": {"inbox": [], "sent": [], "drafts": []},
                "sms": {"threads": {}, "messages": []},
                "calendar": {"calendars": {}, "events": []},
            },
            "summary": [
                {"modality_type": "email", "state_summary": "0 inbox, 0 sent"},
                {"modality_type": "sms", "state_summary": "0 threads"},
                {"modality_type": "calendar", "state_summary": "0 events"},
            ],
        }

        client = EnvironmentClient(mock_http)
        result = client.get_state()

        mock_http.get.assert_called_once_with("/environment/state", params=None)
        assert isinstance(result, EnvironmentStateResponse)
        assert result.current_time == "2025-01-15T10:00:00+00:00"
        assert len(result.modalities) == 3
        assert len(result.summary) == 3

    def test_get_state_with_populated_modalities(self):
        """Test getting state when modalities have data."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "current_time": "2025-01-15T12:00:00+00:00",
            "modalities": {
                "email": {
                    "inbox": [
                        {"id": "msg-1", "subject": "Hello", "from": "sender@example.com"}
                    ],
                    "sent": [
                        {"id": "msg-2", "subject": "Reply", "to": "recipient@example.com"}
                    ],
                    "drafts": [],
                },
            },
            "summary": [
                {"modality_type": "email", "state_summary": "1 inbox, 1 sent"},
            ],
        }

        client = EnvironmentClient(mock_http)
        result = client.get_state()

        assert len(result.modalities["email"]["inbox"]) == 1
        assert result.summary[0].state_summary == "1 inbox, 1 sent"


class TestEnvironmentClientListModalities:
    """Tests for EnvironmentClient.list_modalities() method."""

    def test_list_modalities(self):
        """Test listing available modalities."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "modalities": ["email", "sms", "calendar", "chat", "location", "weather", "time"],
            "count": 7,
        }

        client = EnvironmentClient(mock_http)
        result = client.list_modalities()

        mock_http.get.assert_called_once_with("/environment/modalities", params=None)
        assert isinstance(result, ModalityListResponse)
        assert result.count == 7
        assert "email" in result.modalities
        assert "sms" in result.modalities

    def test_list_modalities_minimal(self):
        """Test listing modalities when only a few exist."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "modalities": ["email", "time"],
            "count": 2,
        }

        client = EnvironmentClient(mock_http)
        result = client.list_modalities()

        assert result.count == 2


class TestEnvironmentClientValidate:
    """Tests for EnvironmentClient.validate() method."""

    def test_validate_valid_environment(self):
        """Test validating a valid environment."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "valid": True,
            "errors": [],
            "checked_at": "2025-01-15T10:00:00+00:00",
        }

        client = EnvironmentClient(mock_http)
        result = client.validate()

        mock_http.post.assert_called_once_with("/environment/validate", json=None, params=None)
        assert isinstance(result, ValidationResponse)
        assert result.valid is True
        assert result.errors == []

    def test_validate_invalid_environment(self):
        """Test validating an invalid environment."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "valid": False,
            "errors": [
                "Email message msg-123 references non-existent thread",
                "Calendar event evt-456 has end time before start time",
            ],
            "checked_at": "2025-01-15T10:00:00+00:00",
        }

        client = EnvironmentClient(mock_http)
        result = client.validate()

        assert result.valid is False
        assert len(result.errors) == 2
        assert "msg-123" in result.errors[0]


# =============================================================================
# AsyncEnvironmentClient Tests
# =============================================================================


class TestAsyncEnvironmentClientGetState:
    """Tests for AsyncEnvironmentClient.get_state() method."""

    async def test_get_state(self):
        """Test getting complete environment state."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "current_time": "2025-01-15T10:00:00+00:00",
            "modalities": {
                "email": {"inbox": [], "sent": []},
                "sms": {"threads": {}},
            },
            "summary": [
                {"modality_type": "email", "state_summary": "0 messages"},
                {"modality_type": "sms", "state_summary": "0 threads"},
            ],
        }

        client = AsyncEnvironmentClient(mock_http)
        result = await client.get_state()

        mock_http.get.assert_called_once_with("/environment/state", params=None)
        assert isinstance(result, EnvironmentStateResponse)
        assert len(result.modalities) == 2


class TestAsyncEnvironmentClientListModalities:
    """Tests for AsyncEnvironmentClient.list_modalities() method."""

    async def test_list_modalities(self):
        """Test listing available modalities."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "modalities": ["email", "sms", "calendar"],
            "count": 3,
        }

        client = AsyncEnvironmentClient(mock_http)
        result = await client.list_modalities()

        mock_http.get.assert_called_once_with("/environment/modalities", params=None)
        assert isinstance(result, ModalityListResponse)
        assert result.count == 3


class TestAsyncEnvironmentClientValidate:
    """Tests for AsyncEnvironmentClient.validate() method."""

    async def test_validate_valid(self):
        """Test validating a valid environment."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "valid": True,
            "errors": [],
            "checked_at": "2025-01-15T10:00:00+00:00",
        }

        client = AsyncEnvironmentClient(mock_http)
        result = await client.validate()

        mock_http.post.assert_called_once_with("/environment/validate", json=None, params=None)
        assert isinstance(result, ValidationResponse)
        assert result.valid is True

    async def test_validate_invalid(self):
        """Test validating an invalid environment."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "valid": False,
            "errors": ["Consistency error in email state"],
            "checked_at": "2025-01-15T10:00:00+00:00",
        }

        client = AsyncEnvironmentClient(mock_http)
        result = await client.validate()

        assert result.valid is False
        assert len(result.errors) == 1
