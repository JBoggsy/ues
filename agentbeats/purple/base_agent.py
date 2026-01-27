"""Base agent class for Purple Agent implementations.

This module defines the abstract interface that all Purple Agent implementations
must follow. The BaseAgent class provides the contract for the assessment lifecycle
methods that the executor will call.

Example:
    Implementing a simple agent::

        from datetime import timedelta

        from agentbeats.purple.base_agent import BaseAgent
        from agentbeats.purple.context import AssessmentContext
        from agentbeats.purple.schemas import (
            AssessmentStartMessage,
            TurnStartMessage,
            AssessmentCompleteMessage,
            TurnCompleteMessage,
            EarlyCompletionMessage,
            TurnResponse,
        )
        from client import AsyncUESClient


        class MySimpleAgent(BaseAgent):
            '''A simple agent that marks all emails as read.'''

            async def on_assessment_start(
                self,
                message: AssessmentStartMessage,
                context: AssessmentContext,
                ues: AsyncUESClient,
            ) -> None:
                # Retrieve user instructions from chat
                chat_state = await ues.chat.get_state()
                if chat_state.messages:
                    context.user_instructions = chat_state.messages[0].content

            async def execute_turn(
                self,
                context: AssessmentContext,
                ues: AsyncUESClient,
            ) -> TurnResponse:
                # Get current email state
                email_state = await ues.email.get_state()

                # Mark all unread emails as read
                for email in email_state.emails:
                    if not email.read:
                        await ues.email.mark_read(email.message_id)
                        context.record_action()

                # Return turn complete
                return TurnCompleteMessage(
                    actions_taken=context.actions_this_turn,
                    notes="Marked all unread emails as read",
                    time_step=timedelta(hours=1),
                )
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from agentbeats.purple.context import AssessmentContext
from agentbeats.purple.schemas import (
    AssessmentCompleteMessage,
    AssessmentStartMessage,
    EarlyCompletionMessage,
    TurnCompleteMessage,
    TurnStartMessage,
    TurnResponse,
)

# Use TYPE_CHECKING to avoid circular imports with the UES client
if TYPE_CHECKING:
    from client import AsyncUESClient


class BaseAgent(ABC):
    """Abstract base class for Purple Agent implementations.

    Subclasses must implement the required lifecycle methods:
        - on_assessment_start: Called when assessment begins
        - execute_turn: Called to execute each turn

    Optional lifecycle methods (with default implementations):
        - on_turn_start: Called at the start of each turn (after first)
        - on_assessment_complete: Called when assessment ends

    The executor manages the A2A protocol and calls these methods at the
    appropriate times. Agents should focus on the task logic without
    worrying about message serialization or protocol details.

    Attributes:
        None required. Subclasses can add their own attributes.

    Example:
        Minimal agent implementation::

            class MinimalAgent(BaseAgent):
                async def on_assessment_start(self, message, context, ues):
                    chat_state = await ues.chat.get_state()
                    context.user_instructions = chat_state.messages[0].content

                async def execute_turn(self, context, ues):
                    return TurnCompleteMessage(
                        actions_taken=0,
                        notes="Did nothing",
                    )
    """

    @abstractmethod
    async def on_assessment_start(
        self,
        message: AssessmentStartMessage,
        context: AssessmentContext,
        ues: "AsyncUESClient",
    ) -> None:
        """Called when the assessment begins.

        This is the first lifecycle method called. Implementations should:
        1. Query /chat/state to retrieve user instructions
        2. Parse and understand the goals and constraints
        3. Set up any agent-specific state

        The user instructions are delivered via the chat modality as directed
        by the assessment_instructions field in the message.

        Args:
            message: The assessment_start message from the Green Agent containing:
                - ues_url: Base URL for UES REST API
                - api_key: API key for authentication
                - assessment_instructions: Fixed text directing to check chat
                - current_time: Starting simulator time
                - initial_state_summary: Counts of items in each modality
            context: The assessment context (mutable). Store user_instructions
                and any parsed data here.
            ues: Async UES client for making API calls. Already configured
                with the correct URL and API key.

        Note:
            After this method returns, execute_turn will be called immediately
            to begin the first turn.

        Example:
            Retrieving user instructions::

                async def on_assessment_start(self, message, context, ues):
                    # Get user instructions from chat
                    chat_state = await ues.chat.get_state()
                    if chat_state.messages:
                        user_msg = chat_state.messages[0]
                        context.user_instructions = user_msg.content

                    # Optionally parse into structured format
                    context.parsed_instructions = self._parse_instructions(
                        context.user_instructions
                    )
        """
        pass

    @abstractmethod
    async def execute_turn(
        self,
        context: AssessmentContext,
        ues: "AsyncUESClient",
    ) -> TurnResponse:
        """Execute a single turn of the assessment.

        This is the core method where the agent does its work. Implementations
        should:
        1. Query state from relevant modalities
        2. Decide what actions to take
        3. Execute actions via UES API
        4. Track actions using context.record_action()
        5. Return TurnCompleteMessage or EarlyCompletionMessage

        This method is called:
        - Immediately after on_assessment_start (first turn)
        - After each on_turn_start (subsequent turns)

        Args:
            context: The assessment context containing:
                - current_time: Current simulator time
                - turn_number: Current turn (0 for first turn)
                - user_instructions: Raw instructions from chat
                - parsed_instructions: Optional structured instructions
                - custom_data: Agent-specific storage
            ues: Async UES client for making API calls.

        Returns:
            TurnCompleteMessage: Signal turn completion with:
                - actions_taken: Number of actions this turn
                - notes: Optional reasoning/explanation
                - time_step: Optional duration to advance time

            EarlyCompletionMessage: Signal early assessment completion with:
                - reason: Optional explanation for ending early

        Example:
            Basic turn execution::

                async def execute_turn(self, context, ues):
                    # Check if we have pending work
                    email_state = await ues.email.get_state()
                    unread = [e for e in email_state.emails if not e.read]

                    if not unread:
                        return EarlyCompletionMessage(
                            reason="No more unread emails to process"
                        )

                    # Process emails
                    for email in unread:
                        await ues.email.mark_read(email.message_id)
                        context.record_action()

                    return TurnCompleteMessage(
                        actions_taken=context.actions_this_turn,
                        notes=f"Processed {len(unread)} emails",
                        time_step=timedelta(hours=1),
                    )
        """
        pass

    async def on_turn_start(
        self,
        message: TurnStartMessage,
        context: AssessmentContext,
    ) -> None:
        """Called at the start of each turn after the first.

        This optional method is called after the Green Agent advances time
        and sends a turn_start message. The default implementation updates
        the context with the new time and event count.

        Override this method if you need to perform setup at the start of
        each turn, such as:
        - Checking what events occurred
        - Updating internal state
        - Logging turn transitions

        Args:
            message: The turn_start message containing:
                - current_time: New simulator time after advancement
                - events_processed: Number of events that fired
            context: The assessment context (mutable).

        Note:
            After this method returns, execute_turn will be called.

        Example:
            Custom turn start handling::

                async def on_turn_start(self, message, context):
                    # Call default implementation to update context
                    await super().on_turn_start(message, context)

                    # Log if new events arrived
                    if message.events_processed > 0:
                        print(f"Turn {context.turn_number}: "
                              f"{message.events_processed} new events")
        """
        context.start_new_turn(message.current_time, message.events_processed)

    async def on_assessment_complete(
        self,
        message: AssessmentCompleteMessage,
        context: AssessmentContext,
    ) -> None:
        """Called when the assessment ends.

        This optional method is called when the Green Agent sends an
        assessment_complete message. Override to perform cleanup or
        final logging.

        Args:
            message: The assessment_complete message containing:
                - reason: Why the assessment ended (scenario_complete,
                  early_completion, timeout, error)
                - message: Optional explanation
            context: The final assessment context.

        Example:
            Logging completion::

                async def on_assessment_complete(self, message, context):
                    print(f"Assessment {context.assessment_id} completed")
                    print(f"Reason: {message.reason}")
                    print(f"Total actions: {context.total_actions}")
                    print(f"Turns: {context.turn_number + 1}")
        """
        pass


class SimpleAgent(BaseAgent):
    """A minimal agent implementation for testing and examples.

    This agent does nothing except retrieve user instructions and
    immediately signal completion. Useful as a template or for
    testing the infrastructure.
    """

    async def on_assessment_start(
        self,
        message: AssessmentStartMessage,
        context: AssessmentContext,
        ues: "AsyncUESClient",
    ) -> None:
        """Retrieve user instructions from chat."""
        chat_state = await ues.chat.get_state()
        if chat_state.messages:
            context.user_instructions = chat_state.messages[0].content

    async def execute_turn(
        self,
        context: AssessmentContext,
        ues: "AsyncUESClient",
    ) -> TurnResponse:
        """Complete immediately without taking actions."""
        return EarlyCompletionMessage(
            reason="SimpleAgent does not perform any actions"
        )


__all__ = [
    "BaseAgent",
    "SimpleAgent",
]
