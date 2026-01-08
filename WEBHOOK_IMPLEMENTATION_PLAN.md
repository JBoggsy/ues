# Webhook Implementation Plan

This document describes the design and implementation plan for adding webhook support to UES. Webhooks enable external services (AI agents, microservices, serverless functions) to receive event notifications via HTTP callbacks without maintaining persistent WebSocket connections.

## Table of Contents

1. [Overview](#overview)
2. [Design Goals](#design-goals)
3. [Architecture](#architecture)
4. [Data Models](#data-models)
5. [API Endpoints](#api-endpoints)
6. [Webhook Dispatcher](#webhook-dispatcher)
7. [Security Considerations](#security-considerations)
8. [Integration with Existing Code](#integration-with-existing-code)
9. [Client Library Extensions](#client-library-extensions)
10. [Implementation Phases](#implementation-phases)
11. [Testing Plan](#testing-plan)
12. [Documentation Plan](#documentation-plan)

---

## Overview

### What Are Webhooks?

Webhooks are HTTP callbacks that UES will POST to registered URLs when events occur. Unlike WebSockets (which require clients to maintain persistent connections), webhooks push event data to external HTTP endpoints that clients configure in advance.

### Comparison with Existing WebSocket Support

| Aspect | WebSocket (existing) | Webhook (new) |
|--------|---------------------|---------------|
| **Connection Model** | Client connects to server | Server POSTs to client URL |
| **Client Requirement** | Must maintain open connection | Just expose HTTP endpoint |
| **Registration** | Connect to `/ws`, send subscribe message | POST to `/webhooks` with callback URL |
| **Delivery Guarantee** | None (missed if disconnected) | Retries, delivery tracking |
| **Use Case** | Real-time UIs, dashboards | External agents, serverless, microservices |
| **Event Filtering** | Send subscription message | Specify `events` array at registration |

### When to Use Webhooks

- External AI agents running as separate HTTP services
- Serverless functions (AWS Lambda, Cloud Functions) triggered by events
- Integration with external systems that can't maintain WebSocket connections
- Audit/logging services that need guaranteed delivery
- Orchestration systems that trigger workflows on events

---

## Design Goals

1. **Consistency**: Reuse existing `WSEventType` enum and `WSEvent` payload format
2. **Reliability**: Support retry logic for failed deliveries
3. **Security**: HMAC signature verification for payload authenticity
4. **Observability**: Delivery status tracking and logging
5. **Simplicity**: Minimal API surface, easy to understand and use
6. **Non-blocking**: Webhook delivery should not slow down API responses
7. **Testability**: Easy to test without external HTTP servers

---

## Architecture

### High-Level Flow

```
1. Client registers webhook:
   POST /webhooks → {url: "https://agent:8080/callback", events: ["email."]}
   
2. Event occurs (e.g., email received):
   POST /email/receive → EmailState updated
   
3. Broadcast to all channels:
   a) ws_manager.broadcast(EMAIL_RECEIVED, data)      # Existing WebSocket
   b) webhook_dispatcher.dispatch(EMAIL_RECEIVED, data)  # NEW webhook dispatch
   
4. WebhookDispatcher:
   - Filters registered webhooks by event type
   - Queues delivery tasks (async, non-blocking)
   - POSTs to each matching webhook URL
   - Handles retries on failure
   - Records delivery status
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Routes                                │
│  (email.py, sms.py, calendar.py, time.py, simulation.py, ...)   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ On state change:
                              │   await ws_manager.broadcast(...)
                              │   await webhook_dispatcher.dispatch(...)
                              ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                                                             │
    │   ┌─────────────────┐       ┌─────────────────────────┐     │
    │   │   ws_manager    │       │   webhook_dispatcher    │     │
    │   │  (websocket.py) │       │     (webhooks.py)       │     │
    │   └────────┬────────┘       └───────────┬─────────────┘     │
    │            │                            │                   │
    │            ▼                            ▼                   │
    │   WebSocket Clients            ┌─────────────────┐          │
    │   (browser, Python)            │ WebhookRegistry │          │
    │                                │  (in-memory)    │          │
    │                                └────────┬────────┘          │
    │                                         │                   │
    │                                         ▼                   │
    │                                ┌─────────────────┐          │
    │                                │ Delivery Queue  │          │
    │                                │  (async tasks)  │          │
    │                                └────────┬────────┘          │
    │                                         │                   │
    └─────────────────────────────────────────┼───────────────────┘
                                              │
                                              ▼
                                    External HTTP Endpoints
                                    (AI agents, serverless, etc.)
```

---

## Data Models

### Location: `api/webhooks.py`

```python
"""Webhook registration and dispatch management.

This module provides infrastructure for HTTP callback notifications.
Webhooks allow external services to receive event notifications without
maintaining persistent WebSocket connections.
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
from pydantic import BaseModel, Field, field_validator, HttpUrl

from api.websocket import WSEventType, WSEvent

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
```

### Webhook Create/Update Request Models

```python
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
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must be http:// or https://")
        return v


class UpdateWebhookRequest(BaseModel):
    """Request to update an existing webhook.
    
    All fields are optional - only provided fields are updated.
    """
    
    url: Optional[str] = None
    events: Optional[list[str]] = None  # Empty list to unset (receive all)
    secret: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    status: Optional[WebhookStatus] = None
    
    @field_validator("url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.startswith(("http://", "https://")):
            raise ValueError("URL must be http:// or https://")
        return v
```

---

## API Endpoints

### Location: `api/routes/webhooks.py`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/webhooks` | Register a new webhook |
| `GET` | `/webhooks` | List all registered webhooks |
| `GET` | `/webhooks/{id}` | Get webhook details |
| `PATCH` | `/webhooks/{id}` | Update webhook configuration |
| `DELETE` | `/webhooks/{id}` | Unregister a webhook |
| `POST` | `/webhooks/{id}/test` | Send a test event to verify connectivity |
| `GET` | `/webhooks/{id}/deliveries` | Get delivery history for a webhook |
| `POST` | `/webhooks/{id}/pause` | Pause webhook (stop deliveries) |
| `POST` | `/webhooks/{id}/resume` | Resume paused webhook |

### Endpoint Details

#### POST /webhooks - Register Webhook

```python
@router.post("/webhooks", response_model=WebhookResponse, status_code=201)
async def create_webhook(request: CreateWebhookRequest) -> WebhookResponse:
    """Register a new webhook callback URL.
    
    The webhook will receive POST requests when matching events occur.
    Events are filtered by the `events` array - use dot-prefix patterns
    (e.g., "email.") to subscribe to all events in a category.
    
    Request Body:
        url: Callback URL (must be http:// or https://)
        events: Event patterns to receive (null = all events)
        secret: HMAC secret for signature verification
        metadata: Custom metadata
    
    Returns:
        The created webhook registration with its ID.
    
    Example:
        POST /webhooks
        {
            "url": "https://my-agent.example.com/ues-callback",
            "events": ["email.received", "sms."],
            "secret": "my-secret-key",
            "metadata": {"agent_name": "Email Bot"}
        }
        
        Response (201):
        {
            "id": "wh_abc123def456",
            "url": "https://my-agent.example.com/ues-callback",
            "events": ["email.received", "sms."],
            "status": "active",
            "created_at": "2026-01-08T10:30:00Z",
            ...
        }
    """
```

#### GET /webhooks - List Webhooks

```python
@router.get("/webhooks", response_model=WebhookListResponse)
async def list_webhooks(
    status: Optional[WebhookStatus] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> WebhookListResponse:
    """List all registered webhooks.
    
    Query Parameters:
        status: Filter by webhook status (active, paused, disabled)
        limit: Maximum results to return (default 50)
        offset: Pagination offset
    
    Returns:
        List of webhook registrations.
    """
```

#### POST /webhooks/{id}/test - Test Webhook

```python
@router.post("/webhooks/{webhook_id}/test", response_model=WebhookTestResponse)
async def test_webhook(webhook_id: str) -> WebhookTestResponse:
    """Send a test event to verify webhook connectivity.
    
    Sends a synthetic "webhook.test" event to the registered URL
    and reports the delivery result. This is useful for verifying
    that the callback URL is accessible and responding correctly.
    
    Path Parameters:
        webhook_id: The webhook to test.
    
    Returns:
        Test result including HTTP status and response time.
    
    Example Response:
        {
            "webhook_id": "wh_abc123",
            "success": true,
            "response_status": 200,
            "response_time_ms": 145,
            "response_body": "OK"
        }
    """
```

---

## Webhook Dispatcher

### Location: `api/webhooks.py`

```python
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
        self._webhooks: dict[str, WebhookRegistration] = {}
        self._lock = asyncio.Lock()
    
    async def add(self, webhook: WebhookRegistration) -> None:
        """Register a new webhook."""
        async with self._lock:
            self._webhooks[webhook.id] = webhook
    
    async def get(self, webhook_id: str) -> Optional[WebhookRegistration]:
        """Get a webhook by ID."""
        return self._webhooks.get(webhook_id)
    
    async def update(self, webhook_id: str, updates: dict[str, Any]) -> Optional[WebhookRegistration]:
        """Update a webhook's configuration."""
        async with self._lock:
            webhook = self._webhooks.get(webhook_id)
            if webhook:
                for key, value in updates.items():
                    if hasattr(webhook, key):
                        setattr(webhook, key, value)
                webhook.updated_at = datetime.now(timezone.utc)
            return webhook
    
    async def delete(self, webhook_id: str) -> bool:
        """Remove a webhook registration."""
        async with self._lock:
            if webhook_id in self._webhooks:
                del self._webhooks[webhook_id]
                return True
            return False
    
    async def list_all(
        self, 
        status: Optional[WebhookStatus] = None
    ) -> list[WebhookRegistration]:
        """List all webhooks, optionally filtered by status."""
        webhooks = list(self._webhooks.values())
        if status:
            webhooks = [w for w in webhooks if w.status == status]
        return webhooks
    
    async def get_matching(self, event_type: str) -> list[WebhookRegistration]:
        """Get all active webhooks that match an event type."""
        return [
            w for w in self._webhooks.values()
            if w.status == WebhookStatus.ACTIVE and w.matches_event(event_type)
        ]
    
    async def clear(self) -> None:
        """Remove all webhook registrations (for testing/reset)."""
        async with self._lock:
            self._webhooks.clear()


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
        self.registry = registry
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.timeout_seconds = timeout_seconds
        self.max_failure_count = max_failure_count
        self._http_client: Optional[httpx.AsyncClient] = None
        self._delivery_history: dict[str, list[DeliveryRecord]] = {}  # webhook_id -> records
        self._max_history_per_webhook = 100
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=self.timeout_seconds)
        return self._http_client
    
    async def close(self) -> None:
        """Close the HTTP client."""
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
        """
        logger.warning(
            f"Webhook delivery failed: {webhook.url} - {record.error_message} "
            f"(attempt {attempt}/{self.max_retries})"
        )
        
        # Update failure tracking
        new_failure_count = webhook.failure_count + 1
        updates = {
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
        """Store a delivery record in history (limited size)."""
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
        """Get recent delivery records for a webhook."""
        history = self._delivery_history.get(webhook_id, [])
        return list(reversed(history[-limit:]))  # Most recent first
    
    async def test_webhook(self, webhook: WebhookRegistration) -> DeliveryRecord:
        """Send a test event to a webhook.
        
        Sends a synthetic "webhook.test" event to verify connectivity.
        This does NOT count against failure tracking.
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
        
        try:
            client = await self._get_client()
            start = asyncio.get_event_loop().time()
            response = await client.post(webhook.url, content=payload, headers=headers)
            elapsed_ms = (asyncio.get_event_loop().time() - start) * 1000
            
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
            record.status = DeliveryStatus.FAILED
            record.error_message = str(e)
            record.attempt_count = 1
            record.last_attempt_at = datetime.now(timezone.utc)
        
        return record


# Global instances (like ws_manager in websocket.py)
webhook_registry = WebhookRegistry()
webhook_dispatcher = WebhookDispatcher(webhook_registry)
```

---

## Security Considerations

### HMAC Signature Verification

When a webhook has a `secret` configured, UES includes an `X-UES-Signature` header with each delivery. The receiver should verify this signature to ensure:

1. The payload came from UES (authenticity)
2. The payload wasn't modified in transit (integrity)

**Verification example (Python):**

```python
import hmac
import hashlib

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify the X-UES-Signature header."""
    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)
```

### URL Validation

- Only `http://` and `https://` URLs are allowed
- In production deployments, consider restricting to `https://` only
- Consider allowing URL allowlists/blocklists for enterprise deployments

### Rate Limiting

The current design does not include rate limiting for webhook deliveries. If needed:
- Add per-webhook rate limits (e.g., max 100 deliveries/minute)
- Add global rate limits across all webhooks
- Queue deliveries when limits are exceeded

### Secret Management

- Secrets are stored in memory (acceptable for development use case)
- Secrets are not returned in GET responses (only shown once at creation)
- For production: consider encrypting secrets at rest

---

## Integration with Existing Code

### Changes to Route Handlers

Each modality route that broadcasts WebSocket events needs to also dispatch webhooks. This is a mechanical change:

**Pattern (in each route file):**

```python
# Add import
from api.webhooks import webhook_dispatcher

# In each endpoint that broadcasts:
@router.post("/email/receive")
async def receive_email(request: ReceiveEmailRequest, engine: SimulationEngineDep):
    # ... existing logic to apply email ...
    
    # Existing WebSocket broadcast
    await ws_manager.broadcast(WSEventType.EMAIL_RECEIVED, {
        "email_id": email.message_id,
        "from": email.from_address,
        # ...
    })
    
    # NEW: Webhook dispatch
    await webhook_dispatcher.dispatch(WSEventType.EMAIL_RECEIVED, {
        "email_id": email.message_id,
        "from": email.from_address,
        # ...
    })
    
    return response
```

### Files to Modify

| File | Change |
|------|--------|
| `api/routes/email.py` | Add webhook dispatch calls (~11 endpoints) |
| `api/routes/sms.py` | Add webhook dispatch calls (~6 endpoints) |
| `api/routes/chat.py` | Add webhook dispatch calls (~3 endpoints) |
| `api/routes/calendar.py` | Add webhook dispatch calls (~4 endpoints) |
| `api/routes/location.py` | Add webhook dispatch call (1 endpoint) |
| `api/routes/weather.py` | Add webhook dispatch call (1 endpoint) |
| `api/routes/time.py` | Add webhook dispatch calls (~6 endpoints) |
| `api/routes/simulation.py` | Add webhook dispatch calls (~4 endpoints) |
| `api/routes/events.py` | Add webhook dispatch calls (~3 endpoints) |
| `main.py` | Register webhook router, add shutdown handler |

### Helper Function

To reduce repetition, add a helper that broadcasts to both channels:

```python
# In api/utils.py or api/broadcast.py

from api.websocket import ws_manager, WSEventType
from api.webhooks import webhook_dispatcher

async def broadcast_event(event_type: WSEventType, data: dict) -> None:
    """Broadcast an event to all WebSocket and webhook subscribers.
    
    This is the standard way to notify clients of state changes.
    Call this instead of directly calling ws_manager.broadcast().
    
    Args:
        event_type: The type of event to broadcast.
        data: Event payload data.
    """
    await ws_manager.broadcast(event_type, data)
    await webhook_dispatcher.dispatch(event_type, data)
```

Then route handlers just call:

```python
from api.broadcast import broadcast_event

await broadcast_event(WSEventType.EMAIL_RECEIVED, email_data)
```

---

## Client Library Extensions

### Location: `client/_webhooks.py`

```python
"""Webhook management client for UES API.

Provides methods for registering, managing, and testing webhooks.

Example:
    from client import UESClient
    
    client = UESClient()
    
    # Register a webhook
    webhook = client.webhooks.register(
        url="https://my-agent.example.com/callback",
        events=["email.", "sms.received"],
        secret="my-secret",
        metadata={"agent": "EmailBot"}
    )
    print(f"Registered webhook: {webhook['id']}")
    
    # Test the webhook
    result = client.webhooks.test(webhook['id'])
    print(f"Test result: {result['success']}")
    
    # List webhooks
    webhooks = client.webhooks.list()
    for wh in webhooks['items']:
        print(f"- {wh['id']}: {wh['url']}")
    
    # Delete webhook
    client.webhooks.delete(webhook['id'])
"""

from typing import Any, Optional

from client._base import BaseSubClient


class WebhookSubClient(BaseSubClient):
    """Sub-client for webhook management operations."""
    
    def register(
        self,
        url: str,
        events: Optional[list[str]] = None,
        secret: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Register a new webhook.
        
        Args:
            url: Callback URL to POST events to.
            events: Event patterns to receive (None = all).
            secret: HMAC secret for signature verification.
            metadata: Custom metadata to store.
        
        Returns:
            The created webhook registration.
        
        Raises:
            ValidationError: If the request data is invalid.
            UESClientError: If registration fails.
        """
        payload = {"url": url}
        if events is not None:
            payload["events"] = events
        if secret is not None:
            payload["secret"] = secret
        if metadata is not None:
            payload["metadata"] = metadata
        
        return self._post("/webhooks", json=payload)
    
    def get(self, webhook_id: str) -> dict[str, Any]:
        """Get a webhook by ID."""
        return self._get(f"/webhooks/{webhook_id}")
    
    def list(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List registered webhooks."""
        params = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        return self._get("/webhooks", params=params)
    
    def update(
        self,
        webhook_id: str,
        url: Optional[str] = None,
        events: Optional[list[str]] = None,
        secret: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        status: Optional[str] = None,
    ) -> dict[str, Any]:
        """Update a webhook configuration."""
        payload = {}
        if url is not None:
            payload["url"] = url
        if events is not None:
            payload["events"] = events
        if secret is not None:
            payload["secret"] = secret
        if metadata is not None:
            payload["metadata"] = metadata
        if status is not None:
            payload["status"] = status
        
        return self._patch(f"/webhooks/{webhook_id}", json=payload)
    
    def delete(self, webhook_id: str) -> None:
        """Delete a webhook registration."""
        self._delete(f"/webhooks/{webhook_id}")
    
    def test(self, webhook_id: str) -> dict[str, Any]:
        """Send a test event to a webhook."""
        return self._post(f"/webhooks/{webhook_id}/test")
    
    def pause(self, webhook_id: str) -> dict[str, Any]:
        """Pause a webhook (stop deliveries)."""
        return self._post(f"/webhooks/{webhook_id}/pause")
    
    def resume(self, webhook_id: str) -> dict[str, Any]:
        """Resume a paused webhook."""
        return self._post(f"/webhooks/{webhook_id}/resume")
    
    def get_deliveries(
        self,
        webhook_id: str,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Get delivery history for a webhook."""
        return self._get(f"/webhooks/{webhook_id}/deliveries", params={"limit": limit})
```

### Integration with UESClient

```python
# In client/client.py

from client._webhooks import WebhookSubClient

class UESClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        # ... existing sub-clients ...
        self.webhooks = WebhookSubClient(self._http)
```

---

## Implementation Phases

### Phase 1: Core Infrastructure (Day 1)

**Files to create:**
- `api/webhooks.py` - Models and dispatcher

**Tasks:**
1. Create `WebhookRegistration` model
2. Create `DeliveryRecord` model
3. Create `WebhookStatus` and `DeliveryStatus` enums
4. Implement `WebhookRegistry` class
5. Implement `WebhookDispatcher` class (dispatch, deliver, retry logic)
6. Implement HMAC signature computation
7. Create global `webhook_registry` and `webhook_dispatcher` instances

**Tests:**
- `tests/api/unit/test_webhook_models.py` - Model validation
- `tests/api/unit/test_webhook_registry.py` - Registry CRUD operations
- `tests/api/unit/test_webhook_dispatcher.py` - Dispatch logic, retry, signatures

### Phase 2: API Routes (Day 1-2)

**Files to create:**
- `api/routes/webhooks.py` - REST endpoints

**Tasks:**
1. Implement `POST /webhooks` (register)
2. Implement `GET /webhooks` (list)
3. Implement `GET /webhooks/{id}` (get details)
4. Implement `PATCH /webhooks/{id}` (update)
5. Implement `DELETE /webhooks/{id}` (unregister)
6. Implement `POST /webhooks/{id}/test` (connectivity test)
7. Implement `GET /webhooks/{id}/deliveries` (delivery history)
8. Implement `POST /webhooks/{id}/pause` and `/resume`
9. Register router in `main.py`

**Tests:**
- `tests/api/webhooks/test_webhook_registration.py`
- `tests/api/webhooks/test_webhook_crud.py`
- `tests/api/webhooks/test_webhook_test_endpoint.py`
- `tests/api/webhooks/test_webhook_deliveries.py`

### Phase 3: Broadcast Integration (Day 2)

**Files to modify:**
- `api/broadcast.py` (new) - Unified broadcast helper
- All route files that call `ws_manager.broadcast()`

**Tasks:**
1. Create `broadcast_event()` helper function
2. Update `email.py` routes to use broadcast helper
3. Update `sms.py` routes
4. Update `chat.py` routes
5. Update `calendar.py` routes
6. Update `location.py` routes
7. Update `weather.py` routes
8. Update `time.py` routes
9. Update `simulation.py` routes
10. Update `events.py` routes
11. Add dispatcher shutdown to `main.py` lifespan

**Tests:**
- `tests/api/webhooks/test_webhook_delivery_integration.py` - End-to-end delivery tests

### Phase 4: Client Library (Day 2-3)

**Files to create:**
- `client/_webhooks.py` - Webhook sub-client

**Files to modify:**
- `client/client.py` - Add webhooks property
- `client/__init__.py` - Export WebhookSubClient

**Tasks:**
1. Implement `WebhookSubClient` with all methods
2. Add to `UESClient` and `AsyncUESClient`
3. Add async version of sub-client
4. Update exports

**Tests:**
- `tests/client/unit/test_webhooks.py` - Unit tests
- `tests/client/integration/test_webhooks_integration.py` - Integration tests

### Phase 5: Documentation (Day 3)

**Files to create:**
- `docs/WEBHOOKS.md` - User documentation

**Tasks:**
1. Write webhook overview and comparison with WebSockets
2. Document all API endpoints with examples
3. Document Python client usage
4. Document HMAC signature verification (with examples)
5. Add troubleshooting section
6. Update `docs/API_CLIENT.md` with webhooks section
7. Update `TODO.md` to mark complete

### Phase 6: Polish & Edge Cases (Day 3)

**Tasks:**
1. Add webhook count to `/simulation/status` response
2. Handle webhook cleanup on `/simulation/clear`
3. Add logging for all webhook operations
4. Test concurrent webhook deliveries
5. Test webhook behavior during simulation reset
6. Consider persistence (stretch goal - save/load with scenarios)

---

## Testing Plan

### Unit Tests (60+ tests)

**`tests/api/unit/test_webhook_models.py`** (~15 tests)
- `WebhookRegistration` instantiation and defaults
- URL validation (http/https only)
- Events list validation
- `matches_event()` method with exact matches
- `matches_event()` method with prefix patterns
- `DeliveryRecord` instantiation
- Status enum values

**`tests/api/unit/test_webhook_registry.py`** (~15 tests)
- Add webhook
- Get webhook by ID
- Get non-existent webhook returns None
- Update webhook fields
- Delete webhook
- Delete non-existent webhook returns False
- List all webhooks
- List webhooks filtered by status
- Get matching webhooks by event type
- Clear all webhooks
- Thread safety with concurrent operations

**`tests/api/unit/test_webhook_dispatcher.py`** (~20 tests)
- Dispatch to matching webhooks
- Dispatch to no webhooks (none registered)
- Dispatch to no webhooks (none match event type)
- Compute HMAC signature
- Delivery success updates webhook stats
- Delivery failure increments failure count
- Auto-disable after max failures
- Retry with exponential backoff
- No retry after max attempts
- Test endpoint doesn't affect failure count
- Delivery history is recorded
- Delivery history is trimmed to max size

### Integration Tests (40+ tests)

**`tests/api/webhooks/test_webhook_registration.py`** (~12 tests)
- POST /webhooks creates webhook
- POST /webhooks with invalid URL returns 422
- POST /webhooks with empty events list returns 422
- POST /webhooks with events=null subscribes to all
- GET /webhooks/{id} returns webhook
- GET /webhooks/{id} with invalid ID returns 404
- PATCH /webhooks/{id} updates fields
- PATCH /webhooks/{id} with invalid ID returns 404
- DELETE /webhooks/{id} removes webhook
- DELETE /webhooks/{id} with invalid ID returns 404
- GET /webhooks lists all webhooks
- GET /webhooks with status filter

**`tests/api/webhooks/test_webhook_test_endpoint.py`** (~8 tests)
- POST /webhooks/{id}/test with reachable URL
- POST /webhooks/{id}/test with unreachable URL
- POST /webhooks/{id}/test includes signature
- POST /webhooks/{id}/test with invalid ID returns 404
- Response includes response_time_ms
- Test doesn't count as failure
- Test works on paused webhook

**`tests/api/webhooks/test_webhook_pause_resume.py`** (~6 tests)
- POST /webhooks/{id}/pause sets status to paused
- POST /webhooks/{id}/resume sets status to active
- Paused webhooks don't receive deliveries
- Resumed webhooks receive deliveries
- Pause/resume with invalid ID returns 404

**`tests/api/webhooks/test_webhook_delivery_integration.py`** (~15 tests)
- Email receive triggers webhook delivery
- SMS receive triggers webhook delivery
- Time advance triggers webhook delivery
- Webhook receives correct event type
- Webhook receives correct data payload
- Signature header is present when secret configured
- Signature is valid (can be verified)
- Multiple webhooks receive same event
- Webhook filtering works (only matching events delivered)
- Disabled webhook doesn't receive events
- Delivery is recorded in history
- GET /webhooks/{id}/deliveries returns records

### Client Library Tests (20+ tests)

**`tests/client/unit/test_webhooks.py`** (~12 tests)
- `webhooks.register()` calls correct endpoint
- `webhooks.get()` calls correct endpoint
- `webhooks.list()` calls correct endpoint with params
- `webhooks.update()` calls correct endpoint
- `webhooks.delete()` calls correct endpoint
- `webhooks.test()` calls correct endpoint
- `webhooks.pause()` calls correct endpoint
- `webhooks.resume()` calls correct endpoint
- `webhooks.get_deliveries()` calls correct endpoint

**`tests/client/integration/test_webhooks_integration.py`** (~8 tests)
- Full CRUD workflow
- Test webhook connectivity
- Pause and resume workflow
- Get delivery history

---

## Documentation Plan

### `docs/WEBHOOKS.md` Structure

```markdown
# Webhook API Documentation

## Overview
- What are webhooks
- When to use webhooks vs WebSockets

## Quick Start
- Register a webhook (curl example)
- Receive your first event

## API Reference
- POST /webhooks
- GET /webhooks
- GET /webhooks/{id}
- PATCH /webhooks/{id}
- DELETE /webhooks/{id}
- POST /webhooks/{id}/test
- GET /webhooks/{id}/deliveries
- POST /webhooks/{id}/pause
- POST /webhooks/{id}/resume

## Event Payload Format
- Standard structure
- Event types reference (link to WEBSOCKET.md)

## Security
- HMAC signature verification
- Python verification example
- Node.js verification example

## Python Client
- Using UESClient.webhooks
- Full example

## Building a Webhook Receiver
- Flask example
- FastAPI example

## Best Practices
- Respond quickly (return 200 immediately)
- Process asynchronously
- Handle retries idempotently
- Store delivery IDs to detect duplicates

## Troubleshooting
- Webhook not receiving events
- Signature verification failing
- Webhook auto-disabled
```

### Updates to Existing Docs

- `README.md`: Add webhooks to feature list
- `docs/API_CLIENT.md`: Add webhooks sub-client section
- `TODO.md`: Mark webhook task complete

---

## Checklist Summary

### Phase 1: Core Infrastructure
- [ ] Create `api/webhooks.py` with models
- [ ] Implement `WebhookRegistry`
- [ ] Implement `WebhookDispatcher`
- [ ] Write unit tests for models
- [ ] Write unit tests for registry
- [ ] Write unit tests for dispatcher

### Phase 2: API Routes
- [ ] Create `api/routes/webhooks.py`
- [ ] Implement all 9 endpoints
- [ ] Register router in `main.py`
- [ ] Write registration tests
- [ ] Write test endpoint tests
- [ ] Write pause/resume tests

### Phase 3: Broadcast Integration
- [ ] Create `api/broadcast.py` helper
- [ ] Update email routes
- [ ] Update sms routes
- [ ] Update chat routes
- [ ] Update calendar routes
- [ ] Update location routes
- [ ] Update weather routes
- [ ] Update time routes
- [ ] Update simulation routes
- [ ] Update events routes
- [ ] Add shutdown handler to `main.py`
- [ ] Write delivery integration tests

### Phase 4: Client Library
- [ ] Create `client/_webhooks.py`
- [ ] Implement sync sub-client
- [ ] Implement async sub-client
- [ ] Add to `UESClient` and `AsyncUESClient`
- [ ] Update `__init__.py` exports
- [ ] Write unit tests
- [ ] Write integration tests

### Phase 5: Documentation
- [ ] Create `docs/WEBHOOKS.md`
- [ ] Update `docs/API_CLIENT.md`
- [ ] Update `README.md`
- [ ] Update `TODO.md`

### Phase 6: Polish
- [ ] Add webhook stats to simulation status
- [ ] Handle webhook cleanup on clear
- [ ] Test concurrent deliveries
- [ ] Test edge cases

---

## Estimated Effort

| Phase | Effort |
|-------|--------|
| Phase 1: Core Infrastructure | 3-4 hours |
| Phase 2: API Routes | 2-3 hours |
| Phase 3: Broadcast Integration | 2-3 hours |
| Phase 4: Client Library | 2 hours |
| Phase 5: Documentation | 2 hours |
| Phase 6: Polish | 1-2 hours |
| **Total** | **12-16 hours** |

---

## Future Enhancements (Out of Scope)

- **Persistent storage**: Save webhooks to database
- **Scenario integration**: Include webhooks in scenario export/import
- **Rate limiting**: Per-webhook and global delivery rate limits
- **Dead letter queue**: Store undeliverable events for replay
- **Webhook templates**: Pre-configured webhook patterns for common agents
- **Web UI**: Webhook management in the React app
