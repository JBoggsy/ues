"""Webhook management client for UES API.

Provides methods for registering, managing, and testing webhooks.

Example:
    Synchronous usage::
    
        from ues.client import UESClient
        
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
    
    Asynchronous usage::
    
        from ues.client import AsyncUESClient
        
        async with AsyncUESClient() as client:
            webhook = await client.webhooks.register(
                url="https://my-agent.example.com/callback",
                events=["email."]
            )
            print(f"Created: {webhook['id']}")
"""

from __future__ import annotations

from typing import Any, Optional

from ues.client._base import AsyncBaseClient, BaseClient


class WebhooksClient(BaseClient):
    """Sub-client for webhook management operations (synchronous).
    
    Provides methods to register, update, delete, test, and query webhooks.
    """
    
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
            events: Event patterns to receive (None = all events).
                    Use prefix patterns like "email." to match all email events.
            secret: HMAC secret for signature verification. When provided,
                   the X-UES-Signature header will be included in deliveries.
            metadata: Custom metadata to store with the webhook.
        
        Returns:
            The created webhook registration including its ID.
        
        Raises:
            ValidationError: If the request data is invalid.
            UESClientError: If registration fails.
        
        Example:
            >>> webhook = client.webhooks.register(
            ...     url="https://example.com/callback",
            ...     events=["email.received", "sms."],
            ...     secret="my-secret-key",
            ...     metadata={"agent_name": "EmailBot"}
            ... )
            >>> print(webhook["id"])
            wh_abc123def456
        """
        payload: dict[str, Any] = {"url": url}
        if events is not None:
            payload["events"] = events
        if secret is not None:
            payload["secret"] = secret
        if metadata is not None:
            payload["metadata"] = metadata
        
        return self._post("/webhooks", json=payload)
    
    def get(self, webhook_id: str) -> dict[str, Any]:
        """Get a webhook by ID.
        
        Args:
            webhook_id: The webhook's unique identifier.
        
        Returns:
            The webhook registration details.
        
        Raises:
            NotFoundError: If the webhook doesn't exist.
        """
        return self._get(f"/webhooks/{webhook_id}")
    
    def list(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List registered webhooks.
        
        Args:
            status: Filter by status ("active", "paused", "disabled").
            limit: Maximum number of results (default 50, max 200).
            offset: Pagination offset.
        
        Returns:
            Dictionary with "items", "total", "limit", and "offset" keys.
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
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
        """Update a webhook configuration.
        
        Only provided fields are updated. All fields are optional.
        
        Args:
            webhook_id: The webhook's unique identifier.
            url: New callback URL.
            events: New event patterns (empty list = receive all events).
            secret: New HMAC secret.
            metadata: New metadata (replaces existing).
            status: New status ("active", "paused").
        
        Returns:
            The updated webhook registration.
        
        Raises:
            NotFoundError: If the webhook doesn't exist.
        """
        payload: dict[str, Any] = {}
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
        """Delete a webhook registration.
        
        Removes the webhook and stops all future deliveries.
        
        Args:
            webhook_id: The webhook's unique identifier.
        
        Raises:
            NotFoundError: If the webhook doesn't exist.
        """
        self._delete(f"/webhooks/{webhook_id}")
    
    def test(self, webhook_id: str) -> dict[str, Any]:
        """Send a test event to a webhook.
        
        Sends a synthetic "webhook.test" event to verify connectivity.
        The test does NOT count against the webhook's failure count.
        
        Args:
            webhook_id: The webhook to test.
        
        Returns:
            Test result including success status, response code, and timing.
        
        Raises:
            NotFoundError: If the webhook doesn't exist.
        
        Example:
            >>> result = client.webhooks.test("wh_abc123")
            >>> if result["success"]:
            ...     print(f"Webhook OK, {result['response_time_ms']:.1f}ms")
            ... else:
            ...     print(f"Webhook failed: {result['error_message']}")
        """
        return self._post(f"/webhooks/{webhook_id}/test")
    
    def pause(self, webhook_id: str) -> dict[str, Any]:
        """Pause a webhook (stop receiving events).
        
        A paused webhook will not receive any event deliveries until resumed.
        
        Args:
            webhook_id: The webhook to pause.
        
        Returns:
            The updated webhook with status "paused".
        
        Raises:
            NotFoundError: If the webhook doesn't exist.
        """
        return self._post(f"/webhooks/{webhook_id}/pause")
    
    def resume(self, webhook_id: str) -> dict[str, Any]:
        """Resume a paused webhook.
        
        Resumes event deliveries and resets the failure count.
        
        Args:
            webhook_id: The webhook to resume.
        
        Returns:
            The updated webhook with status "active".
        
        Raises:
            NotFoundError: If the webhook doesn't exist.
        """
        return self._post(f"/webhooks/{webhook_id}/resume")
    
    def get_deliveries(
        self,
        webhook_id: str,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Get delivery history for a webhook.
        
        Returns recent delivery attempts, both successful and failed.
        Results are ordered by most recent first.
        
        Args:
            webhook_id: The webhook's unique identifier.
            limit: Maximum number of records (default 50, max 200).
        
        Returns:
            Dictionary with "items" and "total" keys.
        
        Raises:
            NotFoundError: If the webhook doesn't exist.
        """
        return self._get(f"/webhooks/{webhook_id}/deliveries", params={"limit": limit})


class AsyncWebhooksClient(AsyncBaseClient):
    """Sub-client for webhook management operations (asynchronous).
    
    Provides async methods to register, update, delete, test, and query webhooks.
    """
    
    async def register(
        self,
        url: str,
        events: Optional[list[str]] = None,
        secret: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Register a new webhook.
        
        Args:
            url: Callback URL to POST events to.
            events: Event patterns to receive (None = all events).
                    Use prefix patterns like "email." to match all email events.
            secret: HMAC secret for signature verification. When provided,
                   the X-UES-Signature header will be included in deliveries.
            metadata: Custom metadata to store with the webhook.
        
        Returns:
            The created webhook registration including its ID.
        
        Raises:
            ValidationError: If the request data is invalid.
            UESClientError: If registration fails.
        """
        payload: dict[str, Any] = {"url": url}
        if events is not None:
            payload["events"] = events
        if secret is not None:
            payload["secret"] = secret
        if metadata is not None:
            payload["metadata"] = metadata
        
        return await self._post("/webhooks", json=payload)
    
    async def get(self, webhook_id: str) -> dict[str, Any]:
        """Get a webhook by ID.
        
        Args:
            webhook_id: The webhook's unique identifier.
        
        Returns:
            The webhook registration details.
        
        Raises:
            NotFoundError: If the webhook doesn't exist.
        """
        return await self._get(f"/webhooks/{webhook_id}")
    
    async def list(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List registered webhooks.
        
        Args:
            status: Filter by status ("active", "paused", "disabled").
            limit: Maximum number of results (default 50, max 200).
            offset: Pagination offset.
        
        Returns:
            Dictionary with "items", "total", "limit", and "offset" keys.
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        return await self._get("/webhooks", params=params)
    
    async def update(
        self,
        webhook_id: str,
        url: Optional[str] = None,
        events: Optional[list[str]] = None,
        secret: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        status: Optional[str] = None,
    ) -> dict[str, Any]:
        """Update a webhook configuration.
        
        Only provided fields are updated. All fields are optional.
        
        Args:
            webhook_id: The webhook's unique identifier.
            url: New callback URL.
            events: New event patterns (empty list = receive all events).
            secret: New HMAC secret.
            metadata: New metadata (replaces existing).
            status: New status ("active", "paused").
        
        Returns:
            The updated webhook registration.
        
        Raises:
            NotFoundError: If the webhook doesn't exist.
        """
        payload: dict[str, Any] = {}
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
        
        return await self._patch(f"/webhooks/{webhook_id}", json=payload)
    
    async def delete(self, webhook_id: str) -> None:
        """Delete a webhook registration.
        
        Removes the webhook and stops all future deliveries.
        
        Args:
            webhook_id: The webhook's unique identifier.
        
        Raises:
            NotFoundError: If the webhook doesn't exist.
        """
        await self._delete(f"/webhooks/{webhook_id}")
    
    async def test(self, webhook_id: str) -> dict[str, Any]:
        """Send a test event to a webhook.
        
        Sends a synthetic "webhook.test" event to verify connectivity.
        The test does NOT count against the webhook's failure count.
        
        Args:
            webhook_id: The webhook to test.
        
        Returns:
            Test result including success status, response code, and timing.
        
        Raises:
            NotFoundError: If the webhook doesn't exist.
        """
        return await self._post(f"/webhooks/{webhook_id}/test")
    
    async def pause(self, webhook_id: str) -> dict[str, Any]:
        """Pause a webhook (stop receiving events).
        
        A paused webhook will not receive any event deliveries until resumed.
        
        Args:
            webhook_id: The webhook to pause.
        
        Returns:
            The updated webhook with status "paused".
        
        Raises:
            NotFoundError: If the webhook doesn't exist.
        """
        return await self._post(f"/webhooks/{webhook_id}/pause")
    
    async def resume(self, webhook_id: str) -> dict[str, Any]:
        """Resume a paused webhook.
        
        Resumes event deliveries and resets the failure count.
        
        Args:
            webhook_id: The webhook to resume.
        
        Returns:
            The updated webhook with status "active".
        
        Raises:
            NotFoundError: If the webhook doesn't exist.
        """
        return await self._post(f"/webhooks/{webhook_id}/resume")
    
    async def get_deliveries(
        self,
        webhook_id: str,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Get delivery history for a webhook.
        
        Returns recent delivery attempts, both successful and failed.
        Results are ordered by most recent first.
        
        Args:
            webhook_id: The webhook's unique identifier.
            limit: Maximum number of records (default 50, max 200).
        
        Returns:
            Dictionary with "items" and "total" keys.
        
        Raises:
            NotFoundError: If the webhook doesn't exist.
        """
        return await self._get(
            f"/webhooks/{webhook_id}/deliveries", params={"limit": limit}
        )
