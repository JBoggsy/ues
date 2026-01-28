"""Unit tests for the APIKey model.

This module tests the APIKey model including:
- Instantiation with defaults and custom values
- Permission checking with exact matches and wildcards
- Key revocation
- Usage recording
- Secret validation

Test Organization:
- TestAPIKey: Basic model tests
- TestAPIKeyPermissions: Permission checking tests
- TestAPIKeyRevocation: Revocation tests
- TestAPIKeyValidation: Secret validation tests
"""

from datetime import datetime, timedelta, timezone

import pytest

from ues.models.api_key import (
    APIKey,
    generate_key_id,
    generate_key_secret,
    hash_secret,
)


# =============================================================================
# Helper Functions Tests
# =============================================================================


class TestHelperFunctions:
    """Tests for module-level helper functions."""

    def test_generate_key_id_format(self):
        """Test that generate_key_id returns properly formatted ID."""
        key_id = generate_key_id()
        
        assert key_id.startswith("ues_")
        assert len(key_id) == 20  # "ues_" + 16 hex chars
        # Verify the suffix is hex
        assert all(c in "0123456789abcdef" for c in key_id[4:])

    def test_generate_key_id_unique(self):
        """Test that generate_key_id returns unique values."""
        ids = [generate_key_id() for _ in range(100)]
        
        assert len(ids) == len(set(ids))

    def test_generate_key_secret_length(self):
        """Test that generate_key_secret returns proper length."""
        secret = generate_key_secret()
        
        # 32 bytes = 64 hex characters
        assert len(secret) == 64
        assert all(c in "0123456789abcdef" for c in secret)

    def test_generate_key_secret_unique(self):
        """Test that generate_key_secret returns unique values."""
        secrets = [generate_key_secret() for _ in range(100)]
        
        assert len(secrets) == len(set(secrets))

    def test_hash_secret_deterministic(self):
        """Test that hash_secret is deterministic."""
        secret = "test_secret"
        
        hash1 = hash_secret(secret)
        hash2 = hash_secret(secret)
        
        assert hash1 == hash2

    def test_hash_secret_different_for_different_inputs(self):
        """Test that different secrets produce different hashes."""
        hash1 = hash_secret("secret1")
        hash2 = hash_secret("secret2")
        
        assert hash1 != hash2

    def test_hash_secret_format(self):
        """Test that hash_secret returns proper SHA-256 format."""
        hashed = hash_secret("test")
        
        # SHA-256 produces 64 hex characters
        assert len(hashed) == 64
        assert all(c in "0123456789abcdef" for c in hashed)


# =============================================================================
# APIKey Model Tests
# =============================================================================


class TestAPIKey:
    """Tests for APIKey model instantiation and basic properties."""

    def test_instantiation_with_required_fields(self):
        """Test that APIKey can be instantiated with required fields only."""
        key = APIKey(
            key_hash="test_hash",
            name="Test Key",
        )
        
        assert key.key_hash == "test_hash"
        assert key.name == "Test Key"
        assert key.key_id.startswith("ues_")
        assert key.permissions == []
        assert key.created_at is not None
        assert key.created_by is None
        assert key.last_used_at is None
        assert key.revoked_at is None

    def test_instantiation_with_all_fields(self):
        """Test that APIKey can be instantiated with all fields."""
        created_at = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        key = APIKey(
            key_id="ues_custom_id123",
            key_hash="custom_hash",
            name="Custom Key",
            permissions=["email:*", "sms:state"],
            created_at=created_at,
            created_by="ues_parent_key",
            last_used_at=None,
            revoked_at=None,
        )
        
        assert key.key_id == "ues_custom_id123"
        assert key.key_hash == "custom_hash"
        assert key.name == "Custom Key"
        assert key.permissions == ["email:*", "sms:state"]
        assert key.created_at == created_at
        assert key.created_by == "ues_parent_key"

    def test_is_active_when_not_revoked(self):
        """Test that is_active returns True when key is not revoked."""
        key = APIKey(
            key_hash="hash",
            name="Test",
        )
        
        assert key.is_active is True

    def test_is_active_when_revoked(self):
        """Test that is_active returns False when key is revoked."""
        key = APIKey(
            key_hash="hash",
            name="Test",
            revoked_at=datetime.now(timezone.utc),
        )
        
        assert key.is_active is False

    def test_unique_key_ids(self):
        """Test that each APIKey gets a unique ID."""
        keys = [
            APIKey(key_hash="hash", name=f"Key {i}")
            for i in range(10)
        ]
        
        key_ids = [k.key_id for k in keys]
        assert len(key_ids) == len(set(key_ids))


# =============================================================================
# Permission Tests
# =============================================================================


class TestAPIKeyPermissions:
    """Tests for APIKey.has_permission() method."""

    def test_exact_match(self):
        """Test that exact permission matches work."""
        key = APIKey(
            key_hash="hash",
            name="Test",
            permissions=["email:send", "sms:state"],
        )
        
        assert key.has_permission("email:send") is True
        assert key.has_permission("sms:state") is True
        assert key.has_permission("email:state") is False
        assert key.has_permission("calendar:create") is False

    def test_admin_wildcard_grants_everything(self):
        """Test that '*' permission grants access to everything."""
        key = APIKey(
            key_hash="hash",
            name="Admin",
            permissions=["*"],
        )
        
        assert key.has_permission("email:send") is True
        assert key.has_permission("sms:state") is True
        assert key.has_permission("calendar:create") is True
        assert key.has_permission("keys:create") is True
        assert key.has_permission("any:random:permission") is True

    def test_resource_wildcard(self):
        """Test that resource wildcards work (e.g., 'email:*')."""
        key = APIKey(
            key_hash="hash",
            name="Email Bot",
            permissions=["email:*"],
        )
        
        assert key.has_permission("email:send") is True
        assert key.has_permission("email:receive") is True
        assert key.has_permission("email:state") is True
        assert key.has_permission("email:query") is True
        assert key.has_permission("sms:send") is False
        assert key.has_permission("calendar:create") is False

    def test_sub_resource_wildcard(self):
        """Test that sub-resource wildcards work (e.g., 'calendar:calendars:*')."""
        key = APIKey(
            key_hash="hash",
            name="Calendar Manager",
            permissions=["calendar:calendars:*"],
        )
        
        assert key.has_permission("calendar:calendars:create") is True
        assert key.has_permission("calendar:calendars:delete") is True
        assert key.has_permission("calendar:calendars:list") is True
        # calendar:state doesn't match calendar:calendars:*
        assert key.has_permission("calendar:state") is False
        assert key.has_permission("calendar:create") is False

    def test_resource_wildcard_covers_sub_resources(self):
        """Test that 'calendar:*' covers sub-resources like 'calendar:calendars:create'."""
        key = APIKey(
            key_hash="hash",
            name="Calendar Full Access",
            permissions=["calendar:*"],
        )
        
        assert key.has_permission("calendar:state") is True
        assert key.has_permission("calendar:create") is True
        assert key.has_permission("calendar:calendars:create") is True
        assert key.has_permission("calendar:calendars:list") is True

    def test_multiple_permissions(self):
        """Test keys with multiple permission types."""
        key = APIKey(
            key_hash="hash",
            name="Multi",
            permissions=["email:*", "sms:state", "sms:query", "calendar:calendars:*"],
        )
        
        # email:* should match all email permissions
        assert key.has_permission("email:send") is True
        assert key.has_permission("email:state") is True
        
        # Exact sms matches
        assert key.has_permission("sms:state") is True
        assert key.has_permission("sms:query") is True
        assert key.has_permission("sms:send") is False
        
        # calendar:calendars:* matches
        assert key.has_permission("calendar:calendars:create") is True
        assert key.has_permission("calendar:state") is False

    def test_empty_permissions(self):
        """Test key with no permissions."""
        key = APIKey(
            key_hash="hash",
            name="Empty",
            permissions=[],
        )
        
        assert key.has_permission("email:send") is False
        assert key.has_permission("any:permission") is False

    def test_permission_is_case_sensitive(self):
        """Test that permission matching is case-sensitive."""
        key = APIKey(
            key_hash="hash",
            name="Test",
            permissions=["email:send"],
        )
        
        assert key.has_permission("email:send") is True
        assert key.has_permission("EMAIL:send") is False
        assert key.has_permission("email:SEND") is False
        assert key.has_permission("Email:Send") is False


# =============================================================================
# Revocation Tests
# =============================================================================


class TestAPIKeyRevocation:
    """Tests for APIKey.revoke() method."""

    def test_revoke_sets_revoked_at(self):
        """Test that revoke() sets the revoked_at timestamp."""
        key = APIKey(
            key_hash="hash",
            name="Test",
        )
        
        assert key.revoked_at is None
        
        key.revoke()
        
        assert key.revoked_at is not None
        assert isinstance(key.revoked_at, datetime)

    def test_revoke_makes_key_inactive(self):
        """Test that revoking a key makes is_active False."""
        key = APIKey(
            key_hash="hash",
            name="Test",
        )
        
        assert key.is_active is True
        
        key.revoke()
        
        assert key.is_active is False

    def test_revoke_idempotent(self):
        """Test that calling revoke() multiple times doesn't change timestamp."""
        key = APIKey(
            key_hash="hash",
            name="Test",
        )
        
        key.revoke()
        first_revoked_at = key.revoked_at
        
        # Small delay to ensure timestamp would change if updated
        import time
        time.sleep(0.01)
        
        key.revoke()
        
        # Should still be the first timestamp
        assert key.revoked_at == first_revoked_at


# =============================================================================
# Usage Recording Tests
# =============================================================================


class TestAPIKeyUsageRecording:
    """Tests for APIKey.record_usage() method."""

    def test_record_usage_sets_last_used_at(self):
        """Test that record_usage() sets last_used_at."""
        key = APIKey(
            key_hash="hash",
            name="Test",
        )
        
        assert key.last_used_at is None
        
        key.record_usage()
        
        assert key.last_used_at is not None
        assert isinstance(key.last_used_at, datetime)

    def test_record_usage_updates_timestamp(self):
        """Test that record_usage() updates the timestamp."""
        key = APIKey(
            key_hash="hash",
            name="Test",
        )
        
        key.record_usage()
        first_usage = key.last_used_at
        
        # Small delay
        import time
        time.sleep(0.01)
        
        key.record_usage()
        
        assert key.last_used_at > first_usage


# =============================================================================
# Secret Validation Tests
# =============================================================================


class TestAPIKeyValidation:
    """Tests for APIKey.validate_secret() method."""

    def test_validate_correct_secret(self):
        """Test that validate_secret returns True for correct secret."""
        secret = "my_test_secret"
        key = APIKey(
            key_hash=hash_secret(secret),
            name="Test",
        )
        
        assert key.validate_secret(secret) is True

    def test_validate_incorrect_secret(self):
        """Test that validate_secret returns False for wrong secret."""
        secret = "my_test_secret"
        key = APIKey(
            key_hash=hash_secret(secret),
            name="Test",
        )
        
        assert key.validate_secret("wrong_secret") is False
        assert key.validate_secret("") is False
        assert key.validate_secret(secret + "x") is False

    def test_validate_empty_secret(self):
        """Test validation with empty string secret."""
        key = APIKey(
            key_hash=hash_secret(""),
            name="Test",
        )
        
        assert key.validate_secret("") is True
        assert key.validate_secret("anything") is False

    def test_validate_uses_constant_time_comparison(self):
        """Test that validation uses constant-time comparison.
        
        This is a basic sanity check - we can't really test timing in unit tests,
        but we can verify the code path works correctly.
        """
        secret = generate_key_secret()
        key = APIKey(
            key_hash=hash_secret(secret),
            name="Test",
        )
        
        # Just verify it works with generated secrets
        assert key.validate_secret(secret) is True
        
        # And wrong secrets fail
        wrong_secret = generate_key_secret()
        assert key.validate_secret(wrong_secret) is False
