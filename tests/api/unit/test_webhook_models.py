"""Unit tests for webhook models.

Tests the WebhookRegistration, DeliveryRecord, and request/response models.
"""

import pytest
from datetime import datetime, timezone

from ues.api.webhooks import (
    CreateWebhookRequest,
    DeliveryRecord,
    DeliveryStatus,
    UpdateWebhookRequest,
    WebhookRegistration,
    WebhookResponse,
    WebhookStatus,
)


class TestWebhookRegistration:
    """Tests for WebhookRegistration model."""
    
    def test_instantiation_with_defaults(self):
        """Test creating a webhook with only required fields."""
        webhook = WebhookRegistration(url="https://example.com/callback")
        
        assert webhook.url == "https://example.com/callback"
        assert webhook.id.startswith("wh_")
        assert webhook.events is None  # Subscribe to all
        assert webhook.secret is None
        assert webhook.status == WebhookStatus.ACTIVE
        assert webhook.failure_count == 0
        assert webhook.metadata == {}
        assert isinstance(webhook.created_at, datetime)
        assert isinstance(webhook.updated_at, datetime)
    
    def test_instantiation_with_all_fields(self):
        """Test creating a webhook with all fields specified."""
        webhook = WebhookRegistration(
            id="wh_custom123",
            url="https://example.com/callback",
            events=["email.", "sms.received"],
            secret="my-secret",
            status=WebhookStatus.PAUSED,
            metadata={"agent_name": "TestBot"},
            failure_count=5,
        )
        
        assert webhook.id == "wh_custom123"
        assert webhook.url == "https://example.com/callback"
        assert webhook.events == ["email.", "sms.received"]
        assert webhook.secret == "my-secret"
        assert webhook.status == WebhookStatus.PAUSED
        assert webhook.metadata == {"agent_name": "TestBot"}
        assert webhook.failure_count == 5
    
    def test_url_validation_http(self):
        """Test that http:// URLs are accepted."""
        webhook = WebhookRegistration(url="http://localhost:8080/callback")
        assert webhook.url == "http://localhost:8080/callback"
    
    def test_url_validation_https(self):
        """Test that https:// URLs are accepted."""
        webhook = WebhookRegistration(url="https://secure.example.com/webhook")
        assert webhook.url == "https://secure.example.com/webhook"
    
    def test_url_validation_invalid(self):
        """Test that invalid URLs are rejected."""
        with pytest.raises(ValueError, match="URL must start with http"):
            WebhookRegistration(url="ftp://example.com/callback")
    
    def test_url_validation_no_scheme(self):
        """Test that URLs without scheme are rejected."""
        with pytest.raises(ValueError, match="URL must start with http"):
            WebhookRegistration(url="example.com/callback")
    
    def test_events_validation_empty_list(self):
        """Test that empty events list is rejected."""
        with pytest.raises(ValueError, match="events list cannot be empty"):
            WebhookRegistration(url="https://example.com", events=[])
    
    def test_events_validation_none(self):
        """Test that None events means subscribe to all."""
        webhook = WebhookRegistration(url="https://example.com", events=None)
        assert webhook.events is None
    
    def test_matches_event_all_events(self):
        """Test that None events matches any event type."""
        webhook = WebhookRegistration(url="https://example.com", events=None)
        
        assert webhook.matches_event("email.received") is True
        assert webhook.matches_event("sms.sent") is True
        assert webhook.matches_event("simulation.started") is True
    
    def test_matches_event_exact_match(self):
        """Test exact event type matching."""
        webhook = WebhookRegistration(
            url="https://example.com",
            events=["email.received", "sms.sent"]
        )
        
        assert webhook.matches_event("email.received") is True
        assert webhook.matches_event("sms.sent") is True
        assert webhook.matches_event("email.sent") is False
        assert webhook.matches_event("sms.received") is False
    
    def test_matches_event_prefix_match(self):
        """Test prefix matching with trailing dot."""
        webhook = WebhookRegistration(
            url="https://example.com",
            events=["email.", "time."]
        )
        
        assert webhook.matches_event("email.received") is True
        assert webhook.matches_event("email.sent") is True
        assert webhook.matches_event("time.advanced") is True
        assert webhook.matches_event("sms.received") is False
    
    def test_matches_event_mixed(self):
        """Test mixed exact and prefix patterns."""
        webhook = WebhookRegistration(
            url="https://example.com",
            events=["email.", "sms.received"]
        )
        
        assert webhook.matches_event("email.received") is True
        assert webhook.matches_event("email.sent") is True
        assert webhook.matches_event("sms.received") is True
        assert webhook.matches_event("sms.sent") is False


class TestDeliveryRecord:
    """Tests for DeliveryRecord model."""
    
    def test_instantiation_with_required_fields(self):
        """Test creating a delivery record with required fields."""
        record = DeliveryRecord(
            webhook_id="wh_abc123",
            event_type="email.received",
            event_data={"email_id": "123"},
        )
        
        assert record.id.startswith("del_")
        assert record.webhook_id == "wh_abc123"
        assert record.event_type == "email.received"
        assert record.event_data == {"email_id": "123"}
        assert record.status == DeliveryStatus.PENDING
        assert record.attempt_count == 0
        assert isinstance(record.created_at, datetime)
    
    def test_instantiation_with_all_fields(self):
        """Test creating a delivery record with all fields."""
        now = datetime.now(timezone.utc)
        record = DeliveryRecord(
            id="del_custom",
            webhook_id="wh_abc123",
            event_type="email.received",
            event_data={"email_id": "123"},
            status=DeliveryStatus.DELIVERED,
            attempt_count=2,
            created_at=now,
            delivered_at=now,
            response_status=200,
            response_body="OK",
        )
        
        assert record.id == "del_custom"
        assert record.status == DeliveryStatus.DELIVERED
        assert record.attempt_count == 2
        assert record.response_status == 200
        assert record.response_body == "OK"


class TestCreateWebhookRequest:
    """Tests for CreateWebhookRequest model."""
    
    def test_instantiation_minimal(self):
        """Test creating a request with only URL."""
        request = CreateWebhookRequest(url="https://example.com/callback")
        
        assert request.url == "https://example.com/callback"
        assert request.events is None
        assert request.secret is None
        assert request.metadata == {}
    
    def test_instantiation_full(self):
        """Test creating a request with all fields."""
        request = CreateWebhookRequest(
            url="https://example.com/callback",
            events=["email."],
            secret="my-secret",
            metadata={"name": "test"},
        )
        
        assert request.url == "https://example.com/callback"
        assert request.events == ["email."]
        assert request.secret == "my-secret"
        assert request.metadata == {"name": "test"}
    
    def test_url_validation_invalid(self):
        """Test that invalid URLs are rejected."""
        with pytest.raises(ValueError, match="URL must be http"):
            CreateWebhookRequest(url="invalid-url")
    
    def test_events_validation_empty(self):
        """Test that empty events list is rejected."""
        with pytest.raises(ValueError, match="events list cannot be empty"):
            CreateWebhookRequest(url="https://example.com", events=[])


class TestUpdateWebhookRequest:
    """Tests for UpdateWebhookRequest model."""
    
    def test_all_fields_optional(self):
        """Test that all fields are optional."""
        request = UpdateWebhookRequest()
        
        assert request.url is None
        assert request.events is None
        assert request.secret is None
        assert request.metadata is None
        assert request.status is None
    
    def test_partial_update(self):
        """Test creating a partial update request."""
        request = UpdateWebhookRequest(
            url="https://new-url.com",
            status=WebhookStatus.PAUSED,
        )
        
        assert request.url == "https://new-url.com"
        assert request.status == WebhookStatus.PAUSED
        assert request.events is None
    
    def test_url_validation_invalid(self):
        """Test that invalid URLs are rejected."""
        with pytest.raises(ValueError, match="URL must be http"):
            UpdateWebhookRequest(url="invalid-url")


class TestWebhookStatus:
    """Tests for WebhookStatus enum."""
    
    def test_values(self):
        """Test enum values."""
        assert WebhookStatus.ACTIVE == "active"
        assert WebhookStatus.PAUSED == "paused"
        assert WebhookStatus.DISABLED == "disabled"


class TestDeliveryStatus:
    """Tests for DeliveryStatus enum."""
    
    def test_values(self):
        """Test enum values."""
        assert DeliveryStatus.PENDING == "pending"
        assert DeliveryStatus.DELIVERED == "delivered"
        assert DeliveryStatus.FAILED == "failed"
        assert DeliveryStatus.RETRYING == "retrying"
