"""Admin sub-client for the UES API.

This module provides AdminClient and AsyncAdminClient for interacting
with the admin endpoints (/admin/*) for API key management.

These endpoints are only available when UES_ACCESS_CONTROL is enabled
and require proctor-level access.

This is an internal module. Import from `client` instead.

Example:
    Synchronous usage::
    
        from client import UESClient
        
        # Use proctor API key
        client = UESClient(api_key="ues_proctor_...")
        
        # Create a user key for an agent
        user_key = client.admin.create_key(
            level="user",
            agent_id="email-bot",
            assessment_id="assessment-123",
        )
        print(f"Created key: {user_key.api_key}")
        
        # List all keys
        keys = client.admin.list_keys()
        print(f"Total keys: {keys.total}")
        
        # Cleanup after assessment
        result = client.admin.cleanup_assessment("assessment-123")
        print(f"Invalidated {result.invalidated_count} keys")
    
    Asynchronous usage::
    
        from client import AsyncUESClient
        
        async with AsyncUESClient(api_key="ues_proctor_...") as client:
            user_key = await client.admin.create_key(level="user")
            print(f"Created: {user_key.api_key}")
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from client._base import AsyncBaseClient, BaseClient

if TYPE_CHECKING:
    from client._http import AsyncHTTPClient, HTTPClient


# Enums


class AccessLevel(str, Enum):
    """Access level for API keys.
    
    Attributes:
        PROCTOR: Full API access (assessment orchestrator).
        USER: Restricted to user-side actions (agent being tested).
    """
    
    PROCTOR = "proctor"
    USER = "user"


# Response models


class KeyResponse(BaseModel):
    """Response model for a created or retrieved API key.
    
    Attributes:
        api_key: The API key string.
        level: Access level of the key.
        agent_id: Agent identifier if set.
        assessment_id: Assessment identifier if set.
        created_at: When the key was created.
        metadata: Additional metadata if set.
    """
    
    api_key: str
    level: AccessLevel
    agent_id: str | None = None
    assessment_id: str | None = None
    created_at: datetime
    metadata: dict[str, Any] | None = None


class KeyListResponse(BaseModel):
    """Response model for listing API keys.
    
    Attributes:
        keys: List of key responses.
        total: Total number of keys.
    """
    
    keys: list[KeyResponse]
    total: int


class InvalidateKeyResponse(BaseModel):
    """Response model for key invalidation.
    
    Attributes:
        success: Whether the key was found and invalidated.
        message: Description of what happened.
    """
    
    success: bool
    message: str


class CleanupResponse(BaseModel):
    """Response model for bulk key cleanup.
    
    Attributes:
        invalidated_count: Number of keys that were invalidated.
        assessment_id: The assessment that was cleaned up.
    """
    
    invalidated_count: int
    assessment_id: str


# Synchronous AdminClient


class AdminClient(BaseClient):
    """Synchronous client for admin endpoints (/admin/*).
    
    Provides methods for API key management. These endpoints require
    proctor-level access and are only available when UES_ACCESS_CONTROL
    is enabled.
    
    Example:
        with UESClient(api_key="ues_proctor_...") as client:
            # Create a user-level key
            key = client.admin.create_key(
                level="user",
                agent_id="my-agent",
                assessment_id="test-001",
                metadata={"description": "Test agent key"},
            )
            print(f"Created: {key.api_key}")
            
            # List all keys for an assessment
            keys = client.admin.list_keys(assessment_id="test-001")
            for k in keys.keys:
                print(f"- {k.api_key}: {k.level}")
            
            # Invalidate a specific key
            result = client.admin.invalidate_key(key.api_key)
            print(f"Invalidated: {result.success}")
            
            # Cleanup all keys for an assessment
            cleanup = client.admin.cleanup_assessment("test-001")
            print(f"Cleaned up {cleanup.invalidated_count} keys")
    """
    
    _BASE_PATH = "/admin"
    
    def create_key(
        self,
        level: AccessLevel | str,
        agent_id: str | None = None,
        assessment_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> KeyResponse:
        """Create a new API key.
        
        Creates an API key with the specified access level and optional
        metadata. Requires proctor-level access.
        
        Args:
            level: Access level for the key ("proctor" or "user").
            agent_id: Optional identifier for the agent using this key.
            assessment_id: Optional assessment identifier for scoping.
            metadata: Optional additional metadata to store with the key.
        
        Returns:
            The created key details including the key string.
        
        Raises:
            APIError: If not authenticated or not a proctor.
            ValidationError: If the request parameters are invalid.
        
        Example:
            key = client.admin.create_key(
                level="user",
                agent_id="email-processor",
                assessment_id="assessment-123",
                metadata={"description": "Email processing agent"},
            )
            print(f"Use this key: {key.api_key}")
        """
        # Convert string to enum if needed
        if isinstance(level, str):
            level = AccessLevel(level)
        
        request_data: dict[str, Any] = {"level": level.value}
        if agent_id is not None:
            request_data["agent_id"] = agent_id
        if assessment_id is not None:
            request_data["assessment_id"] = assessment_id
        if metadata is not None:
            request_data["metadata"] = metadata
        
        data = self._post(f"{self._BASE_PATH}/keys", json=request_data)
        return KeyResponse(**data)
    
    def list_keys(
        self,
        level: AccessLevel | str | None = None,
        assessment_id: str | None = None,
    ) -> KeyListResponse:
        """List all API keys.
        
        Returns all registered API keys, optionally filtered by access
        level or assessment ID. Requires proctor-level access.
        
        Args:
            level: Filter by access level ("proctor" or "user").
            assessment_id: Filter by assessment identifier.
        
        Returns:
            List of keys with total count.
        
        Raises:
            APIError: If not authenticated or not a proctor.
        
        Example:
            # List all keys
            all_keys = client.admin.list_keys()
            print(f"Total: {all_keys.total}")
            
            # List only user keys for an assessment
            user_keys = client.admin.list_keys(
                level="user",
                assessment_id="assessment-123",
            )
        """
        params: dict[str, Any] = {}
        if level is not None:
            if isinstance(level, str):
                level = AccessLevel(level)
            params["level"] = level.value
        if assessment_id is not None:
            params["assessment_id"] = assessment_id
        
        data = self._get(f"{self._BASE_PATH}/keys", params=params if params else None)
        return KeyListResponse(**data)
    
    def invalidate_key(self, api_key: str) -> InvalidateKeyResponse:
        """Invalidate (revoke) an API key.
        
        Permanently invalidates the specified API key. After invalidation,
        any requests using this key will receive 401 Unauthorized.
        
        Args:
            api_key: The API key to invalidate.
        
        Returns:
            Confirmation of invalidation with success status.
        
        Raises:
            NotFoundError: If the key doesn't exist.
            APIError: If not authenticated or not a proctor.
        
        Example:
            result = client.admin.invalidate_key("ues_user_abc123...")
            if result.success:
                print("Key revoked successfully")
        """
        data = self._delete(f"{self._BASE_PATH}/keys/{api_key}")
        return InvalidateKeyResponse(**data)
    
    def cleanup_assessment(self, assessment_id: str) -> CleanupResponse:
        """Invalidate all keys for an assessment.
        
        Bulk cleanup operation that invalidates all API keys associated
        with a specific assessment. Useful for cleanup after an assessment
        is complete.
        
        Args:
            assessment_id: The assessment identifier to clean up.
        
        Returns:
            Cleanup results with count of invalidated keys.
        
        Raises:
            APIError: If not authenticated or not a proctor.
        
        Example:
            result = client.admin.cleanup_assessment("assessment-123")
            print(f"Cleaned up {result.invalidated_count} keys")
        """
        data = self._post(f"{self._BASE_PATH}/keys/cleanup/{assessment_id}")
        return CleanupResponse(**data)


# Asynchronous AsyncAdminClient


class AsyncAdminClient(AsyncBaseClient):
    """Asynchronous client for admin endpoints (/admin/*).
    
    Provides async methods for API key management. These endpoints require
    proctor-level access and are only available when UES_ACCESS_CONTROL
    is enabled.
    
    Example:
        async with AsyncUESClient(api_key="ues_proctor_...") as client:
            # Create a user-level key
            key = await client.admin.create_key(
                level="user",
                agent_id="my-agent",
            )
            print(f"Created: {key.api_key}")
            
            # List all keys
            keys = await client.admin.list_keys()
            print(f"Total: {keys.total}")
    """
    
    _BASE_PATH = "/admin"
    
    async def create_key(
        self,
        level: AccessLevel | str,
        agent_id: str | None = None,
        assessment_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> KeyResponse:
        """Create a new API key.
        
        Creates an API key with the specified access level and optional
        metadata. Requires proctor-level access.
        
        Args:
            level: Access level for the key ("proctor" or "user").
            agent_id: Optional identifier for the agent using this key.
            assessment_id: Optional assessment identifier for scoping.
            metadata: Optional additional metadata to store with the key.
        
        Returns:
            The created key details including the key string.
        
        Raises:
            APIError: If not authenticated or not a proctor.
            ValidationError: If the request parameters are invalid.
        """
        if isinstance(level, str):
            level = AccessLevel(level)
        
        request_data: dict[str, Any] = {"level": level.value}
        if agent_id is not None:
            request_data["agent_id"] = agent_id
        if assessment_id is not None:
            request_data["assessment_id"] = assessment_id
        if metadata is not None:
            request_data["metadata"] = metadata
        
        data = await self._post(f"{self._BASE_PATH}/keys", json=request_data)
        return KeyResponse(**data)
    
    async def list_keys(
        self,
        level: AccessLevel | str | None = None,
        assessment_id: str | None = None,
    ) -> KeyListResponse:
        """List all API keys.
        
        Returns all registered API keys, optionally filtered by access
        level or assessment ID. Requires proctor-level access.
        
        Args:
            level: Filter by access level ("proctor" or "user").
            assessment_id: Filter by assessment identifier.
        
        Returns:
            List of keys with total count.
        
        Raises:
            APIError: If not authenticated or not a proctor.
        """
        params: dict[str, Any] = {}
        if level is not None:
            if isinstance(level, str):
                level = AccessLevel(level)
            params["level"] = level.value
        if assessment_id is not None:
            params["assessment_id"] = assessment_id
        
        data = await self._get(f"{self._BASE_PATH}/keys", params=params if params else None)
        return KeyListResponse(**data)
    
    async def invalidate_key(self, api_key: str) -> InvalidateKeyResponse:
        """Invalidate (revoke) an API key.
        
        Permanently invalidates the specified API key. After invalidation,
        any requests using this key will receive 401 Unauthorized.
        
        Args:
            api_key: The API key to invalidate.
        
        Returns:
            Confirmation of invalidation with success status.
        
        Raises:
            NotFoundError: If the key doesn't exist.
            APIError: If not authenticated or not a proctor.
        """
        data = await self._delete(f"{self._BASE_PATH}/keys/{api_key}")
        return InvalidateKeyResponse(**data)
    
    async def cleanup_assessment(self, assessment_id: str) -> CleanupResponse:
        """Invalidate all keys for an assessment.
        
        Bulk cleanup operation that invalidates all API keys associated
        with a specific assessment. Useful for cleanup after an assessment
        is complete.
        
        Args:
            assessment_id: The assessment identifier to clean up.
        
        Returns:
            Cleanup results with count of invalidated keys.
        
        Raises:
            APIError: If not authenticated or not a proctor.
        """
        data = await self._post(f"{self._BASE_PATH}/keys/cleanup/{assessment_id}")
        return CleanupResponse(**data)
