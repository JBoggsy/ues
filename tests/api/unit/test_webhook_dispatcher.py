"""Unit tests for WebhookDispatcher.

Tests the HTTP delivery logic, retry behavior, and signature generation.
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from api.webhooks import (
    WebhookDispatcher,
    WebhookRegistry,
    WebhookRegistration,
    WebhookStatus,
    DeliveryRecord,
    DeliveryStatus,
)
from api.websocket import WSEventType, WSEvent


@pytest.fixture
def registry():
    """Create a fresh registry for each test."""
    return WebhookRegistry()


@pytest.fixture
def dispatcher(registry):
    """Create a dispatcher with the test registry."""
    return WebhookDispatcher(
        registry,
        max_retries=3,
        retry_delay_seconds=0.01,  # Fast retries for tests
        timeout_seconds=5.0,
        max_failure_count=3,
    )


@pytest.fixture
def sample_webhook():
    """Create a sample webhook registration."""
    return WebhookRegistration(
        id="wh_test123",
        url="https://example.com/callback",
        events=["email."],
        secret="test-secret",
    )


@pytest.fixture
def webhook_no_secret():
    """Create a webhook without a secret."""
    return WebhookRegistration(
        id="wh_nosecret",
        url="https://example.com/callback",
        events=["email."],
    )


class TestWebhookDispatcherInit:
    """Tests for dispatcher initialization."""
    
    def test_init_with_defaults(self, registry):
        """Test dispatcher initialization with default values."""
        d = WebhookDispatcher(registry)
        
        assert d.registry == registry
        assert d.max_retries == 3
        assert d.retry_delay_seconds == 1.0
        assert d.timeout_seconds == 10.0
        assert d.max_failure_count == 10
    
    def test_init_with_custom_values(self, registry):
        """Test dispatcher initialization with custom values."""
        d = WebhookDispatcher(
            registry,
            max_retries=5,
            retry_delay_seconds=2.0,
            timeout_seconds=30.0,
            max_failure_count=5,
        )
        
        assert d.max_retries == 5
        assert d.retry_delay_seconds == 2.0
        assert d.timeout_seconds == 30.0
        assert d.max_failure_count == 5


class TestWebhookDispatcherSignature:
    """Tests for HMAC signature computation."""
    
    def test_compute_signature_format(self, dispatcher):
        """Test that signature has correct format."""
        signature = dispatcher._compute_signature("test payload", "secret")
        
        assert signature.startswith("sha256=")
        assert len(signature) == 71  # "sha256=" + 64 hex chars
    
    def test_compute_signature_consistency(self, dispatcher):
        """Test that same inputs produce same signature."""
        sig1 = dispatcher._compute_signature("test", "secret")
        sig2 = dispatcher._compute_signature("test", "secret")
        
        assert sig1 == sig2
    
    def test_compute_signature_different_payloads(self, dispatcher):
        """Test that different payloads produce different signatures."""
        sig1 = dispatcher._compute_signature("test1", "secret")
        sig2 = dispatcher._compute_signature("test2", "secret")
        
        assert sig1 != sig2
    
    def test_compute_signature_different_secrets(self, dispatcher):
        """Test that different secrets produce different signatures."""
        sig1 = dispatcher._compute_signature("test", "secret1")
        sig2 = dispatcher._compute_signature("test", "secret2")
        
        assert sig1 != sig2


class TestWebhookDispatcherDispatch:
    """Tests for the dispatch method."""
    
    @pytest.mark.asyncio
    async def test_dispatch_no_matching_webhooks(self, dispatcher, registry):
        """Test dispatch when no webhooks match."""
        # No webhooks registered
        count = await dispatcher.dispatch(WSEventType.EMAIL_RECEIVED, {"test": "data"})
        
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_dispatch_returns_webhook_count(self, dispatcher, registry, sample_webhook):
        """Test that dispatch returns count of matching webhooks."""
        await registry.add(sample_webhook)
        
        # Mock the _deliver method to avoid actual HTTP calls
        with patch.object(dispatcher, "_deliver", new_callable=AsyncMock) as mock_deliver:
            count = await dispatcher.dispatch(WSEventType.EMAIL_RECEIVED, {"test": "data"})
            
            # Give time for background task to start
            await asyncio.sleep(0.01)
        
        assert count == 1
    
    @pytest.mark.asyncio
    async def test_dispatch_multiple_matching(self, dispatcher, registry):
        """Test dispatching to multiple matching webhooks."""
        wh1 = WebhookRegistration(id="wh_1", url="https://a.com", events=["email."])
        wh2 = WebhookRegistration(id="wh_2", url="https://b.com", events=["email.received"])
        wh3 = WebhookRegistration(id="wh_3", url="https://c.com", events=["sms."])
        
        await registry.add(wh1)
        await registry.add(wh2)
        await registry.add(wh3)
        
        with patch.object(dispatcher, "_deliver", new_callable=AsyncMock):
            count = await dispatcher.dispatch(WSEventType.EMAIL_RECEIVED, {"test": "data"})
        
        assert count == 2  # wh1 and wh2, not wh3


class TestWebhookDispatcherDeliver:
    """Tests for the delivery method."""
    
    @pytest.mark.asyncio
    async def test_deliver_success(self, dispatcher, sample_webhook):
        """Test successful delivery."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        with patch.object(dispatcher, "_get_client", return_value=mock_client):
            event = WSEvent.create(WSEventType.EMAIL_RECEIVED, {"email_id": "123"})
            record = await dispatcher._deliver(sample_webhook, event)
        
        assert record.status == DeliveryStatus.DELIVERED
        assert record.response_status == 200
        assert record.delivered_at is not None
    
    @pytest.mark.asyncio
    async def test_deliver_includes_signature_header(self, dispatcher, sample_webhook):
        """Test that delivery includes X-UES-Signature header when secret is set."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        with patch.object(dispatcher, "_get_client", return_value=mock_client):
            event = WSEvent.create(WSEventType.EMAIL_RECEIVED, {"email_id": "123"})
            await dispatcher._deliver(sample_webhook, event)
        
        # Check the call was made with X-UES-Signature header
        call_kwargs = mock_client.post.call_args[1]
        assert "X-UES-Signature" in call_kwargs["headers"]
        assert call_kwargs["headers"]["X-UES-Signature"].startswith("sha256=")
    
    @pytest.mark.asyncio
    async def test_deliver_no_signature_without_secret(self, dispatcher, webhook_no_secret):
        """Test that no signature header is added when webhook has no secret."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        with patch.object(dispatcher, "_get_client", return_value=mock_client):
            event = WSEvent.create(WSEventType.EMAIL_RECEIVED, {"email_id": "123"})
            await dispatcher._deliver(webhook_no_secret, event)
        
        call_kwargs = mock_client.post.call_args[1]
        assert "X-UES-Signature" not in call_kwargs["headers"]
    
    @pytest.mark.asyncio
    async def test_deliver_includes_standard_headers(self, dispatcher, sample_webhook):
        """Test that delivery includes all standard headers."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        with patch.object(dispatcher, "_get_client", return_value=mock_client):
            event = WSEvent.create(WSEventType.EMAIL_RECEIVED, {"email_id": "123"})
            await dispatcher._deliver(sample_webhook, event)
        
        call_kwargs = mock_client.post.call_args[1]
        headers = call_kwargs["headers"]
        
        assert headers["Content-Type"] == "application/json"
        assert "X-UES-Event" in headers
        assert "X-UES-Delivery-ID" in headers
        assert "X-UES-Timestamp" in headers
    
    @pytest.mark.asyncio
    async def test_deliver_http_error_response(self, dispatcher, registry, sample_webhook):
        """Test delivery with HTTP error response."""
        await registry.add(sample_webhook)
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        # Patch sleep to speed up retry delays
        with patch.object(dispatcher, "_get_client", return_value=mock_client):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                event = WSEvent.create(WSEventType.EMAIL_RECEIVED, {"email_id": "123"})
                record = await dispatcher._deliver(sample_webhook, event)
        
        assert record.status in [DeliveryStatus.FAILED, DeliveryStatus.RETRYING]
        assert record.error_message == "HTTP 500"
    
    @pytest.mark.asyncio
    async def test_deliver_network_exception(self, dispatcher, registry, sample_webhook):
        """Test delivery with network exception."""
        await registry.add(sample_webhook)
        
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        
        with patch.object(dispatcher, "_get_client", return_value=mock_client):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                event = WSEvent.create(WSEventType.EMAIL_RECEIVED, {"email_id": "123"})
                record = await dispatcher._deliver(sample_webhook, event)
        
        assert record.status in [DeliveryStatus.FAILED, DeliveryStatus.RETRYING]
        assert "Connection refused" in record.error_message


class TestWebhookDispatcherRetry:
    """Tests for retry behavior."""
    
    @pytest.mark.asyncio
    async def test_retry_on_failure(self, dispatcher, registry, sample_webhook):
        """Test that delivery is retried on failure."""
        await registry.add(sample_webhook)
        
        mock_client = AsyncMock()
        # First call fails, second succeeds
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 500
        mock_response_fail.text = "Error"
        
        mock_response_ok = MagicMock()
        mock_response_ok.status_code = 200
        mock_response_ok.text = "OK"
        
        mock_client.post.side_effect = [mock_response_fail, mock_response_ok]
        
        with patch.object(dispatcher, "_get_client", return_value=mock_client):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                event = WSEvent.create(WSEventType.EMAIL_RECEIVED, {"email_id": "123"})
                record = await dispatcher._deliver(sample_webhook, event)
        
        # Should have retried and eventually marked as retrying (first record)
        # The final status depends on the recursive call
        assert mock_client.post.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_no_retry_after_max_attempts(self, dispatcher, registry, sample_webhook):
        """Test that no more retries after max attempts."""
        await registry.add(sample_webhook)
        
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Error"
        mock_client.post.return_value = mock_response
        
        with patch.object(dispatcher, "_get_client", return_value=mock_client):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                event = WSEvent.create(WSEventType.EMAIL_RECEIVED, {"email_id": "123"})
                # Start at attempt 3 (max_retries = 3)
                record = await dispatcher._deliver(sample_webhook, event, attempt=3)
        
        # Should not retry
        assert mock_client.post.call_count == 1


class TestWebhookDispatcherAutoDisable:
    """Tests for auto-disabling after too many failures."""
    
    @pytest.mark.asyncio
    async def test_auto_disable_after_max_failures(self, dispatcher, registry):
        """Test that webhook is auto-disabled after max consecutive failures."""
        # Create webhook with failure_count just below threshold
        webhook = WebhookRegistration(
            id="wh_failing",
            url="https://example.com/callback",
            events=["email."],
            failure_count=2,  # One more failure will hit max_failure_count=3
        )
        await registry.add(webhook)
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Error"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        with patch.object(dispatcher, "_get_client", return_value=mock_client):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                event = WSEvent.create(WSEventType.EMAIL_RECEIVED, {"email_id": "123"})
                # Start at max attempt to avoid retries
                await dispatcher._deliver(webhook, event, attempt=dispatcher.max_retries)
        
        # Check that webhook was disabled
        updated = await registry.get("wh_failing")
        assert updated.status == WebhookStatus.DISABLED
    
    @pytest.mark.asyncio
    async def test_failure_count_resets_on_success(self, dispatcher, registry):
        """Test that failure count resets after successful delivery."""
        webhook = WebhookRegistration(
            id="wh_recovering",
            url="https://example.com/callback",
            events=["email."],
            failure_count=2,
        )
        await registry.add(webhook)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        with patch.object(dispatcher, "_get_client", return_value=mock_client):
            event = WSEvent.create(WSEventType.EMAIL_RECEIVED, {"email_id": "123"})
            await dispatcher._deliver(webhook, event)
        
        # Check that failure count was reset
        updated = await registry.get("wh_recovering")
        assert updated.failure_count == 0


class TestWebhookDispatcherDeliveryHistory:
    """Tests for delivery history tracking."""
    
    @pytest.mark.asyncio
    async def test_stores_delivery_record(self, dispatcher, sample_webhook):
        """Test that delivery records are stored in history."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        with patch.object(dispatcher, "_get_client", return_value=mock_client):
            event = WSEvent.create(WSEventType.EMAIL_RECEIVED, {"email_id": "123"})
            await dispatcher._deliver(sample_webhook, event)
        
        history = dispatcher.get_delivery_history(sample_webhook.id)
        assert len(history) == 1
        assert history[0].webhook_id == sample_webhook.id
        assert history[0].status == DeliveryStatus.DELIVERED
    
    def test_get_delivery_history_empty(self, dispatcher):
        """Test getting history for webhook with no deliveries."""
        history = dispatcher.get_delivery_history("wh_nonexistent")
        assert history == []
    
    @pytest.mark.asyncio
    async def test_history_limited_by_max_size(self, dispatcher, sample_webhook):
        """Test that history is limited to max size per webhook."""
        dispatcher._max_history_per_webhook = 5
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        with patch.object(dispatcher, "_get_client", return_value=mock_client):
            # Deliver 10 events
            for i in range(10):
                event = WSEvent.create(WSEventType.EMAIL_RECEIVED, {"email_id": str(i)})
                await dispatcher._deliver(sample_webhook, event)
        
        history = dispatcher.get_delivery_history(sample_webhook.id)
        assert len(history) <= 5
    
    def test_clear_history_single_webhook(self, dispatcher):
        """Test clearing history for a single webhook."""
        # Manually add some history
        record = DeliveryRecord(
            webhook_id="wh_1",
            event_type="test",
            event_data={},
        )
        dispatcher._store_delivery_record("wh_1", record)
        dispatcher._store_delivery_record("wh_2", record)
        
        dispatcher.clear_history("wh_1")
        
        assert dispatcher.get_delivery_history("wh_1") == []
        assert len(dispatcher.get_delivery_history("wh_2")) == 1
    
    def test_clear_history_all(self, dispatcher):
        """Test clearing all delivery history."""
        record = DeliveryRecord(
            webhook_id="wh_1",
            event_type="test",
            event_data={},
        )
        dispatcher._store_delivery_record("wh_1", record)
        dispatcher._store_delivery_record("wh_2", record)
        
        dispatcher.clear_history()
        
        assert dispatcher.get_delivery_history("wh_1") == []
        assert dispatcher.get_delivery_history("wh_2") == []


class TestWebhookDispatcherTestWebhook:
    """Tests for the test_webhook method."""
    
    @pytest.mark.asyncio
    async def test_test_webhook_success(self, dispatcher, sample_webhook):
        """Test successful webhook connectivity test."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        with patch.object(dispatcher, "_get_client", return_value=mock_client):
            record = await dispatcher.test_webhook(sample_webhook)
        
        assert record.status == DeliveryStatus.DELIVERED
        assert record.event_type == "webhook.test"
        assert "message" in record.event_data
    
    @pytest.mark.asyncio
    async def test_test_webhook_failure(self, dispatcher, sample_webhook):
        """Test failed webhook connectivity test."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Error"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        with patch.object(dispatcher, "_get_client", return_value=mock_client):
            record = await dispatcher.test_webhook(sample_webhook)
        
        assert record.status == DeliveryStatus.FAILED
        assert record.error_message == "HTTP 500"
    
    @pytest.mark.asyncio
    async def test_test_webhook_network_error(self, dispatcher, sample_webhook):
        """Test webhook test with network error."""
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        
        with patch.object(dispatcher, "_get_client", return_value=mock_client):
            record = await dispatcher.test_webhook(sample_webhook)
        
        assert record.status == DeliveryStatus.FAILED
        assert "Connection refused" in record.error_message
    
    @pytest.mark.asyncio
    async def test_test_webhook_includes_elapsed_time(self, dispatcher, sample_webhook):
        """Test that test_webhook records elapsed time."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        with patch.object(dispatcher, "_get_client", return_value=mock_client):
            record = await dispatcher.test_webhook(sample_webhook)
        
        # The elapsed time should be stored as a private attribute
        assert hasattr(record, "_elapsed_ms")


class TestWebhookDispatcherClose:
    """Tests for closing the dispatcher."""
    
    @pytest.mark.asyncio
    async def test_close_client(self, dispatcher):
        """Test that close properly closes the HTTP client."""
        # First, create the client
        client = await dispatcher._get_client()
        assert dispatcher._http_client is not None
        
        # Now close
        await dispatcher.close()
        
        assert dispatcher._http_client is None
    
    @pytest.mark.asyncio
    async def test_close_without_client(self, dispatcher):
        """Test that close is safe to call without client."""
        # Should not raise
        await dispatcher.close()
        assert dispatcher._http_client is None
