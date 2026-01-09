"""Unit tests for the WebhooksClient and AsyncWebhooksClient.

This module tests the webhooks sub-client that provides methods for
registering, updating, deleting, and managing webhook callbacks.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from client._webhooks import (
    AsyncWebhooksClient,
    WebhooksClient,
)


# =============================================================================
# Sync Client Tests
# =============================================================================


class TestWebhooksClientRegister:
    """Tests for WebhooksClient.register method."""

    def test_register_minimal(self):
        """Test registering a webhook with minimal parameters."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "id": "wh_new",
            "url": "https://example.com/callback",
            "events": None,
            "status": "active",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
            "metadata": {},
            "failure_count": 0,
            "last_delivery_at": None,
            "last_failure_at": None,
            "has_secret": False,
        }

        client = WebhooksClient(mock_http)
        result = client.register(url="https://example.com/callback")

        assert result["id"] == "wh_new"
        mock_http.post.assert_called_once_with(
            "/webhooks",
            json={"url": "https://example.com/callback"},
            params=None,
        )

    def test_register_with_all_options(self):
        """Test registering a webhook with all options."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "id": "wh_full",
            "url": "https://example.com/callback",
            "events": ["email.", "sms."],
            "status": "active",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
            "metadata": {"agent": "TestBot"},
            "failure_count": 0,
            "last_delivery_at": None,
            "last_failure_at": None,
            "has_secret": True,
        }

        client = WebhooksClient(mock_http)
        result = client.register(
            url="https://example.com/callback",
            events=["email.", "sms."],
            secret="my-secret",
            metadata={"agent": "TestBot"},
        )

        assert result["events"] == ["email.", "sms."]
        assert result["has_secret"] is True
        mock_http.post.assert_called_once_with(
            "/webhooks",
            json={
                "url": "https://example.com/callback",
                "events": ["email.", "sms."],
                "secret": "my-secret",
                "metadata": {"agent": "TestBot"},
            },
            params=None,
        )


class TestWebhooksClientGet:
    """Tests for WebhooksClient.get method."""

    def test_get_webhook(self):
        """Test getting a webhook by ID."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "id": "wh_test",
            "url": "https://example.com/callback",
            "events": ["email."],
            "status": "active",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
            "metadata": {},
            "failure_count": 0,
            "last_delivery_at": None,
            "last_failure_at": None,
            "has_secret": False,
        }

        client = WebhooksClient(mock_http)
        result = client.get("wh_test")

        assert result["id"] == "wh_test"
        mock_http.get.assert_called_once_with("/webhooks/wh_test", params=None)


class TestWebhooksClientList:
    """Tests for WebhooksClient.list method."""

    def test_list_webhooks_default(self):
        """Test listing webhooks with defaults."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "items": [],
            "total": 0,
            "limit": 50,
            "offset": 0,
        }

        client = WebhooksClient(mock_http)
        result = client.list()

        assert result["items"] == []
        mock_http.get.assert_called_once_with(
            "/webhooks",
            params={"limit": 50, "offset": 0},
        )

    def test_list_webhooks_with_filter(self):
        """Test listing webhooks with status filter."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "items": [],
            "total": 0,
            "limit": 10,
            "offset": 5,
        }

        client = WebhooksClient(mock_http)
        result = client.list(status="active", limit=10, offset=5)

        mock_http.get.assert_called_once_with(
            "/webhooks",
            params={"status": "active", "limit": 10, "offset": 5},
        )


class TestWebhooksClientUpdate:
    """Tests for WebhooksClient.update method."""

    def test_update_url(self):
        """Test updating a webhook URL."""
        mock_http = MagicMock()
        mock_http.patch.return_value = {
            "id": "wh_test",
            "url": "https://new.com/callback",
            "events": None,
            "status": "active",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
            "metadata": {},
            "failure_count": 0,
            "last_delivery_at": None,
            "last_failure_at": None,
            "has_secret": False,
        }

        client = WebhooksClient(mock_http)
        result = client.update("wh_test", url="https://new.com/callback")

        assert result["url"] == "https://new.com/callback"
        mock_http.patch.assert_called_once_with(
            "/webhooks/wh_test",
            json={"url": "https://new.com/callback"},
            params=None,
        )


class TestWebhooksClientDelete:
    """Tests for WebhooksClient.delete method."""

    def test_delete_webhook(self):
        """Test deleting a webhook."""
        mock_http = MagicMock()
        mock_http.delete.return_value = None

        client = WebhooksClient(mock_http)
        client.delete("wh_test")

        mock_http.delete.assert_called_once_with("/webhooks/wh_test", params=None)


class TestWebhooksClientTest:
    """Tests for WebhooksClient.test method."""

    def test_test_webhook(self):
        """Test sending a test event to a webhook."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "webhook_id": "wh_test",
            "success": True,
            "response_status": 200,
            "response_time_ms": 50.0,
            "response_body": "OK",
            "error_message": None,
        }

        client = WebhooksClient(mock_http)
        result = client.test("wh_test")

        assert result["success"] is True
        mock_http.post.assert_called_once_with("/webhooks/wh_test/test", json=None, params=None)


class TestWebhooksClientPauseResume:
    """Tests for WebhooksClient.pause and resume methods."""

    def test_pause_webhook(self):
        """Test pausing a webhook."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "id": "wh_test",
            "url": "https://example.com/callback",
            "events": None,
            "status": "paused",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
            "metadata": {},
            "failure_count": 0,
            "last_delivery_at": None,
            "last_failure_at": None,
            "has_secret": False,
        }

        client = WebhooksClient(mock_http)
        result = client.pause("wh_test")

        assert result["status"] == "paused"
        mock_http.post.assert_called_once_with("/webhooks/wh_test/pause", json=None, params=None)

    def test_resume_webhook(self):
        """Test resuming a webhook."""
        mock_http = MagicMock()
        mock_http.post.return_value = {
            "id": "wh_test",
            "url": "https://example.com/callback",
            "events": None,
            "status": "active",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
            "metadata": {},
            "failure_count": 0,
            "last_delivery_at": None,
            "last_failure_at": None,
            "has_secret": False,
        }

        client = WebhooksClient(mock_http)
        result = client.resume("wh_test")

        assert result["status"] == "active"
        mock_http.post.assert_called_once_with("/webhooks/wh_test/resume", json=None, params=None)


class TestWebhooksClientDeliveries:
    """Tests for WebhooksClient.get_deliveries method."""

    def test_get_deliveries(self):
        """Test getting delivery history."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "items": [],
            "total": 0,
        }

        client = WebhooksClient(mock_http)
        result = client.get_deliveries("wh_test")

        assert result["items"] == []
        mock_http.get.assert_called_once_with(
            "/webhooks/wh_test/deliveries",
            params={"limit": 50},
        )

    def test_get_deliveries_with_limit(self):
        """Test getting delivery history with custom limit."""
        mock_http = MagicMock()
        mock_http.get.return_value = {
            "items": [],
            "total": 0,
        }

        client = WebhooksClient(mock_http)
        result = client.get_deliveries("wh_test", limit=10)

        mock_http.get.assert_called_once_with(
            "/webhooks/wh_test/deliveries",
            params={"limit": 10},
        )


# =============================================================================
# Async Client Tests
# =============================================================================


class TestAsyncWebhooksClientRegister:
    """Tests for AsyncWebhooksClient.register method."""

    @pytest.mark.asyncio
    async def test_register_minimal(self):
        """Test registering a webhook with minimal parameters."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "id": "wh_new",
            "url": "https://example.com/callback",
            "events": None,
            "status": "active",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
            "metadata": {},
            "failure_count": 0,
            "last_delivery_at": None,
            "last_failure_at": None,
            "has_secret": False,
        }

        client = AsyncWebhooksClient(mock_http)
        result = await client.register(url="https://example.com/callback")

        assert result["id"] == "wh_new"
        mock_http.post.assert_called_once_with(
            "/webhooks",
            json={"url": "https://example.com/callback"},
            params=None,
        )


class TestAsyncWebhooksClientGet:
    """Tests for AsyncWebhooksClient.get method."""

    @pytest.mark.asyncio
    async def test_get_webhook(self):
        """Test getting a webhook by ID."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "id": "wh_test",
            "url": "https://example.com/callback",
            "events": ["email."],
            "status": "active",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
            "metadata": {},
            "failure_count": 0,
            "last_delivery_at": None,
            "last_failure_at": None,
            "has_secret": False,
        }

        client = AsyncWebhooksClient(mock_http)
        result = await client.get("wh_test")

        assert result["id"] == "wh_test"


class TestAsyncWebhooksClientList:
    """Tests for AsyncWebhooksClient.list method."""

    @pytest.mark.asyncio
    async def test_list_webhooks(self):
        """Test listing webhooks."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "items": [],
            "total": 0,
            "limit": 50,
            "offset": 0,
        }

        client = AsyncWebhooksClient(mock_http)
        result = await client.list()

        assert result["items"] == []


class TestAsyncWebhooksClientUpdate:
    """Tests for AsyncWebhooksClient.update method."""

    @pytest.mark.asyncio
    async def test_update_webhook(self):
        """Test updating a webhook."""
        mock_http = AsyncMock()
        mock_http.patch.return_value = {
            "id": "wh_test",
            "url": "https://new.com/callback",
            "events": None,
            "status": "active",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
            "metadata": {},
            "failure_count": 0,
            "last_delivery_at": None,
            "last_failure_at": None,
            "has_secret": False,
        }

        client = AsyncWebhooksClient(mock_http)
        result = await client.update("wh_test", url="https://new.com/callback")

        assert result["url"] == "https://new.com/callback"


class TestAsyncWebhooksClientDelete:
    """Tests for AsyncWebhooksClient.delete method."""

    @pytest.mark.asyncio
    async def test_delete_webhook(self):
        """Test deleting a webhook."""
        mock_http = AsyncMock()
        mock_http.delete.return_value = None

        client = AsyncWebhooksClient(mock_http)
        await client.delete("wh_test")

        mock_http.delete.assert_called_once_with("/webhooks/wh_test", params=None)


class TestAsyncWebhooksClientTest:
    """Tests for AsyncWebhooksClient.test method."""

    @pytest.mark.asyncio
    async def test_test_webhook(self):
        """Test sending a test event to a webhook."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "webhook_id": "wh_test",
            "success": True,
            "response_status": 200,
            "response_time_ms": 50.0,
            "response_body": "OK",
            "error_message": None,
        }

        client = AsyncWebhooksClient(mock_http)
        result = await client.test("wh_test")

        assert result["success"] is True


class TestAsyncWebhooksClientPauseResume:
    """Tests for AsyncWebhooksClient.pause and resume methods."""

    @pytest.mark.asyncio
    async def test_pause_webhook(self):
        """Test pausing a webhook."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "id": "wh_test",
            "url": "https://example.com/callback",
            "events": None,
            "status": "paused",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
            "metadata": {},
            "failure_count": 0,
            "last_delivery_at": None,
            "last_failure_at": None,
            "has_secret": False,
        }

        client = AsyncWebhooksClient(mock_http)
        result = await client.pause("wh_test")

        assert result["status"] == "paused"

    @pytest.mark.asyncio
    async def test_resume_webhook(self):
        """Test resuming a webhook."""
        mock_http = AsyncMock()
        mock_http.post.return_value = {
            "id": "wh_test",
            "url": "https://example.com/callback",
            "events": None,
            "status": "active",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
            "metadata": {},
            "failure_count": 0,
            "last_delivery_at": None,
            "last_failure_at": None,
            "has_secret": False,
        }

        client = AsyncWebhooksClient(mock_http)
        result = await client.resume("wh_test")

        assert result["status"] == "active"


class TestAsyncWebhooksClientDeliveries:
    """Tests for AsyncWebhooksClient.get_deliveries method."""

    @pytest.mark.asyncio
    async def test_get_deliveries(self):
        """Test getting delivery history."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "items": [],
            "total": 0,
        }

        client = AsyncWebhooksClient(mock_http)
        result = await client.get_deliveries("wh_test")

        assert result["items"] == []
