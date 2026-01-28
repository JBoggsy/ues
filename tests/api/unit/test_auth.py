"""Unit tests for API authentication module.

This module tests the auth components including:
- APIKeyRegistry CRUD operations
- Authentication dependencies
- Permission checking dependencies
- Global registry management

Test Organization:
- TestAPIKeyRegistry: CRUD and validation tests
- TestAPIKeyRegistryEdgeCases: Error handling and edge cases
- TestAuthDependencies: FastAPI dependency tests
- TestGlobalRegistry: Global registry lifecycle tests
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from ues.api.auth import (
    APIKeyRegistry,
    CurrentKeyDep,
    Permissions,
    get_api_key_registry,
    get_current_key,
    initialize_api_key_registry,
    require_permission,
    shutdown_api_key_registry,
)
from ues.models.api_key import APIKey, hash_secret


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def registry():
    """Provide a fresh APIKeyRegistry for each test."""
    return APIKeyRegistry()


@pytest.fixture
def registry_with_admin(registry):
    """Provide a registry with an admin key created."""
    secret, key = registry.create_admin_key()
    return registry, secret, key


@pytest.fixture(autouse=True)
def reset_global_registry():
    """Reset the global registry before and after each test."""
    import ues.api.auth as auth_module
    
    # Store original state
    original_registry = auth_module._api_key_registry
    
    # Reset before test
    auth_module._api_key_registry = None
    
    yield
    
    # Reset after test
    auth_module._api_key_registry = original_registry


# =============================================================================
# Permissions Constants Tests
# =============================================================================


class TestPermissions:
    """Tests for the Permissions constants class."""

    def test_time_permissions_exist(self):
        """Test that time-related permissions are defined."""
        assert Permissions.TIME_READ == "time:read"
        assert Permissions.TIME_ADVANCE == "time:advance"
        assert Permissions.TIME_SET == "time:set"
        assert Permissions.TIME_PAUSE == "time:pause"

    def test_email_permissions_exist(self):
        """Test that email-related permissions are defined."""
        assert Permissions.EMAIL_STATE == "email:state"
        assert Permissions.EMAIL_SEND == "email:send"
        assert Permissions.EMAIL_RECEIVE == "email:receive"

    def test_calendar_sub_resource_permissions(self):
        """Test that calendar sub-resource permissions are defined."""
        assert Permissions.CALENDAR_CALENDARS_LIST == "calendar:calendars:list"
        assert Permissions.CALENDAR_CALENDARS_CREATE == "calendar:calendars:create"

    def test_key_management_permissions(self):
        """Test that key management permissions are defined."""
        assert Permissions.KEYS_CREATE == "keys:create"
        assert Permissions.KEYS_LIST == "keys:list"
        assert Permissions.KEYS_READ == "keys:read"
        assert Permissions.KEYS_REVOKE == "keys:revoke"


# =============================================================================
# APIKeyRegistry Tests
# =============================================================================


class TestAPIKeyRegistry:
    """Tests for APIKeyRegistry CRUD operations."""

    def test_initialization(self, registry):
        """Test that registry initializes with empty state."""
        assert registry._keys == {}
        assert registry._hash_to_id == {}
        assert registry._admin_key_id is None
        assert registry.admin_key_id is None

    def test_create_admin_key(self, registry):
        """Test creating an admin key."""
        secret, key = registry.create_admin_key()
        
        assert secret is not None
        assert len(secret) == 64  # 32 bytes hex
        assert key.name == "Admin Key"
        assert key.permissions == ["*"]
        assert key.is_active is True
        assert registry.admin_key_id == key.key_id

    def test_create_admin_key_only_once(self, registry_with_admin):
        """Test that admin key can only be created once."""
        registry, _, _ = registry_with_admin
        
        with pytest.raises(ValueError) as exc_info:
            registry.create_admin_key()
        
        assert "Admin key already exists" in str(exc_info.value)

    def test_create_key(self, registry):
        """Test creating a regular key."""
        secret, key = registry.create_key(
            name="Test Key",
            permissions=["email:*", "sms:state"],
        )
        
        assert secret is not None
        assert len(secret) == 64
        assert key.name == "Test Key"
        assert key.permissions == ["email:*", "sms:state"]
        assert key.is_active is True
        assert key.created_by is None

    def test_create_key_with_created_by(self, registry_with_admin):
        """Test creating a key with created_by set."""
        registry, _, admin_key = registry_with_admin
        
        secret, key = registry.create_key(
            name="Child Key",
            permissions=["email:state"],
            created_by=admin_key.key_id,
        )
        
        assert key.created_by == admin_key.key_id

    def test_validate_key_success(self, registry):
        """Test validating a correct secret."""
        secret, created_key = registry.create_key(
            name="Test",
            permissions=["email:*"],
        )
        
        validated_key = registry.validate_key(secret)
        
        assert validated_key is not None
        assert validated_key.key_id == created_key.key_id
        assert validated_key.last_used_at is not None

    def test_validate_key_wrong_secret(self, registry):
        """Test validating an incorrect secret."""
        registry.create_key(name="Test", permissions=[])
        
        result = registry.validate_key("wrong_secret")
        
        assert result is None

    def test_validate_key_nonexistent(self, registry):
        """Test validating a secret for a key that doesn't exist."""
        result = registry.validate_key("nonexistent_secret")
        
        assert result is None

    def test_validate_key_revoked(self, registry):
        """Test that revoked keys cannot be validated."""
        secret, key = registry.create_key(name="Test", permissions=[])
        
        # Revoke the key
        registry.revoke_key(key.key_id)
        
        result = registry.validate_key(secret)
        
        assert result is None

    def test_get_key(self, registry):
        """Test retrieving a key by ID."""
        _, created_key = registry.create_key(name="Test", permissions=[])
        
        retrieved_key = registry.get_key(created_key.key_id)
        
        assert retrieved_key is not None
        assert retrieved_key.key_id == created_key.key_id

    def test_get_key_nonexistent(self, registry):
        """Test retrieving a key that doesn't exist."""
        result = registry.get_key("nonexistent_id")
        
        assert result is None

    def test_list_keys_empty(self, registry):
        """Test listing keys when registry is empty."""
        keys = registry.list_keys()
        
        assert keys == []

    def test_list_keys(self, registry):
        """Test listing all keys."""
        registry.create_key(name="Key 1", permissions=[])
        registry.create_key(name="Key 2", permissions=[])
        registry.create_key(name="Key 3", permissions=[])
        
        keys = registry.list_keys()
        
        assert len(keys) == 3
        names = [k.name for k in keys]
        assert "Key 1" in names
        assert "Key 2" in names
        assert "Key 3" in names

    def test_list_keys_exclude_revoked(self, registry):
        """Test listing keys with revoked filtered out."""
        registry.create_key(name="Active 1", permissions=[])
        _, key2 = registry.create_key(name="Revoked", permissions=[])
        registry.create_key(name="Active 2", permissions=[])
        
        registry.revoke_key(key2.key_id)
        
        active_keys = registry.list_keys(include_revoked=False)
        
        assert len(active_keys) == 2
        names = [k.name for k in active_keys]
        assert "Active 1" in names
        assert "Active 2" in names
        assert "Revoked" not in names

    def test_list_keys_include_revoked(self, registry):
        """Test listing keys with revoked included."""
        registry.create_key(name="Active", permissions=[])
        _, key2 = registry.create_key(name="Revoked", permissions=[])
        
        registry.revoke_key(key2.key_id)
        
        all_keys = registry.list_keys(include_revoked=True)
        
        assert len(all_keys) == 2

    def test_revoke_key(self, registry):
        """Test revoking a key."""
        _, key = registry.create_key(name="Test", permissions=[])
        
        result = registry.revoke_key(key.key_id)
        
        assert result is True
        assert key.is_active is False
        assert key.revoked_at is not None

    def test_revoke_key_nonexistent(self, registry):
        """Test revoking a key that doesn't exist."""
        result = registry.revoke_key("nonexistent_id")
        
        assert result is False

    def test_revoke_key_already_revoked(self, registry):
        """Test revoking a key that's already revoked."""
        _, key = registry.create_key(name="Test", permissions=[])
        
        registry.revoke_key(key.key_id)
        first_revoked_at = key.revoked_at
        
        # Revoking again should succeed but not change timestamp
        result = registry.revoke_key(key.key_id)
        
        assert result is True
        assert key.revoked_at == first_revoked_at

    def test_revoke_admin_key_raises(self, registry_with_admin):
        """Test that revoking the admin key raises an error."""
        registry, _, admin_key = registry_with_admin
        
        with pytest.raises(ValueError) as exc_info:
            registry.revoke_key(admin_key.key_id)
        
        assert "Cannot revoke the admin key" in str(exc_info.value)

    def test_clear(self, registry):
        """Test clearing all keys."""
        registry.create_admin_key()
        registry.create_key(name="Key 1", permissions=[])
        registry.create_key(name="Key 2", permissions=[])
        
        registry.clear()
        
        assert registry._keys == {}
        assert registry._hash_to_id == {}
        assert registry._admin_key_id is None


# =============================================================================
# Registry Edge Cases
# =============================================================================


class TestAPIKeyRegistryEdgeCases:
    """Tests for edge cases and error handling."""

    def test_multiple_keys_same_name(self, registry):
        """Test that multiple keys can have the same name."""
        _, key1 = registry.create_key(name="Same Name", permissions=[])
        _, key2 = registry.create_key(name="Same Name", permissions=[])
        
        assert key1.key_id != key2.key_id
        assert key1.name == key2.name

    def test_key_with_empty_permissions(self, registry):
        """Test creating a key with no permissions."""
        _, key = registry.create_key(name="No Perms", permissions=[])
        
        assert key.permissions == []
        assert key.has_permission("anything") is False

    def test_key_with_wildcard_permission(self, registry):
        """Test creating a non-admin key with wildcard permission."""
        _, key = registry.create_key(name="Custom Admin", permissions=["*"])
        
        assert key.has_permission("email:send") is True
        assert key.has_permission("anything") is True


# =============================================================================
# Global Registry Tests
# =============================================================================


class TestGlobalRegistry:
    """Tests for global registry management functions."""

    def test_get_registry_before_init_raises(self):
        """Test that getting registry before init raises RuntimeError."""
        with pytest.raises(RuntimeError) as exc_info:
            get_api_key_registry()
        
        assert "not initialized" in str(exc_info.value)

    def test_initialize_registry(self):
        """Test initializing the global registry."""
        secret, key = initialize_api_key_registry()
        
        assert secret is not None
        assert key.name == "Admin Key"
        
        # Should be able to get registry now
        registry = get_api_key_registry()
        assert registry is not None

    def test_shutdown_registry(self):
        """Test shutting down the global registry."""
        initialize_api_key_registry()
        
        # Should work
        get_api_key_registry()
        
        shutdown_api_key_registry()
        
        # Should raise after shutdown
        with pytest.raises(RuntimeError):
            get_api_key_registry()


# =============================================================================
# Authentication Dependency Tests
# =============================================================================


class TestGetCurrentKey:
    """Tests for get_current_key dependency."""

    @pytest.mark.asyncio
    async def test_no_api_key_provided(self):
        """Test that missing API key raises 401."""
        request = MagicMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_key(request, api_key=None)
        
        assert exc_info.value.status_code == 401
        assert "API key required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_api_key(self):
        """Test that invalid API key raises 401."""
        initialize_api_key_registry()
        request = MagicMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_key(request, api_key="invalid_key")
        
        assert exc_info.value.status_code == 401
        assert "Invalid or revoked" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_valid_api_key(self):
        """Test that valid API key returns the key."""
        secret, admin_key = initialize_api_key_registry()
        request = MagicMock()
        
        key = await get_current_key(request, api_key=secret)
        
        assert key.key_id == admin_key.key_id
        assert request.state.api_key_id == admin_key.key_id
        assert request.state.api_key_name == admin_key.name

    @pytest.mark.asyncio
    async def test_revoked_key(self):
        """Test that revoked key raises 401."""
        initialize_api_key_registry()
        registry = get_api_key_registry()
        
        secret, key = registry.create_key(name="Test", permissions=[])
        registry.revoke_key(key.key_id)
        
        request = MagicMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_key(request, api_key=secret)
        
        assert exc_info.value.status_code == 401


# =============================================================================
# Permission Requirement Tests
# =============================================================================


class TestRequirePermission:
    """Tests for require_permission dependency factory."""

    @pytest.mark.asyncio
    async def test_key_with_required_permission(self):
        """Test that key with required permission succeeds."""
        initialize_api_key_registry()
        registry = get_api_key_registry()
        
        secret, _ = registry.create_key(
            name="Email Bot",
            permissions=["email:send"],
        )
        
        # Create mock request
        request = MagicMock()
        
        # First get the key
        key = await get_current_key(request, api_key=secret)
        
        # Then check permission
        check_perm = require_permission("email:send")
        result = await check_perm(key)
        
        assert result.name == "Email Bot"

    @pytest.mark.asyncio
    async def test_key_without_required_permission(self):
        """Test that key without required permission raises 403."""
        initialize_api_key_registry()
        registry = get_api_key_registry()
        
        secret, _ = registry.create_key(
            name="Email Bot",
            permissions=["email:state"],  # No email:send
        )
        
        # Create mock request
        request = MagicMock()
        
        # First get the key
        key = await get_current_key(request, api_key=secret)
        
        # Then check permission - should fail
        check_perm = require_permission("email:send")
        
        with pytest.raises(HTTPException) as exc_info:
            await check_perm(key)
        
        assert exc_info.value.status_code == 403
        assert "Permission denied" in exc_info.value.detail
        assert "email:send" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_admin_key_has_all_permissions(self):
        """Test that admin key passes any permission check."""
        secret, _ = initialize_api_key_registry()
        
        request = MagicMock()
        key = await get_current_key(request, api_key=secret)
        
        # Admin should have any permission
        for perm in ["email:send", "calendar:create", "keys:revoke", "random:perm"]:
            check_perm = require_permission(perm)
            result = await check_perm(key)
            assert result is not None

    @pytest.mark.asyncio
    async def test_wildcard_permission(self):
        """Test that resource wildcards work in permission checks."""
        initialize_api_key_registry()
        registry = get_api_key_registry()
        
        secret, _ = registry.create_key(
            name="Email Full",
            permissions=["email:*"],
        )
        
        request = MagicMock()
        key = await get_current_key(request, api_key=secret)
        
        # Should have all email permissions
        for perm in ["email:send", "email:receive", "email:state", "email:query"]:
            check_perm = require_permission(perm)
            result = await check_perm(key)
            assert result is not None
        
        # But not other permissions
        check_sms = require_permission("sms:send")
        with pytest.raises(HTTPException) as exc_info:
            await check_sms(key)
        assert exc_info.value.status_code == 403
