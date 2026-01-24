"""Tests for API access control middleware integration.

This module tests the access control middleware when UES_ACCESS_CONTROL is enabled.
Tests verify that:
- Public routes work without authentication
- Protected routes return 401 without API key
- Protected routes return 401 with invalid API key
- Protected routes return 403 with insufficient permissions
- Proctor keys can access all endpoints
- User keys can only access user-allowed endpoints

Note: These tests need special handling because middleware must be added before
the TestClient is created with lifespan context. We use a module-level setup.
"""

import pytest
from fastapi.testclient import TestClient

from api.access_control import AccessLevel, key_registry


# Module-level setup: Add middleware once before any tests run
# This must happen before TestClient is created with lifespan
_app_configured = False


def _configure_app():
    """Add access control middleware to the app (once)."""
    global _app_configured
    if not _app_configured:
        from main import AccessControlMiddleware, app
        
        # Check if middleware already added
        middleware_classes = [m.cls for m in app.user_middleware if hasattr(m, 'cls')]
        if AccessControlMiddleware not in middleware_classes:
            app.add_middleware(AccessControlMiddleware)
        _app_configured = True


# Configure app at module import time
_configure_app()


@pytest.fixture(autouse=True)
def clean_registry():
    """Ensure key registry is clean before and after each test."""
    key_registry.clear()
    yield
    key_registry.clear()


@pytest.fixture
def client_with_access_control():
    """Create a test client with access control middleware.
    
    The middleware was added at module import time. Using TestClient
    as a context manager properly initializes the SimulationEngine via lifespan.
    """
    from main import app
    
    # Using context manager ensures lifespan startup/shutdown runs
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def proctor_key():
    """Create a proctor-level API key."""
    return key_registry.generate_key(
        level=AccessLevel.PROCTOR,
        agent_id="test-proctor",
        assessment_id="test-assessment",
    )


@pytest.fixture
def user_key():
    """Create a user-level API key."""
    return key_registry.generate_key(
        level=AccessLevel.USER,
        agent_id="test-user",
        assessment_id="test-assessment",
    )


class TestAccessControlMiddleware:
    """Tests for the AccessControlMiddleware class."""
    
    def test_public_routes_without_key(self, client_with_access_control):
        """Public routes should work without API key."""
        # Root endpoint
        response = client_with_access_control.get("/")
        assert response.status_code == 200
        
        # Health check
        response = client_with_access_control.get("/health")
        assert response.status_code == 200
    
    def test_protected_route_missing_key(self, client_with_access_control):
        """Protected routes should return 401 without API key."""
        response = client_with_access_control.get("/email/state")
        assert response.status_code == 401
        assert "Missing X-API-Key header" in response.json()["detail"]
    
    def test_protected_route_invalid_key(self, client_with_access_control):
        """Protected routes should return 401 with invalid API key."""
        response = client_with_access_control.get(
            "/email/state",
            headers={"X-API-Key": "invalid_key_12345"},
        )
        assert response.status_code == 401
        assert "Invalid or expired API key" in response.json()["detail"]
    
    def test_proctor_can_access_user_routes(self, client_with_access_control, proctor_key):
        """Proctor keys should be able to access user-allowed routes."""
        response = client_with_access_control.get(
            "/email/state",
            headers={"X-API-Key": proctor_key},
        )
        assert response.status_code == 200
    
    def test_proctor_can_access_proctor_routes(self, client_with_access_control, proctor_key):
        """Proctor keys should be able to access proctor-only routes."""
        response = client_with_access_control.get(
            "/simulation/status",
            headers={"X-API-Key": proctor_key},
        )
        assert response.status_code == 200
    
    def test_user_can_access_user_routes(self, client_with_access_control, user_key):
        """User keys should be able to access user-allowed routes."""
        response = client_with_access_control.get(
            "/email/state",
            headers={"X-API-Key": user_key},
        )
        assert response.status_code == 200
    
    def test_user_cannot_access_proctor_routes(self, client_with_access_control, user_key):
        """User keys should NOT be able to access proctor-only routes."""
        # Time control is proctor-only
        response = client_with_access_control.post(
            "/simulator/time/advance",
            headers={"X-API-Key": user_key},
            json={"seconds": 60},
        )
        assert response.status_code == 403
        assert "proctor-level access" in response.json()["detail"]
    
    def test_user_cannot_access_simulation_control(self, client_with_access_control, user_key):
        """User keys should NOT be able to control simulation."""
        response = client_with_access_control.post(
            "/simulation/reset",
            headers={"X-API-Key": user_key},
        )
        assert response.status_code == 403
    
    def test_user_cannot_receive_email(self, client_with_access_control, user_key):
        """User keys should NOT be able to use simulator-side actions."""
        response = client_with_access_control.post(
            "/email/receive",
            headers={"X-API-Key": user_key},
            json={
                "from_address": "test@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Test",
                "body_text": "Test body",
            },
        )
        assert response.status_code == 403
    
    def test_user_can_send_email(self, client_with_access_control, user_key):
        """User keys should be able to use user-side actions."""
        response = client_with_access_control.post(
            "/email/send",
            headers={"X-API-Key": user_key},
            json={
                "from_address": "user@example.com",
                "to_addresses": ["recipient@example.com"],
                "subject": "Test",
                "body_text": "Test body",
            },
        )
        # Should be 200 (success) or 400/422 (validation error), not 401/403
        assert response.status_code not in [401, 403]
    
    def test_invalidated_key_returns_401(self, client_with_access_control, user_key):
        """Invalidated keys should return 401."""
        # First request works
        response = client_with_access_control.get(
            "/email/state",
            headers={"X-API-Key": user_key},
        )
        assert response.status_code == 200
        
        # Invalidate the key
        key_registry.invalidate_key(user_key)
        
        # Second request should fail
        response = client_with_access_control.get(
            "/email/state",
            headers={"X-API-Key": user_key},
        )
        assert response.status_code == 401


class TestRoutePermissionCoverage:
    """Tests to verify all important routes have correct permissions."""
    
    def test_time_control_routes_are_proctor_only(self, client_with_access_control, user_key):
        """All time control routes should require proctor access."""
        routes = [
            ("POST", "/simulator/time/advance", {"seconds": 1}),
            ("POST", "/simulator/time/set", {"time": "2025-01-01T00:00:00Z"}),
            ("POST", "/simulator/time/pause", None),
            ("POST", "/simulator/time/resume", None),
        ]
        
        for method, path, body in routes:
            if method == "POST":
                response = client_with_access_control.post(
                    path,
                    headers={"X-API-Key": user_key},
                    json=body,
                )
            else:
                response = client_with_access_control.request(
                    method,
                    path,
                    headers={"X-API-Key": user_key},
                )
            assert response.status_code == 403, f"{method} {path} should be proctor-only"
    
    def test_state_routes_are_user_accessible(self, client_with_access_control, user_key):
        """State query routes should be accessible to user keys."""
        routes = [
            "/email/state",
            "/sms/state",
            "/calendar/state",
            "/chat/state",
            "/location/state",
            "/weather/state",
            "/simulator/time",
            "/simulation/status",
        ]
        
        for path in routes:
            response = client_with_access_control.get(
                path,
                headers={"X-API-Key": user_key},
            )
            assert response.status_code in [200, 404], f"GET {path} should be user-accessible"
    
    def test_user_actions_are_accessible(self, client_with_access_control, user_key):
        """User-side action routes should be accessible to user keys."""
        # Just test that we don't get 403 - actual validation may fail
        routes = [
            ("/email/send", {"from_address": "a@b.com", "to_addresses": ["c@d.com"], "subject": "x", "body_text": "y"}),
            ("/sms/send", {"from_number": "+1234567890", "to_number": "+0987654321", "body": "test"}),
            ("/chat/send", {"content": "hello"}),
        ]
        
        for path, body in routes:
            response = client_with_access_control.post(
                path,
                headers={"X-API-Key": user_key},
                json=body,
            )
            # Should not be 401 or 403 (auth errors)
            # May be 200, 400, or 422 depending on validation
            assert response.status_code not in [401, 403], f"POST {path} should be user-accessible"
