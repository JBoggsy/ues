"""Purple Agent infrastructure for UES AgentBeats benchmark.

This package provides common infrastructure for implementing Purple Agents
(participants) in the UES (User Environment Simulator) AgentBeats benchmark.

Components:
    - schemas: A2A message schemas for Green-Purple communication
    - context: AssessmentContext for tracking state across turns
    - base_agent: BaseAgent abstract class defining the agent interface
    - executor: PurpleExecutor for A2A protocol lifecycle management
    - server: Server setup utilities for running Purple Agent servers

Example:
    Creating and running a simple Purple Agent::

        from datetime import timedelta

        from agentbeats.purple import (
            BaseAgent,
            AssessmentContext,
            AssessmentStartMessage,
            TurnCompleteMessage,
            EarlyCompletionMessage,
            TurnResponse,
            run_purple_agent,
        )
        from client import AsyncUESClient


        class MyAgent(BaseAgent):
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

                # Check if done
                if context.actions_this_turn == 0:
                    return EarlyCompletionMessage(reason="All emails processed")

                # Return turn complete
                return TurnCompleteMessage(
                    actions_taken=context.actions_this_turn,
                    notes="Marked unread emails as read",
                    time_step=timedelta(hours=1),
                )


        if __name__ == "__main__":
            run_purple_agent(
                agent_factory=MyAgent,
                name="Email Reader Agent",
                description="Marks all unread emails as read",
            )
"""

# =============================================================================
# Schemas (A2A Messages)
# =============================================================================

from agentbeats.purple.schemas import (
    # State summaries
    ModalityCounts,
    InitialStateSummary,
    # Green → Purple messages
    AssessmentStartMessage,
    TurnStartMessage,
    AssessmentCompleteMessage,
    AssessmentCompleteReason,
    DEFAULT_ASSESSMENT_INSTRUCTIONS,
    # Purple → Green messages
    TurnCompleteMessage,
    EarlyCompletionMessage,
    # Type aliases
    GreenToPurpleMessage,
    PurpleToGreenMessage,
    TurnResponse,
    # Purple-specific schemas
    ParsedGoal,
    ParsedConstraint,
    ParsedUserInstructions,
)

# =============================================================================
# Context
# =============================================================================

from agentbeats.purple.context import (
    AssessmentContext,
    create_context_from_assessment_start,
)

# =============================================================================
# Base Agent
# =============================================================================

from agentbeats.purple.base_agent import (
    BaseAgent,
    SimpleAgent,
)

# =============================================================================
# Executor (A2A Lifecycle)
# =============================================================================

from agentbeats.purple.executor import (
    PurpleExecutor,
    MessageParseError,
    parse_green_message,
    serialize_response,
)

# =============================================================================
# Server Setup
# =============================================================================

from agentbeats.purple.server import (
    create_agent_card,
    create_cli_parser,
    create_purple_server,
    run_purple_agent,
)

# =============================================================================
# UES Client (Tracked Wrapper)
# =============================================================================

from agentbeats.purple.ues_client import (
    TrackedAsyncUESClient,
    TrackedCalendarClient,
    TrackedChatClient,
    TrackedEmailClient,
    TrackedLocationClient,
    TrackedSMSClient,
    TrackedWeatherClient,
    create_tracked_client,
)

# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Schemas - State summaries
    "ModalityCounts",
    "InitialStateSummary",
    # Schemas - Green → Purple messages
    "AssessmentStartMessage",
    "TurnStartMessage",
    "AssessmentCompleteMessage",
    "AssessmentCompleteReason",
    "DEFAULT_ASSESSMENT_INSTRUCTIONS",
    # Schemas - Purple → Green messages
    "TurnCompleteMessage",
    "EarlyCompletionMessage",
    # Schemas - Type aliases
    "GreenToPurpleMessage",
    "PurpleToGreenMessage",
    "TurnResponse",
    # Schemas - Purple-specific
    "ParsedGoal",
    "ParsedConstraint",
    "ParsedUserInstructions",
    # Context
    "AssessmentContext",
    "create_context_from_assessment_start",
    # Base Agent
    "BaseAgent",
    "SimpleAgent",
    # Executor
    "PurpleExecutor",
    "MessageParseError",
    "parse_green_message",
    "serialize_response",
    # Server
    "create_agent_card",
    "create_cli_parser",
    "create_purple_server",
    "run_purple_agent",
    # UES Client
    "TrackedAsyncUESClient",
    "TrackedCalendarClient",
    "TrackedChatClient",
    "TrackedEmailClient",
    "TrackedLocationClient",
    "TrackedSMSClient",
    "TrackedWeatherClient",
    "create_tracked_client",
]
