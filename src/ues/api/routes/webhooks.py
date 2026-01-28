"""Webhook management REST API endpoints.

Provides endpoints for registering, managing, and testing webhooks.
Webhooks receive HTTP POST callbacks when simulation events occur.

All endpoints require authentication via X-API-Key header.

Example usage:
    # Register a webhook via curl:
    curl -X POST http://localhost:8000/webhooks \\
        -H "Content-Type: application/json" \\
        -H "X-API-Key: your_api_key" \\
        -d '{"url": "https://my-agent.example.com/callback", "events": ["email."]}'
    
    # Test a webhook:
    curl -X POST http://localhost:8000/webhooks/wh_abc123def456/test \\
        -H "X-API-Key: your_api_key"
    
    # List all webhooks:
    curl http://localhost:8000/webhooks -H "X-API-Key: your_api_key"
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ues.api.auth import Permissions, require_permission
from ues.api.webhooks import (
    CreateWebhookRequest,
    DeliveryListResponse,
    DeliveryStatus,
    UpdateWebhookRequest,
    WebhookListResponse,
    WebhookRegistration,
    WebhookResponse,
    WebhookStatus,
    WebhookTestResponse,
    webhook_dispatcher,
    webhook_registry,
)
from ues.models.api_key import APIKey

router = APIRouter(
    prefix="/webhooks",
    tags=["webhooks"],
)


def _webhook_to_response(webhook: WebhookRegistration) -> WebhookResponse:
    """Convert a WebhookRegistration to a WebhookResponse.
    
    Args:
        webhook: The internal webhook registration.
    
    Returns:
        A WebhookResponse suitable for API responses.
    """
    return WebhookResponse(
        id=webhook.id,
        url=webhook.url,
        events=webhook.events,
        status=webhook.status,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at,
        metadata=webhook.metadata,
        failure_count=webhook.failure_count,
        last_delivery_at=webhook.last_delivery_at,
        last_failure_at=webhook.last_failure_at,
        has_secret=webhook.secret is not None,
    )


@router.post("", response_model=WebhookResponse, status_code=201)
async def create_webhook(
    request: CreateWebhookRequest,
    _: Annotated[APIKey, Depends(require_permission(Permissions.WEBHOOKS_CREATE))],
) -> WebhookResponse:
    """Register a new webhook callback URL.
    
    The webhook will receive POST requests when matching events occur.
    Events are filtered by the `events` array - use dot-prefix patterns
    (e.g., "email.") to subscribe to all events in a category.
    
    Args:
        request: The webhook registration request.
    
    Returns:
        The created webhook registration with its ID.
    
    Requires:
        Permission: webhooks:create
    
    Example:
        Request::
        
            POST /webhooks
            {
                "url": "https://my-agent.example.com/ues-callback",
                "events": ["email.received", "sms."],
                "secret": "my-secret-key",
                "metadata": {"agent_name": "Email Bot"}
            }
        
        Response (201)::
        
            {
                "id": "wh_abc123def456",
                "url": "https://my-agent.example.com/ues-callback",
                "events": ["email.received", "sms."],
                "status": "active",
                "created_at": "2026-01-08T10:30:00Z",
                "has_secret": true,
                ...
            }
    """
    webhook = WebhookRegistration(
        url=request.url,
        events=request.events,
        secret=request.secret,
        metadata=request.metadata,
    )
    await webhook_registry.add(webhook)
    return _webhook_to_response(webhook)


@router.get("", response_model=WebhookListResponse)
async def list_webhooks(
    _: Annotated[APIKey, Depends(require_permission(Permissions.WEBHOOKS_LIST))],
    status: Optional[WebhookStatus] = Query(
        default=None, description="Filter by webhook status"
    ),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum results"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
) -> WebhookListResponse:
    """List all registered webhooks.
    
    Args:
        status: Optional filter by webhook status (active, paused, disabled).
        limit: Maximum number of results to return (default 50, max 200).
        offset: Pagination offset for large result sets.
    
    Returns:
        List of webhook registrations.
    
    Requires:
        Permission: webhooks:list
    """
    webhooks, total = await webhook_registry.list_all(
        status=status, limit=limit, offset=offset
    )
    return WebhookListResponse(
        items=[_webhook_to_response(w) for w in webhooks],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: str,
    _: Annotated[APIKey, Depends(require_permission(Permissions.WEBHOOKS_READ))],
) -> WebhookResponse:
    """Get details of a specific webhook.
    
    Args:
        webhook_id: The webhook's unique identifier.
    
    Returns:
        The webhook registration details.
    
    Raises:
        HTTPException: 404 if webhook not found.
    
    Requires:
        Permission: webhooks:read
    """
    webhook = await webhook_registry.get(webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail=f"Webhook {webhook_id} not found")
    return _webhook_to_response(webhook)


@router.patch("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: str,
    request: UpdateWebhookRequest,
    _: Annotated[APIKey, Depends(require_permission(Permissions.WEBHOOKS_UPDATE))],
) -> WebhookResponse:
    """Update a webhook's configuration.
    
    Only provided fields are updated. All fields are optional.
    
    Args:
        webhook_id: The webhook's unique identifier.
        request: The fields to update.
    
    Returns:
        The updated webhook registration.
    
    Raises:
        HTTPException: 404 if webhook not found.
    
    Requires:
        Permission: webhooks:update
    """
    webhook = await webhook_registry.get(webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail=f"Webhook {webhook_id} not found")
    
    # Build updates dict from non-None fields
    updates = {}
    if request.url is not None:
        updates["url"] = request.url
    if request.events is not None:
        # Allow empty list to mean "receive all events"
        updates["events"] = request.events if request.events else None
    if request.secret is not None:
        updates["secret"] = request.secret
    if request.metadata is not None:
        updates["metadata"] = request.metadata
    if request.status is not None:
        updates["status"] = request.status
    
    if updates:
        webhook = await webhook_registry.update(webhook_id, updates)
    
    return _webhook_to_response(webhook)  # type: ignore


@router.delete("/{webhook_id}", status_code=204)
async def delete_webhook(
    webhook_id: str,
    _: Annotated[APIKey, Depends(require_permission(Permissions.WEBHOOKS_DELETE))],
) -> None:
    """Unregister a webhook.
    
    Removes the webhook registration and stops all future deliveries.
    
    Args:
        webhook_id: The webhook's unique identifier.
    
    Raises:
        HTTPException: 404 if webhook not found.
    
    Requires:
        Permission: webhooks:delete
    """
    deleted = await webhook_registry.delete(webhook_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Webhook {webhook_id} not found")
    
    # Also clean up delivery history
    webhook_dispatcher.clear_history(webhook_id)


@router.post("/{webhook_id}/test", response_model=WebhookTestResponse)
async def test_webhook(
    webhook_id: str,
    _: Annotated[APIKey, Depends(require_permission(Permissions.WEBHOOKS_TEST))],
) -> WebhookTestResponse:
    """Send a test event to verify webhook connectivity.
    
    Sends a synthetic "webhook.test" event to the registered URL
    and reports the delivery result. This is useful for verifying
    that the callback URL is accessible and responding correctly.
    
    The test does NOT count against the webhook's failure count.
    
    Args:
        webhook_id: The webhook to test.
    
    Returns:
        Test result including HTTP status and response time.
    
    Raises:
        HTTPException: 404 if webhook not found.
    
    Requires:
        Permission: webhooks:test
    """
    webhook = await webhook_registry.get(webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail=f"Webhook {webhook_id} not found")
    
    record = await webhook_dispatcher.test_webhook(webhook)
    
    return WebhookTestResponse(
        webhook_id=webhook_id,
        success=record.status == DeliveryStatus.DELIVERED,
        response_status=record.response_status,
        response_time_ms=getattr(record, "_elapsed_ms", None),
        response_body=record.response_body,
        error_message=record.error_message,
    )


@router.get("/{webhook_id}/deliveries", response_model=DeliveryListResponse)
async def get_webhook_deliveries(
    webhook_id: str,
    _: Annotated[APIKey, Depends(require_permission(Permissions.WEBHOOKS_DELIVERIES))],
    limit: int = Query(default=50, ge=1, le=200, description="Maximum results"),
) -> DeliveryListResponse:
    """Get delivery history for a webhook.
    
    Returns recent delivery attempts, including both successful and
    failed deliveries. Results are ordered by most recent first.
    
    Args:
        webhook_id: The webhook's unique identifier.
        limit: Maximum number of records to return (default 50).
    
    Returns:
        List of delivery records for this webhook.
    
    Raises:
        HTTPException: 404 if webhook not found.
    
    Requires:
        Permission: webhooks:deliveries
    """
    webhook = await webhook_registry.get(webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail=f"Webhook {webhook_id} not found")
    
    deliveries = webhook_dispatcher.get_delivery_history(webhook_id, limit=limit)
    return DeliveryListResponse(
        items=deliveries,
        total=len(deliveries),
    )


@router.post("/{webhook_id}/pause", response_model=WebhookResponse)
async def pause_webhook(
    webhook_id: str,
    _: Annotated[APIKey, Depends(require_permission(Permissions.WEBHOOKS_PAUSE))],
) -> WebhookResponse:
    """Pause a webhook (stop receiving events).
    
    A paused webhook will not receive any event deliveries until resumed.
    This is useful for temporary maintenance of the receiving endpoint.
    
    Args:
        webhook_id: The webhook to pause.
    
    Returns:
        The updated webhook with status "paused".
    
    Raises:
        HTTPException: 404 if webhook not found.
    
    Requires:
        Permission: webhooks:pause
    """
    webhook = await webhook_registry.get(webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail=f"Webhook {webhook_id} not found")
    
    webhook = await webhook_registry.update(webhook_id, {"status": WebhookStatus.PAUSED})
    return _webhook_to_response(webhook)  # type: ignore


@router.post("/{webhook_id}/resume", response_model=WebhookResponse)
async def resume_webhook(
    webhook_id: str,
    _: Annotated[APIKey, Depends(require_permission(Permissions.WEBHOOKS_RESUME))],
) -> WebhookResponse:
    """Resume a paused webhook.
    
    Resumes event deliveries to a previously paused webhook.
    Also resets the failure count, allowing a disabled webhook
    to be re-enabled.
    
    Args:
        webhook_id: The webhook to resume.
    
    Returns:
        The updated webhook with status "active".
    
    Raises:
        HTTPException: 404 if webhook not found.
    
    Requires:
        Permission: webhooks:resume
    """
    webhook = await webhook_registry.get(webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail=f"Webhook {webhook_id} not found")
    
    # Reset failure count when resuming to give disabled webhooks a fresh start
    webhook = await webhook_registry.update(
        webhook_id, {"status": WebhookStatus.ACTIVE, "failure_count": 0}
    )
    return _webhook_to_response(webhook)  # type: ignore
