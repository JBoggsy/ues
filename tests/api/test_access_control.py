"""Tests for API access control models and KeyRegistry.

This module tests the core access control functionality including:
- AccessLevel enum
- AccessContext model
- KeyRegistry CRUD operations
- Endpoint permission mapping
"""

from datetime import datetime, timezone

import pytest

from api.access_control import (
    AccessContext,
    AccessLevel,
    KeyRegistry,
    PUBLIC_ROUTES,
    PROCTOR_ONLY_ROUTES,
    USER_ALLOWED_ROUTES,
    get_route_permission,
    is_access_allowed,
)


# =============================================================================
# AccessLevel Tests
# =============================================================================


class TestAccessLevel:
    """Tests for the AccessLevel enum."""

    def test_proctor_value(self):
        """PROCTOR level should have string value 'proctor'."""
        assert AccessLevel.PROCTOR.value == "proctor"

    def test_user_value(self):
        """USER level should have string value 'user'."""
        assert AccessLevel.USER.value == "user"

    def test_enum_is_string_subclass(self):
        """AccessLevel should be usable as a string."""
        assert isinstance(AccessLevel.PROCTOR, str)
        assert AccessLevel.USER == "user"


# =============================================================================
# AccessContext Tests
# =============================================================================


class TestAccessContext:
    """Tests for the AccessContext model."""

    def test_minimal_context(self):
        """Context can be created with just key and level."""
        ctx = AccessContext(api_key="test_key", level=AccessLevel.USER)
        assert ctx.api_key == "test_key"
        assert ctx.level == AccessLevel.USER
        assert ctx.agent_id is None
        assert ctx.assessment_id is None
        assert ctx.metadata is None
        assert ctx.created_at is not None

    def test_full_context(self):
        """Context can be created with all fields."""
        now = datetime.now(timezone.utc)
        ctx = AccessContext(
            api_key="ues_proctor_abc123",
            level=AccessLevel.PROCTOR,
            agent_id="green-agent",
            assessment_id="assessment-001",
            created_at=now,
            metadata={"extra": "data"},
        )
        assert ctx.api_key == "ues_proctor_abc123"
        assert ctx.level == AccessLevel.PROCTOR
        assert ctx.agent_id == "green-agent"
        assert ctx.assessment_id == "assessment-001"
        assert ctx.created_at == now
        assert ctx.metadata == {"extra": "data"}

    def test_created_at_defaults_to_now(self):
        """created_at should default to current UTC time."""
        before = datetime.now(timezone.utc)
        ctx = AccessContext(api_key="key", level=AccessLevel.USER)
        after = datetime.now(timezone.utc)
        assert before <= ctx.created_at <= after

    def test_context_serialization(self):
        """Context should be JSON serializable."""
        ctx = AccessContext(
            api_key="key",
            level=AccessLevel.USER,
            agent_id="test",
        )
        data = ctx.model_dump()
        assert data["api_key"] == "key"
        assert data["level"] == "user"
        assert data["agent_id"] == "test"


# =============================================================================
# KeyRegistry Tests
# =============================================================================


class TestKeyRegistry:
    """Tests for the KeyRegistry class."""

    @pytest.fixture
    def registry(self):
        """Create a fresh KeyRegistry for each test."""
        return KeyRegistry()

    def test_generate_key_returns_string(self, registry):
        """generate_key should return a string key."""
        key = registry.generate_key(level=AccessLevel.USER)
        assert isinstance(key, str)
        assert len(key) > 0

    def test_generated_key_format(self, registry):
        """Generated keys should follow the ues_{level}_{token} format."""
        user_key = registry.generate_key(level=AccessLevel.USER)
        proctor_key = registry.generate_key(level=AccessLevel.PROCTOR)
        
        assert user_key.startswith("ues_user_")
        assert proctor_key.startswith("ues_proctor_")

    def test_generated_keys_are_unique(self, registry):
        """Each generated key should be unique."""
        keys = [registry.generate_key(level=AccessLevel.USER) for _ in range(100)]
        assert len(set(keys)) == 100

    def test_validate_key_returns_context(self, registry):
        """validate_key should return the context for a valid key."""
        key = registry.generate_key(
            level=AccessLevel.USER,
            agent_id="test-agent",
        )
        ctx = registry.validate_key(key)
        assert ctx is not None
        assert ctx.api_key == key
        assert ctx.level == AccessLevel.USER
        assert ctx.agent_id == "test-agent"

    def test_validate_key_returns_none_for_invalid(self, registry):
        """validate_key should return None for invalid keys."""
        assert registry.validate_key("invalid_key") is None
        assert registry.validate_key("ues_user_fake") is None
        assert registry.validate_key("") is None

    def test_get_context_alias(self, registry):
        """get_context should be an alias for validate_key."""
        key = registry.generate_key(level=AccessLevel.PROCTOR)
        assert registry.get_context(key) == registry.validate_key(key)

    def test_invalidate_key_removes_key(self, registry):
        """invalidate_key should remove the key from the registry."""
        key = registry.generate_key(level=AccessLevel.USER)
        assert registry.validate_key(key) is not None
        
        result = registry.invalidate_key(key)
        
        assert result is True
        assert registry.validate_key(key) is None

    def test_invalidate_key_returns_false_for_unknown(self, registry):
        """invalidate_key should return False for unknown keys."""
        assert registry.invalidate_key("unknown_key") is False

    def test_invalidate_keys_by_assessment(self, registry):
        """invalidate_keys_by_assessment should remove all keys for an assessment."""
        # Create keys for different assessments
        key1 = registry.generate_key(level=AccessLevel.PROCTOR, assessment_id="assess-1")
        key2 = registry.generate_key(level=AccessLevel.USER, assessment_id="assess-1")
        key3 = registry.generate_key(level=AccessLevel.USER, assessment_id="assess-2")
        
        # Invalidate assessment-1 keys
        count = registry.invalidate_keys_by_assessment("assess-1")
        
        assert count == 2
        assert registry.validate_key(key1) is None
        assert registry.validate_key(key2) is None
        assert registry.validate_key(key3) is not None  # assess-2 key still valid

    def test_invalidate_keys_by_assessment_returns_zero_for_unknown(self, registry):
        """invalidate_keys_by_assessment should return 0 for unknown assessment."""
        assert registry.invalidate_keys_by_assessment("unknown") == 0

    def test_list_keys_returns_all(self, registry):
        """list_keys with no filter should return all keys."""
        registry.generate_key(level=AccessLevel.USER)
        registry.generate_key(level=AccessLevel.PROCTOR)
        registry.generate_key(level=AccessLevel.USER)
        
        keys = registry.list_keys()
        assert len(keys) == 3

    def test_list_keys_filtered_by_assessment(self, registry):
        """list_keys should filter by assessment_id when provided."""
        registry.generate_key(level=AccessLevel.USER, assessment_id="assess-1")
        registry.generate_key(level=AccessLevel.USER, assessment_id="assess-1")
        registry.generate_key(level=AccessLevel.USER, assessment_id="assess-2")
        
        assess1_keys = registry.list_keys(assessment_id="assess-1")
        assess2_keys = registry.list_keys(assessment_id="assess-2")
        
        assert len(assess1_keys) == 2
        assert len(assess2_keys) == 1

    def test_clear_removes_all_keys(self, registry):
        """clear should remove all keys from the registry."""
        registry.generate_key(level=AccessLevel.USER)
        registry.generate_key(level=AccessLevel.PROCTOR)
        
        count = registry.clear()
        
        assert count == 2
        assert len(registry.list_keys()) == 0

    def test_metadata_is_preserved(self, registry):
        """Metadata should be preserved in the context."""
        key = registry.generate_key(
            level=AccessLevel.USER,
            metadata={"scenario": "email-triage", "version": 1},
        )
        ctx = registry.validate_key(key)
        assert ctx.metadata == {"scenario": "email-triage", "version": 1}


# =============================================================================
# Route Permission Tests
# =============================================================================


class TestRoutePermissions:
    """Tests for endpoint permission mapping."""

    def test_public_routes_are_defined(self):
        """PUBLIC_ROUTES should contain expected routes."""
        assert "GET /" in PUBLIC_ROUTES
        assert "GET /health" in PUBLIC_ROUTES
        assert "GET /docs" in PUBLIC_ROUTES

    def test_proctor_routes_are_defined(self):
        """PROCTOR_ONLY_ROUTES should contain time/simulation control."""
        assert "POST /simulator/time/advance" in PROCTOR_ONLY_ROUTES
        assert "POST /simulation/reset" in PROCTOR_ONLY_ROUTES
        assert "POST /email/receive" in PROCTOR_ONLY_ROUTES

    def test_user_routes_are_defined(self):
        """USER_ALLOWED_ROUTES should contain state queries and user actions."""
        assert "GET /email/state" in USER_ALLOWED_ROUTES
        assert "POST /email/send" in USER_ALLOWED_ROUTES
        assert "GET /simulator/time" in USER_ALLOWED_ROUTES


class TestGetRoutePermission:
    """Tests for the get_route_permission function."""

    def test_public_route_returns_none(self):
        """Public routes should return None (no auth required)."""
        assert get_route_permission("GET", "/") is None
        assert get_route_permission("GET", "/health") is None
        assert get_route_permission("GET", "/docs") is None

    def test_user_route_returns_user_level(self):
        """User-allowed routes should return USER level."""
        assert get_route_permission("GET", "/email/state") == AccessLevel.USER
        assert get_route_permission("POST", "/email/send") == AccessLevel.USER
        assert get_route_permission("GET", "/simulator/time") == AccessLevel.USER

    def test_proctor_route_returns_proctor_level(self):
        """Proctor-only routes should return PROCTOR level."""
        assert get_route_permission("POST", "/simulator/time/advance") == AccessLevel.PROCTOR
        assert get_route_permission("POST", "/simulation/reset") == AccessLevel.PROCTOR
        assert get_route_permission("POST", "/email/receive") == AccessLevel.PROCTOR

    def test_dynamic_routes_handled(self):
        """Routes with path parameters should be handled correctly."""
        # /simulation/release/{hold_id} is proctor-only
        assert get_route_permission("POST", "/simulation/release/abc123") == AccessLevel.PROCTOR
        # /events/{event_id} DELETE is proctor-only
        assert get_route_permission("DELETE", "/events/event-001") == AccessLevel.PROCTOR

    def test_unknown_routes_default_to_proctor(self):
        """Unknown routes should default to proctor-only (fail-safe)."""
        assert get_route_permission("POST", "/unknown/endpoint") == AccessLevel.PROCTOR
        assert get_route_permission("GET", "/some/random/path") == AccessLevel.PROCTOR


class TestIsAccessAllowed:
    """Tests for the is_access_allowed function."""

    def test_public_route_allows_any_level(self):
        """Public routes (None required) should allow any access level."""
        assert is_access_allowed(None, AccessLevel.USER) is True
        assert is_access_allowed(None, AccessLevel.PROCTOR) is True

    def test_proctor_can_access_everything(self):
        """Proctor level should have access to all routes."""
        assert is_access_allowed(AccessLevel.USER, AccessLevel.PROCTOR) is True
        assert is_access_allowed(AccessLevel.PROCTOR, AccessLevel.PROCTOR) is True

    def test_user_can_access_user_routes(self):
        """User level should have access to user-allowed routes."""
        assert is_access_allowed(AccessLevel.USER, AccessLevel.USER) is True

    def test_user_cannot_access_proctor_routes(self):
        """User level should NOT have access to proctor-only routes."""
        assert is_access_allowed(AccessLevel.PROCTOR, AccessLevel.USER) is False


# =============================================================================
# Integration Tests
# =============================================================================


class TestKeyRegistryIntegration:
    """Integration tests for typical usage patterns."""

    def test_assessment_lifecycle(self):
        """Test typical assessment key lifecycle: create, use, cleanup."""
        registry = KeyRegistry()
        assessment_id = "integration-test-001"
        
        # Green agent creates keys at assessment start
        proctor_key = registry.generate_key(
            level=AccessLevel.PROCTOR,
            agent_id="green-agent",
            assessment_id=assessment_id,
        )
        user_key = registry.generate_key(
            level=AccessLevel.USER,
            agent_id="purple-agent",
            assessment_id=assessment_id,
        )
        
        # Both keys are valid
        assert registry.validate_key(proctor_key) is not None
        assert registry.validate_key(user_key) is not None
        
        # Simulate Purple Agent checking permissions
        user_ctx = registry.validate_key(user_key)
        assert user_ctx.level == AccessLevel.USER
        
        # Can access user routes
        assert is_access_allowed(
            get_route_permission("POST", "/email/send"),
            user_ctx.level
        )
        
        # Cannot access proctor routes
        assert not is_access_allowed(
            get_route_permission("POST", "/simulator/time/advance"),
            user_ctx.level
        )
        
        # Green agent cleans up at assessment end
        count = registry.invalidate_keys_by_assessment(assessment_id)
        assert count == 2
        
        # Both keys are now invalid
        assert registry.validate_key(proctor_key) is None
        assert registry.validate_key(user_key) is None
