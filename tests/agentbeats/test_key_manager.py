"""Tests for AgentBeats Green Agent key manager.

Tests the KeyManager class that provides high-level API key management
for assessments.
"""

import pytest

from agentbeats.green.key_manager import AssessmentKeys, KeyManager, key_manager
from api.access_control import AccessLevel, key_registry


@pytest.fixture(autouse=True)
def clean_registry():
    """Clean up the key registry after each test."""
    yield
    key_registry.clear()


class TestAssessmentKeys:
    """Tests for the AssessmentKeys dataclass."""
    
    def test_assessment_keys_creation(self):
        """AssessmentKeys can be created with required fields."""
        keys = AssessmentKeys(
            assessment_id="test-001",
            proctor_key="ues_proctor_abc",
            user_key="ues_user_xyz",
        )
        
        assert keys.assessment_id == "test-001"
        assert keys.proctor_key == "ues_proctor_abc"
        assert keys.user_key == "ues_user_xyz"


class TestKeyManager:
    """Tests for the KeyManager class."""
    
    def test_provision_assessment_keys(self):
        """provision_assessment_keys creates proctor and user keys."""
        manager = KeyManager()
        
        keys = manager.provision_assessment_keys(
            assessment_id="assess-001",
            proctor_agent_id="green-agent",
            user_agent_id="purple-agent",
        )
        
        assert keys.assessment_id == "assess-001"
        assert keys.proctor_key.startswith("ues_proctor_")
        assert keys.user_key.startswith("ues_user_")
        
        # Keys should be valid
        proctor_ctx = key_registry.validate_key(keys.proctor_key)
        assert proctor_ctx is not None
        assert proctor_ctx.level == AccessLevel.PROCTOR
        assert proctor_ctx.agent_id == "green-agent"
        assert proctor_ctx.assessment_id == "assess-001"
        
        user_ctx = key_registry.validate_key(keys.user_key)
        assert user_ctx is not None
        assert user_ctx.level == AccessLevel.USER
        assert user_ctx.agent_id == "purple-agent"
        assert user_ctx.assessment_id == "assess-001"
    
    def test_provision_keys_with_metadata(self):
        """provision_assessment_keys stores metadata on keys."""
        manager = KeyManager()
        
        keys = manager.provision_assessment_keys(
            assessment_id="assess-002",
            proctor_metadata={"scenario": "email-test"},
            user_metadata={"agent_version": "1.0"},
        )
        
        proctor_ctx = key_registry.validate_key(keys.proctor_key)
        assert proctor_ctx.metadata == {"scenario": "email-test"}
        
        user_ctx = key_registry.validate_key(keys.user_key)
        assert user_ctx.metadata == {"agent_version": "1.0"}
    
    def test_cleanup_assessment(self):
        """cleanup_assessment invalidates all keys for an assessment."""
        manager = KeyManager()
        
        # Provision keys for two assessments
        keys1 = manager.provision_assessment_keys(
            assessment_id="assess-to-cleanup",
        )
        keys2 = manager.provision_assessment_keys(
            assessment_id="assess-to-keep",
        )
        
        # Cleanup the first assessment
        count = manager.cleanup_assessment("assess-to-cleanup")
        
        assert count == 2  # proctor + user key
        
        # Keys for cleaned up assessment should be invalid
        assert key_registry.validate_key(keys1.proctor_key) is None
        assert key_registry.validate_key(keys1.user_key) is None
        
        # Keys for other assessment should still be valid
        assert key_registry.validate_key(keys2.proctor_key) is not None
        assert key_registry.validate_key(keys2.user_key) is not None
    
    def test_get_proctor_context(self):
        """get_proctor_context returns context for valid proctor keys."""
        manager = KeyManager()
        keys = manager.provision_assessment_keys(assessment_id="assess-003")
        
        # Valid proctor key returns context
        ctx = manager.get_proctor_context(keys.proctor_key)
        assert ctx is not None
        assert ctx.level == AccessLevel.PROCTOR
        
        # User key returns None (not a proctor key)
        ctx = manager.get_proctor_context(keys.user_key)
        assert ctx is None
        
        # Invalid key returns None
        ctx = manager.get_proctor_context("ues_proctor_invalid")
        assert ctx is None
    
    def test_get_user_context(self):
        """get_user_context returns context for valid user keys."""
        manager = KeyManager()
        keys = manager.provision_assessment_keys(assessment_id="assess-004")
        
        # Valid user key returns context
        ctx = manager.get_user_context(keys.user_key)
        assert ctx is not None
        assert ctx.level == AccessLevel.USER
        
        # Proctor key returns None (not a user key)
        ctx = manager.get_user_context(keys.proctor_key)
        assert ctx is None
        
        # Invalid key returns None
        ctx = manager.get_user_context("ues_user_invalid")
        assert ctx is None
    
    def test_invalidate_key(self):
        """invalidate_key removes a single key."""
        manager = KeyManager()
        keys = manager.provision_assessment_keys(assessment_id="assess-005")
        
        # Invalidate only the user key
        result = manager.invalidate_key(keys.user_key)
        assert result is True
        
        # User key should now be invalid
        assert key_registry.validate_key(keys.user_key) is None
        
        # Proctor key should still be valid
        assert key_registry.validate_key(keys.proctor_key) is not None
    
    def test_invalidate_nonexistent_key(self):
        """invalidate_key returns False for nonexistent keys."""
        manager = KeyManager()
        
        result = manager.invalidate_key("ues_user_nonexistent")
        assert result is False


class TestModuleSingleton:
    """Tests for the module-level key_manager singleton."""
    
    def test_singleton_exists(self):
        """Module-level key_manager singleton is available."""
        assert key_manager is not None
        assert isinstance(key_manager, KeyManager)
    
    def test_singleton_is_functional(self):
        """Module-level key_manager singleton works correctly."""
        keys = key_manager.provision_assessment_keys(
            assessment_id="singleton-test",
        )
        
        assert keys.proctor_key.startswith("ues_proctor_")
        assert key_registry.validate_key(keys.proctor_key) is not None
        
        # Cleanup
        key_manager.cleanup_assessment("singleton-test")
