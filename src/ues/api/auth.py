"""Authentication and authorization for the UES API.

This module provides:
- APIKeyRegistry: In-memory storage and management of API keys
- Authentication dependencies for FastAPI route protection
- Permission constants for all API endpoints

Example usage in routes:
    from ues.api.auth import require_permission, Permissions
    
    @router.get("/state")
    async def get_state(
        engine: SimulationEngineDep,
        _: Annotated[APIKey, Depends(require_permission(Permissions.EMAIL_STATE))],
    ):
        ...

Example key management:
    registry = APIKeyRegistry()
    secret, key = registry.create_admin_key()
    print(f"Admin key: {secret}")
    
    # Create a limited key
    secret, key = registry.create_key(
        name="Email Bot",
        permissions=["email:*"],
        created_by=key.key_id,
    )
"""

import logging
import secrets
from datetime import datetime, timezone
from typing import Annotated, Callable, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader

from ues.models.api_key import APIKey, generate_key_secret, hash_secret


logger = logging.getLogger(__name__)


# =============================================================================
# Permission Constants
# =============================================================================


class Permissions:
    """Permission constants for all API endpoints.
    
    Permissions follow the pattern: {resource}:{action} or {resource}:{sub-resource}:{action}
    
    Use these constants in route handlers to ensure consistent permission names.
    
    Example:
        @router.get("/state")
        async def get_state(
            _: Annotated[APIKey, Depends(require_permission(Permissions.EMAIL_STATE))],
        ):
            ...
    """
    
    # Time Control (/simulator/time)
    TIME_READ = "time:read"
    TIME_ADVANCE = "time:advance"
    TIME_SET = "time:set"
    TIME_SKIP = "time:skip"
    TIME_SCALE = "time:scale"
    TIME_PAUSE = "time:pause"
    TIME_RESUME = "time:resume"
    
    # Environment (/environment)
    ENVIRONMENT_READ = "environment:read"
    ENVIRONMENT_LIST = "environment:list"
    ENVIRONMENT_VALIDATE = "environment:validate"
    
    # Events (/events)
    EVENTS_LIST = "events:list"
    EVENTS_CREATE = "events:create"
    EVENTS_EXECUTE = "events:execute"
    EVENTS_BATCH = "events:batch"
    EVENTS_READ = "events:read"
    EVENTS_DELETE = "events:delete"
    EVENTS_SUMMARY = "events:summary"
    
    # Simulation (/simulation)
    SIMULATION_START = "simulation:start"
    SIMULATION_STOP = "simulation:stop"
    SIMULATION_STATUS = "simulation:status"
    SIMULATION_RESET = "simulation:reset"
    SIMULATION_CLEAR = "simulation:clear"
    SIMULATION_UNDO = "simulation:undo"
    SIMULATION_REDO = "simulation:redo"
    SIMULATION_HOLD = "simulation:hold"
    SIMULATION_RELEASE = "simulation:release"
    SIMULATION_HOLDS = "simulation:holds"
    
    # Scenario (/scenario)
    SCENARIO_EXPORT = "scenario:export"
    SCENARIO_IMPORT = "scenario:import"
    
    # Webhooks (/webhooks)
    WEBHOOKS_CREATE = "webhooks:create"
    WEBHOOKS_LIST = "webhooks:list"
    WEBHOOKS_READ = "webhooks:read"
    WEBHOOKS_UPDATE = "webhooks:update"
    WEBHOOKS_DELETE = "webhooks:delete"
    WEBHOOKS_TEST = "webhooks:test"
    WEBHOOKS_DELIVERIES = "webhooks:deliveries"
    WEBHOOKS_PAUSE = "webhooks:pause"
    WEBHOOKS_RESUME = "webhooks:resume"
    
    # Email (/email)
    EMAIL_STATE = "email:state"
    EMAIL_QUERY = "email:query"
    EMAIL_SEND = "email:send"
    EMAIL_RECEIVE = "email:receive"
    EMAIL_READ = "email:read"
    EMAIL_UNREAD = "email:unread"
    EMAIL_STAR = "email:star"
    EMAIL_UNSTAR = "email:unstar"
    EMAIL_ARCHIVE = "email:archive"
    EMAIL_DELETE = "email:delete"
    EMAIL_LABEL = "email:label"
    EMAIL_UNLABEL = "email:unlabel"
    EMAIL_MOVE = "email:move"
    
    # SMS (/sms)
    SMS_STATE = "sms:state"
    SMS_QUERY = "sms:query"
    SMS_SEND = "sms:send"
    SMS_RECEIVE = "sms:receive"
    SMS_READ = "sms:read"
    SMS_UNREAD = "sms:unread"
    SMS_DELETE = "sms:delete"
    SMS_REACT = "sms:react"
    SMS_CONVERSATION = "sms:conversation"
    
    # Chat (/chat)
    CHAT_STATE = "chat:state"
    CHAT_QUERY = "chat:query"
    CHAT_SEND = "chat:send"
    CHAT_DELETE = "chat:delete"
    CHAT_CLEAR = "chat:clear"
    
    # Calendar (/calendar)
    CALENDAR_STATE = "calendar:state"
    CALENDAR_QUERY = "calendar:query"
    CALENDAR_CREATE = "calendar:create"
    CALENDAR_UPDATE = "calendar:update"
    CALENDAR_DELETE = "calendar:delete"
    CALENDAR_CALENDARS_LIST = "calendar:calendars:list"
    CALENDAR_CALENDARS_CREATE = "calendar:calendars:create"
    CALENDAR_CALENDARS_UPDATE = "calendar:calendars:update"
    CALENDAR_CALENDARS_DELETE = "calendar:calendars:delete"
    CALENDAR_CALENDARS_DEFAULT = "calendar:calendars:default"
    
    # Location (/location)
    LOCATION_STATE = "location:state"
    LOCATION_QUERY = "location:query"
    LOCATION_UPDATE = "location:update"
    
    # Weather (/weather)
    WEATHER_STATE = "weather:state"
    WEATHER_QUERY = "weather:query"
    WEATHER_UPDATE = "weather:update"
    
    # Key Management (/keys)
    KEYS_CREATE = "keys:create"
    KEYS_LIST = "keys:list"
    KEYS_READ = "keys:read"
    KEYS_REVOKE = "keys:revoke"
    
    # Access Logs (/access-logs)
    LOGS_READ = "logs:read"
    LOGS_CLEAR = "logs:clear"


# =============================================================================
# API Key Registry
# =============================================================================


class APIKeyRegistry:
    """In-memory registry of API keys.
    
    Manages creation, validation, listing, and revocation of API keys.
    Keys are stored in memory only and are not persisted across restarts.
    
    Thread Safety:
        The current implementation is NOT thread-safe. For production use
        with multiple workers, consider using a shared storage backend.
    
    Attributes:
        _keys: Dictionary mapping key_id to APIKey instances.
        _hash_to_id: Dictionary mapping key_hash to key_id for fast lookup.
        _admin_key_id: The key_id of the admin key, if created.
    
    Example:
        registry = APIKeyRegistry()
        
        # Create admin key at startup
        secret, admin_key = registry.create_admin_key()
        print(f"Admin API Key: {secret}")
        
        # Create limited key
        secret, key = registry.create_key(
            name="Bot Key",
            permissions=["email:*", "sms:*"],
        )
        
        # Validate request
        key = registry.validate_key("provided_secret")
        if key and key.is_active:
            # Allow request
            pass
    """
    
    def __init__(self):
        """Initialize an empty key registry."""
        self._keys: dict[str, APIKey] = {}  # key_id -> APIKey
        self._hash_to_id: dict[str, str] = {}  # key_hash -> key_id
        self._admin_key_id: Optional[str] = None
    
    @property
    def admin_key_id(self) -> Optional[str]:
        """Get the admin key ID, if an admin key has been created."""
        return self._admin_key_id
    
    def create_admin_key(self) -> tuple[str, APIKey]:
        """Create the admin key at startup.
        
        The admin key has full access to all endpoints ('*' permission).
        This method should only be called once at server startup.
        
        Returns:
            A tuple of (secret, APIKey) where secret is the plaintext
            key that should be printed to the console and never stored.
        
        Raises:
            ValueError: If an admin key has already been created.
        """
        if self._admin_key_id is not None:
            raise ValueError("Admin key already exists")
        
        secret = generate_key_secret()
        key = APIKey(
            key_hash=hash_secret(secret),
            name="Admin Key",
            permissions=["*"],
        )
        
        self._keys[key.key_id] = key
        self._hash_to_id[key.key_hash] = key.key_id
        self._admin_key_id = key.key_id
        
        logger.info(f"Admin key created with ID: {key.key_id}")
        
        return secret, key
    
    def create_key(
        self,
        name: str,
        permissions: list[str],
        created_by: Optional[str] = None,
    ) -> tuple[str, APIKey]:
        """Create a new API key.
        
        Args:
            name: Human-readable name for the key.
            permissions: List of permissions to grant (supports wildcards).
            created_by: key_id of the key creating this one (for audit trail).
        
        Returns:
            A tuple of (secret, APIKey) where secret is the plaintext
            key that is returned once and never stored.
        
        Example:
            secret, key = registry.create_key(
                name="Email Bot",
                permissions=["email:*", "events:create"],
                created_by=admin_key.key_id,
            )
        """
        secret = generate_key_secret()
        key = APIKey(
            key_hash=hash_secret(secret),
            name=name,
            permissions=permissions,
            created_by=created_by,
        )
        
        self._keys[key.key_id] = key
        self._hash_to_id[key.key_hash] = key.key_id
        
        logger.info(f"Key '{name}' created with ID: {key.key_id}")
        
        return secret, key
    
    def validate_key(self, secret: str) -> Optional[APIKey]:
        """Validate a secret and return the APIKey if valid.
        
        Uses constant-time comparison to prevent timing attacks.
        Updates the key's last_used_at timestamp on successful validation.
        
        Args:
            secret: The plaintext API key secret to validate.
        
        Returns:
            The APIKey if valid and active, None otherwise.
        """
        # Hash the provided secret
        provided_hash = hash_secret(secret)
        
        # Look up by hash
        key_id = self._hash_to_id.get(provided_hash)
        if key_id is None:
            return None
        
        key = self._keys.get(key_id)
        if key is None:
            return None
        
        # Check if key is active
        if not key.is_active:
            logger.warning(f"Attempted to use revoked key: {key.key_id}")
            return None
        
        # Verify the secret matches (constant-time comparison)
        if not key.validate_secret(secret):
            return None
        
        # Record usage
        key.record_usage()
        
        return key
    
    def get_key(self, key_id: str) -> Optional[APIKey]:
        """Get a key by its public ID.
        
        Args:
            key_id: The unique identifier of the key.
        
        Returns:
            The APIKey if found, None otherwise.
        """
        return self._keys.get(key_id)
    
    def list_keys(self, include_revoked: bool = True) -> list[APIKey]:
        """List all keys in the registry.
        
        Args:
            include_revoked: Whether to include revoked keys.
        
        Returns:
            List of all APIKey instances, optionally filtered.
        """
        keys = list(self._keys.values())
        
        if not include_revoked:
            keys = [k for k in keys if k.is_active]
        
        return keys
    
    def revoke_key(self, key_id: str) -> bool:
        """Revoke a key by its ID.
        
        Revoked keys cannot be used to authenticate requests.
        The key is kept in the registry for audit purposes.
        
        Args:
            key_id: The unique identifier of the key to revoke.
        
        Returns:
            True if the key was found and revoked, False otherwise.
        
        Raises:
            ValueError: If attempting to revoke the admin key.
        """
        if key_id == self._admin_key_id:
            raise ValueError("Cannot revoke the admin key")
        
        key = self._keys.get(key_id)
        if key is None:
            return False
        
        if key.revoked_at is not None:
            # Already revoked
            return True
        
        key.revoke()
        logger.info(f"Key revoked: {key_id}")
        
        return True
    
    def clear(self) -> None:
        """Clear all keys from the registry.
        
        This is primarily useful for testing. In production, you would
        typically revoke keys individually rather than clearing all.
        """
        self._keys.clear()
        self._hash_to_id.clear()
        self._admin_key_id = None
        logger.info("API key registry cleared")


# =============================================================================
# Global Registry Instance
# =============================================================================


# Global registry instance - created once at module load time
# In production, this might be replaced with a database-backed implementation
_api_key_registry: Optional[APIKeyRegistry] = None


def get_api_key_registry() -> APIKeyRegistry:
    """Get the global API key registry instance.
    
    Returns:
        The global APIKeyRegistry instance.
    
    Raises:
        RuntimeError: If the registry hasn't been initialized.
    """
    global _api_key_registry
    
    if _api_key_registry is None:
        raise RuntimeError(
            "API key registry not initialized. Call initialize_api_key_registry() first."
        )
    
    return _api_key_registry


def initialize_api_key_registry() -> tuple[str, APIKey]:
    """Initialize the global API key registry and create the admin key.
    
    This should be called once when the FastAPI app starts up.
    
    Returns:
        A tuple of (admin_secret, admin_key) for printing to console.
    """
    global _api_key_registry
    
    _api_key_registry = APIKeyRegistry()
    return _api_key_registry.create_admin_key()


def shutdown_api_key_registry() -> None:
    """Shut down the API key registry.
    
    This should be called when the FastAPI app shuts down.
    """
    global _api_key_registry
    _api_key_registry = None


# =============================================================================
# FastAPI Security Scheme
# =============================================================================


# Define the API key header scheme
api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,  # We'll handle the error ourselves for better messages
    description="API key for authentication. Use the admin key or create a new key via /keys endpoints.",
)


# =============================================================================
# Authentication Dependencies
# =============================================================================


async def get_current_key(
    request: Request,
    api_key: Annotated[Optional[str], Depends(api_key_header)],
) -> APIKey:
    """FastAPI dependency that extracts and validates the API key.
    
    This dependency:
    1. Extracts the X-API-Key header from the request
    2. Validates it against the registry
    3. Sets the key info on request.state for logging
    4. Returns the APIKey or raises 401 Unauthorized
    
    Args:
        request: The incoming FastAPI request.
        api_key: The API key from the X-API-Key header.
    
    Returns:
        The validated APIKey instance.
    
    Raises:
        HTTPException: 401 if no key provided or key is invalid.
    
    Example:
        @router.get("/some-endpoint")
        async def handler(key: Annotated[APIKey, Depends(get_current_key)]):
            print(f"Request from key: {key.name}")
    """
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    registry = get_api_key_registry()
    key = registry.validate_key(api_key)
    
    if key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Store key info on request state for access logging middleware
    request.state.api_key_id = key.key_id
    request.state.api_key_name = key.name
    
    return key


def require_permission(permission: str) -> Callable[..., APIKey]:
    """Create a dependency that requires a specific permission.
    
    This is a dependency factory that returns a dependency function.
    The returned dependency validates the API key AND checks that it
    has the required permission.
    
    Args:
        permission: The permission required (e.g., 'email:send').
    
    Returns:
        A FastAPI dependency function.
    
    Example:
        @router.post("/send")
        async def send_email(
            request: SendEmailRequest,
            _: Annotated[APIKey, Depends(require_permission(Permissions.EMAIL_SEND))],
        ):
            ...
    
        # Or using the constant:
        @router.get("/state")
        async def get_state(
            key: Annotated[APIKey, Depends(require_permission("email:state"))],
        ):
            # key is the validated APIKey with the required permission
            ...
    """
    
    async def check_permission(
        key: Annotated[APIKey, Depends(get_current_key)],
    ) -> APIKey:
        """Check that the current key has the required permission."""
        if not key.has_permission(permission):
            logger.warning(
                f"Permission denied: key '{key.name}' ({key.key_id}) "
                f"lacks permission '{permission}'"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required permission: {permission}",
            )
        return key
    
    return check_permission


# Type alias for dependency injection
# Use this in route handlers: key: CurrentKeyDep
CurrentKeyDep = Annotated[APIKey, Depends(get_current_key)]


def require_permission_dep(permission: str):
    """Create a type annotation for a permission-protected dependency.
    
    This is a convenience function for creating annotated types with
    permission requirements.
    
    Args:
        permission: The permission required.
    
    Returns:
        An Annotated type for use in route handler signatures.
    
    Example:
        @router.get("/state")
        async def get_state(
            key: Annotated[APIKey, Depends(require_permission("email:state"))],
        ):
            ...
    """
    return Annotated[APIKey, Depends(require_permission(permission))]
