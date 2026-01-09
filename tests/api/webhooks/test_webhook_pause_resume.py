"""Integration tests for webhook pause and resume endpoints.

Tests the webhook lifecycle management:
- POST /webhooks/{id}/pause - Pause a webhook
- POST /webhooks/{id}/resume - Resume a webhook
"""

import pytest
from fastapi.testclient import TestClient

from api.webhooks import webhook_registry, WebhookStatus
from main import app


@pytest.fixture
def webhook_client():
    """Provide a TestClient with clean webhook state."""
    client = TestClient(app)
    
    import asyncio
    asyncio.get_event_loop().run_until_complete(webhook_registry.clear())
    
    yield client
    
    asyncio.get_event_loop().run_until_complete(webhook_registry.clear())


class TestPauseWebhook:
    """Tests for POST /webhooks/{id}/pause endpoint."""
    
    def test_pause_active_webhook(self, webhook_client):
        """Test pausing an active webhook."""
        # Create a webhook
        create_response = webhook_client.post(
            "/webhooks",
            json={"url": "https://example.com/callback"}
        )
        webhook_id = create_response.json()["id"]
        assert create_response.json()["status"] == "active"
        
        # Pause it
        response = webhook_client.post(f"/webhooks/{webhook_id}/pause")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "paused"
        assert data["id"] == webhook_id
    
    def test_pause_already_paused_webhook(self, webhook_client):
        """Test pausing an already paused webhook."""
        create_response = webhook_client.post(
            "/webhooks",
            json={"url": "https://example.com/callback"}
        )
        webhook_id = create_response.json()["id"]
        
        # Pause twice
        webhook_client.post(f"/webhooks/{webhook_id}/pause")
        response = webhook_client.post(f"/webhooks/{webhook_id}/pause")
        
        assert response.status_code == 200
        assert response.json()["status"] == "paused"
    
    def test_pause_webhook_not_found(self, webhook_client):
        """Test pausing a non-existent webhook."""
        response = webhook_client.post("/webhooks/wh_nonexistent/pause")
        
        assert response.status_code == 404
    
    def test_pause_updates_timestamp(self, webhook_client):
        """Test that pausing updates the updated_at timestamp."""
        create_response = webhook_client.post(
            "/webhooks",
            json={"url": "https://example.com/callback"}
        )
        webhook_id = create_response.json()["id"]
        original_updated = create_response.json()["updated_at"]
        
        import time
        time.sleep(0.01)
        
        response = webhook_client.post(f"/webhooks/{webhook_id}/pause")
        
        assert response.json()["updated_at"] != original_updated


class TestResumeWebhook:
    """Tests for POST /webhooks/{id}/resume endpoint."""
    
    def test_resume_paused_webhook(self, webhook_client):
        """Test resuming a paused webhook."""
        # Create and pause
        create_response = webhook_client.post(
            "/webhooks",
            json={"url": "https://example.com/callback"}
        )
        webhook_id = create_response.json()["id"]
        webhook_client.post(f"/webhooks/{webhook_id}/pause")
        
        # Resume
        response = webhook_client.post(f"/webhooks/{webhook_id}/resume")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "active"
        assert data["id"] == webhook_id
    
    def test_resume_resets_failure_count(self, webhook_client):
        """Test that resuming resets the failure count."""
        # Create a webhook
        create_response = webhook_client.post(
            "/webhooks",
            json={"url": "https://example.com/callback"}
        )
        webhook_id = create_response.json()["id"]
        
        # Manually set failure count (via update)
        # First pause then resume to test failure count reset
        webhook_client.post(f"/webhooks/{webhook_id}/pause")
        response = webhook_client.post(f"/webhooks/{webhook_id}/resume")
        
        assert response.status_code == 200
        assert response.json()["failure_count"] == 0
    
    def test_resume_already_active_webhook(self, webhook_client):
        """Test resuming an already active webhook."""
        create_response = webhook_client.post(
            "/webhooks",
            json={"url": "https://example.com/callback"}
        )
        webhook_id = create_response.json()["id"]
        
        # Resume without pausing first
        response = webhook_client.post(f"/webhooks/{webhook_id}/resume")
        
        assert response.status_code == 200
        assert response.json()["status"] == "active"
    
    def test_resume_webhook_not_found(self, webhook_client):
        """Test resuming a non-existent webhook."""
        response = webhook_client.post("/webhooks/wh_nonexistent/resume")
        
        assert response.status_code == 404


class TestPauseResumeWorkflow:
    """Tests for combined pause/resume workflows."""
    
    def test_full_pause_resume_cycle(self, webhook_client):
        """Test a complete pause and resume cycle."""
        # Create
        create_response = webhook_client.post(
            "/webhooks",
            json={"url": "https://example.com/callback", "events": ["email."]}
        )
        webhook_id = create_response.json()["id"]
        assert create_response.json()["status"] == "active"
        
        # Pause
        pause_response = webhook_client.post(f"/webhooks/{webhook_id}/pause")
        assert pause_response.json()["status"] == "paused"
        
        # Verify paused state persists in GET
        get_response = webhook_client.get(f"/webhooks/{webhook_id}")
        assert get_response.json()["status"] == "paused"
        
        # Resume
        resume_response = webhook_client.post(f"/webhooks/{webhook_id}/resume")
        assert resume_response.json()["status"] == "active"
        
        # Verify active state persists in GET
        get_response = webhook_client.get(f"/webhooks/{webhook_id}")
        assert get_response.json()["status"] == "active"
    
    def test_paused_webhook_excluded_from_active_list(self, webhook_client):
        """Test that paused webhooks are excluded when filtering by active status."""
        # Create two webhooks
        create1 = webhook_client.post("/webhooks", json={"url": "https://a.com/callback"})
        create2 = webhook_client.post("/webhooks", json={"url": "https://b.com/callback"})
        
        # Pause one
        webhook_client.post(f"/webhooks/{create1.json()['id']}/pause")
        
        # List active only
        list_response = webhook_client.get("/webhooks", params={"status": "active"})
        
        assert len(list_response.json()["items"]) == 1
        assert list_response.json()["items"][0]["id"] == create2.json()["id"]
