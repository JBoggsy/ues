"""A2A server setup for Purple Agent implementations.

This module provides utilities for creating and running A2A servers for
Purple Agents. It handles CLI argument parsing, AgentCard creation, and
server startup with sensible defaults.

Example:
    Running a Purple Agent server with a custom agent::

        from agentbeats.purple import BaseAgent, run_purple_agent
        from agentbeats.purple.schemas import TurnCompleteMessage
        from datetime import timedelta

        class MyAgent(BaseAgent):
            async def on_assessment_start(self, message, context, ues):
                chat_state = await ues.chat.get_state()
                context.user_instructions = chat_state.messages[0].content

            async def execute_turn(self, context, ues):
                return TurnCompleteMessage(
                    actions_taken=0,
                    notes="Did nothing",
                    time_step=timedelta(hours=1),
                )

        if __name__ == "__main__":
            run_purple_agent(
                agent_factory=MyAgent,
                name="My Simple Agent",
                description="A simple Purple Agent example",
            )

    Running with custom options::

        run_purple_agent(
            agent_factory=MyAgent,
            name="My Agent",
            description="Custom agent",
            version="2.0.0",
            default_port=9010,
            skills=[
                AgentSkill(
                    id="email-processing",
                    name="Email Processing",
                    description="Handles email triage and responses",
                ),
            ],
        )

    Using CLI arguments::

        $ python my_agent.py --host 0.0.0.0 --port 9010 --card-url http://external-url.com/
"""

import argparse
import sys
from typing import Callable

import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)

from agentbeats.purple.base_agent import BaseAgent
from agentbeats.purple.executor import PurpleExecutor


def create_agent_card(
    name: str,
    description: str,
    host: str,
    port: int,
    card_url: str | None = None,
    version: str = "1.0.0",
    skills: list[AgentSkill] | None = None,
) -> AgentCard:
    """Create an AgentCard for a Purple Agent.

    The AgentCard describes the agent's capabilities and metadata for the A2A
    protocol. This is used for agent discovery and interaction.

    Args:
        name: Display name for the agent.
        description: Human-readable description of what the agent does.
        host: Host the server is bound to (used for default URL).
        port: Port the server is bound to (used for default URL).
        card_url: Optional URL to advertise in the agent card. If not provided,
            defaults to http://{host}:{port}/.
        version: Semantic version string for the agent.
        skills: Optional list of AgentSkill objects describing the agent's
            capabilities. If not provided, a default skill is created.

    Returns:
        Configured AgentCard for the Purple Agent.

    Example:
        Creating a basic agent card::

            card = create_agent_card(
                name="Email Assistant",
                description="An AI assistant that helps manage emails",
                host="0.0.0.0",
                port=9009,
            )

        Creating a card with custom skills::

            card = create_agent_card(
                name="Calendar Manager",
                description="Manages calendar events",
                host="0.0.0.0",
                port=9010,
                version="2.0.0",
                skills=[
                    AgentSkill(
                        id="schedule-meetings",
                        name="Meeting Scheduler",
                        description="Schedules and manages meetings",
                        tags=["calendar", "meetings", "scheduling"],
                    ),
                ],
            )
    """
    # Create default skill if none provided
    if skills is None:
        skills = [
            AgentSkill(
                id="ues-personal-assistant",
                name=name,
                description=description,
                tags=["ues", "personal-assistant", "agentbeats"],
            )
        ]

    # Build the URL
    url = card_url or f"http://{host}:{port}/"

    return AgentCard(
        name=name,
        description=description,
        url=url,
        version=version,
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(
            streaming=True,  # Support streaming task updates
        ),
        skills=skills,
    )


def create_cli_parser(
    default_host: str = "0.0.0.0",
    default_port: int = 9009,
) -> argparse.ArgumentParser:
    """Create the CLI argument parser for Purple Agent servers.

    Args:
        default_host: Default host if not specified via CLI.
        default_port: Default port if not specified via CLI.

    Returns:
        Configured ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        description="Run a Purple Agent A2A server for UES AgentBeats benchmarks.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--host",
        type=str,
        default=default_host,
        help="Host to bind the server",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=default_port,
        help="Port to bind the server",
    )

    parser.add_argument(
        "--card-url",
        type=str,
        default=None,
        help="URL to advertise in the agent card (optional, defaults to http://host:port/)",
    )

    return parser


def run_purple_agent(
    agent_factory: Callable[[], BaseAgent],
    name: str,
    description: str,
    version: str = "1.0.0",
    skills: list[AgentSkill] | None = None,
    default_host: str = "0.0.0.0",
    default_port: int = 9009,
    args: list[str] | None = None,
) -> None:
    """Run a Purple Agent A2A server.

    This is the main entry point for running a Purple Agent. It handles:
    1. CLI argument parsing (--host, --port, --card-url)
    2. AgentCard creation
    3. PurpleExecutor setup with the agent factory
    4. Server startup using uvicorn

    Args:
        agent_factory: Callable that creates a new BaseAgent instance.
            Called once per assessment context when assessment_start is received.
        name: Display name for the agent.
        description: Human-readable description of what the agent does.
        version: Semantic version string for the agent.
        skills: Optional list of AgentSkill objects describing capabilities.
        default_host: Default host if not specified via CLI.
        default_port: Default port if not specified via CLI.
        args: Optional list of CLI arguments (for testing). If None, uses sys.argv.

    Example:
        Simple usage::

            class MyAgent(BaseAgent):
                ...

            if __name__ == "__main__":
                run_purple_agent(
                    agent_factory=MyAgent,
                    name="My Agent",
                    description="Does amazing things",
                )

        With all options::

            run_purple_agent(
                agent_factory=MyAgent,
                name="Custom Agent",
                description="Handles email and calendar tasks",
                version="2.1.0",
                skills=[
                    AgentSkill(
                        id="email-handler",
                        name="Email Handler",
                        description="Processes emails",
                    ),
                ],
                default_port=9010,
            )
    """
    # Parse CLI arguments
    parser = create_cli_parser(default_host, default_port)
    parsed_args = parser.parse_args(args)

    # Create agent card
    agent_card = create_agent_card(
        name=name,
        description=description,
        host=parsed_args.host,
        port=parsed_args.port,
        card_url=parsed_args.card_url,
        version=version,
        skills=skills,
    )

    # Create executor with agent factory
    executor = PurpleExecutor(agent_factory=agent_factory)

    # Create request handler
    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
    )

    # Create A2A application
    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )

    # Print startup info
    print(f"Starting Purple Agent: {name}")
    print(f"  Version: {version}")
    print(f"  Server: {parsed_args.host}:{parsed_args.port}")
    print(f"  Agent Card URL: {agent_card.url}")

    # Run the server
    uvicorn.run(server.build(), host=parsed_args.host, port=parsed_args.port)


def create_purple_server(
    agent_factory: Callable[[], BaseAgent],
    name: str,
    description: str,
    host: str = "0.0.0.0",
    port: int = 9009,
    card_url: str | None = None,
    version: str = "1.0.0",
    skills: list[AgentSkill] | None = None,
) -> tuple[A2AStarletteApplication, AgentCard]:
    """Create a Purple Agent A2A server without running it.

    This is useful for testing or when you need more control over the server
    lifecycle. Unlike run_purple_agent, this function returns the server
    components without starting uvicorn.

    Args:
        agent_factory: Callable that creates a new BaseAgent instance.
        name: Display name for the agent.
        description: Human-readable description of what the agent does.
        host: Host for the agent card URL.
        port: Port for the agent card URL.
        card_url: Optional URL to advertise in the agent card.
        version: Semantic version string for the agent.
        skills: Optional list of AgentSkill objects.

    Returns:
        Tuple of (A2AStarletteApplication, AgentCard).

    Example:
        Creating a server for testing::

            app, card = create_purple_server(
                agent_factory=MyAgent,
                name="Test Agent",
                description="For testing",
            )

            # Use with TestClient
            from starlette.testclient import TestClient
            client = TestClient(app.build())
    """
    # Create agent card
    agent_card = create_agent_card(
        name=name,
        description=description,
        host=host,
        port=port,
        card_url=card_url,
        version=version,
        skills=skills,
    )

    # Create executor with agent factory
    executor = PurpleExecutor(agent_factory=agent_factory)

    # Create request handler
    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
    )

    # Create A2A application
    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )

    return server, agent_card
