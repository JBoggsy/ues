"""LLM-based Purple Agent example.

This example demonstrates how to build a Purple Agent that uses a Large Language
Model (LLM) to decide what actions to take. It shows:

1. How to structure prompts for the LLM
2. How to parse LLM responses into actions
3. How to execute actions via the UES API
4. How to handle multi-turn conversations with the LLM

This example uses a pluggable LLM interface so you can use any LLM provider
(OpenAI, Anthropic, local models, etc.).

Requirements:
    - An LLM client library (e.g., openai, anthropic, litellm)
    - API keys configured in environment variables

Usage:
    # With OpenAI
    export OPENAI_API_KEY=your-key
    uv run python -m agentbeats.purple.examples.llm_agent --host 0.0.0.0 --port 9009

Note:
    This is a reference implementation. For production use, you should:
    - Add better error handling
    - Implement retry logic for LLM calls
    - Add rate limiting
    - Consider using structured outputs (function calling)
"""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from client import AsyncUESClient

from agentbeats.purple import (
    AssessmentContext,
    AssessmentStartMessage,
    BaseAgent,
    EarlyCompletionMessage,
    TurnCompleteMessage,
    run_purple_agent,
)


logger = logging.getLogger(__name__)


# =============================================================================
# LLM Interface
# =============================================================================


@dataclass
class Message:
    """A message in the LLM conversation."""

    role: str  # "system", "user", or "assistant"
    content: str


@dataclass
class LLMResponse:
    """Response from an LLM."""

    content: str
    raw_response: Any = None


class LLMClient(ABC):
    """Abstract interface for LLM clients.

    Implement this interface to use any LLM provider.
    """

    @abstractmethod
    async def complete(self, messages: list[Message]) -> LLMResponse:
        """Generate a completion for the given messages.

        Args:
            messages: Conversation history as a list of messages.

        Returns:
            The LLM's response.
        """
        pass


class MockLLMClient(LLMClient):
    """Mock LLM client for testing without real API calls.

    This client returns predefined responses based on simple pattern matching.
    Useful for testing the agent structure without incurring API costs.
    """

    def __init__(self) -> None:
        """Initialize the mock client."""
        self._call_count = 0

    async def complete(self, messages: list[Message]) -> LLMResponse:
        """Return a mock response based on the conversation.

        Args:
            messages: Conversation history.

        Returns:
            A mock LLM response with actions to take.
        """
        self._call_count += 1

        # Get the last user message
        last_message = messages[-1].content if messages else ""

        # Simple pattern matching for demo purposes
        if "unread" in last_message.lower():
            return LLMResponse(
                content="""Based on the current state, I will mark unread emails as read.

ACTIONS:
- mark_emails_read: ["msg-1", "msg-2"]

REASONING: The user has unread emails that should be acknowledged."""
            )
        elif "complete" in last_message.lower() or self._call_count > 3:
            return LLMResponse(
                content="""All tasks appear to be complete.

ACTIONS:
- complete: "All emails processed and tasks completed"

REASONING: No more pending items to address."""
            )
        else:
            return LLMResponse(
                content="""I'll check the current state and take appropriate actions.

ACTIONS:
- check_state: true

REASONING: Need to assess the current environment before taking actions."""
            )


# =============================================================================
# Action Parser
# =============================================================================


@dataclass
class ParsedAction:
    """A parsed action from LLM output."""

    action_type: str
    parameters: dict[str, Any] = field(default_factory=dict)


def parse_llm_response(response: str) -> tuple[list[ParsedAction], str]:
    """Parse LLM response to extract actions and reasoning.

    This is a simple parser that looks for ACTIONS: and REASONING: sections.
    For production use, consider using structured outputs or function calling.

    Args:
        response: The raw LLM response text.

    Returns:
        Tuple of (list of parsed actions, reasoning text).
    """
    actions: list[ParsedAction] = []
    reasoning = ""

    # Extract reasoning
    reasoning_match = re.search(
        r"REASONING:\s*(.+?)(?=ACTIONS:|$)", response, re.DOTALL | re.IGNORECASE
    )
    if reasoning_match:
        reasoning = reasoning_match.group(1).strip()

    # Extract actions section
    actions_match = re.search(
        r"ACTIONS:\s*(.+?)(?=REASONING:|$)", response, re.DOTALL | re.IGNORECASE
    )
    if actions_match:
        actions_text = actions_match.group(1).strip()

        # Parse each action line
        for line in actions_text.split("\n"):
            line = line.strip()
            if line.startswith("-"):
                line = line[1:].strip()

            # Parse "action_type: parameters" format
            if ":" in line:
                action_type, params_str = line.split(":", 1)
                action_type = action_type.strip()
                params_str = params_str.strip()

                # Try to parse as JSON
                try:
                    if params_str.startswith("[") or params_str.startswith("{"):
                        params = json.loads(params_str)
                    else:
                        params = params_str.strip('"\'')
                except json.JSONDecodeError:
                    params = params_str

                actions.append(
                    ParsedAction(
                        action_type=action_type,
                        parameters={"value": params} if not isinstance(params, dict) else params,
                    )
                )

    return actions, reasoning


# =============================================================================
# LLM Agent Implementation
# =============================================================================


SYSTEM_PROMPT = """You are an AI personal assistant being evaluated on your ability to manage a user's digital life. You have access to email, SMS, calendar, and chat.

Your task is to help the user by taking actions based on their instructions and the current state of their environment.

When responding, format your output as:

ACTIONS:
- action_type: parameters

REASONING:
Your explanation of why you're taking these actions.

Available actions:
- mark_emails_read: ["message_id1", "message_id2", ...]
- archive_emails: ["message_id1", "message_id2", ...]
- send_email: {"to": "address", "subject": "...", "body": "..."}
- send_sms: {"to": "number", "content": "..."}
- send_chat: {"content": "..."}
- create_event: {"title": "...", "start": "ISO datetime", "end": "ISO datetime"}
- complete: "reason for completion"
- skip: "reason to wait"

Be efficient and complete tasks in as few turns as possible."""


class LLMAgent(BaseAgent):
    """An LLM-powered Purple Agent.

    This agent uses a Large Language Model to decide what actions to take
    based on the current environment state and user instructions.

    Attributes:
        llm: The LLM client to use for generating responses.
        conversation: History of messages exchanged with the LLM.
    """

    def __init__(self, llm: LLMClient | None = None) -> None:
        """Initialize the LLM agent.

        Args:
            llm: The LLM client to use. If None, uses MockLLMClient.
        """
        self.llm = llm or MockLLMClient()
        self.conversation: list[Message] = []

    async def on_assessment_start(
        self,
        message: AssessmentStartMessage,
        context: AssessmentContext,
        ues: AsyncUESClient,
    ) -> None:
        """Initialize the agent and retrieve user instructions.

        Args:
            message: The assessment start message from Green Agent.
            context: The assessment context for state tracking.
            ues: The UES client for API calls.
        """
        # Initialize conversation with system prompt
        self.conversation = [Message(role="system", content=SYSTEM_PROMPT)]

        # Get user instructions from chat
        chat_state = await ues.chat.get_state()
        user_instructions = ""
        for msg in chat_state.messages:
            if msg.role == "user":
                user_instructions = msg.content
                break

        context.user_instructions = user_instructions

        # Add initial context to conversation
        initial_message = f"""Assessment started at {message.current_time.isoformat()}.

User instructions:
{user_instructions}

Initial environment state:
- Email: {message.initial_state_summary.email.total} total, {message.initial_state_summary.email.unread} unread
- SMS: {message.initial_state_summary.sms.total} total, {message.initial_state_summary.sms.unread} unread
- Calendar: {message.initial_state_summary.calendar.total} total, {message.initial_state_summary.calendar.upcoming} upcoming
- Chat: {message.initial_state_summary.chat.total} total, {message.initial_state_summary.chat.unread} unread

What actions should I take?"""

        self.conversation.append(Message(role="user", content=initial_message))

        logger.info("LLM Agent initialized with user instructions")

    async def execute_turn(
        self,
        context: AssessmentContext,
        ues: AsyncUESClient,
    ) -> TurnCompleteMessage | EarlyCompletionMessage:
        """Execute a turn by consulting the LLM and taking actions.

        Args:
            context: The assessment context.
            ues: The UES client for API calls.

        Returns:
            TurnCompleteMessage or EarlyCompletionMessage.
        """
        # Get current state
        state_summary = await self._get_state_summary(ues)

        # Update conversation with current state (if not first turn)
        if context.turn_number > 0:
            self.conversation.append(
                Message(
                    role="user",
                    content=f"""Turn {context.turn_number + 1}. Current time: {context.current_time.isoformat()}.
Events processed since last turn: {context.events_processed_last_turn}

Current state:
{state_summary}

What actions should I take next?""",
                )
            )

        # Get LLM response
        response = await self.llm.complete(self.conversation)
        logger.info(f"LLM response: {response.content[:200]}...")

        # Add assistant response to conversation
        self.conversation.append(Message(role="assistant", content=response.content))

        # Parse actions from response
        actions, reasoning = parse_llm_response(response.content)
        logger.info(f"Parsed {len(actions)} actions: {[a.action_type for a in actions]}")

        # Execute actions
        actions_taken = 0
        for action in actions:
            if action.action_type == "complete":
                reason = action.parameters.get("value", "Tasks completed")
                return EarlyCompletionMessage(reason=str(reason))

            if action.action_type == "skip":
                # Skip this turn but continue
                pass
            else:
                # Execute the action
                executed = await self._execute_action(action, ues)
                if executed:
                    actions_taken += 1
                    context.record_action()

        return TurnCompleteMessage(
            actions_taken=actions_taken,
            notes=reasoning or f"Executed {actions_taken} actions",
            time_step="PT1H",  # Advance 1 hour
        )

    async def _get_state_summary(self, ues: AsyncUESClient) -> str:
        """Get a summary of the current environment state.

        Args:
            ues: The UES client.

        Returns:
            A formatted string summarizing the state.
        """
        email_state = await ues.email.get_state()
        sms_state = await ues.sms.get_state()

        unread_emails = [e for e in email_state.emails if not e.is_read]
        unread_sms = [m for m in sms_state.messages if not m.is_read]

        summary_parts = []

        if unread_emails:
            summary_parts.append(f"Unread emails ({len(unread_emails)}):")
            for email in unread_emails[:5]:  # Limit to 5
                summary_parts.append(
                    f"  - [{email.message_id}] From: {email.from_address}, "
                    f"Subject: {email.subject[:50]}"
                )
            if len(unread_emails) > 5:
                summary_parts.append(f"  ... and {len(unread_emails) - 5} more")

        if unread_sms:
            summary_parts.append(f"\nUnread SMS ({len(unread_sms)}):")
            for sms in unread_sms[:5]:
                summary_parts.append(
                    f"  - [{sms.message_id}] From: {sms.from_number}, "
                    f"Content: {sms.content[:50]}"
                )

        if not summary_parts:
            summary_parts.append("No unread items.")

        return "\n".join(summary_parts)

    async def _execute_action(
        self,
        action: ParsedAction,
        ues: AsyncUESClient,
    ) -> bool:
        """Execute a single action via the UES API.

        Args:
            action: The parsed action to execute.
            ues: The UES client.

        Returns:
            True if the action was executed successfully.
        """
        try:
            if action.action_type == "mark_emails_read":
                message_ids = action.parameters.get("value", [])
                if isinstance(message_ids, list) and message_ids:
                    await ues.email.read(message_ids)
                    logger.info(f"Marked {len(message_ids)} emails as read")
                    return True

            elif action.action_type == "archive_emails":
                message_ids = action.parameters.get("value", [])
                if isinstance(message_ids, list) and message_ids:
                    await ues.email.archive(message_ids)
                    logger.info(f"Archived {len(message_ids)} emails")
                    return True

            elif action.action_type == "send_email":
                params = action.parameters
                await ues.email.send(
                    from_address=params.get("from", "user@example.com"),
                    to_addresses=[params.get("to", "")],
                    subject=params.get("subject", ""),
                    body_text=params.get("body", ""),
                )
                logger.info(f"Sent email to {params.get('to')}")
                return True

            elif action.action_type == "send_sms":
                params = action.parameters
                await ues.sms.send(
                    to_number=params.get("to", ""),
                    content=params.get("content", ""),
                )
                logger.info(f"Sent SMS to {params.get('to')}")
                return True

            elif action.action_type == "send_chat":
                params = action.parameters
                await ues.chat.send(
                    content=params.get("content", ""),
                    role="assistant",
                )
                logger.info("Sent chat message")
                return True

            elif action.action_type == "create_event":
                params = action.parameters
                await ues.calendar.create(
                    title=params.get("title", ""),
                    start=params.get("start", ""),
                    end=params.get("end", params.get("start", "")),
                )
                logger.info(f"Created calendar event: {params.get('title')}")
                return True

            elif action.action_type == "check_state":
                # This is a no-op action that doesn't count
                return False

            else:
                logger.warning(f"Unknown action type: {action.action_type}")
                return False

        except Exception as e:
            logger.error(f"Error executing action {action.action_type}: {e}")
            return False


# =============================================================================
# OpenAI Client Implementation (Optional)
# =============================================================================


class OpenAIClient(LLMClient):
    """LLM client using OpenAI's API.

    Requires the `openai` package and OPENAI_API_KEY environment variable.

    Example:
        client = OpenAIClient(model="gpt-4o")
        agent = LLMAgent(llm=client)
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> None:
        """Initialize the OpenAI client.

        Args:
            model: The model to use (default: gpt-4o-mini).
            temperature: Sampling temperature (default: 0.7).
            max_tokens: Maximum tokens in response (default: 1000).
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazily initialize the OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI()
            except ImportError:
                raise ImportError(
                    "openai package not installed. "
                    "Install with: pip install openai"
                )
        return self._client

    async def complete(self, messages: list[Message]) -> LLMResponse:
        """Generate a completion using OpenAI's API.

        Args:
            messages: Conversation history.

        Returns:
            The model's response.
        """
        client = self._get_client()

        openai_messages = [
            {"role": msg.role, "content": msg.content} for msg in messages
        ]

        response = await client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        content = response.choices[0].message.content or ""
        return LLMResponse(content=content, raw_response=response)


# =============================================================================
# Entry Point
# =============================================================================


def create_llm_agent() -> LLMAgent:
    """Create an LLM agent with the best available LLM client.

    Tries to use OpenAI if available, falls back to mock client.

    Returns:
        An LLMAgent instance.
    """
    import os

    if os.environ.get("OPENAI_API_KEY"):
        try:
            logger.info("Using OpenAI client")
            return LLMAgent(llm=OpenAIClient())
        except ImportError:
            logger.warning("OpenAI key set but openai package not installed")

    logger.info("Using mock LLM client")
    return LLMAgent(llm=MockLLMClient())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    agent = create_llm_agent()
    run_purple_agent(
        agent=agent,
        name="LLM Personal Assistant",
        description="An LLM-powered agent that manages email, SMS, and calendar",
        version="1.0.0",
    )
