"""FastAPI dependencies for API access control.

This module provides injectable dependencies for enforcing access control
in route handlers. These dependencies extract and validate API keys from
request headers and enforce permission levels.

Usage in routes:
    from api.access_dependencies import AccessContextDep, ProctorDep
    
    @router.post("/admin-action")
    async def admin_action(access: ProctorDep):
        # Only proctor-level keys can reach here
        return {"agent_id": access.agent_id}
    
    @router.get("/state")
    async def get_state(access: AccessContextDep):
        # Any valid key can reach here
        return {"level": access.level}
    
    # For endpoints that need agent attribution but work without access control
    @router.post("/events")
    async def create_event(access: OptionalAccessContextDep):
        # access is None if access control is disabled
        agent_id = access.agent_id if access else None
"""

import os
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from api.access_control import (
    AccessContext,
    AccessLevel,
    key_registry,
)


# Check if access control is enabled
def _is_access_control_enabled() -> bool:
    """Check if access control is enabled via environment variable."""
    return os.getenv("UES_ACCESS_CONTROL", "false").lower() == "true"


async def get_api_key(
    x_api_key: Annotated[str | None, Header(description="API key for authentication")] = None,
) -> str:
    """Extract API key from request header.
    
    Args:
        x_api_key: The API key from the X-API-Key header.
    
    Returns:
        The API key string.
    
    Raises:
        HTTPException: 401 if the header is missing.
    """
    if x_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return x_api_key


async def get_access_context(
    api_key: Annotated[str, Depends(get_api_key)],
) -> AccessContext:
    """Validate API key and return access context.
    
    Args:
        api_key: The API key extracted from the header.
    
    Returns:
        The AccessContext for the validated key.
    
    Raises:
        HTTPException: 401 if the key is invalid or expired.
    """
    context = key_registry.validate_key(api_key)
    if context is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return context


async def require_proctor(
    context: Annotated[AccessContext, Depends(get_access_context)],
) -> AccessContext:
    """Require proctor-level access.
    
    Use this dependency for endpoints that should only be accessible
    to proctor-level API keys (e.g., time control, simulation control).
    
    Args:
        context: The access context from the validated key.
    
    Returns:
        The AccessContext if proctor-level.
    
    Raises:
        HTTPException: 403 if the key is user-level.
    """
    if context.level != AccessLevel.PROCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires proctor-level access",
        )
    return context


async def require_user_or_proctor(
    context: Annotated[AccessContext, Depends(get_access_context)],
) -> AccessContext:
    """Require user or proctor-level access.
    
    Use this dependency for endpoints accessible to both access levels.
    This is effectively the same as get_access_context but more explicit
    about the permission intent.
    
    Args:
        context: The access context from the validated key.
    
    Returns:
        The AccessContext (either level is acceptable).
    """
    # Both levels are allowed, just return the context
    return context


async def get_optional_access_context(
    x_api_key: Annotated[str | None, Header(description="API key for authentication")] = None,
) -> AccessContext | None:
    """Get access context if available, or None if access control is disabled.
    
    This dependency is useful for endpoints that need to track agent attribution
    but should still work when access control is disabled.
    
    Behavior:
    - If access control is disabled: returns None (no authentication required)
    - If access control is enabled and key is missing: raises 401
    - If access control is enabled and key is invalid: raises 401
    - If access control is enabled and key is valid: returns AccessContext
    
    Args:
        x_api_key: The API key from the X-API-Key header (optional).
    
    Returns:
        The AccessContext for the validated key, or None if access control
        is disabled.
    
    Raises:
        HTTPException: 401 if access control is enabled and key is missing/invalid.
    """
    # If access control is disabled, return None (allow all requests)
    if not _is_access_control_enabled():
        return None
    
    # Access control is enabled - require valid key
    if x_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    context = key_registry.validate_key(x_api_key)
    if context is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return context


# Type aliases for cleaner route handler signatures
ApiKeyDep = Annotated[str, Depends(get_api_key)]
AccessContextDep = Annotated[AccessContext, Depends(get_access_context)]
ProctorDep = Annotated[AccessContext, Depends(require_proctor)]
UserOrProctorDep = Annotated[AccessContext, Depends(require_user_or_proctor)]
OptionalAccessContextDep = Annotated[AccessContext | None, Depends(get_optional_access_context)]
