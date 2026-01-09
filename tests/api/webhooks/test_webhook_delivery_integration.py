"""Integration tests for webhook delivery and history endpoints.

Tests the delivery tracking features:
- GET /webhooks/{id}/deliveries - Get delivery history
- Delivery integration with simulation events
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from api.webhooks import webhook_registry, webhook_dispatcher, DeliveryStatus
from main import app


@pytest.fixture
def webhook_client():
    """Provide a TestClient with clean webhook state."""
    client = TestClient(app)
    
    import asyncio
    asyncio.get_event_loop().run_until_complete(webhook_registry.clear())
    webhook_dispatcher.clear_history()
    
    yield client
    
    asyncio.get_event_loop().run_until_complete(webhook_registry.clear())
    webhook_dispatcher.clear_history()


class TestGetDeliveries:
    """Tests for GET /webhooks/{id}/deliveries endpoint."""
    
    def test_get_deliveries_empty(self, webhook_client):
        """Test getting delivery history when no deliveries exist."""
        # Create a webhook
        create_response = webhook_client.post(
            "/webhooks",
            json={"url": "https://example.com/callback"}
        )
        webhook_id = create_response.json()["id"]
        
        response = webhook_client.get(f"/webhooks/{webhook_id}/deliveries")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["items"] == []
        assert data["total"] == 0
    
    def test_get_deliveries_after_test(self, webhook_client):
        """Test getting delivery history after a test delivery."""
        create_response = webhook_client.post(
            "/webhooks",
            json={"url": "https://example.com/callback"}
        )
        webhook_id = create_response.json()["id"]
        
        # Do a test delivery (this adds to history)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        with patch.object(webhook_dispatcher, "_get_client", return_value=mock_client):
            # Manually trigger a delivery to populate history
            import asyncio
            from api.webhooks import WebhookRegistration
            from api.websocket import WSEvent, WSEventType
            
            # Get the webhook
            webhook = asyncio.get_event_loop().run_until_complete(
                webhook_registry.get(webhook_id)
            )
            event = WSEvent.create(WSEventType.EMAIL_RECEIVED, {"test": "data"})
            
            # Deliver (this stores in history)
            asyncio.get_event_loop().run_until_complete(
                webhook_dispatcher._deliver(webhook, event)
            )
        
        # Now get deliveries
        response = webhook_client.get(f"/webhooks/{webhook_id}/deliveries")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["webhook_id"] == webhook_id
        assert data["items"][0]["status"] == "delivered"
    
    def test_get_deliveries_not_found(self, webhook_client):
        """Test getting deliveries for a non-existent webhook."""
        response = webhook_client.get("/webhooks/wh_nonexistent/deliveries")
        
        assert response.status_code == 404
    
    def test_get_deliveries_with_limit(self, webhook_client):
        """Test getting deliveries with limit parameter."""
        create_response = webhook_client.post(
            "/webhooks",
            json={"url": "https://example.com/callback"}
        )
        webhook_id = create_response.json()["id"]
        
        # Add multiple deliveries
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        with patch.object(webhook_dispatcher, "_get_client", return_value=mock_client):
            import asyncio
            from api.websocket import WSEvent, WSEventType
            
            webhook = asyncio.get_event_loop().run_until_complete(
                webhook_registry.get(webhook_id)
            )
            
            for i in range(5):
                event = WSEvent.create(WSEventType.EMAIL_RECEIVED, {"index": i})
                asyncio.get_event_loop().run_until_complete(
                    webhook_dispatcher._deliver(webhook, event)
                )
        
        # Get with limit
        response = webhook_client.get(
            f"/webhooks/{webhook_id}/deliveries",
            params={"limit": 3}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["items"]) == 3
    
    def test_deliveries_ordered_most_recent_first(self, webhook_client):
        """Test that deliveries are ordered most recent first."""
        create_response = webhook_client.post(
            "/webhooks",
            json={"url": "https://example.com/callback"}
        )
        webhook_id = create_response.json()["id"]
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        with patch.object(webhook_dispatcher, "_get_client", return_value=mock_client):
            import asyncio
            from api.websocket import WSEvent, WSEventType
            
            webhook = asyncio.get_event_loop().run_until_complete(
                webhook_registry.get(webhook_id)
            )
            
            # Deliver events in order 0, 1, 2
            for i in range(3):
                event = WSEvent.create(WSEventType.EMAIL_RECEIVED, {"order": i})
                asyncio.get_event_loop().run_until_complete(
                    webhook_dispatcher._deliver(webhook, event)
                )
        
        response = webhook_client.get(f"/webhooks/{webhook_id}/deliveries")
        data = response.json()
        
        # Most recent (order: 2) should be first
        assert data["items"][0]["event_data"]["order"] == 2
        assert data["items"][1]["event_data"]["order"] == 1
        assert data["items"][2]["event_data"]["order"] == 0


class TestDeliveryRecordContent:
    """Tests for delivery record content."""
    
    def test_delivery_record_includes_event_details(self, webhook_client):
        """Test that delivery records include event type and data."""
        create_response = webhook_client.post(
            "/webhooks",
            json={"url": "https://example.com/callback"}
        )
        webhook_id = create_response.json()["id"]
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        with patch.object(webhook_dispatcher, "_get_client", return_value=mock_client):
            import asyncio
            from api.websocket import WSEvent, WSEventType
            
            webhook = asyncio.get_event_loop().run_until_complete(
                webhook_registry.get(webhook_id)
            )
            event = WSEvent.create(
                WSEventType.SMS_RECEIVED,
                {"from": "+1234567890", "message": "Hello"}
            )
            asyncio.get_event_loop().run_until_complete(
                webhook_dispatcher._deliver(webhook, event)
            )
        
        response = webhook_client.get(f"/webhooks/{webhook_id}/deliveries")
        record = response.json()["items"][0]
        
        assert record["event_type"] == "sms.received"
        assert record["event_data"]["from"] == "+1234567890"
        assert record["event_data"]["message"] == "Hello"
    
    def test_delivery_record_includes_timestamps(self, webhook_client):
        """Test that delivery records include timing information."""
        create_response = webhook_client.post(
            "/webhooks",
            json={"url": "https://example.com/callback"}
        )
        webhook_id = create_response.json()["id"]
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        with patch.object(webhook_dispatcher, "_get_client", return_value=mock_client):
            import asyncio
            from api.websocket import WSEvent, WSEventType
            
            webhook = asyncio.get_event_loop().run_until_complete(
                webhook_registry.get(webhook_id)
            )
            event = WSEvent.create(WSEventType.EMAIL_RECEIVED, {"test": True})
            asyncio.get_event_loop().run_until_complete(
                webhook_dispatcher._deliver(webhook, event)
            )
        
        response = webhook_client.get(f"/webhooks/{webhook_id}/deliveries")
        record = response.json()["items"][0]
        
        assert "created_at" in record
        assert "delivered_at" in record
        assert "last_attempt_at" in record
    
    def test_delivery_record_includes_response_info(self, webhook_client):
        """Test that delivery records include response information."""
        create_response = webhook_client.post(
            "/webhooks",
            json={"url": "https://example.com/callback"}
        )
        webhook_id = create_response.json()["id"]
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Success response body"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        with patch.object(webhook_dispatcher, "_get_client", return_value=mock_client):
            import asyncio
            from api.websocket import WSEvent, WSEventType
            
            webhook = asyncio.get_event_loop().run_until_complete(
                webhook_registry.get(webhook_id)
            )
            event = WSEvent.create(WSEventType.EMAIL_RECEIVED, {})
            asyncio.get_event_loop().run_until_complete(
                webhook_dispatcher._deliver(webhook, event)
            )
        
        response = webhook_client.get(f"/webhooks/{webhook_id}/deliveries")
        record = response.json()["items"][0]
        
        assert record["response_status"] == 200
        assert record["response_body"] == "Success response body"


class TestDeliveryClearedOnDelete:
    """Tests for delivery history cleanup on webhook deletion."""
    
    def test_history_cleared_on_webhook_delete(self, webhook_client):
        """Test that delivery history is cleared when webhook is deleted."""
        create_response = webhook_client.post(
            "/webhooks",
            json={"url": "https://example.com/callback"}
        )
        webhook_id = create_response.json()["id"]
        
        # Add some delivery history
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        with patch.object(webhook_dispatcher, "_get_client", return_value=mock_client):
            import asyncio
            from api.websocket import WSEvent, WSEventType
            
            webhook = asyncio.get_event_loop().run_until_complete(
                webhook_registry.get(webhook_id)
            )
            event = WSEvent.create(WSEventType.EMAIL_RECEIVED, {})
            asyncio.get_event_loop().run_until_complete(
                webhook_dispatcher._deliver(webhook, event)
            )
        
        # Verify history exists
        history = webhook_dispatcher.get_delivery_history(webhook_id)
        assert len(history) > 0
        
        # Delete webhook
        webhook_client.delete(f"/webhooks/{webhook_id}")
        
        # History should be cleared
        history_after = webhook_dispatcher.get_delivery_history(webhook_id)
        assert len(history_after) == 0
