"""Example Purple Agent implementations.

This package contains example agents demonstrating how to use the
Purple Agent infrastructure for UES AgentBeats assessments.

Examples:
    simple_agent: A minimal agent that processes emails by marking them as read.
    llm_agent: An LLM-powered agent that uses language models for decision making.

Usage:
    from agentbeats.purple.examples import SimpleEmailAgent, LLMAgent
"""

from agentbeats.purple.examples.llm_agent import (
    LLMAgent,
    LLMClient,
    LLMResponse,
    Message,
    MockLLMClient,
    OpenAIClient,
    ParsedAction,
    create_llm_agent,
    parse_llm_response,
)
from agentbeats.purple.examples.simple_agent import SimpleEmailAgent

__all__ = [
    # Simple agent
    "SimpleEmailAgent",
    # LLM agent
    "LLMAgent",
    "LLMClient",
    "LLMResponse",
    "Message",
    "MockLLMClient",
    "OpenAIClient",
    "ParsedAction",
    "create_llm_agent",
    "parse_llm_response",
]
