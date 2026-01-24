"""API access control for UES.

This module implements API key-based access control for securing UES endpoints
during AgentBeats assessments. It provides two access levels:
- PROCTOR: Full API access (for Green Agent / test orchestrator)
- USER: Restricted access to user-side actions only (for Purple Agent / agent being tested)

Access control is opt-in via the UES_ACCESS_CONTROL environment variable.
When disabled (default), all endpoints are accessible without authentication.

Example:
    # Generate keys for an assessment
    proctor_key = key_registry.generate_key(
        level=AccessLevel.PROCTOR,
        agent_id="green-agent",
        assessment_id="assessment-123"
    )
    user_key = key_registry.generate_key(
        level=AccessLevel.USER,
        agent_id="purple-agent",
        assessment_id="assessment-123"
    )
    
    # Validate a key
    context = key_registry.validate_key(user_key)
    if context and context.level == AccessLevel.USER:
        # Check if endpoint is allowed for user level
        ...
    
    # Cleanup after assessment
    key_registry.invalidate_keys_by_assessment("assessment-123")
"""

import secrets
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AccessLevel(str, Enum):
    """Access level for API keys.
    
    Attributes:
        PROCTOR: Full API access - can control time, simulation, events, etc.
        USER: Restricted access - can only query state and perform user-side actions.
    """
    PROCTOR = "proctor"
    USER = "user"


class AccessContext(BaseModel):
    """Context for an authenticated API request.
    
    Contains information about the API key holder and their permissions.
    This context is attached to requests for logging and authorization.
    
    Attributes:
        api_key: The API key used for authentication.
        level: The access level granted by this key.
        agent_id: Identifier of the agent holding this key.
        assessment_id: Identifier of the assessment this key is scoped to.
        created_at: When this key was created.
        metadata: Additional metadata for extensibility.
    """
    api_key: str = Field(description="The API key")
    level: AccessLevel = Field(description="Access level granted")
    agent_id: str | None = Field(default=None, description="Agent identifier")
    assessment_id: str | None = Field(default=None, description="Assessment identifier")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Key creation timestamp"
    )
    metadata: dict[str, Any] | None = Field(default=None, description="Additional metadata")


class KeyRegistry:
    """Registry for managing API keys.
    
    Provides methods for generating, validating, and invalidating API keys.
    Keys are stored in memory and scoped to assessments for easy cleanup.
    
    Thread-safety: This implementation is NOT thread-safe. For production use
    with multiple workers, consider using a shared store (Redis, database).
    """
    
    def __init__(self) -> None:
        """Initialize an empty key registry."""
        self._keys: dict[str, AccessContext] = {}
    
    def generate_key(
        self,
        level: AccessLevel,
        agent_id: str | None = None,
        assessment_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Generate a new API key.
        
        Args:
            level: Access level for the key (PROCTOR or USER).
            agent_id: Optional identifier for the agent holding this key.
            assessment_id: Optional assessment identifier for scoping.
            metadata: Optional additional metadata.
        
        Returns:
            The generated API key string.
        
        Example:
            key = registry.generate_key(
                level=AccessLevel.USER,
                agent_id="test-agent",
                assessment_id="assess-001"
            )
            # Returns: "ues_user_a1b2c3d4..."
        """
        # Generate a secure random token
        token = secrets.token_urlsafe(24)  # 32 chars when base64 encoded
        key = f"ues_{level.value}_{token}"
        
        context = AccessContext(
            api_key=key,
            level=level,
            agent_id=agent_id,
            assessment_id=assessment_id,
            metadata=metadata,
        )
        
        self._keys[key] = context
        return key
    
    def validate_key(self, key: str) -> AccessContext | None:
        """Validate an API key and return its context.
        
        Args:
            key: The API key to validate.
        
        Returns:
            The AccessContext if the key is valid, None otherwise.
        """
        return self._keys.get(key)
    
    def get_context(self, key: str) -> AccessContext | None:
        """Get the context for a key (alias for validate_key).
        
        Args:
            key: The API key.
        
        Returns:
            The AccessContext if the key exists, None otherwise.
        """
        return self.validate_key(key)
    
    def invalidate_key(self, key: str) -> bool:
        """Invalidate a single API key.
        
        Args:
            key: The API key to invalidate.
        
        Returns:
            True if the key was found and invalidated, False otherwise.
        """
        if key in self._keys:
            del self._keys[key]
            return True
        return False
    
    def invalidate_keys_by_assessment(self, assessment_id: str) -> int:
        """Invalidate all keys for a specific assessment.
        
        This is typically called when an assessment completes to clean up
        all keys that were issued for that assessment.
        
        Args:
            assessment_id: The assessment identifier.
        
        Returns:
            The number of keys that were invalidated.
        """
        keys_to_remove = [
            key for key, ctx in self._keys.items()
            if ctx.assessment_id == assessment_id
        ]
        for key in keys_to_remove:
            del self._keys[key]
        return len(keys_to_remove)
    
    def list_keys(self, assessment_id: str | None = None) -> list[AccessContext]:
        """List all keys, optionally filtered by assessment.
        
        Args:
            assessment_id: If provided, only return keys for this assessment.
        
        Returns:
            List of AccessContext objects for matching keys.
        """
        if assessment_id is None:
            return list(self._keys.values())
        return [
            ctx for ctx in self._keys.values()
            if ctx.assessment_id == assessment_id
        ]
    
    def clear(self) -> int:
        """Clear all keys from the registry.
        
        Returns:
            The number of keys that were cleared.
        """
        count = len(self._keys)
        self._keys.clear()
        return count


# =============================================================================
# Endpoint Permissions
# =============================================================================

# Public routes - no authentication required
PUBLIC_ROUTES: set[str] = {
    "GET /",
    "GET /health",
    "GET /docs",
    "GET /docs/oauth2-redirect",
    "GET /redoc",
    "GET /openapi.json",
}

# Routes that require proctor-level access only
PROCTOR_ONLY_ROUTES: set[str] = {
    # Time control
    "POST /simulator/time/advance",
    "POST /simulator/time/set",
    "POST /simulator/time/pause",
    "POST /simulator/time/resume",
    "POST /simulator/time/skip-to-next",
    "POST /simulator/time/set-scale",
    
    # Simulation control
    "POST /simulation/start",
    "POST /simulation/stop",
    "POST /simulation/reset",
    "POST /simulation/clear",
    "POST /simulation/undo",
    "POST /simulation/redo",
    "POST /simulation/hold",
    "GET /simulation/holds",
    
    # Events
    "GET /events",
    "POST /events",
    "POST /events/immediate",
    "POST /events/batch",
    
    # Scenario
    "POST /scenario/import",
    "POST /scenario/import/json",
    "GET /scenario/export",
    "GET /scenario/export/json",
    
    # Simulator-side modality actions (environment control)
    "POST /email/receive",
    "POST /sms/receive",
    "POST /calendar/invite",
    "POST /chat/receive",
    "POST /location/set",
    "POST /location/update",
    "POST /weather/set",
    "POST /weather/update",
    
    # Environment
    "GET /environment/state",
    "POST /environment/query",
    
    # WebSocket/Webhooks
    "POST /webhooks/register",
    "GET /webhooks",
    
    # Admin endpoints (when access control is enabled)
    "POST /admin/keys",
    "GET /admin/keys",
    "DELETE /admin/keys/{api_key}",
    "POST /admin/keys/cleanup/{assessment_id}",
}

# User-allowed routes (both user and proctor can access)
USER_ALLOWED_ROUTES: set[str] = {
    # Read/query - all modalities
    "GET /email/state",
    "POST /email/query",
    "GET /sms/state",
    "POST /sms/query",
    "GET /calendar/state",
    "POST /calendar/query",
    "GET /chat/state",
    "POST /chat/query",
    "GET /location/state",
    "GET /weather/state",
    "GET /simulator/time",
    "GET /simulation/status",
    
    # Email user-side actions
    "POST /email/send",
    "POST /email/reply",
    "POST /email/forward",
    "POST /email/move",
    "POST /email/archive",
    "POST /email/delete",
    "POST /email/label",
    "POST /email/unlabel",
    "POST /email/mark-read",
    "POST /email/mark-unread",
    
    # SMS user-side actions
    "POST /sms/send",
    "POST /sms/react",
    "POST /sms/delete",
    "POST /sms/mark-read",
    
    # Calendar user-side actions
    "POST /calendar/create",
    "POST /calendar/update",
    "POST /calendar/delete",
    "POST /calendar/rsvp",
    
    # Chat user-side actions
    "POST /chat/send",
}


def get_route_permission(method: str, path: str) -> AccessLevel | None:
    """Determine the required access level for a route.
    
    Args:
        method: HTTP method (GET, POST, etc.).
        path: URL path (e.g., "/email/send").
    
    Returns:
        None if the route is public (no auth required).
        AccessLevel.USER if user-level access is sufficient.
        AccessLevel.PROCTOR if proctor-level access is required.
    
    Note:
        Routes with path parameters (e.g., /simulation/release/{hold_id})
        are matched by prefix. Unknown routes default to PROCTOR_ONLY
        for security.
    """
    route_key = f"{method.upper()} {path}"
    
    # Check public routes
    if route_key in PUBLIC_ROUTES:
        return None
    
    # Check user-allowed routes
    if route_key in USER_ALLOWED_ROUTES:
        return AccessLevel.USER
    
    # Check proctor-only routes
    if route_key in PROCTOR_ONLY_ROUTES:
        return AccessLevel.PROCTOR
    
    # Handle routes with path parameters
    # Check for prefix matches in proctor routes
    for proctor_route in PROCTOR_ONLY_ROUTES:
        proctor_method, proctor_path = proctor_route.split(" ", 1)
        if method.upper() == proctor_method and path.startswith(proctor_path.rstrip("/")):
            return AccessLevel.PROCTOR
    
    # Handle dynamic routes like /simulation/release/{hold_id}, /events/{event_id}
    # These are proctor-only
    if path.startswith("/simulation/release/"):
        return AccessLevel.PROCTOR
    if path.startswith("/events/") and method.upper() == "DELETE":
        return AccessLevel.PROCTOR
    if path.startswith("/webhooks/") and method.upper() == "DELETE":
        return AccessLevel.PROCTOR
    if path.startswith("/admin/keys/"):
        return AccessLevel.PROCTOR
    
    # Default to proctor-only for unknown routes (fail-safe)
    return AccessLevel.PROCTOR


def is_access_allowed(required_level: AccessLevel | None, actual_level: AccessLevel) -> bool:
    """Check if the actual access level satisfies the required level.
    
    Args:
        required_level: The level required by the endpoint (None = public).
        actual_level: The level of the requesting user's API key.
    
    Returns:
        True if access should be allowed, False otherwise.
    """
    # Public routes allow any access
    if required_level is None:
        return True
    
    # Proctor can access everything
    if actual_level == AccessLevel.PROCTOR:
        return True
    
    # User can only access user-allowed routes
    if actual_level == AccessLevel.USER:
        return required_level == AccessLevel.USER
    
    return False


# Global key registry singleton
key_registry = KeyRegistry()
