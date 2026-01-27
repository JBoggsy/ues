#!/usr/bin/env python3
"""Simple Purple Agent Example.

This module demonstrates a minimal Purple Agent implementation that:
1. Retrieves user instructions from chat
2. Marks unread emails as read
3. Signals completion when all emails are processed

This is a reference implementation showing the Purple Agent lifecycle and
how to use the infrastructure components.

Usage:
    # Run directly
    python -m agentbeats.purple.examples.simple_agent

    # Or with custom port
    python -m agentbeats.purple.examples.simple_agent --port 9010

    # With custom host and card URL
    python -m agentbeats.purple.examples.simple_agent --host 0.0.0.0 --port 9010 --card-url http://my-server.com/

Example Assessment Flow:
    1. Green Agent sends assessment_start with UES credentials
    2. This agent retrieves user instructions from /chat/state
    3. Agent marks all unread emails as read
    4. Returns TurnCompleteMessage or EarlyCompletionMessage
    5. On turn_start, repeats step 3-4
    6. When no unread emails remain, signals early completion
"""

from datetime import timedelta
from typing import TYPE_CHECKING

from agentbeats.purple import (
    BaseAgent,
    AssessmentContext,
    AssessmentStartMessage,
    TurnStartMessage,
    AssessmentCompleteMessage,
    TurnCompleteMessage,
    EarlyCompletionMessage,
    TurnResponse,
    run_purple_agent,
)

if TYPE_CHECKING:
    from client import AsyncUESClient


class SimpleEmailAgent(BaseAgent):
    """A simple agent that marks all unread emails as read.

    This agent demonstrates the basic Purple Agent lifecycle:
    - Retrieving user instructions on assessment start
    - Querying modality state (email)
    - Taking actions (marking emails as read)
    - Tracking actions with context.record_action()
    - Returning appropriate turn responses
    - Signaling early completion when done

    Attributes:
        None (stateless except for context)

    Example:
        Running the agent::

            if __name__ == "__main__":
                run_purple_agent(
                    agent_factory=SimpleEmailAgent,
                    name="Simple Email Agent",
                    description="Marks all emails as read",
                )
    """

    async def on_assessment_start(
        self,
        message: AssessmentStartMessage,
        context: AssessmentContext,
        ues: "AsyncUESClient",
    ) -> None:
        """Initialize agent state and retrieve user instructions.

        Retrieves the user's instructions from the chat modality. The first
        message in chat contains the user's goals and constraints.

        Args:
            message: Assessment start message with UES credentials.
            context: Assessment context to store instructions in.
            ues: Async UES client for API calls.
        """
        # Retrieve user instructions from chat
        chat_state = await ues.chat.get_state()

        if chat_state.messages:
            # Store raw instructions in context
            user_message = chat_state.messages[0]
            context.user_instructions = user_message.content

            # Log what we received (for debugging)
            print(f"[SimpleEmailAgent] Received instructions: {context.user_instructions[:100]}...")
        else:
            print("[SimpleEmailAgent] Warning: No user instructions found in chat")
            context.user_instructions = "No instructions provided"

        # Log initial state
        if context.initial_state:
            print(f"[SimpleEmailAgent] Initial state:")
            if context.initial_state.email:
                print(f"  - Emails: {context.initial_state.email.total} total, "
                      f"{context.initial_state.email.unread or 0} unread")
            if context.initial_state.calendar:
                print(f"  - Calendar: {context.initial_state.calendar.total} events")

    async def execute_turn(
        self,
        context: AssessmentContext,
        ues: "AsyncUESClient",
    ) -> TurnResponse:
        """Execute a single turn: mark unread emails as read.

        Queries the current email state and marks any unread emails as read.
        If no unread emails remain, signals early completion.

        Args:
            context: Assessment context with current state.
            ues: Async UES client for API calls.

        Returns:
            TurnCompleteMessage with action count and time step,
            or EarlyCompletionMessage if all emails are processed.
        """
        print(f"[SimpleEmailAgent] Turn {context.turn_number}: Starting...")

        # Get current email state
        email_state = await ues.email.get_state()

        # Find unread emails
        unread_emails = [e for e in email_state.emails if not e.read]

        if not unread_emails:
            # No unread emails - we're done!
            print(f"[SimpleEmailAgent] No unread emails. Signaling completion.")
            return EarlyCompletionMessage(
                reason="All emails have been processed (marked as read)",
            )

        # Mark each unread email as read
        print(f"[SimpleEmailAgent] Found {len(unread_emails)} unread emails")

        for email in unread_emails:
            await ues.email.mark_read(email.message_id)
            context.record_action()
            print(f"  - Marked email '{email.subject[:30]}...' as read")

        # Return turn complete with time step
        return TurnCompleteMessage(
            actions_taken=context.actions_this_turn,
            notes=f"Marked {context.actions_this_turn} emails as read",
            time_step=timedelta(hours=1),  # Advance simulation by 1 hour
        )

    async def on_turn_start(
        self,
        message: TurnStartMessage,
        context: AssessmentContext,
    ) -> None:
        """Handle the start of a new turn.

        Updates context with new time and event count. Logs turn information.

        Args:
            message: Turn start message with current time and events.
            context: Assessment context to update.
        """
        # Call parent to update context
        await super().on_turn_start(message, context)

        print(f"[SimpleEmailAgent] Turn {context.turn_number}: "
              f"Time advanced to {context.current_time}, "
              f"{message.events_processed} events processed")

    async def on_assessment_complete(
        self,
        message: AssessmentCompleteMessage,
        context: AssessmentContext,
    ) -> None:
        """Handle assessment completion.

        Logs final statistics.

        Args:
            message: Assessment complete message with reason.
            context: Final assessment context.
        """
        print(f"[SimpleEmailAgent] Assessment complete!")
        print(f"  - Reason: {message.reason}")
        print(f"  - Total turns: {context.turn_number + 1}")
        print(f"  - Total actions: {context.total_actions}")
        print(f"  - Elapsed time: {context.elapsed_time:.1f}s")


def main():
    """Run the Simple Email Agent server."""
    run_purple_agent(
        agent_factory=SimpleEmailAgent,
        name="Simple Email Agent",
        description=(
            "A demonstration Purple Agent that marks all unread emails as read. "
            "This is a minimal example showing the Purple Agent lifecycle."
        ),
        version="1.0.0",
        default_port=9010,  # Use different port than Green Agent (9009)
    )


if __name__ == "__main__":
    main()
