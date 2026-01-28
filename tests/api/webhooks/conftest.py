"""Pytest fixtures for webhook API tests.

Provides authenticated test clients for webhook endpoints.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from ues.api.auth import initialize_api_key_registry, shutdown_api_key_registry
from ues.api.webhooks import webhook_registry, webhook_dispatcher
from ues.main import app


@pytest.fixture
def webhook_client():
    """Provide a TestClient with clean webhook state and authentication.
    
    Initializes the API key registry and clears the webhook registry
    before and after each test.
    """
    # Initialize API key registry
    admin_secret, _ = initialize_api_key_registry()
    
    # Create test client with auth
    client = TestClient(app)
    client.headers["X-API-Key"] = admin_secret
    
    # Clear any existing webhooks and delivery history
    asyncio.get_event_loop().run_until_complete(webhook_registry.clear())
    webhook_dispatcher.clear_history()
    
    yield client
    
    # Cleanup
    asyncio.get_event_loop().run_until_complete(webhook_registry.clear())
    webhook_dispatcher.clear_history()
    shutdown_api_key_registry()
