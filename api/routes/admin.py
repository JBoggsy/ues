"""Admin endpoints for API key management.

These endpoints allow management of API keys for access control.
They are only available when UES_ACCESS_CONTROL is enabled and
require proctor-level access (or the bootstrap key for initial setup).
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from api.access_control import (
    AccessContext,
    AccessLevel,
    key_registry,
)
from api.access_dependencies import ProctorDep

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)


# =============================================================================
# Request/Response Models
# =============================================================================


class CreateKeyRequest(BaseModel):
    """Request model for creating a new API key.
    
    Attributes:
        level: Access level for the key (proctor or user).
        agent_id: Optional identifier for the agent.
        assessment_id: Optional assessment identifier for scoping.
        metadata: Optional additional metadata.
    """
    level: AccessLevel = Field(description="Access level for the key")
    agent_id: str | None = Field(default=None, description="Agent identifier")
    assessment_id: str | None = Field(default=None, description="Assessment identifier")
    metadata: dict[str, Any] | None = Field(default=None, description="Additional metadata")


class KeyResponse(BaseModel):
    """Response model for a created or retrieved key.
    
    Attributes:
        api_key: The API key string.
        level: Access level of the key.
        agent_id: Agent identifier if set.
        assessment_id: Assessment identifier if set.
        created_at: When the key was created.
        metadata: Additional metadata if set.
    """
    api_key: str = Field(description="The API key")
    level: AccessLevel = Field(description="Access level")
    agent_id: str | None = Field(default=None, description="Agent identifier")
    assessment_id: str | None = Field(default=None, description="Assessment identifier")
    created_at: datetime = Field(description="Creation timestamp")
    metadata: dict[str, Any] | None = Field(default=None, description="Additional metadata")
    
    @classmethod
    def from_context(cls, context: AccessContext) -> "KeyResponse":
        """Create a KeyResponse from an AccessContext."""
        return cls(
            api_key=context.api_key,
            level=context.level,
            agent_id=context.agent_id,
            assessment_id=context.assessment_id,
            created_at=context.created_at,
            metadata=context.metadata,
        )


class KeyListResponse(BaseModel):
    """Response model for listing keys.
    
    Attributes:
        keys: List of key responses.
        total: Total number of keys.
    """
    keys: list[KeyResponse] = Field(description="List of keys")
    total: int = Field(description="Total number of keys")


class InvalidateKeyResponse(BaseModel):
    """Response model for key invalidation.
    
    Attributes:
        success: Whether the key was found and invalidated.
        message: Description of what happened.
    """
    success: bool = Field(description="Whether invalidation succeeded")
    message: str = Field(description="Result message")


class CleanupResponse(BaseModel):
    """Response model for bulk key cleanup.
    
    Attributes:
        invalidated_count: Number of keys that were invalidated.
        assessment_id: The assessment that was cleaned up.
    """
    invalidated_count: int = Field(description="Number of keys invalidated")
    assessment_id: str = Field(description="Assessment that was cleaned up")


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/keys", response_model=KeyResponse)
async def create_key(
    request: CreateKeyRequest,
    access: ProctorDep,  # Requires proctor-level access
) -> KeyResponse:
    """Create a new API key.
    
    Requires proctor-level access. Creates a new key with the specified
    access level and optional metadata.
    
    Args:
        request: Key creation parameters.
        access: Access context of the requesting user (must be proctor).
    
    Returns:
        The created key details including the key string.
    """
    key = key_registry.generate_key(
        level=request.level,
        agent_id=request.agent_id,
        assessment_id=request.assessment_id,
        metadata=request.metadata,
    )
    
    context = key_registry.get_context(key)
    if context is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create key",
        )
    
    return KeyResponse.from_context(context)


@router.get("/keys", response_model=KeyListResponse)
async def list_keys(
    assessment_id: str | None = None,
    access: ProctorDep = None,  # Requires proctor-level access
) -> KeyListResponse:
    """List all API keys, optionally filtered by assessment.
    
    Requires proctor-level access. Returns all keys or keys for a
    specific assessment.
    
    Args:
        assessment_id: Optional filter by assessment ID.
        access: Access context of the requesting user (must be proctor).
    
    Returns:
        List of keys with their metadata.
    """
    contexts = key_registry.list_keys(assessment_id=assessment_id)
    
    return KeyListResponse(
        keys=[KeyResponse.from_context(ctx) for ctx in contexts],
        total=len(contexts),
    )


@router.delete("/keys/{api_key:path}", response_model=InvalidateKeyResponse)
async def invalidate_key(
    api_key: str,
    access: ProctorDep,  # Requires proctor-level access
) -> InvalidateKeyResponse:
    """Invalidate a single API key.
    
    Requires proctor-level access. The key will no longer be valid
    for authentication.
    
    Args:
        api_key: The key to invalidate.
        access: Access context of the requesting user (must be proctor).
    
    Returns:
        Result of the invalidation attempt.
    """
    success = key_registry.invalidate_key(api_key)
    
    if success:
        return InvalidateKeyResponse(
            success=True,
            message=f"Key invalidated successfully",
        )
    else:
        return InvalidateKeyResponse(
            success=False,
            message="Key not found",
        )


@router.post("/keys/cleanup/{assessment_id}", response_model=CleanupResponse)
async def cleanup_assessment_keys(
    assessment_id: str,
    access: ProctorDep,  # Requires proctor-level access
) -> CleanupResponse:
    """Invalidate all keys for a specific assessment.
    
    Requires proctor-level access. This is typically called when an
    assessment completes to clean up all issued keys.
    
    Args:
        assessment_id: The assessment to clean up.
        access: Access context of the requesting user (must be proctor).
    
    Returns:
        Number of keys that were invalidated.
    """
    count = key_registry.invalidate_keys_by_assessment(assessment_id)
    
    return CleanupResponse(
        invalidated_count=count,
        assessment_id=assessment_id,
    )
