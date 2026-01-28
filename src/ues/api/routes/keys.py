"""API Key management endpoints.

Provides REST API endpoints for creating, listing, retrieving, and revoking
API keys. These endpoints require authentication and appropriate permissions.

All endpoints are protected by API key authentication. The admin key created
at server startup has full access to all key management operations.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ues.api.auth import (
    Permissions,
    get_api_key_registry,
    require_permission,
)
from ues.models.api_key import APIKey

from typing import Annotated
from fastapi import Depends

router = APIRouter(
    prefix="/keys",
    tags=["keys"],
)


# ============================================================================
# Request Models
# ============================================================================


class CreateKeyRequest(BaseModel):
    """Request model for creating a new API key.

    Attributes:
        name: Human-readable name for the key.
        permissions: List of permissions to grant to this key.
    
    Example:
        {
            "name": "Email Bot",
            "permissions": ["email:*", "events:create"]
        }
    """

    name: str = Field(
        min_length=1,
        max_length=100,
        description="Human-readable name for the key"
    )
    permissions: list[str] = Field(
        min_length=1,
        description="List of permissions to grant (supports wildcards like 'email:*' or '*')"
    )


# ============================================================================
# Response Models
# ============================================================================


class CreateKeyResponse(BaseModel):
    """Response model for successful key creation.

    The `secret` field is only returned once at creation time. It is never
    stored and cannot be retrieved later. Users must save this value securely.

    Attributes:
        key_id: Unique identifier for the key (public, safe to expose).
        secret: The API key secret (only returned once - save it!).
        name: Human-readable name for the key.
        permissions: List of granted permissions.
        created_at: When the key was created (UTC).
        created_by: key_id of the key that created this key.
    """

    key_id: str = Field(description="Unique identifier for the key")
    secret: str = Field(description="API key secret (only returned once - SAVE IT!)")
    name: str = Field(description="Human-readable name for the key")
    permissions: list[str] = Field(description="List of granted permissions")
    created_at: datetime = Field(description="When the key was created (UTC)")
    created_by: Optional[str] = Field(description="key_id of the key that created this key")


class KeyInfo(BaseModel):
    """Response model for key details (without the secret).

    Used when listing or retrieving keys. The secret is never included
    because it is not stored - only its hash.

    Attributes:
        key_id: Unique identifier for the key.
        name: Human-readable name for the key.
        permissions: List of granted permissions.
        created_at: When the key was created (UTC).
        created_by: key_id of the key that created this key.
        last_used_at: When the key was last used (UTC), if ever.
        is_active: Whether the key is active (not revoked).
        revoked_at: When the key was revoked (UTC), if revoked.
    """

    key_id: str = Field(description="Unique identifier for the key")
    name: str = Field(description="Human-readable name for the key")
    permissions: list[str] = Field(description="List of granted permissions")
    created_at: datetime = Field(description="When the key was created (UTC)")
    created_by: Optional[str] = Field(description="key_id of the key that created this key")
    last_used_at: Optional[datetime] = Field(description="When the key was last used (UTC)")
    is_active: bool = Field(description="Whether the key is active (not revoked)")
    revoked_at: Optional[datetime] = Field(
        default=None, description="When the key was revoked (UTC)"
    )

    @classmethod
    def from_api_key(cls, key: APIKey) -> "KeyInfo":
        """Create a KeyInfo from an APIKey model.

        Args:
            key: The APIKey instance to convert.

        Returns:
            A KeyInfo instance with the key's public information.
        """
        return cls(
            key_id=key.key_id,
            name=key.name,
            permissions=key.permissions,
            created_at=key.created_at,
            created_by=key.created_by,
            last_used_at=key.last_used_at,
            is_active=key.is_active,
            revoked_at=key.revoked_at,
        )


class ListKeysResponse(BaseModel):
    """Response model for listing API keys.

    Attributes:
        keys: List of key information objects.
        total: Total number of keys.
        active: Number of active (non-revoked) keys.
        revoked: Number of revoked keys.
    """

    keys: list[KeyInfo] = Field(description="List of key information objects")
    total: int = Field(description="Total number of keys")
    active: int = Field(description="Number of active keys")
    revoked: int = Field(description="Number of revoked keys")


class RevokeKeyResponse(BaseModel):
    """Response model for key revocation.

    Attributes:
        key_id: The ID of the revoked key.
        name: The name of the revoked key.
        revoked_at: When the key was revoked (UTC).
        message: Human-readable message.
    """

    key_id: str = Field(description="The ID of the revoked key")
    name: str = Field(description="The name of the revoked key")
    revoked_at: datetime = Field(description="When the key was revoked (UTC)")
    message: str = Field(description="Human-readable message")


# ============================================================================
# Route Handlers
# ============================================================================


@router.post(
    "",
    response_model=CreateKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key",
    description="""
Create a new API key with the specified name and permissions.

**IMPORTANT**: The `secret` field in the response is only returned once at creation time.
It is never stored and cannot be retrieved later. You must save this value securely.

Permissions support wildcards:
- `*` grants all permissions (admin access)
- `email:*` grants all email permissions
- `calendar:calendars:*` grants all calendar sub-resource permissions
""",
)
async def create_key(
    request: CreateKeyRequest,
    current_key: Annotated[APIKey, Depends(require_permission(Permissions.KEYS_CREATE))],
) -> CreateKeyResponse:
    """Create a new API key.

    Creates a new API key with the specified name and permissions. The secret
    is returned only once and must be saved securely by the caller.

    Args:
        request: The key creation request with name and permissions.
        current_key: The authenticated API key (must have keys:create permission).

    Returns:
        The created key information including the one-time secret.
    """
    registry = get_api_key_registry()

    secret, key = registry.create_key(
        name=request.name,
        permissions=request.permissions,
        created_by=current_key.key_id,
    )

    return CreateKeyResponse(
        key_id=key.key_id,
        secret=secret,
        name=key.name,
        permissions=key.permissions,
        created_at=key.created_at,
        created_by=key.created_by,
    )


@router.get(
    "",
    response_model=ListKeysResponse,
    summary="List all API keys",
    description="""
List all API keys in the system.

By default, includes both active and revoked keys. Use the `include_revoked`
query parameter to filter.

Note: The secret values are never included in list responses.
""",
)
async def list_keys(
    include_revoked: bool = True,
    _: Annotated[APIKey, Depends(require_permission(Permissions.KEYS_LIST))] = None,
) -> ListKeysResponse:
    """List all API keys.

    Returns all API keys in the registry, optionally filtered by status.

    Args:
        include_revoked: Whether to include revoked keys (default: True).

    Returns:
        List of key information with counts.
    """
    registry = get_api_key_registry()
    all_keys = registry.list_keys(include_revoked=include_revoked)

    key_infos = [KeyInfo.from_api_key(k) for k in all_keys]
    active_count = sum(1 for k in all_keys if k.is_active)
    revoked_count = len(all_keys) - active_count

    return ListKeysResponse(
        keys=key_infos,
        total=len(all_keys),
        active=active_count,
        revoked=revoked_count,
    )


@router.get(
    "/{key_id}",
    response_model=KeyInfo,
    summary="Get API key details",
    description="""
Get detailed information about a specific API key.

Note: The secret value is never included in the response because it is
not stored - only its hash is kept for validation.
""",
)
async def get_key(
    key_id: str,
    _: Annotated[APIKey, Depends(require_permission(Permissions.KEYS_READ))] = None,
) -> KeyInfo:
    """Get details for a specific API key.

    Args:
        key_id: The unique identifier of the key to retrieve.

    Returns:
        Key information (without the secret).

    Raises:
        HTTPException: 404 if the key is not found.
    """
    registry = get_api_key_registry()
    key = registry.get_key(key_id)

    if key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key with ID '{key_id}' not found",
        )

    return KeyInfo.from_api_key(key)


@router.delete(
    "/{key_id}",
    response_model=RevokeKeyResponse,
    summary="Revoke an API key",
    description="""
Revoke an API key.

Revoked keys cannot be used for authentication. The key is kept in the
registry for audit purposes but will be marked as inactive.

**Note**: The admin key cannot be revoked.
""",
)
async def revoke_key(
    key_id: str,
    _: Annotated[APIKey, Depends(require_permission(Permissions.KEYS_REVOKE))] = None,
) -> RevokeKeyResponse:
    """Revoke an API key.

    Marks the key as revoked so it can no longer be used for authentication.
    The key is kept for audit purposes.

    Args:
        key_id: The unique identifier of the key to revoke.

    Returns:
        Revocation confirmation with timestamp.

    Raises:
        HTTPException: 404 if the key is not found.
        HTTPException: 400 if attempting to revoke the admin key.
        HTTPException: 409 if the key is already revoked.
    """
    registry = get_api_key_registry()
    key = registry.get_key(key_id)

    if key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key with ID '{key_id}' not found",
        )

    # Check if already revoked before attempting revocation
    if not key.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"API key '{key_id}' is already revoked",
        )

    try:
        success = registry.revoke_key(key_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API key with ID '{key_id}' not found",
            )
    except ValueError as e:
        # Attempting to revoke admin key
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Get updated key info for response
    key = registry.get_key(key_id)

    return RevokeKeyResponse(
        key_id=key_id,
        name=key.name,
        revoked_at=key.revoked_at,
        message=f"API key '{key.name}' has been revoked and can no longer be used",
    )
