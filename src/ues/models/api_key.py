"""API Key model for authentication and authorization.

This module provides the APIKey model used for authenticating API requests
and authorizing access to specific endpoints based on permissions.

Example usage:
    # Create a key with specific permissions
    key = APIKey(
        key_hash="hashed_secret",
        name="My API Key",
        permissions=["email:*", "sms:state", "sms:query"],
    )
    
    # Check permissions
    key.has_permission("email:send")  # True (matches email:*)
    key.has_permission("sms:state")   # True (exact match)
    key.has_permission("calendar:create")  # False (no permission)
"""

import secrets
from datetime import datetime, timezone
from hashlib import sha256
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


def generate_key_id() -> str:
    """Generate a unique key identifier.
    
    Returns:
        A string in the format 'ues_XXXXXXXXXXXXXXXX' (16 hex chars).
    """
    return f"ues_{secrets.token_hex(8)}"


def generate_key_secret() -> str:
    """Generate a secure random secret for an API key.
    
    Returns:
        A 32-byte hex string (64 characters).
    """
    return secrets.token_hex(32)


def hash_secret(secret: str) -> str:
    """Hash an API key secret using SHA-256.
    
    Args:
        secret: The plaintext API key secret.
    
    Returns:
        The SHA-256 hash of the secret as a hex string.
    """
    return sha256(secret.encode()).hexdigest()


class APIKey(BaseModel):
    """Represents an API key with its permissions and metadata.
    
    An APIKey is used to authenticate and authorize API requests. Each key
    has a unique ID (public), a hashed secret (for validation), and a set
    of permissions that determine what endpoints the key can access.
    
    The secret is never stored - only its hash. When validating a request,
    the provided secret is hashed and compared to the stored hash.
    
    Attributes:
        key_id: Unique identifier for the key (public, safe to expose).
        key_hash: SHA-256 hash of the secret key (stored, never expose).
        name: Human-readable name for the key.
        permissions: List of granted permissions (supports wildcards).
        created_at: When the key was created (UTC).
        created_by: key_id of the key that created this key, if any.
        last_used_at: When the key was last used (UTC), if ever.
        revoked_at: When the key was revoked (UTC), or None if active.
    
    Example:
        key = APIKey(
            key_hash=hash_secret("my_secret"),
            name="Email Bot",
            permissions=["email:*", "events:create"],
        )
        
        # Admin key with full access
        admin_key = APIKey(
            key_hash=hash_secret("admin_secret"),
            name="Admin Key",
            permissions=["*"],
        )
    """
    
    key_id: str = Field(
        default_factory=generate_key_id,
        description="Unique identifier for the key (public, safe to expose)"
    )
    key_hash: str = Field(
        description="SHA-256 hash of the secret key (stored, never exposed)"
    )
    name: str = Field(
        description="Human-readable name for the key"
    )
    permissions: list[str] = Field(
        default_factory=list,
        description="List of granted permissions (supports wildcards like 'email:*' or '*')"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the key was created (UTC)"
    )
    created_by: Optional[str] = Field(
        default=None,
        description="key_id of the key that created this key"
    )
    last_used_at: Optional[datetime] = Field(
        default=None,
        description="When the key was last used (UTC)"
    )
    revoked_at: Optional[datetime] = Field(
        default=None,
        description="When the key was revoked (UTC), or None if active"
    )
    
    model_config = ConfigDict(frozen=False)
    
    @property
    def is_active(self) -> bool:
        """Check if the key is active (not revoked).
        
        Returns:
            True if the key has not been revoked, False otherwise.
        """
        return self.revoked_at is None
    
    def has_permission(self, required: str) -> bool:
        """Check if this key has a specific permission.
        
        Handles wildcard expansion:
        - '*' grants all permissions (admin)
        - 'email:*' grants all email permissions (e.g., matches email:send, email:state)
        - 'calendar:calendars:*' grants all calendar sub-resource permissions
        
        Args:
            required: The permission to check for (e.g., 'email:send').
        
        Returns:
            True if the key has the required permission, False otherwise.
        
        Example:
            key = APIKey(
                key_hash="...",
                name="Test",
                permissions=["email:*", "sms:state"],
            )
            
            key.has_permission("email:send")      # True (wildcard match)
            key.has_permission("sms:state")       # True (exact match)
            key.has_permission("sms:send")        # False (no permission)
            key.has_permission("calendar:state")  # False (no permission)
        """
        # Admin wildcard grants everything
        if "*" in self.permissions:
            return True
        
        # Exact match
        if required in self.permissions:
            return True
        
        # Check for wildcard matches at each level
        # e.g., 'email:send' should match 'email:*'
        # e.g., 'calendar:calendars:create' should match 'calendar:*' or 'calendar:calendars:*'
        parts = required.split(":")
        
        for i in range(len(parts)):
            # Build prefix and wildcard pattern
            # For 'calendar:calendars:create':
            #   i=0: 'calendar:*'
            #   i=1: 'calendar:calendars:*'
            prefix = ":".join(parts[:i + 1])
            wildcard = f"{prefix}:*"
            
            if wildcard in self.permissions:
                return True
        
        return False
    
    def revoke(self) -> None:
        """Mark this key as revoked.
        
        Once revoked, the key cannot be used to authenticate requests.
        This operation cannot be undone.
        """
        if self.revoked_at is None:
            self.revoked_at = datetime.now(timezone.utc)
    
    def record_usage(self) -> None:
        """Record that this key was used.
        
        Updates the last_used_at timestamp to the current UTC time.
        """
        self.last_used_at = datetime.now(timezone.utc)
    
    def validate_secret(self, secret: str) -> bool:
        """Validate a secret against this key's hash.
        
        Uses constant-time comparison to prevent timing attacks.
        
        Args:
            secret: The plaintext secret to validate.
        
        Returns:
            True if the secret is valid, False otherwise.
        """
        provided_hash = hash_secret(secret)
        return secrets.compare_digest(provided_hash, self.key_hash)
