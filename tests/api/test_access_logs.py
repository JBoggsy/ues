"""Integration tests for access log API endpoints.

This module tests the /access-logs API endpoints including:
- GET /access-logs - Query access log entries with filters
- GET /access-logs/stats - Get aggregate statistics
- POST /access-logs/clear - Clear all access log entries

All tests use fixtures that provide an authenticated client with appropriate
permissions for access log operations.

Test Organization:
- TestQueryAccessLogs: Query endpoint tests
- TestAccessLogStatistics: Statistics endpoint tests
- TestClearAccessLogs: Clear endpoint tests
- TestAccessLogsPermissions: Permission/auth tests
- TestMiddlewareIntegration: Tests that verify middleware is logging requests
"""

import pytest
from fastapi.testclient import TestClient

from ues.api.auth import (
    get_api_key_registry,
    initialize_api_key_registry,
    shutdown_api_key_registry,
)
from ues.api.dependencies import get_simulation_engine
from ues.api.middleware import get_access_log, initialize_access_log, shutdown_access_log
from ues.main import app


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def reset_access_log():
    """Reset the access log before and after each test.
    
    This ensures each test starts with a fresh log and clean state.
    """
    import ues.api.middleware.access_logging as log_module
    
    # Store original state
    original_log = log_module._access_log
    
    # Reset before test
    log_module._access_log = None
    
    yield
    
    # Reset after test
    log_module._access_log = original_log


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
    
    # Initialize access log
    initialize_access_log(max_entries=1000)
    
    # Create test client with admin key in default headers
    client = TestClient(app)
    client.headers["X-API-Key"] = admin_secret
    
    yield client, admin_secret, admin_key
    
    # Cleanup
    shutdown_access_log()
    shutdown_api_key_registry()
    app.dependency_overrides.clear()


@pytest.fixture
def limited_client(admin_client):
    """Provide a TestClient with a limited-permission API key.
    
    Creates a key that has only read permissions on logs.
    
    Yields:
        A tuple of (TestClient, limited_key_secret, limited_key_info, admin_client).
    """
    client, admin_secret, admin_key = admin_client
    
    # Create a limited key using admin
    response = client.post(
        "/keys",
        json={
            "name": "Log Reader",
            "permissions": ["logs:read"],
        },
    )
    assert response.status_code == 201
    limited_data = response.json()
    
    # Create new client with limited key
    limited_client = TestClient(app)
    limited_client.headers["X-API-Key"] = limited_data["secret"]
    
    yield limited_client, limited_data["secret"], limited_data, admin_client


# =============================================================================
# Query Endpoint Tests
# =============================================================================


class TestQueryAccessLogs:
    """Tests for GET /access-logs endpoint."""
    
    def test_query_empty_log(self, admin_client):
        """Test querying after clearing the access log.
        
        Note: The clear request itself is logged, so the log won't be truly
        empty after clearing - it will have the clear request entry.
        """
        client, _, _ = admin_client
        
        # Clear any logs from setup
        client.post("/access-logs/clear")
        
        response = client.get("/access-logs")
        
        assert response.status_code == 200
        data = response.json()
        # The clear request itself is logged, so count should be 1
        assert data["count"] == 1
        assert data["entries"][0]["path"] == "/access-logs/clear"
        assert data["has_more"] is False
    
    def test_query_returns_recent_entries(self, admin_client):
        """Test that queries return recent entries from middleware."""
        client, _, _ = admin_client
        
        # Clear logs
        client.post("/access-logs/clear")
        
        # Make some requests that will be logged
        client.get("/simulation/status")
        client.get("/email/state")
        
        response = client.get("/access-logs")
        
        assert response.status_code == 200
        data = response.json()
        # Should have at least 2 entries from the status and email requests
        # (plus possibly the clear and query requests themselves)
        assert data["count"] >= 2
    
    def test_query_with_limit(self, admin_client):
        """Test query with limit parameter."""
        client, _, _ = admin_client
        
        # Clear and make multiple requests
        client.post("/access-logs/clear")
        for _ in range(5):
            client.get("/simulation/status")
        
        response = client.get("/access-logs", params={"limit": 2})
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert data["limit"] == 2
        assert data["has_more"] is True
    
    def test_query_with_offset(self, admin_client):
        """Test query with offset parameter."""
        client, _, _ = admin_client
        
        # Clear and make requests
        client.post("/access-logs/clear")
        for _ in range(5):
            client.get("/simulation/status")
        
        # Get all entries first
        all_response = client.get("/access-logs")
        all_entries = all_response.json()["entries"]
        
        # Get with offset
        response = client.get("/access-logs", params={"offset": 2})
        
        assert response.status_code == 200
        data = response.json()
        # Should have skipped 2 entries
        assert data["offset"] == 2
    
    def test_query_filter_by_path_prefix(self, admin_client):
        """Test query filtering by path prefix."""
        client, _, _ = admin_client
        
        # Clear and make various requests
        client.post("/access-logs/clear")
        client.get("/simulation/status")
        client.get("/email/state")
        client.get("/sms/state")
        
        response = client.get("/access-logs", params={"path_prefix": "/email"})
        
        assert response.status_code == 200
        data = response.json()
        # All entries should be email-related
        for entry in data["entries"]:
            assert entry["path"].startswith("/email")
    
    def test_query_filter_by_method(self, admin_client):
        """Test query filtering by HTTP method."""
        client, _, _ = admin_client
        
        # Clear logs
        client.post("/access-logs/clear")
        
        # Make GET and POST requests
        client.get("/simulation/status")
        client.post("/simulation/start", json={"auto_advance": False})
        
        response = client.get("/access-logs", params={"method": "POST"})
        
        assert response.status_code == 200
        data = response.json()
        for entry in data["entries"]:
            assert entry["method"] == "POST"
    
    def test_query_filter_errors_only(self, admin_client):
        """Test query filtering for errors only."""
        client, _, _ = admin_client
        
        # Clear logs
        client.post("/access-logs/clear")
        
        # Make a successful request
        client.get("/simulation/status")
        
        # Make a request that will fail (invalid endpoint)
        client.get("/nonexistent/endpoint")
        
        response = client.get("/access-logs", params={"errors_only": "true"})
        
        assert response.status_code == 200
        data = response.json()
        for entry in data["entries"]:
            assert entry["is_error"] is True
    
    def test_query_filter_by_status_code(self, admin_client):
        """Test query filtering by exact status code."""
        client, _, _ = admin_client
        
        # Clear logs
        client.post("/access-logs/clear")
        
        # Make requests
        client.get("/simulation/status")
        
        response = client.get("/access-logs", params={"status_code": 200})
        
        assert response.status_code == 200
        data = response.json()
        for entry in data["entries"]:
            assert entry["status_code"] == 200
    
    def test_query_entries_include_key_info(self, admin_client):
        """Test that query entries include API key information."""
        client, _, admin_key = admin_client
        
        # Clear logs
        client.post("/access-logs/clear")
        
        # Make a request
        client.get("/simulation/status")
        
        response = client.get("/access-logs")
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1
        
        # Find an entry that should have key info
        entry = data["entries"][0]
        assert entry["key_id"] == admin_key.key_id
        assert entry["key_name"] == "Admin Key"
    
    def test_query_entries_include_response_info(self, admin_client):
        """Test that query entries include response information."""
        client, _, _ = admin_client
        
        # Clear and make a request
        client.post("/access-logs/clear")
        client.get("/simulation/status")
        
        response = client.get("/access-logs")
        
        assert response.status_code == 200
        data = response.json()
        
        entry = data["entries"][0]
        assert "log_id" in entry
        assert "timestamp" in entry
        assert "method" in entry
        assert "path" in entry
        assert "status_code" in entry
        assert "duration_ms" in entry
        assert "is_success" in entry
        assert "is_error" in entry


# =============================================================================
# Statistics Endpoint Tests
# =============================================================================


class TestAccessLogStatistics:
    """Tests for GET /access-logs/stats endpoint."""
    
    def test_statistics_empty_log(self, admin_client):
        """Test statistics after clearing the log.
        
        Note: The clear request itself is logged, so statistics will show 1 entry.
        """
        client, _, _ = admin_client
        
        # Clear logs
        client.post("/access-logs/clear")
        
        response = client.get("/access-logs/stats")
        
        assert response.status_code == 200
        data = response.json()
        # The clear request itself is logged
        assert data["total_entries"] == 1
        assert data["success_count"] == 1  # The clear request was successful
        assert data["client_error_count"] == 0
        assert data["server_error_count"] == 0
        assert data["unique_keys"] == 1  # Admin key
    
    def test_statistics_with_entries(self, admin_client):
        """Test statistics with log entries."""
        client, _, _ = admin_client
        
        # Clear logs
        client.post("/access-logs/clear")
        
        # Make some requests
        client.get("/simulation/status")  # 200
        client.get("/email/state")  # 200
        client.get("/nonexistent")  # 404
        
        response = client.get("/access-logs/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_entries"] >= 3
        assert data["max_entries"] == 1000  # From fixture
        assert data["success_count"] >= 2
        assert "is_full" in data
    
    def test_statistics_includes_timestamps(self, admin_client):
        """Test that statistics include timestamp range."""
        client, _, _ = admin_client
        
        # Clear logs
        client.post("/access-logs/clear")
        
        # Make a request
        client.get("/simulation/status")
        
        response = client.get("/access-logs/stats")
        
        assert response.status_code == 200
        data = response.json()
        # After a request, timestamps should be set
        assert data["earliest_timestamp"] is not None
        assert data["latest_timestamp"] is not None


# =============================================================================
# Clear Endpoint Tests
# =============================================================================


class TestClearAccessLogs:
    """Tests for POST /access-logs/clear endpoint."""
    
    def test_clear_empty_log(self, admin_client):
        """Test clearing an empty log."""
        client, _, _ = admin_client
        
        # First clear
        response = client.post("/access-logs/clear")
        
        # Second clear (log is empty except for the clear request itself)
        response = client.post("/access-logs/clear")
        
        assert response.status_code == 200
        data = response.json()
        assert data["cleared_count"] >= 0
        assert "message" in data
    
    def test_clear_populated_log(self, admin_client):
        """Test clearing a populated log."""
        client, _, _ = admin_client
        
        # Make several requests
        for _ in range(5):
            client.get("/simulation/status")
        
        # Clear
        response = client.post("/access-logs/clear")
        
        assert response.status_code == 200
        data = response.json()
        assert data["cleared_count"] >= 5
        assert "Successfully cleared" in data["message"]
        
        # Verify log is empty
        stats_response = client.get("/access-logs/stats")
        # Note: The stats request itself may be logged
        assert stats_response.json()["total_entries"] <= 1


# =============================================================================
# Permission Tests
# =============================================================================


class TestAccessLogsPermissions:
    """Tests for access log endpoint permissions."""
    
    def test_query_requires_auth(self, admin_client):
        """Test that query endpoint requires authentication."""
        client, _, _ = admin_client
        
        # Create unauthenticated client
        unauth_client = TestClient(app)
        
        response = unauth_client.get("/access-logs")
        
        assert response.status_code == 401
    
    def test_stats_requires_auth(self, admin_client):
        """Test that stats endpoint requires authentication."""
        client, _, _ = admin_client
        
        unauth_client = TestClient(app)
        
        response = unauth_client.get("/access-logs/stats")
        
        assert response.status_code == 401
    
    def test_clear_requires_auth(self, admin_client):
        """Test that clear endpoint requires authentication."""
        client, _, _ = admin_client
        
        unauth_client = TestClient(app)
        
        response = unauth_client.post("/access-logs/clear")
        
        assert response.status_code == 401
    
    def test_query_with_read_permission(self, limited_client):
        """Test that query works with logs:read permission."""
        client, _, _, _ = limited_client
        
        response = client.get("/access-logs")
        
        assert response.status_code == 200
    
    def test_stats_with_read_permission(self, limited_client):
        """Test that stats works with logs:read permission."""
        client, _, _, _ = limited_client
        
        response = client.get("/access-logs/stats")
        
        assert response.status_code == 200
    
    def test_clear_requires_clear_permission(self, limited_client):
        """Test that clear requires logs:clear permission."""
        client, _, _, _ = limited_client
        
        response = client.post("/access-logs/clear")
        
        # Limited client only has logs:read, not logs:clear
        assert response.status_code == 403


# =============================================================================
# Middleware Integration Tests
# =============================================================================


class TestMiddlewareIntegration:
    """Tests that verify the middleware is properly logging requests."""
    
    def test_middleware_logs_authenticated_requests(self, admin_client):
        """Test that authenticated requests are logged with key info."""
        client, _, admin_key = admin_client
        
        # Clear logs
        client.post("/access-logs/clear")
        
        # Make a specific request
        client.get("/email/state")
        
        # Query for that request
        response = client.get("/access-logs", params={"path_prefix": "/email"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1
        
        # Find the email request
        email_entries = [e for e in data["entries"] if e["path"] == "/email/state"]
        assert len(email_entries) >= 1
        
        entry = email_entries[0]
        assert entry["key_id"] == admin_key.key_id
        assert entry["key_name"] == "Admin Key"
        assert entry["method"] == "GET"
        assert entry["status_code"] == 200
        assert entry["is_success"] is True
    
    def test_middleware_logs_error_responses(self, admin_client):
        """Test that error responses are logged correctly."""
        client, _, _ = admin_client
        
        # Clear logs
        client.post("/access-logs/clear")
        
        # Make a request that will 404
        client.get("/nonexistent/path")
        
        response = client.get("/access-logs", params={"errors_only": "true"})
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have at least one error entry
        assert data["count"] >= 1
        entry = data["entries"][0]
        assert entry["is_error"] is True
        assert entry["status_code"] >= 400
    
    def test_middleware_skips_health_endpoint(self, admin_client):
        """Test that /health endpoint is not logged."""
        client, _, _ = admin_client
        
        # Clear logs
        client.post("/access-logs/clear")
        
        # Make health check request (no auth needed)
        unauth_client = TestClient(app)
        unauth_client.get("/health")
        
        # Query for health requests
        response = client.get("/access-logs", params={"path_prefix": "/health"})
        
        assert response.status_code == 200
        data = response.json()
        # Health endpoint should be skipped
        assert data["count"] == 0
    
    def test_middleware_skips_root_endpoint(self, admin_client):
        """Test that / endpoint is not logged."""
        client, _, _ = admin_client
        
        # Clear logs
        client.post("/access-logs/clear")
        
        # Make root request
        unauth_client = TestClient(app)
        unauth_client.get("/")
        
        # Query for root requests
        response = client.get("/access-logs")
        
        assert response.status_code == 200
        data = response.json()
        # Check that no entries have path "/"
        root_entries = [e for e in data["entries"] if e["path"] == "/"]
        assert len(root_entries) == 0
    
    def test_middleware_logs_duration(self, admin_client):
        """Test that request duration is logged."""
        client, _, _ = admin_client
        
        # Clear logs
        client.post("/access-logs/clear")
        
        # Make a request
        client.get("/simulation/status")
        
        response = client.get("/access-logs")
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1
        
        entry = data["entries"][0]
        assert "duration_ms" in entry
        assert entry["duration_ms"] >= 0
    
    def test_multiple_keys_tracked_separately(self, limited_client):
        """Test that requests from different keys are tracked separately."""
        limited, _, limited_data, (admin, _, admin_key) = limited_client
        
        # Clear logs using admin
        admin.post("/access-logs/clear")
        
        # Make request with admin key
        admin.get("/simulation/status")
        
        # Make request with limited key
        limited.get("/access-logs")
        
        # Query all logs with admin
        response = admin.get("/access-logs")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have entries from both keys
        key_ids = {e["key_id"] for e in data["entries"]}
        assert admin_key.key_id in key_ids
        assert limited_data["key_id"] in key_ids
