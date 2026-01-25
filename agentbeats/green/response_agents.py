"""Response Generator Sub-agents for character-based event generation.

This module implements the Response Generator Sub-agents that monitor Purple Agent
actions and generate realistic character responses. When the Purple Agent sends
emails, SMS, or calendar invites to scenario characters, these agents:

1. Detect outgoing messages to known characters
2. Check if a response is needed (not all messages warrant replies)
3. Generate in-character responses using LLM
4. Schedule responses with realistic delays

This enables dynamic, reactive scenarios where the environment responds naturally
to the agent's actions, rather than following a scripted sequence.

Example:
    >>> from agentbeats.green.response_agents import ResponseAgentManager
    >>> from agentbeats.green.characters import CharacterRegistry
    >>> from agentbeats.green.llm import OllamaProvider, LLMConfig
    >>>
    >>> # Initialize components
    >>> registry = CharacterRegistry.from_dict(scenario_characters)
    >>> llm_config = LLMConfig(model="gemma3:12b", seed=42)
    >>> llm_provider = OllamaProvider(llm_config)
    >>>
    >>> # Create manager
    >>> manager = ResponseAgentManager(
    ...     ues_client=client,
    ...     characters=registry,
    ...     llm_provider=llm_provider,
    ...     seed=42,
    ... )
    >>>
    >>> # After Purple completes a turn, process their actions
    >>> responses = await manager.process_turn(current_state)
    >>> print(f"Scheduled {len(responses)} response events")
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, Field

from agentbeats.green.characters import CharacterProfile, CharacterRegistry
from agentbeats.green.llm import (
    LLMConfig,
    LLMError,
    LLMProvider,
    ResponseDecision,
    ResponseNecessityChecker,
)

# Try to import UES client, fall back for testing
try:
    from client import AsyncUESClient
except ImportError:
    AsyncUESClient = Any  # type: ignore


logger = logging.getLogger(__name__)


# =============================================================================
# Response Models
# =============================================================================


class ScheduledResponse(BaseModel):
    """A response event scheduled to be injected into the simulation.

    Represents a character's reply that will be delivered at a future
    simulator time. Created by ResponseAgentManager and submitted to
    UES via the events API.

    Attributes:
        modality: The modality for this response (email, sms, calendar).
        scheduled_time: When the response should be delivered (simulator time).
        data: Modality-specific event data (e.g., email fields, SMS body).
        character_name: Name of the character responding (for logging).
        original_message_id: ID of the message being replied to (for tracking).
        response_decision: Why this response was generated.
    """

    modality: str = Field(
        ...,
        description="Response modality (email, sms, calendar)",
    )
    scheduled_time: datetime = Field(
        ...,
        description="When to deliver the response (simulator time)",
    )
    data: dict[str, Any] = Field(
        ...,
        description="Modality-specific event data",
    )
    character_name: str = Field(
        ...,
        description="Name of the responding character",
    )
    original_message_id: str | None = Field(
        default=None,
        description="ID of the message being replied to",
    )
    response_decision: str | None = Field(
        default=None,
        description="Reason why this response was generated",
    )


@dataclass
class OutgoingMessage:
    """An outgoing message detected in the modality state.

    Used internally to track messages that may need responses.

    Attributes:
        modality: Source modality (email, sms).
        message_id: Unique identifier for the message.
        recipient: Email address or phone number of the recipient.
        content: Message content (body text).
        subject: Subject line (email only).
        thread_id: Thread/conversation identifier.
        sent_at: When the message was sent.
        conversation_context: Prior messages in the thread for context.
    """

    modality: str
    message_id: str
    recipient: str
    content: str
    subject: str | None = None
    thread_id: str | None = None
    sent_at: datetime | None = None
    conversation_context: str | None = None


@dataclass
class ResponseAgentState:
    """Internal state for tracking processed messages.

    Maintains sets of message IDs that have been processed to avoid
    generating duplicate responses.

    Attributes:
        processed_email_ids: Set of email message IDs already processed.
        processed_sms_ids: Set of SMS message IDs already processed.
        scheduled_responses: List of responses scheduled this session.
    """

    processed_email_ids: set[str] = field(default_factory=set)
    processed_sms_ids: set[str] = field(default_factory=set)
    scheduled_responses: list[ScheduledResponse] = field(default_factory=list)


# =============================================================================
# System Prompts
# =============================================================================


EMAIL_RESPONSE_SYSTEM_PROMPT = """You are generating an email response as a specific character.

Character Information:
{character_prompt}

Generate a realistic email reply that:
1. Matches the character's personality and communication style
2. Addresses the content of the original message
3. Is appropriately formal or casual based on the relationship
4. Is concise but complete

Output format - include ONLY the email body, no subject line or headers.
Do not include greetings like "Dear [Name]" unless it fits the character's style.
Do not include signatures unless it fits the character's style.
"""

SMS_RESPONSE_SYSTEM_PROMPT = """You are generating an SMS response as a specific character.

Character Information:
{character_prompt}

Generate a realistic text message reply that:
1. Matches the character's personality and communication style
2. Is SHORT (1-3 sentences max, like a real text)
3. Uses appropriate casual language/emoji for the character
4. Addresses the content of the original message

Output ONLY the message text, nothing else.
"""


# =============================================================================
# Response Agent Manager
# =============================================================================


class ResponseAgentManager:
    """Orchestrates character-based response generation.

    The ResponseAgentManager is the main coordinator for the Response Generator
    Sub-agents. It monitors modality states for outgoing messages, determines
    which messages need responses, generates in-character replies, and schedules
    them for delivery.

    Key responsibilities:
    - Detect outgoing messages to known characters (via CharacterRegistry)
    - Check if each message warrants a response (via ResponseNecessityChecker)
    - Generate in-character responses (via LLM with character system prompts)
    - Calculate realistic response delays (based on character ResponseTiming)
    - Schedule response events via UES events API

    Attributes:
        client: UES client for API calls.
        characters: Registry of known characters.
        llm_provider: LLM provider for text generation.
        necessity_checker: Checker for response necessity decisions.
        seed: Random seed for reproducibility.
        user_email: The simulated user's email address.
        user_phone: The simulated user's phone number.

    Example:
        >>> manager = ResponseAgentManager(client, registry, llm_provider, seed=42)
        >>> responses = await manager.process_turn()
        >>> for r in responses:
        ...     print(f"{r.character_name} will respond at {r.scheduled_time}")
    """

    def __init__(
        self,
        ues_client: "AsyncUESClient",
        characters: CharacterRegistry,
        llm_provider: LLMProvider,
        seed: int | None = None,
        user_email: str = "user@example.com",
        user_phone: str = "+15551234567",
    ):
        """Initialize the response agent manager.

        Args:
            ues_client: Async UES client for API calls.
            characters: Registry of known scenario characters.
            llm_provider: LLM provider for response generation.
            seed: Random seed for deterministic delay variance.
            user_email: The simulated user's email address.
            user_phone: The simulated user's phone number.
        """
        self.client = ues_client
        self.characters = characters
        self.llm_provider = llm_provider
        self.necessity_checker = ResponseNecessityChecker(llm_provider)
        self.seed = seed
        self.user_email = user_email
        self.user_phone = user_phone

        # Internal state
        self._state = ResponseAgentState()

    async def process_turn(self) -> list[ScheduledResponse]:
        """Process current modality states and generate responses.

        This is the main entry point called after Purple Agent completes
        a turn. It scans all modalities for outgoing messages, determines
        which need responses, and schedules them.

        Returns:
            List of ScheduledResponse objects that were created.
        """
        responses: list[ScheduledResponse] = []

        # Get current simulator time
        time_state = await self.client.time.get_state()
        current_time = time_state.current_time

        # Detect outgoing messages
        outgoing_messages = await self._detect_outgoing_messages()
        logger.info(f"Detected {len(outgoing_messages)} outgoing messages")

        # Process each message
        for message in outgoing_messages:
            # Look up character
            character = self.characters.get_by_identifier(message.recipient)
            if not character:
                logger.debug(
                    f"No character found for recipient: {message.recipient}"
                )
                continue

            # Check if response is needed
            decision = await self._check_response_needed(message, character)
            if not decision.needs_response:
                logger.info(
                    f"No response needed for {message.message_id}: {decision.reason}"
                )
                continue

            # Generate the response
            response_content = await self._generate_response(message, character)
            if not response_content:
                logger.warning(
                    f"Failed to generate response for {message.message_id}"
                )
                continue

            # Calculate delay and schedule
            delay = self._calculate_delay(character, message.message_id)
            scheduled_time = current_time + delay

            # Build and schedule the response event
            scheduled = await self._schedule_response(
                message=message,
                character=character,
                response_content=response_content,
                scheduled_time=scheduled_time,
                decision_reason=decision.reason,
            )
            if scheduled:
                responses.append(scheduled)
                self._state.scheduled_responses.append(scheduled)
                logger.info(
                    f"Scheduled response from {character.name} at {scheduled_time}"
                )

        return responses

    async def _detect_outgoing_messages(self) -> list[OutgoingMessage]:
        """Detect outgoing messages from modality states.

        Scans email and SMS modalities for messages sent by the user
        that haven't been processed yet.

        Returns:
            List of OutgoingMessage objects for processing.
        """
        messages: list[OutgoingMessage] = []

        # Check email modality
        try:
            messages.extend(await self._detect_outgoing_emails())
        except Exception as e:
            logger.error(f"Error detecting outgoing emails: {e}")

        # Check SMS modality
        try:
            messages.extend(await self._detect_outgoing_sms())
        except Exception as e:
            logger.error(f"Error detecting outgoing SMS: {e}")

        return messages

    async def _detect_outgoing_emails(self) -> list[OutgoingMessage]:
        """Detect outgoing emails from the email modality.

        Returns:
            List of OutgoingMessage objects for outgoing emails.
        """
        messages: list[OutgoingMessage] = []
        email_state = await self.client.email.get_state()

        for email in email_state.emails.values():
            # Only process sent emails
            if email.folder != "sent":
                continue

            # Skip already processed
            if email.message_id in self._state.processed_email_ids:
                continue

            # Mark as processed
            self._state.processed_email_ids.add(email.message_id)

            # Create OutgoingMessage for each recipient
            for recipient in email.to_addresses:
                # Skip if recipient is not a known character
                if recipient not in self.characters:
                    continue

                # Build conversation context from thread
                context = self._build_email_thread_context(
                    email_state, email.thread_id, email.message_id
                )

                messages.append(
                    OutgoingMessage(
                        modality="email",
                        message_id=email.message_id,
                        recipient=recipient,
                        content=email.body_text or "",
                        subject=email.subject,
                        thread_id=email.thread_id,
                        sent_at=email.sent_at,
                        conversation_context=context,
                    )
                )

        return messages

    def _build_email_thread_context(
        self,
        email_state: Any,
        thread_id: str | None,
        exclude_id: str,
    ) -> str | None:
        """Build conversation context from an email thread.

        Args:
            email_state: Current email modality state.
            thread_id: Thread ID to gather context from.
            exclude_id: Message ID to exclude (the current message).

        Returns:
            String containing prior messages, or None if no context.
        """
        if not thread_id:
            return None

        # Find all emails in this thread
        thread_emails = [
            e
            for e in email_state.emails.values()
            if e.thread_id == thread_id and e.message_id != exclude_id
        ]

        if not thread_emails:
            return None

        # Sort by sent time
        thread_emails.sort(key=lambda e: e.sent_at or datetime.min)

        # Build context string
        context_parts = []
        for email in thread_emails[-5:]:  # Last 5 messages max
            sender = email.from_address
            body = (email.body_text or "")[:500]  # Truncate long messages
            context_parts.append(f"From: {sender}\n{body}")

        return "\n---\n".join(context_parts)

    async def _detect_outgoing_sms(self) -> list[OutgoingMessage]:
        """Detect outgoing SMS from the SMS modality.

        Returns:
            List of OutgoingMessage objects for outgoing SMS.
        """
        messages: list[OutgoingMessage] = []
        sms_state = await self.client.sms.get_state()

        for msg in sms_state.messages.values():
            # Only process outgoing messages
            if msg.direction != "outgoing":
                continue

            # Skip already processed
            if msg.message_id in self._state.processed_sms_ids:
                continue

            # Mark as processed
            self._state.processed_sms_ids.add(msg.message_id)

            # Determine recipient(s)
            recipients = msg.to_numbers or []
            if msg.thread_id:
                # For group chats, we might need to respond as multiple characters
                # For now, handle individual recipients
                pass

            for recipient in recipients:
                # Skip if recipient is not a known character
                if recipient not in self.characters:
                    continue

                # Build conversation context
                context = self._build_sms_thread_context(
                    sms_state, msg.thread_id, msg.message_id
                )

                messages.append(
                    OutgoingMessage(
                        modality="sms",
                        message_id=msg.message_id,
                        recipient=recipient,
                        content=msg.body or "",
                        thread_id=msg.thread_id,
                        sent_at=msg.sent_at,
                        conversation_context=context,
                    )
                )

        return messages

    def _build_sms_thread_context(
        self,
        sms_state: Any,
        thread_id: str | None,
        exclude_id: str,
    ) -> str | None:
        """Build conversation context from an SMS thread.

        Args:
            sms_state: Current SMS modality state.
            thread_id: Thread/conversation ID.
            exclude_id: Message ID to exclude.

        Returns:
            String containing prior messages, or None.
        """
        if not thread_id:
            return None

        # Find conversation
        conversation = sms_state.conversations.get(thread_id)
        if not conversation:
            return None

        # Get messages in this conversation
        thread_msgs = [
            sms_state.messages.get(mid)
            for mid in conversation.message_ids
            if mid != exclude_id and mid in sms_state.messages
        ]

        thread_msgs = [m for m in thread_msgs if m is not None]
        if not thread_msgs:
            return None

        # Sort by sent time
        thread_msgs.sort(key=lambda m: m.sent_at or datetime.min)

        # Build context
        context_parts = []
        for msg in thread_msgs[-10:]:  # Last 10 messages max
            direction = "You" if msg.direction == "outgoing" else msg.from_number
            context_parts.append(f"{direction}: {msg.body}")

        return "\n".join(context_parts)

    async def _check_response_needed(
        self,
        message: OutgoingMessage,
        character: CharacterProfile,
    ) -> ResponseDecision:
        """Check if a message warrants a response.

        Uses the ResponseNecessityChecker to determine if the character
        should reply to this message.

        Args:
            message: The outgoing message to evaluate.
            character: The character who would respond.

        Returns:
            ResponseDecision indicating if response is needed.
        """
        try:
            return await self.necessity_checker.check(
                message_content=message.content,
                conversation_context=message.conversation_context,
                sender_name=character.name,
            )
        except LLMError as e:
            logger.error(f"LLM error checking response necessity: {e}")
            # Default to responding on error (safer for testing)
            return ResponseDecision(
                needs_response=True,
                reason="LLM check failed, defaulting to respond",
            )

    async def _generate_response(
        self,
        message: OutgoingMessage,
        character: CharacterProfile,
    ) -> str | None:
        """Generate an in-character response.

        Uses the LLM to generate a response that matches the character's
        personality and communication style.

        Args:
            message: The message being replied to.
            character: The character generating the response.

        Returns:
            Generated response content, or None on failure.
        """
        # Build system prompt with character info
        character_prompt = character.build_system_prompt()

        if message.modality == "email":
            system_prompt = EMAIL_RESPONSE_SYSTEM_PROMPT.format(
                character_prompt=character_prompt
            )
        else:  # SMS
            system_prompt = SMS_RESPONSE_SYSTEM_PROMPT.format(
                character_prompt=character_prompt
            )

        # Build the user prompt
        prompt = self._build_response_prompt(message)

        try:
            response = await self.llm_provider.generate(prompt, system_prompt)
            return response.strip()
        except LLMError as e:
            logger.error(f"LLM error generating response: {e}")
            return None

    def _build_response_prompt(self, message: OutgoingMessage) -> str:
        """Build the prompt for response generation.

        Args:
            message: The message to respond to.

        Returns:
            Prompt string for the LLM.
        """
        parts = []

        if message.conversation_context:
            parts.append(f"Previous conversation:\n{message.conversation_context}\n")

        if message.modality == "email":
            parts.append(f"Subject: {message.subject or '(no subject)'}")
            parts.append(f"\nMessage to respond to:\n{message.content}")
            parts.append("\nGenerate your email reply:")
        else:
            parts.append(f"Message to respond to:\n{message.content}")
            parts.append("\nGenerate your text message reply:")

        return "\n".join(parts)

    def _calculate_delay(
        self,
        character: CharacterProfile,
        message_id: str,
    ) -> timedelta:
        """Calculate response delay based on character timing.

        Uses the character's ResponseTiming configuration to determine
        how long before they respond. If a seed is set, the delay is
        deterministic based on the message ID.

        Args:
            character: The character who is responding.
            message_id: ID of the message (for deterministic variance).

        Returns:
            Timedelta for when to schedule the response.
        """
        timing = character.response_timing
        base_minutes = timing.base_delay_minutes
        variance_minutes = timing.variance_minutes

        if variance_minutes == 0 or self.seed is None:
            # No variance or no seed - use base delay
            variance = 0
        else:
            # Deterministic variance based on seed + message_id
            hash_input = f"{self.seed}:{message_id}"
            hash_bytes = hashlib.sha256(hash_input.encode()).digest()
            hash_int = int.from_bytes(hash_bytes[:4], "big")
            variance = (hash_int % (variance_minutes * 2)) - variance_minutes

        total_minutes = max(1, base_minutes + variance)  # At least 1 minute
        return timedelta(minutes=total_minutes)

    async def _schedule_response(
        self,
        message: OutgoingMessage,
        character: CharacterProfile,
        response_content: str,
        scheduled_time: datetime,
        decision_reason: str,
    ) -> ScheduledResponse | None:
        """Schedule a response event via UES events API.

        Creates and submits an event that will inject the response
        into the simulation at the scheduled time.

        Args:
            message: The original message being replied to.
            character: The character who is responding.
            response_content: The generated response content.
            scheduled_time: When to deliver the response.
            decision_reason: Why this response was generated.

        Returns:
            ScheduledResponse if successful, None on failure.
        """
        if message.modality == "email":
            return await self._schedule_email_response(
                message, character, response_content, scheduled_time, decision_reason
            )
        elif message.modality == "sms":
            return await self._schedule_sms_response(
                message, character, response_content, scheduled_time, decision_reason
            )
        else:
            logger.warning(f"Unknown modality: {message.modality}")
            return None

    async def _schedule_email_response(
        self,
        message: OutgoingMessage,
        character: CharacterProfile,
        response_content: str,
        scheduled_time: datetime,
        decision_reason: str,
    ) -> ScheduledResponse | None:
        """Schedule an email response event.

        Args:
            message: Original email being replied to.
            character: Character sending the reply.
            response_content: Email body content.
            scheduled_time: When to deliver.
            decision_reason: Why responding.

        Returns:
            ScheduledResponse if successful.
        """
        # Build email event data
        event_data = {
            "operation": "receive",
            "from_address": character.email,
            "to_addresses": [self.user_email],
            "subject": f"Re: {message.subject}" if message.subject else "Re:",
            "body_text": response_content,
            "thread_id": message.thread_id,
            "in_reply_to": message.message_id,
        }

        try:
            await self.client.events.create(
                scheduled_time=scheduled_time,
                modality="email",
                data=event_data,
            )
        except Exception as e:
            logger.error(f"Failed to schedule email response: {e}")
            return None

        return ScheduledResponse(
            modality="email",
            scheduled_time=scheduled_time,
            data=event_data,
            character_name=character.name,
            original_message_id=message.message_id,
            response_decision=decision_reason,
        )

    async def _schedule_sms_response(
        self,
        message: OutgoingMessage,
        character: CharacterProfile,
        response_content: str,
        scheduled_time: datetime,
        decision_reason: str,
    ) -> ScheduledResponse | None:
        """Schedule an SMS response event.

        Args:
            message: Original SMS being replied to.
            character: Character sending the reply.
            response_content: SMS body content.
            scheduled_time: When to deliver.
            decision_reason: Why responding.

        Returns:
            ScheduledResponse if successful.
        """
        # Build SMS event data
        event_data = {
            "operation": "receive",
            "from_number": character.phone,
            "to_numbers": [self.user_phone],
            "body": response_content,
            "thread_id": message.thread_id,
        }

        try:
            await self.client.events.create(
                scheduled_time=scheduled_time,
                modality="sms",
                data=event_data,
            )
        except Exception as e:
            logger.error(f"Failed to schedule SMS response: {e}")
            return None

        return ScheduledResponse(
            modality="sms",
            scheduled_time=scheduled_time,
            data=event_data,
            character_name=character.name,
            original_message_id=message.message_id,
            response_decision=decision_reason,
        )

    def reset_state(self) -> None:
        """Reset internal state for a new assessment.

        Clears the sets of processed message IDs and scheduled responses.
        Call this when starting a new assessment.
        """
        self._state = ResponseAgentState()
        logger.info("Response agent state reset")

    def get_scheduled_responses(self) -> list[ScheduledResponse]:
        """Get all responses scheduled during this session.

        Returns:
            List of ScheduledResponse objects.
        """
        return list(self._state.scheduled_responses)


# =============================================================================
# Factory Function
# =============================================================================


def create_response_agent_manager(
    ues_client: "AsyncUESClient",
    scenario_characters: dict[str, dict],
    llm_config: LLMConfig | None = None,
    seed: int | None = None,
    user_email: str = "user@example.com",
    user_phone: str = "+15551234567",
) -> ResponseAgentManager:
    """Create a ResponseAgentManager from scenario character data.

    Convenience factory function that handles creating the character
    registry and LLM provider from configuration.

    Args:
        ues_client: Async UES client.
        scenario_characters: Character definitions from scenario config.
        llm_config: LLM configuration (defaults to local Ollama).
        seed: Random seed for reproducibility.
        user_email: Simulated user's email.
        user_phone: Simulated user's phone.

    Returns:
        Configured ResponseAgentManager.

    Example:
        >>> from agentbeats.green.response_agents import create_response_agent_manager
        >>> manager = create_response_agent_manager(
        ...     ues_client=client,
        ...     scenario_characters=scenario["characters"],
        ...     seed=42,
        ... )
    """
    from agentbeats.green.llm import OllamaProvider

    # Create character registry
    registry = CharacterRegistry.from_scenario_characters(scenario_characters)

    # Create LLM provider
    if llm_config is None:
        llm_config = LLMConfig(seed=seed)
    llm_provider = OllamaProvider(llm_config)

    return ResponseAgentManager(
        ues_client=ues_client,
        characters=registry,
        llm_provider=llm_provider,
        seed=seed,
        user_email=user_email,
        user_phone=user_phone,
    )
