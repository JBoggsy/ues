"""UES A2A Green Agent for AgentBeats.

This package implements the A2A green agent interface for the User Environment
Simulator (UES) benchmark. It allows evaluation of AI personal assistant agents
through the AgentBeats platform.
"""

from agentbeats.green.key_manager import AssessmentKeys, KeyManager, key_manager

__version__ = "0.1.0"

__all__ = [
    "AssessmentKeys",
    "KeyManager",
    "key_manager",
]
