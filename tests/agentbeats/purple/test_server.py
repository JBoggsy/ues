"""Tests for Purple Agent server module.

This module tests the server setup utilities for Purple Agents,
including AgentCard creation, CLI parsing, and server configuration.
"""

import argparse
from unittest.mock import MagicMock, patch

import pytest
from a2a.types import AgentCard, AgentSkill

from agentbeats.purple.server import (
    create_agent_card,
    create_cli_parser,
    create_purple_server,
)
from agentbeats.purple.base_agent import BaseAgent
from agentbeats.purple.schemas import TurnCompleteMessage


# =============================================================================
# Test Agent
# =============================================================================


class TestAgent(BaseAgent):
    """Simple test agent for server tests."""

    async def on_assessment_start(self, message, context, ues):
        pass

    async def execute_turn(self, context, ues):
        return TurnCompleteMessage(actions_taken=0)


# =============================================================================
# Tests: create_agent_card
# =============================================================================


class TestCreateAgentCard:
    """Tests for the create_agent_card function."""

    def test_create_basic_card(self):
        """Creates card with required fields."""
        card = create_agent_card(
            name="Test Agent",
            description="A test agent",
            host="0.0.0.0",
            port=9009,
        )

        assert isinstance(card, AgentCard)
        assert card.name == "Test Agent"
        assert card.description == "A test agent"
        assert card.url == "http://0.0.0.0:9009/"
        assert card.version == "1.0.0"

    def test_create_card_with_custom_url(self):
        """Creates card with custom card_url."""
        card = create_agent_card(
            name="Test Agent",
            description="A test agent",
            host="localhost",
            port=8000,
            card_url="http://external-host.com:9009/",
        )

        assert card.url == "http://external-host.com:9009/"

    def test_create_card_with_custom_version(self):
        """Creates card with custom version."""
        card = create_agent_card(
            name="Test Agent",
            description="A test agent",
            host="0.0.0.0",
            port=9009,
            version="2.1.0",
        )

        assert card.version == "2.1.0"

    def test_create_card_with_custom_skills(self):
        """Creates card with custom skills."""
        skills = [
            AgentSkill(
                id="email-handler",
                name="Email Handler",
                description="Handles email tasks",
                tags=["email", "triage"],
            ),
            AgentSkill(
                id="calendar-manager",
                name="Calendar Manager",
                description="Manages calendar events",
                tags=["calendar"],
            ),
        ]

        card = create_agent_card(
            name="Multi-Skill Agent",
            description="Agent with multiple skills",
            host="0.0.0.0",
            port=9009,
            skills=skills,
        )

        assert len(card.skills) == 2
        assert card.skills[0].id == "email-handler"
        assert card.skills[1].id == "calendar-manager"

    def test_create_card_default_skill(self):
        """Creates default skill if none provided."""
        card = create_agent_card(
            name="Simple Agent",
            description="A simple agent",
            host="0.0.0.0",
            port=9009,
        )

        assert len(card.skills) == 1
        assert card.skills[0].name == "Simple Agent"
        assert "ues" in card.skills[0].tags
        assert "agentbeats" in card.skills[0].tags

    def test_create_card_has_capabilities(self):
        """Card has streaming capability enabled."""
        card = create_agent_card(
            name="Test Agent",
            description="A test agent",
            host="0.0.0.0",
            port=9009,
        )

        assert card.capabilities is not None
        assert card.capabilities.streaming is True

    def test_create_card_input_output_modes(self):
        """Card has text as default input/output mode."""
        card = create_agent_card(
            name="Test Agent",
            description="A test agent",
            host="0.0.0.0",
            port=9009,
        )

        assert "text" in card.default_input_modes
        assert "text" in card.default_output_modes


# =============================================================================
# Tests: create_cli_parser
# =============================================================================


class TestCreateCLIParser:
    """Tests for the create_cli_parser function."""

    def test_create_parser_defaults(self):
        """Creates parser with default values."""
        parser = create_cli_parser()

        # Parse empty args to get defaults
        args = parser.parse_args([])

        assert args.host == "0.0.0.0"
        assert args.port == 9009
        assert args.card_url is None

    def test_create_parser_custom_defaults(self):
        """Creates parser with custom default values."""
        parser = create_cli_parser(
            default_host="localhost",
            default_port=8080,
        )

        args = parser.parse_args([])

        assert args.host == "localhost"
        assert args.port == 8080

    def test_parser_accepts_host(self):
        """Parser accepts --host argument."""
        parser = create_cli_parser()
        args = parser.parse_args(["--host", "127.0.0.1"])

        assert args.host == "127.0.0.1"

    def test_parser_accepts_port(self):
        """Parser accepts --port argument."""
        parser = create_cli_parser()
        args = parser.parse_args(["--port", "9010"])

        assert args.port == 9010

    def test_parser_accepts_card_url(self):
        """Parser accepts --card-url argument."""
        parser = create_cli_parser()
        args = parser.parse_args(["--card-url", "http://external.com/"])

        assert args.card_url == "http://external.com/"

    def test_parser_accepts_all_arguments(self):
        """Parser accepts all arguments together."""
        parser = create_cli_parser()
        args = parser.parse_args([
            "--host", "192.168.1.1",
            "--port", "9999",
            "--card-url", "http://my-agent.example.com/",
        ])

        assert args.host == "192.168.1.1"
        assert args.port == 9999
        assert args.card_url == "http://my-agent.example.com/"

    def test_parser_is_argparse_instance(self):
        """create_cli_parser returns an ArgumentParser."""
        parser = create_cli_parser()
        assert isinstance(parser, argparse.ArgumentParser)


# =============================================================================
# Tests: create_purple_server
# =============================================================================


class TestCreatePurpleServer:
    """Tests for the create_purple_server function."""

    def test_create_server_returns_tuple(self):
        """create_purple_server returns (app, card) tuple."""
        result = create_purple_server(
            agent_factory=TestAgent,
            name="Test Agent",
            description="A test agent",
        )

        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_create_server_returns_agent_card(self):
        """create_purple_server returns configured AgentCard."""
        app, card = create_purple_server(
            agent_factory=TestAgent,
            name="My Agent",
            description="My description",
            version="2.0.0",
        )

        assert isinstance(card, AgentCard)
        assert card.name == "My Agent"
        assert card.description == "My description"
        assert card.version == "2.0.0"

    def test_create_server_with_custom_host_port(self):
        """create_purple_server uses custom host/port for URL."""
        app, card = create_purple_server(
            agent_factory=TestAgent,
            name="Test Agent",
            description="Test",
            host="192.168.1.100",
            port=9999,
        )

        assert card.url == "http://192.168.1.100:9999/"

    def test_create_server_with_card_url(self):
        """create_purple_server uses card_url if provided."""
        app, card = create_purple_server(
            agent_factory=TestAgent,
            name="Test Agent",
            description="Test",
            card_url="http://external.example.com/",
        )

        assert card.url == "http://external.example.com/"

    def test_create_server_with_skills(self):
        """create_purple_server passes skills to card."""
        skills = [
            AgentSkill(
                id="test-skill",
                name="Test Skill",
                description="A test skill",
                tags=["test"],
            ),
        ]

        app, card = create_purple_server(
            agent_factory=TestAgent,
            name="Test Agent",
            description="Test",
            skills=skills,
        )

        assert len(card.skills) == 1
        assert card.skills[0].id == "test-skill"

    def test_create_server_app_can_build(self):
        """create_purple_server app can be built."""
        app, card = create_purple_server(
            agent_factory=TestAgent,
            name="Test Agent",
            description="Test",
        )

        # Should not raise
        starlette_app = app.build()
        assert starlette_app is not None


# =============================================================================
# Tests: run_purple_agent (without actually running)
# =============================================================================


class TestRunPurpleAgent:
    """Tests for run_purple_agent function setup (mocked uvicorn)."""

    @patch("agentbeats.purple.server.uvicorn")
    def test_run_purple_agent_calls_uvicorn(self, mock_uvicorn):
        """run_purple_agent calls uvicorn.run."""
        from agentbeats.purple.server import run_purple_agent

        run_purple_agent(
            agent_factory=TestAgent,
            name="Test Agent",
            description="Test",
            args=[],  # Empty args to use defaults
        )

        mock_uvicorn.run.assert_called_once()

    @patch("agentbeats.purple.server.uvicorn")
    def test_run_purple_agent_uses_cli_args(self, mock_uvicorn):
        """run_purple_agent uses CLI arguments."""
        from agentbeats.purple.server import run_purple_agent

        run_purple_agent(
            agent_factory=TestAgent,
            name="Test Agent",
            description="Test",
            args=["--host", "127.0.0.1", "--port", "9010"],
        )

        call_args = mock_uvicorn.run.call_args
        assert call_args.kwargs["host"] == "127.0.0.1"
        assert call_args.kwargs["port"] == 9010

    @patch("agentbeats.purple.server.uvicorn")
    def test_run_purple_agent_uses_default_port(self, mock_uvicorn):
        """run_purple_agent uses default_port when not in CLI."""
        from agentbeats.purple.server import run_purple_agent

        run_purple_agent(
            agent_factory=TestAgent,
            name="Test Agent",
            description="Test",
            default_port=9999,
            args=[],
        )

        call_args = mock_uvicorn.run.call_args
        assert call_args.kwargs["port"] == 9999

    @patch("agentbeats.purple.server.uvicorn")
    def test_run_purple_agent_uses_default_host(self, mock_uvicorn):
        """run_purple_agent uses default_host when not in CLI."""
        from agentbeats.purple.server import run_purple_agent

        run_purple_agent(
            agent_factory=TestAgent,
            name="Test Agent",
            description="Test",
            default_host="localhost",
            args=[],
        )

        call_args = mock_uvicorn.run.call_args
        assert call_args.kwargs["host"] == "localhost"

    @patch("agentbeats.purple.server.uvicorn")
    @patch("builtins.print")
    def test_run_purple_agent_prints_startup_info(self, mock_print, mock_uvicorn):
        """run_purple_agent prints startup information."""
        from agentbeats.purple.server import run_purple_agent

        run_purple_agent(
            agent_factory=TestAgent,
            name="My Cool Agent",
            description="Test",
            version="3.0.0",
            args=[],
        )

        # Check that startup info was printed
        print_calls = [str(call) for call in mock_print.call_args_list]
        print_output = " ".join(print_calls)

        assert "My Cool Agent" in print_output
        assert "3.0.0" in print_output
