"""A2A Green Agent server for UES (User Environment Simulator).

This module sets up the A2A server and defines the AgentCard for the UES
benchmark. The green agent evaluates personal assistant agents on their
ability to handle multi-modal tasks in simulated environments.
"""

import argparse

import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)

from executor import Executor


def create_agent_card(host: str, port: int, card_url: str | None) -> AgentCard:
    """Create the AgentCard describing UES benchmark capabilities.

    Args:
        host: Host the server is bound to.
        port: Port the server is bound to.
        card_url: Optional URL to advertise in the agent card.

    Returns:
        Configured AgentCard for the UES green agent.
    """
    # Primary skill: Personal Assistant Benchmark
    personal_assistant_benchmark = AgentSkill(
        id="ues-personal-assistant-benchmark",
        name="Personal Assistant Benchmark",
        description=(
            "Evaluates AI personal assistant agents on their ability to handle "
            "realistic multi-modal tasks. Assessments simulate real-world scenarios "
            "involving email, calendar, SMS, location, and weather data. Agents are "
            "scored on accuracy, efficiency, completeness, and safety across "
            "difficulty levels from easy to hard."
        ),
        tags=[
            "benchmark",
            "evaluation",
            "personal-assistant",
            "multi-modal",
            "email",
            "calendar",
            "sms",
            "location",
            "weather",
        ],
        examples=[
            # Example assessment request
            '{"participants": {"assistant": "http://localhost:9010/"}, '
            '"config": {"scenario_id": "email-triage-basic", "max_turns": 20}}',
            # Example with more config options
            '{"participants": {"assistant": "http://localhost:9010/"}, '
            '"config": {"scenario_id": "calendar-conflict-resolution", '
            '"time_limit_seconds": 300, "seed": 42}}',
        ],
    )

    return AgentCard(
        name="UES Benchmark",
        description=(
            "User Environment Simulator (UES) - A green agent benchmark for "
            "evaluating AI personal assistant agents. UES provides reproducible, "
            "multi-modal test scenarios that simulate real-world personal assistant "
            "tasks. Agents interact with a simulated environment via REST API, "
            "handling emails, calendar events, SMS messages, and contextual data "
            "like location and weather. Assessments measure task completion accuracy, "
            "action efficiency, response completeness, and safety compliance."
        ),
        url=card_url or f"http://{host}:{port}/",
        version="0.1.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(
            streaming=True,  # Support streaming task updates
        ),
        skills=[personal_assistant_benchmark],
    )


def main():
    """Run the UES A2A green agent server."""
    parser = argparse.ArgumentParser(
        description="Run the UES A2A green agent benchmark server."
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind the server (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9009,
        help="Port to bind the server (default: 9009)",
    )
    parser.add_argument(
        "--card-url",
        type=str,
        help="URL to advertise in the agent card (optional)",
    )
    args = parser.parse_args()

    agent_card = create_agent_card(args.host, args.port, args.card_url)

    request_handler = DefaultRequestHandler(
        agent_executor=Executor(),
        task_store=InMemoryTaskStore(),
    )

    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )

    print(f"Starting UES A2A Green Agent on {args.host}:{args.port}")
    print(f"Agent Card URL: {agent_card.url}")
    uvicorn.run(server.build(), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
