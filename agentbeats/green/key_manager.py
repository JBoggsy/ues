"""API Key management for AgentBeats Green Agent.

This module provides utilities for managing API keys during assessments.
It wraps the UES access control system to provide a clean interface for
the Green Agent to provision and clean up keys.
"""

from dataclasses import dataclass
from typing import Any

from api.access_control import AccessContext, AccessLevel, key_registry


@dataclass
class AssessmentKeys:
    """Container for API keys issued for an assessment.
    
    Attributes:
        assessment_id: Unique identifier for the assessment.
        proctor_key: API key for the Green Agent (full access).
        user_key: API key for the Purple Agent (restricted access).
    """
    assessment_id: str
    proctor_key: str
    user_key: str


class KeyManager:
    """Manager for provisioning and cleaning up assessment API keys.
    
    The KeyManager provides a high-level interface for the Green Agent
    to create and manage API keys for assessments.
    
    Example:
        key_manager = KeyManager()
        
        # Start assessment - provision keys
        keys = key_manager.provision_assessment_keys(
            assessment_id="assess-001",
            proctor_agent_id="green-agent",
            user_agent_id="purple-agent",
        )
        
        # Give user_key to Purple Agent...
        # Run assessment...
        
        # End assessment - clean up all keys
        key_manager.cleanup_assessment(keys.assessment_id)
    """
    
    def provision_assessment_keys(
        self,
        assessment_id: str,
        proctor_agent_id: str | None = None,
        user_agent_id: str | None = None,
        proctor_metadata: dict[str, Any] | None = None,
        user_metadata: dict[str, Any] | None = None,
    ) -> AssessmentKeys:
        """Provision API keys for a new assessment.
        
        Creates a proctor key (for the Green Agent) and a user key
        (for the Purple Agent being evaluated).
        
        Args:
            assessment_id: Unique identifier for this assessment.
            proctor_agent_id: Identifier for the Green Agent.
            user_agent_id: Identifier for the Purple Agent.
            proctor_metadata: Optional metadata for the proctor key.
            user_metadata: Optional metadata for the user key.
        
        Returns:
            AssessmentKeys containing both generated keys.
        """
        proctor_key = key_registry.generate_key(
            level=AccessLevel.PROCTOR,
            agent_id=proctor_agent_id,
            assessment_id=assessment_id,
            metadata=proctor_metadata,
        )
        
        user_key = key_registry.generate_key(
            level=AccessLevel.USER,
            agent_id=user_agent_id,
            assessment_id=assessment_id,
            metadata=user_metadata,
        )
        
        return AssessmentKeys(
            assessment_id=assessment_id,
            proctor_key=proctor_key,
            user_key=user_key,
        )
    
    def cleanup_assessment(self, assessment_id: str) -> int:
        """Clean up all API keys for an assessment.
        
        Should be called when an assessment ends (successfully or not)
        to invalidate all issued keys.
        
        Args:
            assessment_id: The assessment to clean up.
        
        Returns:
            Number of keys that were invalidated.
        """
        return key_registry.invalidate_keys_by_assessment(assessment_id)
    
    def get_proctor_context(self, proctor_key: str) -> AccessContext | None:
        """Get the context for a proctor key.
        
        Useful for validation or logging.
        
        Args:
            proctor_key: The proctor API key.
        
        Returns:
            AccessContext if valid, None otherwise.
        """
        context = key_registry.validate_key(proctor_key)
        if context and context.level == AccessLevel.PROCTOR:
            return context
        return None
    
    def get_user_context(self, user_key: str) -> AccessContext | None:
        """Get the context for a user key.
        
        Useful for validation or logging.
        
        Args:
            user_key: The user API key.
        
        Returns:
            AccessContext if valid, None otherwise.
        """
        context = key_registry.validate_key(user_key)
        if context and context.level == AccessLevel.USER:
            return context
        return None
    
    def invalidate_key(self, api_key: str) -> bool:
        """Invalidate a single API key.
        
        Useful if a specific key needs to be revoked mid-assessment.
        
        Args:
            api_key: The key to invalidate.
        
        Returns:
            True if the key was found and invalidated, False otherwise.
        """
        return key_registry.invalidate_key(api_key)


# Module-level singleton for convenience
key_manager = KeyManager()
