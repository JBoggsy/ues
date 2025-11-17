"""Agent-related models."""

from pydantic import BaseModel


class AgentConfiguration(BaseModel):
    """Configuration for an AI agent that participates in the simulation.

    Args:
        id: Unique agent identifier.
        name: Human-readable agent name.
        prompt_template: Template for generating agent prompts.
        triggers: List of AgentTrigger instances defining when the agent acts.
        is_enabled: Whether this agent is currently active.
    """

    pass


class AgentTrigger(BaseModel):
    """Defines when an agent should be triggered.

    Args:
        event_type: Type of event that triggers this agent (e.g., "email_received").
        conditions: Dictionary of conditions that must be met.
        frequency: How often the agent can be triggered (e.g., "once_per_hour").
    """

    pass


class AgentResponse(BaseModel):
    """Response from an agent after being triggered.

    Args:
        generated_events: List of new SimulatorEvent instances created by the agent.
        metadata: Additional metadata about the agent's decision-making process.
    """

    pass
