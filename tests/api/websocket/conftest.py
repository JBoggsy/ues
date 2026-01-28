"""Pytest fixtures for WebSocket API tests.

Provides authenticated test clients for WebSocket endpoints.
"""

import pytest

from ues.api.auth import initialize_api_key_registry, shutdown_api_key_registry


# Module-level variable to store the admin API key secret
_admin_api_key: str | None = None


@pytest.fixture(autouse=True)
def setup_api_key_registry():
    """Initialize the API key registry before each test.
    
    This fixture runs automatically for all tests in this module.
    It initializes the API key registry before each test and shuts it
    down afterwards to ensure clean state.
    
    The admin API key secret is stored in the module-level variable
    _admin_api_key for use by other fixtures or test helpers.
    """
    global _admin_api_key
    _admin_api_key, _ = initialize_api_key_registry()
    yield _admin_api_key
    shutdown_api_key_registry()
    _admin_api_key = None


@pytest.fixture
def api_key():
    """Provide the admin API key for tests that need it explicitly.
    
    Returns:
        The admin API key secret.
    """
    return _admin_api_key


def get_auth_headers() -> dict[str, str]:
    """Get authentication headers for HTTP requests.
    
    Returns:
        A dict with X-API-Key header set to the admin API key.
        
    Raises:
        RuntimeError: If API key registry not initialized.
    """
    if _admin_api_key is None:
        raise RuntimeError("API key registry not initialized. "
                          "Ensure setup_api_key_registry fixture is active.")
    return {"X-API-Key": _admin_api_key}
