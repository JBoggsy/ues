"""Tests for Response Generator Sub-agents.

Tests cover response detection, necessity checking, generation, and scheduling
for the ResponseAgentManager.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentbeats.green.characters import (
    CharacterProfile,
    CharacterRegistry,
    ResponseTiming,
)
from agentbeats.green.llm import (
    LLMConfig,
    LLMError,
    MockLLMProvider,
    ResponseDecision,
)
from agentbeats.green.response_agents import (
    OutgoingMessage,
    ResponseAgentManager,
    ResponseAgentState,
    ScheduledResponse,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_characters() -> CharacterRegistry:
    """Create a sample character registry for testing."""
    characters = [
        CharacterProfile(
            name="Jamie Walsh",
            email="jamie@example.com",
            phone="+15551111111",
            personality="Friendly and outgoing",
            communication_style="Casual with exclamation marks!",
            response_timing=ResponseTiming(base_delay_minutes=15, variance_minutes=10),
        ),
        CharacterProfile(
            name="Taylor Chen",
            email="taylor@example.com",
            personality="Professional and concise",
            communication_style="Formal business tone",
            response_timing=ResponseTiming(base_delay_minutes=60, variance_minutes=30),
        ),
        CharacterProfile(
            name="Alex Rivera",
            phone="+15552222222",
            personality="Chill and relaxed",
            communication_style="Very casual, uses emoji",
            response_timing=ResponseTiming(base_delay_minutes=30, variance_minutes=20),
        ),
    ]
    return CharacterRegistry(characters)


@pytest.fixture
def mock_llm_provider() -> MockLLMProvider:
    """Create a mock LLM provider for testing."""
    config = LLMConfig(seed=42)
    return MockLLMProvider(config)


@pytest.fixture
def mock_ues_client():
    """Create a mock UES client for testing."""
    client = MagicMock()

    # Mock time.get_state()
    time_state = MagicMock()
    time_state.current_time = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    client.time = MagicMock()
    client.time.get_state = AsyncMock(return_value=time_state)

    # Mock email.get_state()
    client.email = MagicMock()
    client.email.get_state = AsyncMock(return_value=MagicMock(emails={}))

    # Mock sms.get_state()
    client.sms = MagicMock()
    client.sms.get_state = AsyncMock(
        return_value=MagicMock(messages={}, conversations={})
    )

    # Mock events.create()
    client.events = MagicMock()
    client.events.create = AsyncMock(return_value=MagicMock(event_id="evt-123"))

    return client


# =============================================================================
# ScheduledResponse Model Tests
# =============================================================================


class TestScheduledResponse:
    """Tests for ScheduledResponse model."""

    def test_minimal_valid(self):
        """Create with required fields only."""
        response = ScheduledResponse(
            modality="email",
            scheduled_time=datetime(2025, 1, 15, 11, 0, 0, tzinfo=timezone.utc),
            data={"operation": "receive", "from_address": "test@example.com"},
            character_name="Test Character",
        )
        assert response.modality == "email"
        assert response.original_message_id is None
        assert response.response_decision is None

    def test_full_response(self):
        """Create with all fields."""
        response = ScheduledResponse(
            modality="sms",
            scheduled_time=datetime(2025, 1, 15, 11, 30, 0, tzinfo=timezone.utc),
            data={
                "operation": "receive",
                "from_number": "+15551234567",
                "body": "Got it!",
            },
            character_name="Alex",
            original_message_id="msg-456",
            response_decision="Question requires an answer",
        )
        assert response.modality == "sms"
        assert response.original_message_id == "msg-456"
        assert response.response_decision == "Question requires an answer"


# =============================================================================
# OutgoingMessage Tests
# =============================================================================


class TestOutgoingMessage:
    """Tests for OutgoingMessage dataclass."""

    def test_minimal_creation(self):
        """Create with required fields only."""
        msg = OutgoingMessage(
            modality="email",
            message_id="msg-123",
            recipient="jamie@example.com",
            content="Hello!",
        )
        assert msg.modality == "email"
        assert msg.message_id == "msg-123"
        assert msg.subject is None
        assert msg.thread_id is None

    def test_full_creation(self):
        """Create with all fields."""
        msg = OutgoingMessage(
            modality="email",
            message_id="msg-456",
            recipient="taylor@example.com",
            content="Meeting tomorrow?",
            subject="Quick question",
            thread_id="thread-789",
            sent_at=datetime(2025, 1, 15, 9, 0, 0, tzinfo=timezone.utc),
            conversation_context="Previous: Yes, let's discuss.",
        )
        assert msg.subject == "Quick question"
        assert msg.thread_id == "thread-789"
        assert msg.conversation_context is not None


# =============================================================================
# ResponseAgentState Tests
# =============================================================================


class TestResponseAgentState:
    """Tests for ResponseAgentState dataclass."""

    def test_initial_state_empty(self):
        """New state should be empty."""
        state = ResponseAgentState()
        assert len(state.processed_email_ids) == 0
        assert len(state.processed_sms_ids) == 0
        assert len(state.scheduled_responses) == 0

    def test_state_tracking(self):
        """State can track processed IDs."""
        state = ResponseAgentState()
        state.processed_email_ids.add("email-1")
        state.processed_email_ids.add("email-2")
        state.processed_sms_ids.add("sms-1")

        assert "email-1" in state.processed_email_ids
        assert "email-2" in state.processed_email_ids
        assert "sms-1" in state.processed_sms_ids
        assert "email-3" not in state.processed_email_ids


# =============================================================================
# ResponseAgentManager Unit Tests
# =============================================================================


class TestResponseAgentManagerInit:
    """Tests for ResponseAgentManager initialization."""

    def test_basic_init(self, mock_ues_client, sample_characters, mock_llm_provider):
        """Initialize with required parameters."""
        manager = ResponseAgentManager(
            ues_client=mock_ues_client,
            characters=sample_characters,
            llm_provider=mock_llm_provider,
        )
        assert manager.client == mock_ues_client
        assert manager.characters == sample_characters
        assert manager.seed is None
        assert manager.user_email == "user@example.com"

    def test_init_with_options(
        self, mock_ues_client, sample_characters, mock_llm_provider
    ):
        """Initialize with all options."""
        manager = ResponseAgentManager(
            ues_client=mock_ues_client,
            characters=sample_characters,
            llm_provider=mock_llm_provider,
            seed=42,
            user_email="sam@example.com",
            user_phone="+15559876543",
        )
        assert manager.seed == 42
        assert manager.user_email == "sam@example.com"
        assert manager.user_phone == "+15559876543"


class TestDelayCalculation:
    """Tests for response delay calculation."""

    def test_base_delay_no_seed(
        self, mock_ues_client, sample_characters, mock_llm_provider
    ):
        """Without seed, use base delay only."""
        manager = ResponseAgentManager(
            ues_client=mock_ues_client,
            characters=sample_characters,
            llm_provider=mock_llm_provider,
            seed=None,  # No seed
        )

        character = sample_characters.get_by_email("jamie@example.com")
        delay = manager._calculate_delay(character, "msg-123")

        # Should be exactly base delay (15 minutes) since no variance without seed
        assert delay == timedelta(minutes=15)

    def test_deterministic_delay_with_seed(
        self, mock_ues_client, sample_characters, mock_llm_provider
    ):
        """With seed, delay should be deterministic."""
        manager = ResponseAgentManager(
            ues_client=mock_ues_client,
            characters=sample_characters,
            llm_provider=mock_llm_provider,
            seed=42,
        )

        character = sample_characters.get_by_email("jamie@example.com")

        # Same message ID should give same delay
        delay1 = manager._calculate_delay(character, "msg-123")
        delay2 = manager._calculate_delay(character, "msg-123")
        assert delay1 == delay2

        # Different message ID should (likely) give different delay
        delay3 = manager._calculate_delay(character, "msg-456")
        # Note: Could theoretically be equal, but very unlikely

    def test_delay_respects_timing_config(
        self, mock_ues_client, sample_characters, mock_llm_provider
    ):
        """Delay should respect character timing configuration."""
        manager = ResponseAgentManager(
            ues_client=mock_ues_client,
            characters=sample_characters,
            llm_provider=mock_llm_provider,
            seed=42,
        )

        # Jamie: base=15, variance=10 -> range [5, 25] minutes
        jamie = sample_characters.get_by_email("jamie@example.com")
        jamie_delay = manager._calculate_delay(jamie, "msg-test")
        assert timedelta(minutes=1) <= jamie_delay <= timedelta(minutes=25)

        # Taylor: base=60, variance=30 -> range [30, 90] minutes
        taylor = sample_characters.get_by_email("taylor@example.com")
        taylor_delay = manager._calculate_delay(taylor, "msg-test")
        assert timedelta(minutes=1) <= taylor_delay <= timedelta(minutes=90)


class TestResetState:
    """Tests for state reset functionality."""

    def test_reset_clears_state(
        self, mock_ues_client, sample_characters, mock_llm_provider
    ):
        """Reset should clear all tracked state."""
        manager = ResponseAgentManager(
            ues_client=mock_ues_client,
            characters=sample_characters,
            llm_provider=mock_llm_provider,
        )

        # Add some state
        manager._state.processed_email_ids.add("email-1")
        manager._state.processed_sms_ids.add("sms-1")
        manager._state.scheduled_responses.append(
            ScheduledResponse(
                modality="email",
                scheduled_time=datetime.now(timezone.utc),
                data={},
                character_name="Test",
            )
        )

        # Reset
        manager.reset_state()

        # Verify cleared
        assert len(manager._state.processed_email_ids) == 0
        assert len(manager._state.processed_sms_ids) == 0
        assert len(manager._state.scheduled_responses) == 0


class TestBuildResponsePrompt:
    """Tests for response prompt building."""

    def test_email_prompt_structure(
        self, mock_ues_client, sample_characters, mock_llm_provider
    ):
        """Email prompt should include subject and body."""
        manager = ResponseAgentManager(
            ues_client=mock_ues_client,
            characters=sample_characters,
            llm_provider=mock_llm_provider,
        )

        message = OutgoingMessage(
            modality="email",
            message_id="msg-123",
            recipient="jamie@example.com",
            content="Are you coming to the party?",
            subject="Party invitation",
        )

        prompt = manager._build_response_prompt(message)

        assert "Subject: Party invitation" in prompt
        assert "Are you coming to the party?" in prompt
        assert "email reply" in prompt.lower()

    def test_sms_prompt_structure(
        self, mock_ues_client, sample_characters, mock_llm_provider
    ):
        """SMS prompt should not include subject."""
        manager = ResponseAgentManager(
            ues_client=mock_ues_client,
            characters=sample_characters,
            llm_provider=mock_llm_provider,
        )

        message = OutgoingMessage(
            modality="sms",
            message_id="msg-123",
            recipient="+15552222222",
            content="Hey, you free tonight?",
        )

        prompt = manager._build_response_prompt(message)

        assert "Hey, you free tonight?" in prompt
        assert "text message" in prompt.lower()
        assert "Subject:" not in prompt

    def test_prompt_with_conversation_context(
        self, mock_ues_client, sample_characters, mock_llm_provider
    ):
        """Prompt should include conversation context if provided."""
        manager = ResponseAgentManager(
            ues_client=mock_ues_client,
            characters=sample_characters,
            llm_provider=mock_llm_provider,
        )

        message = OutgoingMessage(
            modality="email",
            message_id="msg-123",
            recipient="jamie@example.com",
            content="What about Saturday?",
            subject="Re: Party",
            conversation_context="From: jamie@example.com\nSounds good! When?",
        )

        prompt = manager._build_response_prompt(message)

        assert "Previous conversation" in prompt
        assert "Sounds good! When?" in prompt


# =============================================================================
# ResponseAgentManager Async Tests
# =============================================================================


class TestProcessTurn:
    """Tests for the main process_turn method."""

    @pytest.mark.asyncio
    async def test_no_outgoing_messages(
        self, mock_ues_client, sample_characters, mock_llm_provider
    ):
        """No responses when no outgoing messages."""
        manager = ResponseAgentManager(
            ues_client=mock_ues_client,
            characters=sample_characters,
            llm_provider=mock_llm_provider,
        )

        responses = await manager.process_turn()

        assert responses == []
        mock_ues_client.events.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_email_to_known_character(
        self, mock_ues_client, sample_characters, mock_llm_provider
    ):
        """Process email to known character."""
        # Setup mock email state with sent email
        email = MagicMock()
        email.message_id = "email-001"
        email.folder = "sent"
        email.to_addresses = ["jamie@example.com"]
        email.from_address = "user@example.com"
        email.subject = "Party this weekend?"
        email.body_text = "Hey Jamie! Want to come to my party?"
        email.thread_id = "thread-001"
        email.sent_at = datetime(2025, 1, 15, 9, 30, 0, tzinfo=timezone.utc)

        email_state = MagicMock()
        email_state.emails = {"email-001": email}
        mock_ues_client.email.get_state = AsyncMock(return_value=email_state)

        # Setup mock LLM responses
        mock_llm_provider.queue_response("NEEDS_RESPONSE: Contains a question")
        mock_llm_provider.queue_response(
            "OMG yes!! I would love to come! Can't wait!"
        )

        manager = ResponseAgentManager(
            ues_client=mock_ues_client,
            characters=sample_characters,
            llm_provider=mock_llm_provider,
            seed=42,
            user_email="user@example.com",
        )

        responses = await manager.process_turn()

        # Should have one response
        assert len(responses) == 1
        response = responses[0]
        assert response.modality == "email"
        assert response.character_name == "Jamie Walsh"
        assert response.original_message_id == "email-001"

        # Should have scheduled event
        mock_ues_client.events.create.assert_called_once()
        call_kwargs = mock_ues_client.events.create.call_args.kwargs
        assert call_kwargs["modality"] == "email"
        assert call_kwargs["data"]["operation"] == "receive"
        assert call_kwargs["data"]["from_address"] == "jamie@example.com"

    @pytest.mark.asyncio
    async def test_email_to_unknown_character(
        self, mock_ues_client, sample_characters, mock_llm_provider
    ):
        """Email to unknown recipient should not trigger response."""
        email = MagicMock()
        email.message_id = "email-002"
        email.folder = "sent"
        email.to_addresses = ["stranger@example.com"]  # Not in registry
        email.subject = "Hello"
        email.body_text = "Hi there!"
        email.thread_id = "thread-002"
        email.sent_at = datetime(2025, 1, 15, 9, 30, 0, tzinfo=timezone.utc)

        email_state = MagicMock()
        email_state.emails = {"email-002": email}
        mock_ues_client.email.get_state = AsyncMock(return_value=email_state)

        manager = ResponseAgentManager(
            ues_client=mock_ues_client,
            characters=sample_characters,
            llm_provider=mock_llm_provider,
        )

        responses = await manager.process_turn()

        assert responses == []
        mock_ues_client.events.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_response_not_needed(
        self, mock_ues_client, sample_characters, mock_llm_provider
    ):
        """No response when necessity checker says not needed."""
        email = MagicMock()
        email.message_id = "email-003"
        email.folder = "sent"
        email.to_addresses = ["jamie@example.com"]
        email.subject = "Re: Party"
        email.body_text = "Sounds good, see you then!"  # Closing statement
        email.thread_id = "thread-003"
        email.sent_at = datetime(2025, 1, 15, 9, 30, 0, tzinfo=timezone.utc)

        email_state = MagicMock()
        email_state.emails = {"email-003": email}
        mock_ues_client.email.get_state = AsyncMock(return_value=email_state)

        # Mock LLM to say no response needed
        mock_llm_provider.queue_response(
            "NO_RESPONSE: This is a closing statement, conversation complete"
        )

        manager = ResponseAgentManager(
            ues_client=mock_ues_client,
            characters=sample_characters,
            llm_provider=mock_llm_provider,
        )

        responses = await manager.process_turn()

        assert responses == []
        mock_ues_client.events.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_sms_to_known_character(
        self, mock_ues_client, sample_characters, mock_llm_provider
    ):
        """Process SMS to known character."""
        # Setup mock SMS state
        sms = MagicMock()
        sms.message_id = "sms-001"
        sms.direction = "outgoing"
        sms.to_numbers = ["+15552222222"]  # Alex's number
        sms.from_number = "+15559876543"
        sms.body = "Hey Alex! Party at my place Saturday?"
        sms.thread_id = "conv-001"
        sms.sent_at = datetime(2025, 1, 15, 9, 30, 0, tzinfo=timezone.utc)

        sms_state = MagicMock()
        sms_state.messages = {"sms-001": sms}
        sms_state.conversations = {}
        mock_ues_client.sms.get_state = AsyncMock(return_value=sms_state)

        # Setup LLM responses
        mock_llm_provider.queue_response("NEEDS_RESPONSE: Invitation question")
        mock_llm_provider.queue_response("sounds good! 🎉 count me in")

        manager = ResponseAgentManager(
            ues_client=mock_ues_client,
            characters=sample_characters,
            llm_provider=mock_llm_provider,
            seed=42,
            user_phone="+15559876543",
        )

        responses = await manager.process_turn()

        assert len(responses) == 1
        response = responses[0]
        assert response.modality == "sms"
        assert response.character_name == "Alex Rivera"

        # Check event was created
        mock_ues_client.events.create.assert_called_once()
        call_kwargs = mock_ues_client.events.create.call_args.kwargs
        assert call_kwargs["modality"] == "sms"
        assert call_kwargs["data"]["from_number"] == "+15552222222"

    @pytest.mark.asyncio
    async def test_already_processed_message_skipped(
        self, mock_ues_client, sample_characters, mock_llm_provider
    ):
        """Already processed messages should be skipped."""
        email = MagicMock()
        email.message_id = "email-already-processed"
        email.folder = "sent"
        email.to_addresses = ["jamie@example.com"]
        email.subject = "Test"
        email.body_text = "Test message"
        email.thread_id = "thread-001"
        email.sent_at = datetime(2025, 1, 15, 9, 30, 0, tzinfo=timezone.utc)

        email_state = MagicMock()
        email_state.emails = {"email-already-processed": email}
        mock_ues_client.email.get_state = AsyncMock(return_value=email_state)

        manager = ResponseAgentManager(
            ues_client=mock_ues_client,
            characters=sample_characters,
            llm_provider=mock_llm_provider,
        )

        # Pre-mark as processed
        manager._state.processed_email_ids.add("email-already-processed")

        responses = await manager.process_turn()

        assert responses == []
        # LLM should not have been called
        assert len(mock_llm_provider.get_call_history()) == 0

    @pytest.mark.asyncio
    async def test_inbox_email_ignored(
        self, mock_ues_client, sample_characters, mock_llm_provider
    ):
        """Emails in inbox (received) should not trigger responses."""
        email = MagicMock()
        email.message_id = "email-inbox"
        email.folder = "inbox"  # Not sent
        email.to_addresses = ["user@example.com"]
        email.from_address = "jamie@example.com"
        email.subject = "Hello"
        email.body_text = "Hi!"
        email.thread_id = "thread-001"

        email_state = MagicMock()
        email_state.emails = {"email-inbox": email}
        mock_ues_client.email.get_state = AsyncMock(return_value=email_state)

        manager = ResponseAgentManager(
            ues_client=mock_ues_client,
            characters=sample_characters,
            llm_provider=mock_llm_provider,
        )

        responses = await manager.process_turn()

        assert responses == []


class TestGetScheduledResponses:
    """Tests for retrieving scheduled responses."""

    @pytest.mark.asyncio
    async def test_returns_all_scheduled(
        self, mock_ues_client, sample_characters, mock_llm_provider
    ):
        """Should return all scheduled responses."""
        # Setup multiple emails
        email1 = MagicMock()
        email1.message_id = "email-001"
        email1.folder = "sent"
        email1.to_addresses = ["jamie@example.com"]
        email1.subject = "Party?"
        email1.body_text = "Coming to the party?"
        email1.thread_id = "thread-001"
        email1.sent_at = datetime(2025, 1, 15, 9, 0, 0, tzinfo=timezone.utc)

        email2 = MagicMock()
        email2.message_id = "email-002"
        email2.folder = "sent"
        email2.to_addresses = ["taylor@example.com"]
        email2.subject = "Meeting"
        email2.body_text = "Can we meet tomorrow?"
        email2.thread_id = "thread-002"
        email2.sent_at = datetime(2025, 1, 15, 9, 30, 0, tzinfo=timezone.utc)

        email_state = MagicMock()
        email_state.emails = {"email-001": email1, "email-002": email2}
        mock_ues_client.email.get_state = AsyncMock(return_value=email_state)

        # Queue LLM responses for both
        mock_llm_provider.queue_response("NEEDS_RESPONSE: Question")
        mock_llm_provider.queue_response("Yes! I'll be there!")
        mock_llm_provider.queue_response("NEEDS_RESPONSE: Meeting request")
        mock_llm_provider.queue_response("Sure, let's schedule for 2pm.")

        manager = ResponseAgentManager(
            ues_client=mock_ues_client,
            characters=sample_characters,
            llm_provider=mock_llm_provider,
            seed=42,
        )

        await manager.process_turn()

        all_scheduled = manager.get_scheduled_responses()

        assert len(all_scheduled) == 2
        names = {r.character_name for r in all_scheduled}
        assert "Jamie Walsh" in names
        assert "Taylor Chen" in names


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_llm_error_on_necessity_check_defaults_to_respond(
        self, mock_ues_client, sample_characters
    ):
        """LLM error on necessity check should default to responding."""
        # Create a provider that raises an error
        error_config = LLMConfig(seed=42)
        error_provider = MockLLMProvider(error_config)

        # Override generate to raise
        async def raise_error(*args, **kwargs):
            raise LLMError("Connection failed")

        error_provider.generate = raise_error

        email = MagicMock()
        email.message_id = "email-error"
        email.folder = "sent"
        email.to_addresses = ["jamie@example.com"]
        email.subject = "Test"
        email.body_text = "Hello?"
        email.thread_id = "thread-error"
        email.sent_at = datetime(2025, 1, 15, 9, 0, 0, tzinfo=timezone.utc)

        email_state = MagicMock()
        email_state.emails = {"email-error": email}
        mock_ues_client.email.get_state = AsyncMock(return_value=email_state)

        manager = ResponseAgentManager(
            ues_client=mock_ues_client,
            characters=sample_characters,
            llm_provider=error_provider,
        )

        # The necessity check will fail, but should default to needing response
        # Then generate will also fail, so no response scheduled
        responses = await manager.process_turn()

        # No response because generate also fails
        assert responses == []

    @pytest.mark.asyncio
    async def test_event_creation_failure_handled(
        self, mock_ues_client, sample_characters, mock_llm_provider
    ):
        """Event creation failure should be handled gracefully."""
        email = MagicMock()
        email.message_id = "email-fail"
        email.folder = "sent"
        email.to_addresses = ["jamie@example.com"]
        email.subject = "Test"
        email.body_text = "Hello?"
        email.thread_id = "thread-fail"
        email.sent_at = datetime(2025, 1, 15, 9, 0, 0, tzinfo=timezone.utc)

        email_state = MagicMock()
        email_state.emails = {"email-fail": email}
        mock_ues_client.email.get_state = AsyncMock(return_value=email_state)

        # Make event creation fail
        mock_ues_client.events.create = AsyncMock(side_effect=Exception("API Error"))

        mock_llm_provider.queue_response("NEEDS_RESPONSE: Question")
        mock_llm_provider.queue_response("Sure!")

        manager = ResponseAgentManager(
            ues_client=mock_ues_client,
            characters=sample_characters,
            llm_provider=mock_llm_provider,
        )

        # Should not raise, just return empty
        responses = await manager.process_turn()
        assert responses == []


# =============================================================================
# Integration with ResponseNecessityChecker Tests
# =============================================================================


class TestResponseNecessityIntegration:
    """Tests for integration with ResponseNecessityChecker."""

    @pytest.mark.asyncio
    async def test_necessity_checker_receives_context(
        self, mock_ues_client, sample_characters, mock_llm_provider
    ):
        """Necessity checker should receive conversation context."""
        email = MagicMock()
        email.message_id = "email-context"
        email.folder = "sent"
        email.to_addresses = ["jamie@example.com"]
        email.subject = "Re: Plans"
        email.body_text = "What time works for you?"
        email.thread_id = "thread-context"
        email.sent_at = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

        # Create previous email in thread
        prev_email = MagicMock()
        prev_email.message_id = "email-prev"
        prev_email.folder = "inbox"
        prev_email.from_address = "jamie@example.com"
        prev_email.subject = "Re: Plans"
        prev_email.body_text = "I'm free this weekend!"
        prev_email.thread_id = "thread-context"
        prev_email.sent_at = datetime(2025, 1, 15, 9, 0, 0, tzinfo=timezone.utc)

        email_state = MagicMock()
        email_state.emails = {
            "email-context": email,
            "email-prev": prev_email,
        }
        mock_ues_client.email.get_state = AsyncMock(return_value=email_state)

        mock_llm_provider.queue_response("NEEDS_RESPONSE: Question about time")
        mock_llm_provider.queue_response("How about 3pm?")

        manager = ResponseAgentManager(
            ues_client=mock_ues_client,
            characters=sample_characters,
            llm_provider=mock_llm_provider,
        )

        await manager.process_turn()

        # Check the first LLM call (necessity check) included context
        calls = mock_llm_provider.get_call_history()
        necessity_call = calls[0]
        assert "I'm free this weekend!" in necessity_call["prompt"]
