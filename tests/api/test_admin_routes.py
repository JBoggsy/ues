"""Tests for admin API routes for key management.

These tests verify the admin endpoints for creating, listing, and
invalidating API keys.
"""

import os
from typing import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


# =============================================================================
# Test Fixture
# =============================================================================


# Configure access control before importing the app
def _configure_app():
    """Configure the app with access control enabled before import."""
    os.environ["UES_ACCESS_CONTROL"] = "true"
    
    # Import fresh to pick up env var
    import importlib
    import main
    importlib.reload(main)
    return main.app


@pytest.fixture
def client_with_access_control() -> Generator[TestClient, None, None]:
    """Create a test client with access control enabled."""
    # Save original env
    original_env = os.environ.get("UES_ACCESS_CONTROL")
    
    try:
        app = _configure_app()
        
        # Must use context manager for lifespan to run
        with TestClient(app) as client:
            yield client
    finally:
        # Restore original env
        if original_env is not None:
            os.environ["UES_ACCESS_CONTROL"] = original_env
        elif "UES_ACCESS_CONTROL" in os.environ:
            del os.environ["UES_ACCESS_CONTROL"]
        
        # Reimport to reset
        import importlib
        import main
        importlib.reload(main)


@pytest.fixture
def proctor_key() -> str:
    """Generate a proctor key for testing."""
    from api.access_control import AccessLevel, key_registry
    return key_registry.generate_key(
        level=AccessLevel.PROCTOR,
        agent_id="test-proctor",
        assessment_id="test-assessment",
    )


@pytest.fixture
def user_key() -> str:
    """Generate a user key for testing."""
    from api.access_control import AccessLevel, key_registry
    return key_registry.generate_key(
        level=AccessLevel.USER,
        agent_id="test-user",
        assessment_id="test-assessment",
    )


@pytest.fixture(autouse=True)
def clean_registry():
    """Clean up the key registry after each test."""
    yield
    from api.access_control import key_registry
    key_registry.clear()


# =============================================================================
# Test: POST /admin/keys - Create Key
# =============================================================================


class TestCreateKey:
    """Tests for POST /admin/keys endpoint."""
    
    def test_create_key_requires_authentication(
        self,
        client_with_access_control: TestClient,
    ):
        """Creating a key without authentication returns 401."""
        response = client_with_access_control.post(
            "/admin/keys",
            json={"level": "user"},
        )
        
        assert response.status_code == 401
        assert "Missing X-API-Key" in response.json()["detail"]
    
    def test_create_key_requires_proctor_access(
        self,
        client_with_access_control: TestClient,
        user_key: str,
    ):
        """Creating a key with user-level access returns 403."""
        response = client_with_access_control.post(
            "/admin/keys",
            json={"level": "user"},
            headers={"X-API-Key": user_key},
        )
        
        assert response.status_code == 403
        assert "proctor" in response.json()["detail"].lower()
    
    def test_create_user_key_with_proctor_access(
        self,
        client_with_access_control: TestClient,
        proctor_key: str,
    ):
        """Creating a user key with proctor access succeeds."""
        response = client_with_access_control.post(
            "/admin/keys",
            json={
                "level": "user",
                "agent_id": "new-agent",
                "assessment_id": "assess-001",
            },
            headers={"X-API-Key": proctor_key},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["level"] == "user"
        assert data["agent_id"] == "new-agent"
        assert data["assessment_id"] == "assess-001"
        assert data["api_key"].startswith("ues_user_")
    
    def test_create_proctor_key_with_proctor_access(
        self,
        client_with_access_control: TestClient,
        proctor_key: str,
    ):
        """Creating a proctor key with proctor access succeeds."""
        response = client_with_access_control.post(
            "/admin/keys",
            json={
                "level": "proctor",
                "agent_id": "another-proctor",
            },
            headers={"X-API-Key": proctor_key},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["level"] == "proctor"
        assert data["agent_id"] == "another-proctor"
        assert data["api_key"].startswith("ues_proctor_")
    
    def test_create_key_with_metadata(
        self,
        client_with_access_control: TestClient,
        proctor_key: str,
    ):
        """Creating a key with metadata stores the metadata."""
        response = client_with_access_control.post(
            "/admin/keys",
            json={
                "level": "user",
                "metadata": {"custom_field": "value", "number": 42},
            },
            headers={"X-API-Key": proctor_key},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["metadata"] == {"custom_field": "value", "number": 42}


# =============================================================================
# Test: GET /admin/keys - List Keys
# =============================================================================


class TestListKeys:
    """Tests for GET /admin/keys endpoint."""
    
    def test_list_keys_requires_authentication(
        self,
        client_with_access_control: TestClient,
    ):
        """Listing keys without authentication returns 401."""
        response = client_with_access_control.get("/admin/keys")
        
        assert response.status_code == 401
    
    def test_list_keys_requires_proctor_access(
        self,
        client_with_access_control: TestClient,
        user_key: str,
    ):
        """Listing keys with user-level access returns 403."""
        response = client_with_access_control.get(
            "/admin/keys",
            headers={"X-API-Key": user_key},
        )
        
        assert response.status_code == 403
    
    def test_list_all_keys(
        self,
        client_with_access_control: TestClient,
        proctor_key: str,
        user_key: str,
    ):
        """Listing all keys returns all registered keys."""
        response = client_with_access_control.get(
            "/admin/keys",
            headers={"X-API-Key": proctor_key},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2  # At least proctor_key and user_key
        
        # Verify our test keys are in the list
        keys = {k["api_key"] for k in data["keys"]}
        assert proctor_key in keys
        assert user_key in keys
    
    def test_list_keys_filtered_by_assessment(
        self,
        client_with_access_control: TestClient,
        proctor_key: str,
    ):
        """Listing keys can be filtered by assessment_id."""
        from api.access_control import AccessLevel, key_registry
        
        # Create keys for different assessments
        key_registry.generate_key(
            level=AccessLevel.USER,
            agent_id="agent-1",
            assessment_id="assessment-A",
        )
        key_registry.generate_key(
            level=AccessLevel.USER,
            agent_id="agent-2",
            assessment_id="assessment-B",
        )
        key_registry.generate_key(
            level=AccessLevel.USER,
            agent_id="agent-3",
            assessment_id="assessment-A",
        )
        
        # Filter by assessment-A
        response = client_with_access_control.get(
            "/admin/keys",
            params={"assessment_id": "assessment-A"},
            headers={"X-API-Key": proctor_key},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should only include keys for assessment-A
        for key in data["keys"]:
            assert key["assessment_id"] == "assessment-A"
        
        assert data["total"] == 2  # agent-1 and agent-3


# =============================================================================
# Test: DELETE /admin/keys/{api_key} - Invalidate Key
# =============================================================================


class TestInvalidateKey:
    """Tests for DELETE /admin/keys/{api_key} endpoint."""
    
    def test_invalidate_key_requires_authentication(
        self,
        client_with_access_control: TestClient,
    ):
        """Invalidating a key without authentication returns 401."""
        response = client_with_access_control.delete(
            "/admin/keys/ues_user_somekey"
        )
        
        assert response.status_code == 401
    
    def test_invalidate_key_requires_proctor_access(
        self,
        client_with_access_control: TestClient,
        user_key: str,
    ):
        """Invalidating a key with user-level access returns 403."""
        response = client_with_access_control.delete(
            f"/admin/keys/{user_key}",
            headers={"X-API-Key": user_key},
        )
        
        assert response.status_code == 403
    
    def test_invalidate_existing_key(
        self,
        client_with_access_control: TestClient,
        proctor_key: str,
    ):
        """Invalidating an existing key succeeds."""
        from api.access_control import AccessLevel, key_registry
        
        # Create a key to invalidate
        key_to_invalidate = key_registry.generate_key(
            level=AccessLevel.USER,
            agent_id="temp-agent",
        )
        
        # Verify key exists
        assert key_registry.validate_key(key_to_invalidate) is not None
        
        # Invalidate it
        response = client_with_access_control.delete(
            f"/admin/keys/{key_to_invalidate}",
            headers={"X-API-Key": proctor_key},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify key is gone
        assert key_registry.validate_key(key_to_invalidate) is None
    
    def test_invalidate_nonexistent_key(
        self,
        client_with_access_control: TestClient,
        proctor_key: str,
    ):
        """Invalidating a nonexistent key returns success=False."""
        response = client_with_access_control.delete(
            "/admin/keys/ues_user_nonexistent",
            headers={"X-API-Key": proctor_key},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "not found" in data["message"].lower()


# =============================================================================
# Test: POST /admin/keys/cleanup/{assessment_id} - Cleanup Assessment Keys
# =============================================================================


class TestCleanupAssessmentKeys:
    """Tests for POST /admin/keys/cleanup/{assessment_id} endpoint."""
    
    def test_cleanup_requires_authentication(
        self,
        client_with_access_control: TestClient,
    ):
        """Cleanup without authentication returns 401."""
        response = client_with_access_control.post(
            "/admin/keys/cleanup/test-assessment"
        )
        
        assert response.status_code == 401
    
    def test_cleanup_requires_proctor_access(
        self,
        client_with_access_control: TestClient,
        user_key: str,
    ):
        """Cleanup with user-level access returns 403."""
        response = client_with_access_control.post(
            "/admin/keys/cleanup/test-assessment",
            headers={"X-API-Key": user_key},
        )
        
        assert response.status_code == 403
    
    def test_cleanup_assessment_keys(
        self,
        client_with_access_control: TestClient,
        proctor_key: str,
    ):
        """Cleanup invalidates all keys for the assessment."""
        from api.access_control import AccessLevel, key_registry
        
        # Create keys for the assessment
        key1 = key_registry.generate_key(
            level=AccessLevel.USER,
            agent_id="agent-1",
            assessment_id="cleanup-test",
        )
        key2 = key_registry.generate_key(
            level=AccessLevel.USER,
            agent_id="agent-2",
            assessment_id="cleanup-test",
        )
        key3 = key_registry.generate_key(
            level=AccessLevel.USER,
            agent_id="agent-other",
            assessment_id="other-assessment",
        )
        
        # Cleanup the assessment
        response = client_with_access_control.post(
            "/admin/keys/cleanup/cleanup-test",
            headers={"X-API-Key": proctor_key},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["invalidated_count"] == 2
        assert data["assessment_id"] == "cleanup-test"
        
        # Verify keys for cleanup-test are gone
        assert key_registry.validate_key(key1) is None
        assert key_registry.validate_key(key2) is None
        
        # Verify key for other assessment still exists
        assert key_registry.validate_key(key3) is not None
    
    def test_cleanup_nonexistent_assessment(
        self,
        client_with_access_control: TestClient,
        proctor_key: str,
    ):
        """Cleanup for nonexistent assessment returns count 0."""
        response = client_with_access_control.post(
            "/admin/keys/cleanup/nonexistent-assessment",
            headers={"X-API-Key": proctor_key},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["invalidated_count"] == 0
