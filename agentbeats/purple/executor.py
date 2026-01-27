"""A2A AgentExecutor for Purple Agent implementations.

This module provides the PurpleExecutor class that handles the A2A protocol
lifecycle for Purple Agents. It manages incoming messages from the Green Agent,
coordinates with agent implementations, and sends responses back.

The executor handles:
    - Parsing incoming A2A messages (assessment_start, turn_start, assessment_complete)
    - Creating and managing AssessmentContext for each assessment
    - Instantiating AsyncUESClient with correct authentication
    - Calling agent lifecycle methods at appropriate times
    - Serializing and sending responses back to Green Agent

Example:
    Creating an executor with an agent factory::

        from agentbeats.purple.executor import PurpleExecutor
        from my_agent import MyAgent

        # Create executor with factory function
        executor = PurpleExecutor(agent_factory=MyAgent)

        # The executor is used by the A2A server (handled automatically)
        # See server.py for how to run a complete Purple Agent server.
"""

import json
from typing import Callable, Protocol

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    Task,
    TaskState,
    UnsupportedOperationError,
    InvalidRequestError,
)
from a2a.utils.errors import ServerError
from a2a.utils import get_message_text, new_agent_text_message, new_task

from client import AsyncUESClient
from agentbeats.purple.context import AssessmentContext, create_context_from_assessment_start
from agentbeats.purple.schemas import (
    AssessmentStartMessage,
    TurnStartMessage,
    AssessmentCompleteMessage,
    TurnCompleteMessage,
    EarlyCompletionMessage,
    TurnResponse,
)


# Terminal task states - no further processing allowed
TERMINAL_STATES = {
    TaskState.completed,
    TaskState.canceled,
    TaskState.failed,
    TaskState.rejected,
}


class AgentFactory(Protocol):
    """Protocol for agent factory functions.

    An agent factory is a callable that creates a new BaseAgent instance.
    This allows for dependency injection and testing.
    """

    def __call__(self) -> "BaseAgent":
        """Create a new agent instance.

        Returns:
            A new BaseAgent instance.
        """
        ...


# Avoid circular import - BaseAgent is only used for type hints
from agentbeats.purple.base_agent import BaseAgent


class MessageParseError(Exception):
    """Raised when a Green Agent message cannot be parsed.

    Attributes:
        raw_message: The original message text that failed to parse.
        reason: Description of why parsing failed.
    """

    def __init__(self, raw_message: str, reason: str) -> None:
        self.raw_message = raw_message
        self.reason = reason
        super().__init__(f"Failed to parse Green Agent message: {reason}")


def parse_green_message(
    text: str,
) -> AssessmentStartMessage | TurnStartMessage | AssessmentCompleteMessage:
    """Parse a message from the Green Agent.

    Determines the message type based on fields present:
        - AssessmentStartMessage: Has ues_url, api_key, assessment_instructions
        - TurnStartMessage: Has current_time, events_processed (no ues_url)
        - AssessmentCompleteMessage: Has reason field

    Args:
        text: JSON string message from Green Agent.

    Returns:
        Parsed message of the appropriate type.

    Raises:
        MessageParseError: If the message cannot be parsed.

    Example:
        >>> text = '{"ues_url": "http://localhost:8000", "api_key": "key123", ...}'
        >>> msg = parse_green_message(text)
        >>> isinstance(msg, AssessmentStartMessage)
        True
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise MessageParseError(text, f"Invalid JSON: {e}")

    if not isinstance(data, dict):
        raise MessageParseError(text, f"Expected object, got {type(data).__name__}")

    # Determine message type based on fields
    # AssessmentStartMessage has ues_url and api_key
    if "ues_url" in data and "api_key" in data:
        try:
            return AssessmentStartMessage.model_validate(data)
        except Exception as e:
            raise MessageParseError(text, f"Invalid AssessmentStartMessage: {e}")

    # AssessmentCompleteMessage has reason field (enum value)
    if "reason" in data and "events_processed" not in data:
        try:
            return AssessmentCompleteMessage.model_validate(data)
        except Exception as e:
            raise MessageParseError(text, f"Invalid AssessmentCompleteMessage: {e}")

    # TurnStartMessage has current_time and events_processed
    if "current_time" in data and "events_processed" in data:
        try:
            return TurnStartMessage.model_validate(data)
        except Exception as e:
            raise MessageParseError(text, f"Invalid TurnStartMessage: {e}")

    raise MessageParseError(
        text,
        "Cannot determine message type: expected AssessmentStartMessage "
        "(ues_url, api_key), TurnStartMessage (current_time, events_processed), "
        "or AssessmentCompleteMessage (reason)",
    )


def serialize_response(response: TurnResponse) -> str:
    """Serialize a Purple Agent response for A2A transmission.

    Args:
        response: TurnCompleteMessage or EarlyCompletionMessage.

    Returns:
        JSON string suitable for A2A transmission.

    Example:
        >>> response = TurnCompleteMessage(actions_taken=3, notes="Done")
        >>> json_str = serialize_response(response)
        >>> print(json_str)
        '{"actions_taken":3,"notes":"Done",...}'
    """
    return response.model_dump_json()


class PurpleExecutor(AgentExecutor):
    """A2A executor for Purple Agent implementations.

    Manages the A2A protocol lifecycle and coordinates with a BaseAgent
    implementation. For each assessment context, the executor:
    1. Creates an agent instance using the factory
    2. Manages the AssessmentContext
    3. Creates and configures the AsyncUESClient
    4. Routes messages to the appropriate agent lifecycle methods
    5. Serializes and sends responses

    Attributes:
        agents: Map of context_id to agent instances.
        contexts: Map of context_id to assessment contexts.
        ues_clients: Map of context_id to UES client instances.

    Example:
        Basic usage with a custom agent::

            from agentbeats.purple.executor import PurpleExecutor

            class MyAgent(BaseAgent):
                async def on_assessment_start(self, message, context, ues):
                    ...
                async def execute_turn(self, context, ues):
                    return TurnCompleteMessage(actions_taken=0)

            executor = PurpleExecutor(agent_factory=MyAgent)
    """

    def __init__(self, agent_factory: Callable[[], BaseAgent]) -> None:
        """Initialize the executor with an agent factory.

        Args:
            agent_factory: Callable that creates a new BaseAgent instance.
                Called once per assessment context when assessment_start is received.
        """
        self._agent_factory = agent_factory
        self.agents: dict[str, BaseAgent] = {}
        self.contexts: dict[str, AssessmentContext] = {}
        self.ues_clients: dict[str, AsyncUESClient] = {}

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Handle an incoming A2A request from the Green Agent.

        Routes the message to the appropriate handler based on message type:
            - AssessmentStartMessage → _handle_assessment_start
            - TurnStartMessage → _handle_turn_start
            - AssessmentCompleteMessage → _handle_assessment_complete

        Args:
            context: The A2A request context containing the message and task.
            event_queue: Queue for emitting task events and updates.

        Raises:
            ServerError: If the request is invalid or cannot be processed.
        """
        msg = context.message
        if not msg:
            raise ServerError(
                error=InvalidRequestError(message="Missing message in request")
            )

        task = context.current_task
        if task and task.status.state in TERMINAL_STATES:
            raise ServerError(
                error=InvalidRequestError(
                    message=f"Task {task.id} already processed (state: {task.status.state})"
                )
            )

        # Create task if this is a new request
        if not task:
            task = new_task(msg)
            await event_queue.enqueue_event(task)

        context_id = task.context_id

        # Create updater for progress reporting
        updater = TaskUpdater(event_queue, task.id, context_id)

        await updater.start_work()
        try:
            # Parse the incoming message
            text = get_message_text(msg)
            parsed = parse_green_message(text)

            # Route to appropriate handler
            if isinstance(parsed, AssessmentStartMessage):
                await self._handle_assessment_start(parsed, context_id, updater)
            elif isinstance(parsed, TurnStartMessage):
                await self._handle_turn_start(parsed, context_id, updater)
            elif isinstance(parsed, AssessmentCompleteMessage):
                await self._handle_assessment_complete(parsed, context_id, updater)

            # Only complete if not already in terminal state
            if not updater._terminal_state_reached:
                await updater.complete()

        except MessageParseError as e:
            await updater.failed(
                new_agent_text_message(
                    f"Message parse error: {e.reason}",
                    context_id=context_id,
                    task_id=task.id,
                )
            )
        except Exception as e:
            await updater.failed(
                new_agent_text_message(
                    f"Agent error: {e}",
                    context_id=context_id,
                    task_id=task.id,
                )
            )
        finally:
            # Clean up if assessment is complete or failed
            # Note: We don't clean up here since turn_start may still come
            # Cleanup happens in _handle_assessment_complete
            pass

    async def _handle_assessment_start(
        self,
        message: AssessmentStartMessage,
        context_id: str,
        updater: TaskUpdater,
    ) -> None:
        """Handle the assessment_start message.

        Creates the agent, context, and UES client, then calls the agent's
        on_assessment_start method followed by execute_turn for the first turn.

        Args:
            message: The parsed AssessmentStartMessage.
            context_id: The A2A context/task ID.
            updater: TaskUpdater for sending responses.
        """
        # Create context from the assessment start message
        assessment_ctx = create_context_from_assessment_start(
            assessment_id=context_id,
            ues_url=message.ues_url,
            api_key=message.api_key,
            current_time=message.current_time,
            initial_state=message.initial_state_summary,
        )

        # Create agent instance
        agent = self._agent_factory()

        # Create UES client
        ues = AsyncUESClient(
            base_url=message.ues_url,
            api_key=message.api_key,
        )

        # Store for later turns
        self.agents[context_id] = agent
        self.contexts[context_id] = assessment_ctx
        self.ues_clients[context_id] = ues

        # Call agent's assessment start handler
        await agent.on_assessment_start(message, assessment_ctx, ues)

        # Execute first turn immediately (no turn_start for first turn)
        response = await agent.execute_turn(assessment_ctx, ues)

        # Send response
        await self._send_response(response, context_id, updater)

    async def _handle_turn_start(
        self,
        message: TurnStartMessage,
        context_id: str,
        updater: TaskUpdater,
    ) -> None:
        """Handle a turn_start message.

        Updates the context with new time and event count, calls the agent's
        on_turn_start method, then calls execute_turn.

        Args:
            message: The parsed TurnStartMessage.
            context_id: The A2A context/task ID.
            updater: TaskUpdater for sending responses.

        Raises:
            ValueError: If no agent/context exists for this context_id.
        """
        # Get existing agent and context
        agent = self.agents.get(context_id)
        ctx = self.contexts.get(context_id)
        ues = self.ues_clients.get(context_id)

        if not agent or not ctx or not ues:
            raise ValueError(
                f"No active assessment for context {context_id}. "
                "Did you receive assessment_start first?"
            )

        # Call agent's turn start handler (updates context)
        await agent.on_turn_start(message, ctx)

        # Execute the turn
        response = await agent.execute_turn(ctx, ues)

        # Send response
        await self._send_response(response, context_id, updater)

    async def _handle_assessment_complete(
        self,
        message: AssessmentCompleteMessage,
        context_id: str,
        updater: TaskUpdater,
    ) -> None:
        """Handle the assessment_complete message.

        Calls the agent's on_assessment_complete method and cleans up resources.

        Args:
            message: The parsed AssessmentCompleteMessage.
            context_id: The A2A context/task ID.
            updater: TaskUpdater for sending responses.
        """
        # Get existing agent and context
        agent = self.agents.get(context_id)
        ctx = self.contexts.get(context_id)

        if agent and ctx:
            # Call agent's cleanup handler
            await agent.on_assessment_complete(message, ctx)

        # Clean up resources
        self._cleanup_context(context_id)

        # No response needed for assessment_complete - task just completes

    async def _send_response(
        self,
        response: TurnResponse,
        context_id: str,
        updater: TaskUpdater,
    ) -> None:
        """Serialize and send a response to the Green Agent.

        Args:
            response: TurnCompleteMessage or EarlyCompletionMessage.
            context_id: The A2A context/task ID.
            updater: TaskUpdater for sending the response.
        """
        # Serialize the response
        json_response = serialize_response(response)

        # Send as a text message
        await updater.update_status(
            TaskState.working,
            new_agent_text_message(
                json_response,
                context_id=context_id,
            ),
        )

    def _cleanup_context(self, context_id: str) -> None:
        """Clean up resources for a completed assessment.

        Args:
            context_id: The A2A context/task ID to clean up.
        """
        self.agents.pop(context_id, None)
        self.contexts.pop(context_id, None)
        self.ues_clients.pop(context_id, None)

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Handle a cancellation request.

        Cleans up the assessment context if one exists.

        Args:
            context: The A2A request context.
            event_queue: Queue for emitting events.

        Raises:
            ServerError: Cancellation is not fully supported yet.
        """
        # Clean up if we have an active context
        task = context.current_task
        if task:
            self._cleanup_context(task.context_id)

        # For now, raise unsupported - could implement graceful shutdown later
        raise ServerError(error=UnsupportedOperationError())
