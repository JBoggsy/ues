"""Webhook registration and dispatch management.

This module provides infrastructure for HTTP callback notifications.
Webhooks allow external services to receive event notifications without
maintaining persistent WebSocket connections.

Example usage:
    # In a REST route that modifies state:
    from api.webhooks import webhook_dispatcher, webhook_registry
    from api.websocket import WSEventType
    
    @router.post("/email/receive")
    async def receive_email(...):
        result = ...  # process email
        await webhook_dispatcher.dispatch(WSEventType.EMAIL_RECEIVED, {
            "email_id": result["email_id"],
            "from": result["from_address"],
        })
        return result
    
    # Register a webhook via API:
    webhook = WebhookRegistration(
        url="https://my-agent.example.com/callback",
        events=["email.", "sms.received"],
        secret="my-secret-key",
    )
    await webhook_registry.add(webhook)
"""

import asyncio
import hashlib
import hmac
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field, field_validator

from ues.api.websocket import WSEventType, WSEvent

logger = logging.getLogger(__name__)


class WebhookStatus(str, Enum):
    """Status of a webhook registration."""
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"  # Auto-disabled after too many failures


class DeliveryStatus(str, Enum):
    """Status of a webhook delivery attempt."""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


class WebhookRegistration(BaseModel):
    """A registered webhook callback configuration.
    
    Attributes:
        id: Unique identifier for this webhook (auto-generated).
        url: The callback URL to POST events to.
        events: List of event type patterns to receive. None = all events.
                Supports exact matches ("email.received") and prefixes ("email.").
        secret: Optional HMAC secret for signature verification.
        status: Current status of the webhook (active, paused, disabled).
        created_at: When the webhook was registered.
        updated_at: Last modification time.
        metadata: Arbitrary metadata (e.g., agent_name, description).
        failure_count: Consecutive delivery failures (resets on success).
        last_delivery_at: Timestamp of last successful delivery.
        last_failure_at: Timestamp of last failed delivery.
    """
    
    id: str = Field(default_factory=lambda: f"wh_{uuid.uuid4().hex[:12]}")
    url: str = Field(description="Callback URL to POST events to")
    events: Optional[list[str]] = Field(
        default=None,
        description="Event type patterns to receive. None = all events."
    )
    secret: Optional[str] = Field(
        default=None,
        description="HMAC secret for signature verification"
    )
    status: WebhookStatus = Field(
        default=WebhookStatus.ACTIVE,
        description="Current webhook status"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metadata"
    )
    failure_count: int = Field(default=0, ge=0)
    last_delivery_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    
    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate that URL is a valid HTTP(S) URL."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v
    
    @field_validator("events")
    @classmethod
    def validate_events(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Validate event patterns."""
        if v is None:
            return None
        if not v:
            raise ValueError("events list cannot be empty, use None for all events")
        return v
    
    def matches_event(self, event_type: str) -> bool:
        """Check if this webhook should receive an event type.
        
        Args:
            event_type: The event type string (e.g., "email.received").
        
        Returns:
            True if this webhook is subscribed to this event type.
        """
        if self.events is None:
            return True  # Subscribed to all events
        
        for pattern in self.events:
            if event_type == pattern:
                return True
            if pattern.endswith(".") and event_type.startswith(pattern):
                return True
        return False


class DeliveryRecord(BaseModel):
    """Record of a webhook delivery attempt.
    
    Attributes:
        id: Unique delivery ID.
        webhook_id: ID of the webhook this delivery is for.
        event_type: The event type that was delivered.
        event_data: The event data payload.
        status: Current delivery status.
        attempt_count: Number of delivery attempts made.
        created_at: When the delivery was queued.
        delivered_at: When delivery succeeded (if applicable).
        last_attempt_at: When the last attempt was made.
        response_status: HTTP status code from last attempt.
        response_body: Response body from last attempt (truncated).
        error_message: Error message if delivery failed.
    """
    
    id: str = Field(default_factory=lambda: f"del_{uuid.uuid4().hex[:12]}")
    webhook_id: str
    event_type: str
    event_data: dict[str, Any]
    status: DeliveryStatus = DeliveryStatus.PENDING
    attempt_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    delivered_at: Optional[datetime] = None
    last_attempt_at: Optional[datetime] = None
    response_status: Optional[int] = None
    response_body: Optional[str] = None  # Truncated to 500 chars
    error_message: Optional[str] = None


class CreateWebhookRequest(BaseModel):
    """Request to register a new webhook.
    
    Attributes:
        url: The callback URL to POST events to.
        events: Event type patterns to receive. Omit or null for all events.
        secret: Optional HMAC secret for payload signature verification.
        metadata: Arbitrary metadata to store with the webhook.
    """
    
    url: str = Field(description="Callback URL to POST events to")
    events: Optional[list[str]] = Field(
        default=None,
        description="Event patterns (e.g., ['email.', 'sms.received']). Null = all."
    )
    secret: Optional[str] = Field(
        default=None,
        description="HMAC secret for X-UES-Signature header"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom metadata (e.g., agent_name, description)"
    )
    
    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must be http:// or https://")
        return v
    
    @field_validator("events")
    @classmethod
    def validate_events(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Validate event patterns."""
        if v is not None and len(v) == 0:
            raise ValueError("events list cannot be empty, use null for all events")
        return v


class UpdateWebhookRequest(BaseModel):
    """Request to update an existing webhook.
    
    All fields are optional - only provided fields are updated.
    """
    
    url: Optional[str] = None
    events: Optional[list[str]] = None
    secret: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    status: Optional[WebhookStatus] = None
    
    @field_validator("url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate URL if provided."""
        if v is not None and not v.startswith(("http://", "https://")):
            raise ValueError("URL must be http:// or https://")
        return v


class WebhookResponse(BaseModel):
    """Response model for a webhook registration.
    
    Note: The secret field is intentionally excluded from responses.
    Secrets are only shown once at creation time.
    """
    
    id: str
    url: str
    events: Optional[list[str]]
    status: WebhookStatus
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any]
    failure_count: int
    last_delivery_at: Optional[datetime]
    last_failure_at: Optional[datetime]
    has_secret: bool = Field(description="Whether a secret is configured")


class WebhookListResponse(BaseModel):
    """Response model for listing webhooks."""
    
    items: list[WebhookResponse]
    total: int
    limit: int
    offset: int


class WebhookTestResponse(BaseModel):
    """Response model for webhook connectivity test."""
    
    webhook_id: str
    success: bool
    response_status: Optional[int]
    response_time_ms: Optional[float]
    response_body: Optional[str]
    error_message: Optional[str]


class DeliveryListResponse(BaseModel):
    """Response model for listing delivery records."""
    
    items: list[DeliveryRecord]
    total: int


# =============================================================================
# Webhook Registry
# =============================================================================


class WebhookRegistry:
    """In-memory registry of webhook registrations.
    
    Thread-safe storage for webhook configurations. In a production
    deployment, this could be backed by a database, but for UES's
    primary use case (local development/testing), in-memory is sufficient.
    
    Attributes:
        _webhooks: Map of webhook ID to WebhookRegistration.
        _lock: Async lock for thread-safe access.
    """
    
    def __init__(self) -> None:
        """Initialize the registry with empty storage."""
        self._webhooks: dict[str, WebhookRegistration] = {}
        self._lock = asyncio.Lock()
    
    async def add(self, webhook: WebhookRegistration) -> None:
        """Register a new webhook.
        
        Args:
            webhook: The webhook registration to add.
        """
        async with self._lock:
            self._webhooks[webhook.id] = webhook
    
    async def get(self, webhook_id: str) -> Optional[WebhookRegistration]:
        """Get a webhook by ID.
        
        Args:
            webhook_id: The webhook's unique identifier.
        
        Returns:
            The webhook registration if found, None otherwise.
        """
        return self._webhooks.get(webhook_id)
    
    async def update(
        self, webhook_id: str, updates: dict[str, Any]
    ) -> Optional[WebhookRegistration]:
        """Update a webhook's configuration.
        
        Args:
            webhook_id: The webhook's unique identifier.
            updates: Dictionary of fields to update.
        
        Returns:
            The updated webhook registration if found, None otherwise.
        """
        async with self._lock:
            webhook = self._webhooks.get(webhook_id)
            if webhook:
                for key, value in updates.items():
                    if hasattr(webhook, key):
                        setattr(webhook, key, value)
                webhook.updated_at = datetime.now(timezone.utc)
            return webhook
    
    async def delete(self, webhook_id: str) -> bool:
        """Remove a webhook registration.
        
        Args:
            webhook_id: The webhook's unique identifier.
        
        Returns:
            True if the webhook was deleted, False if not found.
        """
        async with self._lock:
            if webhook_id in self._webhooks:
                del self._webhooks[webhook_id]
                return True
            return False
    
    async def list_all(
        self,
        status: Optional[WebhookStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[WebhookRegistration], int]:
        """List all webhooks, optionally filtered by status.
        
        Args:
            status: Filter by webhook status (optional).
            limit: Maximum number of results to return.
            offset: Number of results to skip.
        
        Returns:
            Tuple of (list of webhooks, total count before pagination).
        """
        webhooks = list(self._webhooks.values())
        if status:
            webhooks = [w for w in webhooks if w.status == status]
        
        total = len(webhooks)
        return webhooks[offset:offset + limit], total
    
    async def get_matching(self, event_type: str) -> list[WebhookRegistration]:
        """Get all active webhooks that match an event type.
        
        Args:
            event_type: The event type to match (e.g., "email.received").
        
        Returns:
            List of active webhooks that should receive this event.
        """
        return [
            w for w in self._webhooks.values()
            if w.status == WebhookStatus.ACTIVE and w.matches_event(event_type)
        ]
    
    async def clear(self) -> None:
        """Remove all webhook registrations (for testing/reset)."""
        async with self._lock:
            self._webhooks.clear()
    
    def count(self) -> int:
        """Get the number of registered webhooks.
        
        Returns:
            The total count of registered webhooks.
        """
        return len(self._webhooks)
    
    def count_active(self) -> int:
        """Get the number of active webhooks.
        
        Returns:
            The count of webhooks with status ACTIVE.
        """
        return sum(1 for w in self._webhooks.values() if w.status == WebhookStatus.ACTIVE)


# =============================================================================
# Webhook Dispatcher
# =============================================================================


class WebhookDispatcher:
    """Dispatches events to registered webhook URLs.
    
    Handles the actual HTTP delivery of events to webhook endpoints.
    Deliveries are performed asynchronously to avoid blocking API responses.
    Includes retry logic for failed deliveries.
    
    Configuration:
        max_retries: Maximum retry attempts for failed deliveries (default 3)
        retry_delay_seconds: Base delay between retries, with exponential backoff
        timeout_seconds: HTTP request timeout
        max_failure_count: Consecutive failures before auto-disabling webhook
    
    Attributes:
        registry: The WebhookRegistry to look up webhook configurations.
        _http_client: Shared httpx.AsyncClient for making requests.
        _delivery_history: Recent delivery records (limited size).
    """
    
    def __init__(
        self,
        registry: WebhookRegistry,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
        timeout_seconds: float = 10.0,
        max_failure_count: int = 10,
    ) -> None:
        """Initialize the dispatcher.
        
        Args:
            registry: The WebhookRegistry for looking up webhooks.
            max_retries: Maximum delivery retry attempts.
            retry_delay_seconds: Base delay between retries.
            timeout_seconds: HTTP request timeout.
            max_failure_count: Failures before auto-disabling.
        """
        self.registry = registry
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.timeout_seconds = timeout_seconds
        self.max_failure_count = max_failure_count
        self._http_client: Optional[httpx.AsyncClient] = None
        self._delivery_history: dict[str, list[DeliveryRecord]] = {}
        self._max_history_per_webhook = 100
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client.
        
        Returns:
            The shared httpx.AsyncClient instance.
        """
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=self.timeout_seconds)
        return self._http_client
    
    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
    
    def _compute_signature(self, payload: str, secret: str) -> str:
        """Compute HMAC-SHA256 signature for payload verification.
        
        The signature allows webhook receivers to verify that the
        payload came from UES and wasn't tampered with.
        
        Args:
            payload: The JSON payload string.
            secret: The webhook's HMAC secret.
        
        Returns:
            Signature in format "sha256=<hex_digest>".
        """
        signature = hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    
    async def dispatch(
        self,
        event_type: WSEventType,
        data: dict[str, Any],
    ) -> int:
        """Dispatch an event to all matching webhooks.
        
        This is the main entry point, called alongside ws_manager.broadcast().
        Deliveries are scheduled as background tasks to avoid blocking.
        
        Args:
            event_type: The type of event to dispatch.
            data: Event payload data.
        
        Returns:
            Number of webhooks the event was dispatched to.
        """
        matching = await self.registry.get_matching(event_type.value)
        if not matching:
            return 0
        
        event = WSEvent.create(event_type, data)
        
        for webhook in matching:
            # Schedule delivery as background task
            asyncio.create_task(
                self._deliver(webhook, event)
            )
        
        logger.debug(f"Dispatched {event_type.value} to {len(matching)} webhooks")
        return len(matching)
    
    async def _deliver(
        self,
        webhook: WebhookRegistration,
        event: WSEvent,
        attempt: int = 1,
    ) -> DeliveryRecord:
        """Deliver an event to a specific webhook with retry logic.
        
        Args:
            webhook: The webhook to deliver to.
            event: The event to deliver.
            attempt: Current attempt number (1-based).
        
        Returns:
            DeliveryRecord with the result.
        """
        record = DeliveryRecord(
            webhook_id=webhook.id,
            event_type=event.type,
            event_data=event.data,
        )
        
        payload = event.model_dump_json()
        headers = {
            "Content-Type": "application/json",
            "X-UES-Event": event.type,
            "X-UES-Delivery-ID": record.id,
            "X-UES-Timestamp": event.timestamp,
        }
        
        if webhook.secret:
            headers["X-UES-Signature"] = self._compute_signature(payload, webhook.secret)
        
        try:
            client = await self._get_client()
            record.attempt_count = attempt
            record.last_attempt_at = datetime.now(timezone.utc)
            
            response = await client.post(
                webhook.url,
                content=payload,
                headers=headers,
            )
            
            record.response_status = response.status_code
            record.response_body = response.text[:500] if response.text else None
            
            if 200 <= response.status_code < 300:
                # Success
                record.status = DeliveryStatus.DELIVERED
                record.delivered_at = datetime.now(timezone.utc)
                
                # Reset failure count on success
                await self.registry.update(webhook.id, {
                    "failure_count": 0,
                    "last_delivery_at": record.delivered_at,
                })
                
                logger.debug(f"Delivered {event.type} to {webhook.url}")
            else:
                # Non-2xx response
                record.status = DeliveryStatus.FAILED
                record.error_message = f"HTTP {response.status_code}"
                await self._handle_failure(webhook, record, attempt)
                
        except Exception as e:
            record.status = DeliveryStatus.FAILED
            record.error_message = str(e)
            record.last_attempt_at = datetime.now(timezone.utc)
            await self._handle_failure(webhook, record, attempt)
        
        # Store delivery record
        self._store_delivery_record(webhook.id, record)
        
        return record
    
    async def _handle_failure(
        self,
        webhook: WebhookRegistration,
        record: DeliveryRecord,
        attempt: int,
    ) -> None:
        """Handle a failed delivery attempt.
        
        Implements exponential backoff retry and auto-disable after
        too many consecutive failures.
        
        Args:
            webhook: The webhook that failed.
            record: The delivery record to update.
            attempt: The current attempt number.
        """
        logger.warning(
            f"Webhook delivery failed: {webhook.url} - {record.error_message} "
            f"(attempt {attempt}/{self.max_retries})"
        )
        
        # Update failure tracking
        new_failure_count = webhook.failure_count + 1
        updates: dict[str, Any] = {
            "failure_count": new_failure_count,
            "last_failure_at": datetime.now(timezone.utc),
        }
        
        # Auto-disable after too many failures
        if new_failure_count >= self.max_failure_count:
            updates["status"] = WebhookStatus.DISABLED
            logger.error(
                f"Webhook {webhook.id} auto-disabled after "
                f"{new_failure_count} consecutive failures"
            )
        
        await self.registry.update(webhook.id, updates)
        
        # Retry with exponential backoff
        if attempt < self.max_retries:
            record.status = DeliveryStatus.RETRYING
            delay = self.retry_delay_seconds * (2 ** (attempt - 1))
            await asyncio.sleep(delay)
            
            # Re-fetch webhook in case it was updated/disabled
            updated_webhook = await self.registry.get(webhook.id)
            if updated_webhook and updated_webhook.status == WebhookStatus.ACTIVE:
                # Reconstruct event for retry
                event = WSEvent(
                    type=record.event_type,
                    data=record.event_data,
                    timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                )
                await self._deliver(updated_webhook, event, attempt + 1)
    
    def _store_delivery_record(self, webhook_id: str, record: DeliveryRecord) -> None:
        """Store a delivery record in history (limited size).
        
        Args:
            webhook_id: The webhook's unique identifier.
            record: The delivery record to store.
        """
        if webhook_id not in self._delivery_history:
            self._delivery_history[webhook_id] = []
        
        history = self._delivery_history[webhook_id]
        history.append(record)
        
        # Trim to max size
        if len(history) > self._max_history_per_webhook:
            self._delivery_history[webhook_id] = history[-self._max_history_per_webhook:]
    
    def get_delivery_history(
        self,
        webhook_id: str,
        limit: int = 50,
    ) -> list[DeliveryRecord]:
        """Get recent delivery records for a webhook.
        
        Args:
            webhook_id: The webhook's unique identifier.
            limit: Maximum number of records to return.
        
        Returns:
            List of delivery records, most recent first.
        """
        history = self._delivery_history.get(webhook_id, [])
        return list(reversed(history[-limit:]))  # Most recent first
    
    async def test_webhook(self, webhook: WebhookRegistration) -> DeliveryRecord:
        """Send a test event to a webhook.
        
        Sends a synthetic "webhook.test" event to verify connectivity.
        This does NOT count against failure tracking.
        
        Args:
            webhook: The webhook to test.
        
        Returns:
            DeliveryRecord with the test result.
        """
        test_event = WSEvent(
            type="webhook.test",
            data={
                "webhook_id": webhook.id,
                "message": "This is a test event from UES",
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            },
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        )
        
        # Deliver but don't retry or track failures
        record = DeliveryRecord(
            webhook_id=webhook.id,
            event_type=test_event.type,
            event_data=test_event.data,
        )
        
        payload = test_event.model_dump_json()
        headers = {
            "Content-Type": "application/json",
            "X-UES-Event": test_event.type,
            "X-UES-Delivery-ID": record.id,
            "X-UES-Timestamp": test_event.timestamp,
        }
        
        if webhook.secret:
            headers["X-UES-Signature"] = self._compute_signature(payload, webhook.secret)
        
        start_time: Optional[float] = None
        elapsed_ms: Optional[float] = None
        
        try:
            client = await self._get_client()
            start_time = asyncio.get_event_loop().time()
            response = await client.post(webhook.url, content=payload, headers=headers)
            elapsed_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            record.response_status = response.status_code
            record.response_body = response.text[:500] if response.text else None
            record.attempt_count = 1
            record.last_attempt_at = datetime.now(timezone.utc)
            
            if 200 <= response.status_code < 300:
                record.status = DeliveryStatus.DELIVERED
                record.delivered_at = record.last_attempt_at
            else:
                record.status = DeliveryStatus.FAILED
                record.error_message = f"HTTP {response.status_code}"
                
        except Exception as e:
            if start_time is not None:
                elapsed_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            record.status = DeliveryStatus.FAILED
            record.error_message = str(e)
            record.attempt_count = 1
            record.last_attempt_at = datetime.now(timezone.utc)
        
        # Store elapsed time in a way tests can access
        record._elapsed_ms = elapsed_ms  # type: ignore
        
        return record
    
    def clear_history(self, webhook_id: Optional[str] = None) -> None:
        """Clear delivery history.
        
        Args:
            webhook_id: If provided, clear only that webhook's history.
                       If None, clear all history.
        """
        if webhook_id:
            self._delivery_history.pop(webhook_id, None)
        else:
            self._delivery_history.clear()


# =============================================================================
# Global Instances
# =============================================================================

# Global instances (like ws_manager in websocket.py)
webhook_registry = WebhookRegistry()
webhook_dispatcher = WebhookDispatcher(webhook_registry)
