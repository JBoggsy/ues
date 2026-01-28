"""Integration tests for webhook test endpoint.

Tests the webhook connectivity test feature:
- POST /webhooks/{id}/test - Send a test event to verify connectivity
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ues.api.webhooks import webhook_dispatcher


class TestWebhookTest:
    """Tests for POST /webhooks/{id}/test endpoint."""
    
    def test_test_webhook_success(self, webhook_client):
        """Test successful webhook connectivity test."""
        # Create a webhook
        create_response = webhook_client.post(
            "/webhooks",
            json={"url": "https://example.com/callback"}
        )
        webhook_id = create_response.json()["id"]
        
        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        with patch.object(webhook_dispatcher, "_get_client", return_value=mock_client):
            response = webhook_client.post(f"/webhooks/{webhook_id}/test")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["webhook_id"] == webhook_id
        assert data["success"] is True
        assert data["response_status"] == 200
        assert "response_time_ms" in data
    
    def test_test_webhook_failure(self, webhook_client):
        """Test webhook connectivity test with failed response."""
        create_response = webhook_client.post(
            "/webhooks",
            json={"url": "https://example.com/callback"}
        )
        webhook_id = create_response.json()["id"]
        
        # Mock failed HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        with patch.object(webhook_dispatcher, "_get_client", return_value=mock_client):
            response = webhook_client.post(f"/webhooks/{webhook_id}/test")
        
        assert response.status_code == 200  # The test endpoint returns 200 with result
        data = response.json()
        
        assert data["webhook_id"] == webhook_id
        assert data["success"] is False
        assert data["response_status"] == 500
        assert "error_message" in data
    
    def test_test_webhook_network_error(self, webhook_client):
        """Test webhook connectivity test with network error."""
        import httpx
        
        create_response = webhook_client.post(
            "/webhooks",
            json={"url": "https://example.com/callback"}
        )
        webhook_id = create_response.json()["id"]
        
        # Mock network error
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        
        with patch.object(webhook_dispatcher, "_get_client", return_value=mock_client):
            response = webhook_client.post(f"/webhooks/{webhook_id}/test")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is False
        assert data["error_message"] is not None
        assert "Connection refused" in data["error_message"]
    
    def test_test_webhook_not_found(self, webhook_client):
        """Test testing a non-existent webhook."""
        response = webhook_client.post("/webhooks/wh_nonexistent/test")
        
        assert response.status_code == 404
    
    def test_test_webhook_includes_signature(self, webhook_client):
        """Test that test event includes signature header when secret is set."""
        create_response = webhook_client.post(
            "/webhooks",
            json={
                "url": "https://example.com/callback",
                "secret": "my-secret-key"
            }
        )
        webhook_id = create_response.json()["id"]
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        with patch.object(webhook_dispatcher, "_get_client", return_value=mock_client):
            webhook_client.post(f"/webhooks/{webhook_id}/test")
        
        # Check that the request was made with X-UES-Signature header
        call_kwargs = mock_client.post.call_args[1]
        assert "X-UES-Signature" in call_kwargs["headers"]
        assert call_kwargs["headers"]["X-UES-Signature"].startswith("sha256=")
    
    def test_test_webhook_response_body_truncated(self, webhook_client):
        """Test that response body is truncated to 500 chars."""
        create_response = webhook_client.post(
            "/webhooks",
            json={"url": "https://example.com/callback"}
        )
        webhook_id = create_response.json()["id"]
        
        # Mock response with very long body
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "x" * 1000  # 1000 characters
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        with patch.object(webhook_dispatcher, "_get_client", return_value=mock_client):
            response = webhook_client.post(f"/webhooks/{webhook_id}/test")
        
        data = response.json()
        assert data["response_body"] is not None
        assert len(data["response_body"]) <= 500
    
    def test_test_webhook_paused_state(self, webhook_client):
        """Test that testing a paused webhook still works."""
        create_response = webhook_client.post(
            "/webhooks",
            json={"url": "https://example.com/callback"}
        )
        webhook_id = create_response.json()["id"]
        
        # Pause the webhook
        webhook_client.post(f"/webhooks/{webhook_id}/pause")
        
        # Test should still work
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        with patch.object(webhook_dispatcher, "_get_client", return_value=mock_client):
            response = webhook_client.post(f"/webhooks/{webhook_id}/test")
        
        assert response.status_code == 200
        assert response.json()["success"] is True
