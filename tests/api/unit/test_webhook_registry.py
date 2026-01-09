"""Unit tests for WebhookRegistry.

Tests the in-memory webhook storage and retrieval operations.
"""

import pytest
from datetime import datetime, timezone

from api.webhooks import (
    WebhookRegistration,
    WebhookRegistry,
    WebhookStatus,
)


@pytest.fixture
def registry():
    """Create a fresh registry for each test."""
    return WebhookRegistry()


@pytest.fixture
def sample_webhook():
    """Create a sample webhook registration."""
    return WebhookRegistration(
        id="wh_test123",
        url="https://example.com/callback",
        events=["email."],
        secret="test-secret",
        metadata={"name": "test"},
    )


class TestWebhookRegistryAdd:
    """Tests for adding webhooks to the registry."""
    
    @pytest.mark.asyncio
    async def test_add_webhook(self, registry, sample_webhook):
        """Test adding a webhook to the registry."""
        await registry.add(sample_webhook)
        
        result = await registry.get("wh_test123")
        assert result is not None
        assert result.url == "https://example.com/callback"
    
    @pytest.mark.asyncio
    async def test_add_multiple_webhooks(self, registry):
        """Test adding multiple webhooks."""
        wh1 = WebhookRegistration(id="wh_1", url="https://a.com/callback")
        wh2 = WebhookRegistration(id="wh_2", url="https://b.com/callback")
        
        await registry.add(wh1)
        await registry.add(wh2)
        
        assert registry.count() == 2
    
    @pytest.mark.asyncio
    async def test_add_duplicate_id_replaces(self, registry):
        """Test that adding a webhook with existing ID replaces it."""
        wh1 = WebhookRegistration(id="wh_dup", url="https://first.com")
        wh2 = WebhookRegistration(id="wh_dup", url="https://second.com")
        
        await registry.add(wh1)
        await registry.add(wh2)
        
        result = await registry.get("wh_dup")
        assert result.url == "https://second.com"
        assert registry.count() == 1


class TestWebhookRegistryGet:
    """Tests for retrieving webhooks from the registry."""
    
    @pytest.mark.asyncio
    async def test_get_existing_webhook(self, registry, sample_webhook):
        """Test retrieving an existing webhook."""
        await registry.add(sample_webhook)
        
        result = await registry.get("wh_test123")
        
        assert result is not None
        assert result.id == "wh_test123"
        assert result.url == "https://example.com/callback"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_webhook(self, registry):
        """Test retrieving a non-existent webhook returns None."""
        result = await registry.get("wh_nonexistent")
        assert result is None


class TestWebhookRegistryUpdate:
    """Tests for updating webhooks in the registry."""
    
    @pytest.mark.asyncio
    async def test_update_url(self, registry, sample_webhook):
        """Test updating webhook URL."""
        await registry.add(sample_webhook)
        
        updated = await registry.update("wh_test123", {"url": "https://new.com/callback"})
        
        assert updated is not None
        assert updated.url == "https://new.com/callback"
        assert updated.updated_at > sample_webhook.created_at
    
    @pytest.mark.asyncio
    async def test_update_status(self, registry, sample_webhook):
        """Test updating webhook status."""
        await registry.add(sample_webhook)
        
        updated = await registry.update("wh_test123", {"status": WebhookStatus.PAUSED})
        
        assert updated is not None
        assert updated.status == WebhookStatus.PAUSED
    
    @pytest.mark.asyncio
    async def test_update_multiple_fields(self, registry, sample_webhook):
        """Test updating multiple fields at once."""
        await registry.add(sample_webhook)
        
        updated = await registry.update("wh_test123", {
            "url": "https://new.com",
            "failure_count": 5,
            "status": WebhookStatus.DISABLED,
        })
        
        assert updated.url == "https://new.com"
        assert updated.failure_count == 5
        assert updated.status == WebhookStatus.DISABLED
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_webhook(self, registry):
        """Test updating a non-existent webhook returns None."""
        result = await registry.update("wh_nonexistent", {"url": "https://new.com"})
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_sets_updated_at(self, registry, sample_webhook):
        """Test that update sets updated_at timestamp."""
        await registry.add(sample_webhook)
        original_updated = sample_webhook.updated_at
        
        import asyncio
        await asyncio.sleep(0.01)  # Small delay to ensure different timestamp
        
        updated = await registry.update("wh_test123", {"failure_count": 1})
        
        assert updated.updated_at > original_updated


class TestWebhookRegistryDelete:
    """Tests for deleting webhooks from the registry."""
    
    @pytest.mark.asyncio
    async def test_delete_existing_webhook(self, registry, sample_webhook):
        """Test deleting an existing webhook."""
        await registry.add(sample_webhook)
        
        result = await registry.delete("wh_test123")
        
        assert result is True
        assert await registry.get("wh_test123") is None
        assert registry.count() == 0
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_webhook(self, registry):
        """Test deleting a non-existent webhook returns False."""
        result = await registry.delete("wh_nonexistent")
        assert result is False


class TestWebhookRegistryListAll:
    """Tests for listing webhooks from the registry."""
    
    @pytest.mark.asyncio
    async def test_list_all_empty(self, registry):
        """Test listing webhooks from empty registry."""
        webhooks, total = await registry.list_all()
        
        assert webhooks == []
        assert total == 0
    
    @pytest.mark.asyncio
    async def test_list_all_with_webhooks(self, registry):
        """Test listing all webhooks."""
        wh1 = WebhookRegistration(id="wh_1", url="https://a.com")
        wh2 = WebhookRegistration(id="wh_2", url="https://b.com")
        wh3 = WebhookRegistration(id="wh_3", url="https://c.com")
        
        await registry.add(wh1)
        await registry.add(wh2)
        await registry.add(wh3)
        
        webhooks, total = await registry.list_all()
        
        assert len(webhooks) == 3
        assert total == 3
    
    @pytest.mark.asyncio
    async def test_list_all_filtered_by_status(self, registry):
        """Test listing webhooks filtered by status."""
        wh1 = WebhookRegistration(id="wh_1", url="https://a.com", status=WebhookStatus.ACTIVE)
        wh2 = WebhookRegistration(id="wh_2", url="https://b.com", status=WebhookStatus.PAUSED)
        wh3 = WebhookRegistration(id="wh_3", url="https://c.com", status=WebhookStatus.ACTIVE)
        
        await registry.add(wh1)
        await registry.add(wh2)
        await registry.add(wh3)
        
        webhooks, total = await registry.list_all(status=WebhookStatus.ACTIVE)
        
        assert len(webhooks) == 2
        assert total == 2
        assert all(w.status == WebhookStatus.ACTIVE for w in webhooks)
    
    @pytest.mark.asyncio
    async def test_list_all_with_pagination(self, registry):
        """Test listing webhooks with pagination."""
        for i in range(5):
            wh = WebhookRegistration(id=f"wh_{i}", url=f"https://{i}.com")
            await registry.add(wh)
        
        webhooks, total = await registry.list_all(limit=2, offset=1)
        
        assert len(webhooks) == 2
        assert total == 5


class TestWebhookRegistryGetMatching:
    """Tests for getting webhooks matching an event type."""
    
    @pytest.mark.asyncio
    async def test_get_matching_exact(self, registry):
        """Test getting webhooks with exact event match."""
        wh = WebhookRegistration(
            id="wh_1",
            url="https://a.com",
            events=["email.received"]
        )
        await registry.add(wh)
        
        matching = await registry.get_matching("email.received")
        
        assert len(matching) == 1
        assert matching[0].id == "wh_1"
    
    @pytest.mark.asyncio
    async def test_get_matching_prefix(self, registry):
        """Test getting webhooks with prefix match."""
        wh = WebhookRegistration(
            id="wh_1",
            url="https://a.com",
            events=["email."]
        )
        await registry.add(wh)
        
        matching = await registry.get_matching("email.received")
        
        assert len(matching) == 1
    
    @pytest.mark.asyncio
    async def test_get_matching_all_events(self, registry):
        """Test getting webhooks subscribed to all events."""
        wh = WebhookRegistration(
            id="wh_1",
            url="https://a.com",
            events=None  # All events
        )
        await registry.add(wh)
        
        assert len(await registry.get_matching("email.received")) == 1
        assert len(await registry.get_matching("sms.sent")) == 1
        assert len(await registry.get_matching("anything.any")) == 1
    
    @pytest.mark.asyncio
    async def test_get_matching_excludes_inactive(self, registry):
        """Test that inactive webhooks are not matched."""
        wh = WebhookRegistration(
            id="wh_1",
            url="https://a.com",
            events=["email."],
            status=WebhookStatus.PAUSED,
        )
        await registry.add(wh)
        
        matching = await registry.get_matching("email.received")
        
        assert len(matching) == 0
    
    @pytest.mark.asyncio
    async def test_get_matching_excludes_disabled(self, registry):
        """Test that disabled webhooks are not matched."""
        wh = WebhookRegistration(
            id="wh_1",
            url="https://a.com",
            events=["email."],
            status=WebhookStatus.DISABLED,
        )
        await registry.add(wh)
        
        matching = await registry.get_matching("email.received")
        
        assert len(matching) == 0
    
    @pytest.mark.asyncio
    async def test_get_matching_multiple_webhooks(self, registry):
        """Test matching multiple webhooks for an event."""
        wh1 = WebhookRegistration(id="wh_1", url="https://a.com", events=["email."])
        wh2 = WebhookRegistration(id="wh_2", url="https://b.com", events=["email.received"])
        wh3 = WebhookRegistration(id="wh_3", url="https://c.com", events=["sms."])
        
        await registry.add(wh1)
        await registry.add(wh2)
        await registry.add(wh3)
        
        matching = await registry.get_matching("email.received")
        
        assert len(matching) == 2
        ids = {w.id for w in matching}
        assert ids == {"wh_1", "wh_2"}


class TestWebhookRegistryClear:
    """Tests for clearing the registry."""
    
    @pytest.mark.asyncio
    async def test_clear_all_webhooks(self, registry):
        """Test clearing all webhooks from registry."""
        wh1 = WebhookRegistration(id="wh_1", url="https://a.com")
        wh2 = WebhookRegistration(id="wh_2", url="https://b.com")
        
        await registry.add(wh1)
        await registry.add(wh2)
        assert registry.count() == 2
        
        await registry.clear()
        
        assert registry.count() == 0
    
    @pytest.mark.asyncio
    async def test_clear_empty_registry(self, registry):
        """Test clearing an already empty registry."""
        await registry.clear()  # Should not raise
        assert registry.count() == 0


class TestWebhookRegistryCount:
    """Tests for counting webhooks."""
    
    @pytest.mark.asyncio
    async def test_count_empty(self, registry):
        """Test count on empty registry."""
        assert registry.count() == 0
    
    @pytest.mark.asyncio
    async def test_count_with_webhooks(self, registry):
        """Test count with webhooks."""
        for i in range(3):
            wh = WebhookRegistration(id=f"wh_{i}", url=f"https://{i}.com")
            await registry.add(wh)
        
        assert registry.count() == 3
    
    @pytest.mark.asyncio
    async def test_count_active(self, registry):
        """Test counting only active webhooks."""
        wh1 = WebhookRegistration(id="wh_1", url="https://a.com", status=WebhookStatus.ACTIVE)
        wh2 = WebhookRegistration(id="wh_2", url="https://b.com", status=WebhookStatus.PAUSED)
        wh3 = WebhookRegistration(id="wh_3", url="https://c.com", status=WebhookStatus.ACTIVE)
        
        await registry.add(wh1)
        await registry.add(wh2)
        await registry.add(wh3)
        
        assert registry.count_active() == 2
