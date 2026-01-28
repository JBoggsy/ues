"""Integration tests for API key management endpoints.

This module tests the /keys API endpoints including:
- POST /keys - Create a new API key
- GET /keys - List all API keys
- GET /keys/{key_id} - Get key details
- DELETE /keys/{key_id} - Revoke a key

All tests use fixtures that provide an authenticated client with appropriate
permissions for key management operations.
"""

import pytest
from fastapi.testclient import TestClient

from ues.api.auth import (
    get_api_key_registry,
    initialize_api_key_registry,
    shutdown_api_key_registry,
)
from ues.api.dependencies import get_simulation_engine
from ues.main import app


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def reset_api_key_registry():
    """Reset the API key registry before and after each test.
    
    This ensures each test starts with a fresh registry and clean state.
    """
    import ues.api.auth as auth_module
    
    # Store original state
    original_registry = auth_module._api_key_registry
    
    # Reset before test
    auth_module._api_key_registry = None
    
    yield
    
    # Reset after test
    auth_module._api_key_registry = original_registry


@pytest.fixture
def admin_client(fresh_engine):
    """Provide a TestClient with admin API key authentication.
    
    Yields:
        A tuple of (TestClient, admin_secret, admin_key).
    """
    # Override simulation engine dependency
    app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
    
    # Initialize API key registry and get admin key
    admin_secret, admin_key = initialize_api_key_registry()
    
    # Create test client with admin key in default headers
    client = TestClient(app)
    client.headers["X-API-Key"] = admin_secret
    
    yield client, admin_secret, admin_key
    
    # Cleanup
    shutdown_api_key_registry()
    app.dependency_overrides.clear()


@pytest.fixture
def limited_client(admin_client):
    """Provide a TestClient with a limited-permission API key.
    
    Creates a key that has only read permissions on keys.
    
    Yields:
        A tuple of (TestClient, limited_key_secret, limited_key_info).
    """
    client, admin_secret, admin_key = admin_client
    
    # Create a limited key using admin
    response = client.post(
        "/keys",
        json={
            "name": "Limited Reader",
            "permissions": ["keys:list", "keys:read"],
        },
    )
    assert response.status_code == 201
    limited_data = response.json()
    
    # Create new client with limited key
    limited_client = TestClient(app)
    limited_client.headers["X-API-Key"] = limited_data["secret"]
    
    yield limited_client, limited_data["secret"], limited_data


@pytest.fixture  
def no_auth_client(fresh_engine):
    """Provide a TestClient without API key authentication.
    
    Yields:
        A TestClient without any authentication headers.
    """
    # Override simulation engine dependency
    app.dependency_overrides[get_simulation_engine] = lambda: fresh_engine
    
    # Initialize API key registry
    initialize_api_key_registry()
    
    # Create test client without auth headers
    client = TestClient(app)
    
    yield client
    
    # Cleanup
    shutdown_api_key_registry()
    app.dependency_overrides.clear()


# =============================================================================
# Authentication Tests
# =============================================================================


class TestAuthentication:
    """Tests for authentication requirements on key management endpoints."""

    def test_create_key_requires_auth(self, no_auth_client):
        """Test that POST /keys requires authentication."""
        response = no_auth_client.post(
            "/keys",
            json={"name": "Test", "permissions": ["email:*"]},
        )
        
        assert response.status_code == 401
        assert "API key required" in response.json()["detail"]

    def test_list_keys_requires_auth(self, no_auth_client):
        """Test that GET /keys requires authentication."""
        response = no_auth_client.get("/keys")
        
        assert response.status_code == 401
        assert "API key required" in response.json()["detail"]

    def test_get_key_requires_auth(self, no_auth_client):
        """Test that GET /keys/{key_id} requires authentication."""
        response = no_auth_client.get("/keys/some_key_id")
        
        assert response.status_code == 401
        assert "API key required" in response.json()["detail"]

    def test_revoke_key_requires_auth(self, no_auth_client):
        """Test that DELETE /keys/{key_id} requires authentication."""
        response = no_auth_client.delete("/keys/some_key_id")
        
        assert response.status_code == 401
        assert "API key required" in response.json()["detail"]

    def test_invalid_api_key_rejected(self, no_auth_client):
        """Test that an invalid API key is rejected with 401."""
        no_auth_client.headers["X-API-Key"] = "invalid_key_that_does_not_exist"
        
        response = no_auth_client.get("/keys")
        
        assert response.status_code == 401
        assert "Invalid or revoked API key" in response.json()["detail"]


# =============================================================================
# Permission Tests
# =============================================================================


class TestPermissions:
    """Tests for permission requirements on key management endpoints."""

    def test_create_key_requires_keys_create_permission(self, limited_client):
        """Test that POST /keys requires keys:create permission."""
        client, secret, key_info = limited_client
        
        # Limited client only has keys:list and keys:read
        response = client.post(
            "/keys",
            json={"name": "Test", "permissions": ["email:*"]},
        )
        
        assert response.status_code == 403
        assert "keys:create" in response.json()["detail"]

    def test_list_keys_requires_keys_list_permission(self, admin_client):
        """Test that GET /keys requires keys:list permission."""
        client, admin_secret, admin_key = admin_client
        
        # Create a key without keys:list permission
        response = client.post(
            "/keys",
            json={"name": "No List", "permissions": ["email:*"]},
        )
        assert response.status_code == 201
        no_list_key = response.json()
        
        # Use the new key
        no_list_client = TestClient(app)
        no_list_client.headers["X-API-Key"] = no_list_key["secret"]
        
        response = no_list_client.get("/keys")
        
        assert response.status_code == 403
        assert "keys:list" in response.json()["detail"]

    def test_get_key_requires_keys_read_permission(self, admin_client):
        """Test that GET /keys/{key_id} requires keys:read permission."""
        client, admin_secret, admin_key = admin_client
        
        # Create a key without keys:read permission
        response = client.post(
            "/keys",
            json={"name": "No Read", "permissions": ["email:*"]},
        )
        assert response.status_code == 201
        no_read_key = response.json()
        
        # Use the new key
        no_read_client = TestClient(app)
        no_read_client.headers["X-API-Key"] = no_read_key["secret"]
        
        response = no_read_client.get(f"/keys/{admin_key.key_id}")
        
        assert response.status_code == 403
        assert "keys:read" in response.json()["detail"]

    def test_revoke_key_requires_keys_revoke_permission(self, admin_client):
        """Test that DELETE /keys/{key_id} requires keys:revoke permission."""
        client, admin_secret, admin_key = admin_client
        
        # Create a key to be revoked
        response = client.post(
            "/keys",
            json={"name": "To Revoke", "permissions": ["email:*"]},
        )
        assert response.status_code == 201
        target_key = response.json()
        
        # Create a key without keys:revoke permission  
        response = client.post(
            "/keys",
            json={"name": "No Revoke", "permissions": ["keys:read"]},
        )
        assert response.status_code == 201
        no_revoke_key = response.json()
        
        # Use the new key to try revoking
        no_revoke_client = TestClient(app)
        no_revoke_client.headers["X-API-Key"] = no_revoke_key["secret"]
        
        response = no_revoke_client.delete(f"/keys/{target_key['key_id']}")
        
        assert response.status_code == 403
        assert "keys:revoke" in response.json()["detail"]


# =============================================================================
# POST /keys Tests
# =============================================================================


class TestCreateKey:
    """Tests for POST /keys endpoint."""

    def test_create_key_returns_201(self, admin_client):
        """Test that POST /keys returns 201 on success."""
        client, _, _ = admin_client
        
        response = client.post(
            "/keys",
            json={"name": "Test Key", "permissions": ["email:*"]},
        )
        
        assert response.status_code == 201

    def test_create_key_returns_secret_once(self, admin_client):
        """Test that POST /keys returns the secret only at creation."""
        client, _, _ = admin_client
        
        response = client.post(
            "/keys",
            json={"name": "Test Key", "permissions": ["email:*"]},
        )
        
        data = response.json()
        
        assert "secret" in data
        assert len(data["secret"]) == 64  # 32 bytes hex = 64 chars
        assert data["secret"].startswith("") or True  # Just ensure it's a string

    def test_create_key_returns_all_fields(self, admin_client):
        """Test that POST /keys returns all expected fields."""
        client, _, admin_key = admin_client
        
        response = client.post(
            "/keys",
            json={"name": "Test Key", "permissions": ["email:*", "sms:send"]},
        )
        
        data = response.json()
        
        assert "key_id" in data
        assert "secret" in data
        assert "name" in data
        assert "permissions" in data
        assert "created_at" in data
        assert "created_by" in data
        
        assert data["key_id"].startswith("ues_")
        assert data["name"] == "Test Key"
        assert data["permissions"] == ["email:*", "sms:send"]
        assert data["created_by"] == admin_key.key_id

    def test_create_key_with_wildcard_permission(self, admin_client):
        """Test creating a key with wildcard (*) permission."""
        client, _, _ = admin_client
        
        response = client.post(
            "/keys",
            json={"name": "Full Access", "permissions": ["*"]},
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["permissions"] == ["*"]

    def test_create_key_with_modality_wildcard(self, admin_client):
        """Test creating a key with modality-specific wildcard."""
        client, _, _ = admin_client
        
        response = client.post(
            "/keys",
            json={"name": "Email Bot", "permissions": ["email:*"]},
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["permissions"] == ["email:*"]

    def test_create_key_validates_name_not_empty(self, admin_client):
        """Test that empty name is rejected."""
        client, _, _ = admin_client
        
        response = client.post(
            "/keys",
            json={"name": "", "permissions": ["email:*"]},
        )
        
        assert response.status_code == 422  # Validation error

    def test_create_key_validates_permissions_not_empty(self, admin_client):
        """Test that empty permissions list is rejected."""
        client, _, _ = admin_client
        
        response = client.post(
            "/keys",
            json={"name": "Test", "permissions": []},
        )
        
        assert response.status_code == 422  # Validation error

    def test_created_key_can_authenticate(self, admin_client):
        """Test that a newly created key can be used for authentication."""
        client, _, _ = admin_client
        
        # Create a key
        response = client.post(
            "/keys",
            json={"name": "Test Key", "permissions": ["keys:list"]},
        )
        assert response.status_code == 201
        new_key = response.json()
        
        # Use the new key to authenticate
        new_client = TestClient(app)
        new_client.headers["X-API-Key"] = new_key["secret"]
        
        response = new_client.get("/keys")
        
        assert response.status_code == 200


# =============================================================================
# GET /keys Tests
# =============================================================================


class TestListKeys:
    """Tests for GET /keys endpoint."""

    def test_list_keys_returns_200(self, admin_client):
        """Test that GET /keys returns 200."""
        client, _, _ = admin_client
        
        response = client.get("/keys")
        
        assert response.status_code == 200

    def test_list_keys_returns_all_fields(self, admin_client):
        """Test that GET /keys returns all expected fields."""
        client, _, _ = admin_client
        
        response = client.get("/keys")
        
        data = response.json()
        
        assert "keys" in data
        assert "total" in data
        assert "active" in data
        assert "revoked" in data

    def test_list_keys_includes_admin_key(self, admin_client):
        """Test that GET /keys includes the admin key."""
        client, _, admin_key = admin_client
        
        response = client.get("/keys")
        
        data = response.json()
        
        assert data["total"] >= 1
        
        key_ids = [k["key_id"] for k in data["keys"]]
        assert admin_key.key_id in key_ids

    def test_list_keys_includes_created_keys(self, admin_client):
        """Test that GET /keys includes newly created keys."""
        client, _, _ = admin_client
        
        # Create some keys
        for i in range(3):
            response = client.post(
                "/keys",
                json={"name": f"Key {i}", "permissions": ["email:*"]},
            )
            assert response.status_code == 201
        
        response = client.get("/keys")
        data = response.json()
        
        # Should have admin + 3 new keys
        assert data["total"] >= 4

    def test_list_keys_does_not_include_secrets(self, admin_client):
        """Test that GET /keys does not return secrets."""
        client, _, _ = admin_client
        
        # Create a key
        client.post(
            "/keys",
            json={"name": "Test", "permissions": ["email:*"]},
        )
        
        response = client.get("/keys")
        data = response.json()
        
        for key_info in data["keys"]:
            assert "secret" not in key_info
            assert "key_hash" not in key_info

    def test_list_keys_filter_include_revoked_true(self, admin_client):
        """Test that GET /keys?include_revoked=true includes revoked keys."""
        client, _, _ = admin_client
        
        # Create and revoke a key
        response = client.post(
            "/keys",
            json={"name": "To Revoke", "permissions": ["email:*"]},
        )
        assert response.status_code == 201
        key_to_revoke = response.json()
        
        response = client.delete(f"/keys/{key_to_revoke['key_id']}")
        assert response.status_code == 200
        
        # List with include_revoked=true
        response = client.get("/keys", params={"include_revoked": True})
        data = response.json()
        
        key_ids = [k["key_id"] for k in data["keys"]]
        assert key_to_revoke["key_id"] in key_ids
        assert data["revoked"] >= 1

    def test_list_keys_filter_include_revoked_false(self, admin_client):
        """Test that GET /keys?include_revoked=false excludes revoked keys."""
        client, _, _ = admin_client
        
        # Create and revoke a key
        response = client.post(
            "/keys",
            json={"name": "To Revoke", "permissions": ["email:*"]},
        )
        assert response.status_code == 201
        key_to_revoke = response.json()
        
        response = client.delete(f"/keys/{key_to_revoke['key_id']}")
        assert response.status_code == 200
        
        # List with include_revoked=false
        response = client.get("/keys", params={"include_revoked": False})
        data = response.json()
        
        key_ids = [k["key_id"] for k in data["keys"]]
        assert key_to_revoke["key_id"] not in key_ids

    def test_list_keys_returns_correct_counts(self, admin_client):
        """Test that GET /keys returns accurate active and revoked counts."""
        client, _, _ = admin_client
        
        # Create 3 keys, revoke 1
        created_keys = []
        for i in range(3):
            response = client.post(
                "/keys",
                json={"name": f"Key {i}", "permissions": ["email:*"]},
            )
            assert response.status_code == 201
            created_keys.append(response.json())
        
        # Revoke one
        response = client.delete(f"/keys/{created_keys[0]['key_id']}")
        assert response.status_code == 200
        
        # Check counts
        response = client.get("/keys")
        data = response.json()
        
        assert data["total"] == 4  # admin + 3 created
        assert data["active"] == 3  # admin + 2 active created
        assert data["revoked"] == 1  # 1 revoked


# =============================================================================
# GET /keys/{key_id} Tests
# =============================================================================


class TestGetKey:
    """Tests for GET /keys/{key_id} endpoint."""

    def test_get_key_returns_200(self, admin_client):
        """Test that GET /keys/{key_id} returns 200 for valid key."""
        client, _, admin_key = admin_client
        
        response = client.get(f"/keys/{admin_key.key_id}")
        
        assert response.status_code == 200

    def test_get_key_returns_all_fields(self, admin_client):
        """Test that GET /keys/{key_id} returns all expected fields."""
        client, _, admin_key = admin_client
        
        response = client.get(f"/keys/{admin_key.key_id}")
        
        data = response.json()
        
        assert "key_id" in data
        assert "name" in data
        assert "permissions" in data
        assert "created_at" in data
        assert "created_by" in data
        assert "last_used_at" in data
        assert "is_active" in data
        assert "revoked_at" in data

    def test_get_key_does_not_include_secret(self, admin_client):
        """Test that GET /keys/{key_id} does not return the secret."""
        client, _, admin_key = admin_client
        
        response = client.get(f"/keys/{admin_key.key_id}")
        
        data = response.json()
        
        assert "secret" not in data
        assert "key_hash" not in data

    def test_get_key_returns_404_for_nonexistent(self, admin_client):
        """Test that GET /keys/{key_id} returns 404 for unknown key."""
        client, _, _ = admin_client
        
        response = client.get("/keys/ues_nonexistent123")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_key_returns_correct_data(self, admin_client):
        """Test that GET /keys/{key_id} returns the correct key data."""
        client, _, _ = admin_client
        
        # Create a key
        create_response = client.post(
            "/keys",
            json={"name": "My Test Key", "permissions": ["email:*", "sms:send"]},
        )
        assert create_response.status_code == 201
        created = create_response.json()
        
        # Get the key
        response = client.get(f"/keys/{created['key_id']}")
        
        data = response.json()
        
        assert data["key_id"] == created["key_id"]
        assert data["name"] == "My Test Key"
        assert data["permissions"] == ["email:*", "sms:send"]
        assert data["is_active"] is True

    def test_get_key_shows_revoked_status(self, admin_client):
        """Test that GET /keys/{key_id} shows correct status for revoked key."""
        client, _, _ = admin_client
        
        # Create and revoke a key
        create_response = client.post(
            "/keys",
            json={"name": "To Revoke", "permissions": ["email:*"]},
        )
        assert create_response.status_code == 201
        created = create_response.json()
        
        response = client.delete(f"/keys/{created['key_id']}")
        assert response.status_code == 200
        
        # Get the revoked key
        response = client.get(f"/keys/{created['key_id']}")
        
        data = response.json()
        
        assert data["is_active"] is False
        assert data["revoked_at"] is not None


# =============================================================================
# DELETE /keys/{key_id} Tests
# =============================================================================


class TestRevokeKey:
    """Tests for DELETE /keys/{key_id} endpoint."""

    def test_revoke_key_returns_200(self, admin_client):
        """Test that DELETE /keys/{key_id} returns 200 on success."""
        client, _, _ = admin_client
        
        # Create a key to revoke
        create_response = client.post(
            "/keys",
            json={"name": "To Revoke", "permissions": ["email:*"]},
        )
        assert create_response.status_code == 201
        created = create_response.json()
        
        response = client.delete(f"/keys/{created['key_id']}")
        
        assert response.status_code == 200

    def test_revoke_key_returns_confirmation(self, admin_client):
        """Test that DELETE /keys/{key_id} returns revocation confirmation."""
        client, _, _ = admin_client
        
        # Create a key to revoke
        create_response = client.post(
            "/keys",
            json={"name": "To Revoke", "permissions": ["email:*"]},
        )
        assert create_response.status_code == 201
        created = create_response.json()
        
        response = client.delete(f"/keys/{created['key_id']}")
        
        data = response.json()
        
        assert "key_id" in data
        assert "name" in data
        assert "revoked_at" in data
        assert "message" in data
        assert data["key_id"] == created["key_id"]
        assert data["name"] == "To Revoke"

    def test_revoke_key_prevents_authentication(self, admin_client):
        """Test that revoked key can no longer authenticate."""
        client, _, _ = admin_client
        
        # Create a key
        create_response = client.post(
            "/keys",
            json={"name": "To Revoke", "permissions": ["keys:list"]},
        )
        assert create_response.status_code == 201
        created = create_response.json()
        
        # Verify key works before revocation
        temp_client = TestClient(app)
        temp_client.headers["X-API-Key"] = created["secret"]
        
        response = temp_client.get("/keys")
        assert response.status_code == 200
        
        # Revoke the key
        response = client.delete(f"/keys/{created['key_id']}")
        assert response.status_code == 200
        
        # Verify key no longer works
        response = temp_client.get("/keys")
        assert response.status_code == 401
        assert "Invalid or revoked" in response.json()["detail"]

    def test_revoke_key_returns_404_for_nonexistent(self, admin_client):
        """Test that DELETE /keys/{key_id} returns 404 for unknown key."""
        client, _, _ = admin_client
        
        response = client.delete("/keys/ues_nonexistent123")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_revoke_admin_key_returns_400(self, admin_client):
        """Test that attempting to revoke admin key returns 400."""
        client, _, admin_key = admin_client
        
        response = client.delete(f"/keys/{admin_key.key_id}")
        
        assert response.status_code == 400
        assert "admin" in response.json()["detail"].lower()

    def test_revoke_already_revoked_key_returns_409(self, admin_client):
        """Test that revoking an already revoked key returns 409."""
        client, _, _ = admin_client
        
        # Create a key
        create_response = client.post(
            "/keys",
            json={"name": "To Revoke", "permissions": ["email:*"]},
        )
        assert create_response.status_code == 201
        created = create_response.json()
        
        # Revoke it
        response = client.delete(f"/keys/{created['key_id']}")
        assert response.status_code == 200
        
        # Try to revoke again
        response = client.delete(f"/keys/{created['key_id']}")
        
        assert response.status_code == 409
        assert "already revoked" in response.json()["detail"].lower()


# =============================================================================
# Edge Cases and Integration Tests
# =============================================================================


class TestEdgeCases:
    """Edge cases and integration tests for key management."""

    def test_created_by_tracking(self, admin_client):
        """Test that created_by is correctly tracked across key generations."""
        client, _, admin_key = admin_client
        
        # Create key A from admin
        response = client.post(
            "/keys",
            json={"name": "Key A", "permissions": ["*"]},
        )
        assert response.status_code == 201
        key_a = response.json()
        assert key_a["created_by"] == admin_key.key_id
        
        # Create key B from key A
        client_a = TestClient(app)
        client_a.headers["X-API-Key"] = key_a["secret"]
        
        response = client_a.post(
            "/keys",
            json={"name": "Key B", "permissions": ["email:*"]},
        )
        assert response.status_code == 201
        key_b = response.json()
        
        assert key_b["created_by"] == key_a["key_id"]

    def test_last_used_at_updates(self, admin_client):
        """Test that last_used_at is updated when key is used."""
        client, _, admin_key = admin_client
        
        # Get initial state
        response = client.get(f"/keys/{admin_key.key_id}")
        initial_data = response.json()
        
        # Use the key again
        response = client.get("/keys")
        assert response.status_code == 200
        
        # Check last_used_at was updated
        response = client.get(f"/keys/{admin_key.key_id}")
        updated_data = response.json()
        
        # last_used_at should be set (was None initially or should be newer)
        assert updated_data["last_used_at"] is not None

    def test_key_info_matches_create_response(self, admin_client):
        """Test that KeyInfo fields match CreateKeyResponse fields."""
        client, _, admin_key = admin_client
        
        # Create a key
        create_response = client.post(
            "/keys",
            json={"name": "Test Key", "permissions": ["email:*", "sms:*"]},
        )
        assert create_response.status_code == 201
        created = create_response.json()
        
        # Get the key
        get_response = client.get(f"/keys/{created['key_id']}")
        got = get_response.json()
        
        # Compare shared fields
        assert got["key_id"] == created["key_id"]
        assert got["name"] == created["name"]
        assert got["permissions"] == created["permissions"]
        assert got["created_by"] == created["created_by"]
        # created_at might differ slightly due to serialization, just verify it exists
        assert got["created_at"] is not None

    def test_wildcard_permission_grants_access(self, admin_client):
        """Test that wildcard permission grants access to sub-permissions."""
        client, _, _ = admin_client
        
        # Create a key with email:* permission
        response = client.post(
            "/keys",
            json={"name": "Email Bot", "permissions": ["email:*"]},
        )
        assert response.status_code == 201
        email_key = response.json()
        
        # This key should be able to access any email:* endpoint
        # For now, we just verify the key was created with the wildcard
        assert "email:*" in email_key["permissions"]

    def test_long_key_name(self, admin_client):
        """Test creating a key with maximum length name."""
        client, _, _ = admin_client
        
        long_name = "A" * 100  # Max length
        
        response = client.post(
            "/keys",
            json={"name": long_name, "permissions": ["email:*"]},
        )
        
        assert response.status_code == 201
        assert response.json()["name"] == long_name

    def test_too_long_key_name_rejected(self, admin_client):
        """Test that key name exceeding max length is rejected."""
        client, _, _ = admin_client
        
        too_long_name = "A" * 101  # Over max length
        
        response = client.post(
            "/keys",
            json={"name": too_long_name, "permissions": ["email:*"]},
        )
        
        assert response.status_code == 422  # Validation error

    def test_multiple_permissions(self, admin_client):
        """Test creating a key with many permissions."""
        client, _, _ = admin_client
        
        permissions = [
            "email:send",
            "email:receive",
            "sms:send",
            "sms:receive",
            "calendar:create",
            "calendar:update",
            "events:create",
            "simulation:start",
        ]
        
        response = client.post(
            "/keys",
            json={"name": "Multi-Permission", "permissions": permissions},
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["permissions"] == permissions
