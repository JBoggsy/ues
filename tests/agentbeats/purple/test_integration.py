"""Integration tests for Purple Agent workflow.

This module tests the complete Purple Agent lifecycle by simulating
the interaction between a Purple Agent and the Green Agent.

Tests cover:
- Full assessment lifecycle (start → turns → complete)
- Message parsing and response serialization
- Context management across turns
- Early completion handling
- Error scenarios
"""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentbeats.purple import (
    BaseAgent,
    AssessmentContext,
    AssessmentStartMessage,
    TurnStartMessage,
    AssessmentCompleteMessage,
    TurnCompleteMessage,
    EarlyCompletionMessage,
    InitialStateSummary,
    ModalityCounts,
    AssessmentCompleteReason,
    PurpleExecutor,
    parse_green_message,
    serialize_response,
)
from agentbeats.purple.examples.simple_agent import SimpleEmailAgent


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_time() -> datetime:
    """Sample datetime for testing."""
    return datetime(2026, 1, 22, 9, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def sample_initial_state() -> InitialStateSummary:
    """Sample initial state summary."""
    return InitialStateSummary(
        email=ModalityCounts(total=10, unread=3),
        calendar=ModalityCounts(total=5, events_today=2),
        sms=ModalityCounts(total=2),
    )


@pytest.fixture
def assessment_start_json(
    sample_time: datetime,
    sample_initial_state: InitialStateSummary,
) -> str:
    """JSON string for assessment start message."""
    msg = AssessmentStartMessage(
        ues_url="http://localhost:8000",
        api_key="test-api-key-123",
        current_time=sample_time,
        initial_state_summary=sample_initial_state,
    )
    return msg.model_dump_json()


@pytest.fixture
def turn_start_json(sample_time: datetime) -> str:
    """JSON string for turn start message."""
    msg = TurnStartMessage(
        current_time=sample_time + timedelta(hours=1),
        events_processed=2,
    )
    return msg.model_dump_json()


@pytest.fixture
def assessment_complete_json() -> str:
    """JSON string for assessment complete message."""
    msg = AssessmentCompleteMessage(
        reason=AssessmentCompleteReason.SCENARIO_COMPLETE,
    )
    return msg.model_dump_json()


# =============================================================================
# Mock UES Client
# =============================================================================


class MockEmail:
    """Mock email for testing."""

    def __init__(self, message_id: str, subject: str, read: bool = False):
        self.message_id = message_id
        self.subject = subject
        self.read = read


class MockEmailState:
    """Mock email state for testing."""

    def __init__(self, emails: list[MockEmail]):
        self.emails = emails


class MockChatMessage:
    """Mock chat message for testing."""

    def __init__(self, content: str, role: str = "user"):
        self.content = content
        self.role = role


class MockChatState:
    """Mock chat state for testing."""

    def __init__(self, messages: list[MockChatMessage]):
        self.messages = messages


def create_mock_ues_client(
    emails: list[MockEmail] | None = None,
    chat_messages: list[MockChatMessage] | None = None,
) -> MagicMock:
    """Create a mock AsyncUESClient for testing.

    Args:
        emails: List of mock emails to return from email.get_state().
        chat_messages: List of mock chat messages to return from chat.get_state().

    Returns:
        Configured mock client.
    """
    client = MagicMock()

    # Mock email client
    email_state = MockEmailState(emails or [])
    client.email.get_state = AsyncMock(return_value=email_state)
    client.email.mark_read = AsyncMock()

    # Mock chat client
    chat_state = MockChatState(chat_messages or [])
    client.chat.get_state = AsyncMock(return_value=chat_state)

    # Mock other clients (return empty states)
    client.calendar.get_state = AsyncMock(return_value=MagicMock(events=[]))
    client.sms.get_state = AsyncMock(return_value=MagicMock(conversations=[]))
    client.weather.get_state = AsyncMock(return_value=MagicMock())
    client.location.get_state = AsyncMock(return_value=MagicMock())
    client.time.get_state = AsyncMock(return_value=MagicMock())

    return client


# =============================================================================
# Integration Tests: Message Round-Trip
# =============================================================================


class TestMessageRoundTrip:
    """Tests for message parsing and serialization round-trip."""

    def test_assessment_start_round_trip(self, assessment_start_json: str):
        """Parse assessment_start JSON and verify fields."""
        msg = parse_green_message(assessment_start_json)

        assert isinstance(msg, AssessmentStartMessage)
        assert msg.ues_url == "http://localhost:8000"
        assert msg.api_key == "test-api-key-123"
        assert msg.initial_state_summary.email.total == 10
        assert msg.initial_state_summary.email.unread == 3

    def test_turn_start_round_trip(self, turn_start_json: str):
        """Parse turn_start JSON and verify fields."""
        msg = parse_green_message(turn_start_json)

        assert isinstance(msg, TurnStartMessage)
        assert msg.events_processed == 2

    def test_assessment_complete_round_trip(self, assessment_complete_json: str):
        """Parse assessment_complete JSON and verify fields."""
        msg = parse_green_message(assessment_complete_json)

        assert isinstance(msg, AssessmentCompleteMessage)
        assert msg.reason == AssessmentCompleteReason.SCENARIO_COMPLETE

    def test_turn_complete_serialization(self):
        """Serialize TurnCompleteMessage and verify JSON."""
        response = TurnCompleteMessage(
            actions_taken=5,
            notes="Processed 5 items",
            time_step=timedelta(hours=2),
        )

        json_str = serialize_response(response)
        data = json.loads(json_str)

        assert data["actions_taken"] == 5
        assert data["notes"] == "Processed 5 items"
        assert "time_step" in data

    def test_early_completion_serialization(self):
        """Serialize EarlyCompletionMessage and verify JSON."""
        response = EarlyCompletionMessage(
            reason="All goals achieved",
        )

        json_str = serialize_response(response)
        data = json.loads(json_str)

        assert data["reason"] == "All goals achieved"


# =============================================================================
# Integration Tests: SimpleEmailAgent Lifecycle
# =============================================================================


class TestSimpleEmailAgentLifecycle:
    """Integration tests for SimpleEmailAgent full lifecycle."""

    @pytest.fixture
    def agent(self) -> SimpleEmailAgent:
        """Create a SimpleEmailAgent instance."""
        return SimpleEmailAgent()

    @pytest.fixture
    def context(self, sample_time: datetime, sample_initial_state: InitialStateSummary) -> AssessmentContext:
        """Create an AssessmentContext for testing."""
        return AssessmentContext(
            assessment_id="test-assessment-001",
            ues_url="http://localhost:8000",
            api_key="test-key",
            current_time=sample_time,
            initial_state=sample_initial_state,
        )

    @pytest.fixture
    def assessment_start_msg(
        self,
        sample_time: datetime,
        sample_initial_state: InitialStateSummary,
    ) -> AssessmentStartMessage:
        """Create an AssessmentStartMessage for testing."""
        return AssessmentStartMessage(
            ues_url="http://localhost:8000",
            api_key="test-key",
            current_time=sample_time,
            initial_state_summary=sample_initial_state,
        )

    @pytest.mark.asyncio
    async def test_on_assessment_start_retrieves_instructions(
        self,
        agent: SimpleEmailAgent,
        context: AssessmentContext,
        assessment_start_msg: AssessmentStartMessage,
    ):
        """Agent retrieves user instructions from chat on start."""
        mock_ues = create_mock_ues_client(
            chat_messages=[MockChatMessage("Please manage my emails")]
        )

        await agent.on_assessment_start(assessment_start_msg, context, mock_ues)

        assert context.user_instructions == "Please manage my emails"
        mock_ues.chat.get_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_assessment_start_handles_empty_chat(
        self,
        agent: SimpleEmailAgent,
        context: AssessmentContext,
        assessment_start_msg: AssessmentStartMessage,
    ):
        """Agent handles empty chat gracefully."""
        mock_ues = create_mock_ues_client(chat_messages=[])

        await agent.on_assessment_start(assessment_start_msg, context, mock_ues)

        assert context.user_instructions == "No instructions provided"

    @pytest.mark.asyncio
    async def test_execute_turn_marks_emails_read(
        self,
        agent: SimpleEmailAgent,
        context: AssessmentContext,
    ):
        """Agent marks unread emails as read and tracks actions."""
        mock_ues = create_mock_ues_client(
            emails=[
                MockEmail("email-1", "Subject 1", read=False),
                MockEmail("email-2", "Subject 2", read=False),
                MockEmail("email-3", "Subject 3", read=True),  # Already read
            ]
        )

        response = await agent.execute_turn(context, mock_ues)

        # Should mark 2 unread emails
        assert isinstance(response, TurnCompleteMessage)
        assert response.actions_taken == 2
        assert context.actions_this_turn == 2
        assert context.total_actions == 2

        # Verify mark_read called for unread emails
        assert mock_ues.email.mark_read.call_count == 2
        mock_ues.email.mark_read.assert_any_call("email-1")
        mock_ues.email.mark_read.assert_any_call("email-2")

    @pytest.mark.asyncio
    async def test_execute_turn_returns_early_completion_when_done(
        self,
        agent: SimpleEmailAgent,
        context: AssessmentContext,
    ):
        """Agent returns early completion when no unread emails."""
        mock_ues = create_mock_ues_client(
            emails=[
                MockEmail("email-1", "Subject 1", read=True),
                MockEmail("email-2", "Subject 2", read=True),
            ]
        )

        response = await agent.execute_turn(context, mock_ues)

        assert isinstance(response, EarlyCompletionMessage)
        assert "processed" in response.reason.lower()
        assert mock_ues.email.mark_read.call_count == 0

    @pytest.mark.asyncio
    async def test_execute_turn_returns_early_completion_when_no_emails(
        self,
        agent: SimpleEmailAgent,
        context: AssessmentContext,
    ):
        """Agent returns early completion when no emails exist."""
        mock_ues = create_mock_ues_client(emails=[])

        response = await agent.execute_turn(context, mock_ues)

        assert isinstance(response, EarlyCompletionMessage)

    @pytest.mark.asyncio
    async def test_on_turn_start_updates_context(
        self,
        agent: SimpleEmailAgent,
        context: AssessmentContext,
        sample_time: datetime,
    ):
        """on_turn_start updates context with new time and events."""
        # Set up initial state
        context.actions_this_turn = 5
        context.turn_number = 0

        turn_start_msg = TurnStartMessage(
            current_time=sample_time + timedelta(hours=2),
            events_processed=3,
        )

        await agent.on_turn_start(turn_start_msg, context)

        assert context.turn_number == 1
        assert context.actions_this_turn == 0  # Reset
        assert context.current_time == sample_time + timedelta(hours=2)
        assert context.events_processed_last_turn == 3

    @pytest.mark.asyncio
    async def test_full_assessment_lifecycle(
        self,
        agent: SimpleEmailAgent,
        context: AssessmentContext,
        assessment_start_msg: AssessmentStartMessage,
        sample_time: datetime,
    ):
        """Test complete assessment lifecycle with multiple turns."""
        # Turn 1: 3 unread emails
        mock_ues_turn1 = create_mock_ues_client(
            chat_messages=[MockChatMessage("Manage my inbox")],
            emails=[
                MockEmail("e1", "Email 1", read=False),
                MockEmail("e2", "Email 2", read=False),
                MockEmail("e3", "Email 3", read=False),
            ],
        )

        # Assessment start
        await agent.on_assessment_start(assessment_start_msg, context, mock_ues_turn1)
        assert context.user_instructions == "Manage my inbox"

        # Turn 1: Execute
        response1 = await agent.execute_turn(context, mock_ues_turn1)
        assert isinstance(response1, TurnCompleteMessage)
        assert response1.actions_taken == 3
        assert context.total_actions == 3

        # Turn 2: Simulate time advance, some new emails arrived
        turn_start_msg = TurnStartMessage(
            current_time=sample_time + timedelta(hours=1),
            events_processed=2,
        )
        await agent.on_turn_start(turn_start_msg, context)

        mock_ues_turn2 = create_mock_ues_client(
            emails=[
                MockEmail("e1", "Email 1", read=True),
                MockEmail("e2", "Email 2", read=True),
                MockEmail("e3", "Email 3", read=True),
                MockEmail("e4", "New Email", read=False),  # New unread
            ],
        )

        response2 = await agent.execute_turn(context, mock_ues_turn2)
        assert isinstance(response2, TurnCompleteMessage)
        assert response2.actions_taken == 1
        assert context.total_actions == 4

        # Turn 3: No more unread emails
        turn_start_msg2 = TurnStartMessage(
            current_time=sample_time + timedelta(hours=2),
            events_processed=0,
        )
        await agent.on_turn_start(turn_start_msg2, context)

        mock_ues_turn3 = create_mock_ues_client(
            emails=[
                MockEmail("e1", "Email 1", read=True),
                MockEmail("e2", "Email 2", read=True),
                MockEmail("e3", "Email 3", read=True),
                MockEmail("e4", "New Email", read=True),
            ],
        )

        response3 = await agent.execute_turn(context, mock_ues_turn3)
        assert isinstance(response3, EarlyCompletionMessage)

        # Assessment complete
        complete_msg = AssessmentCompleteMessage(
            reason=AssessmentCompleteReason.EARLY_COMPLETION,
        )
        await agent.on_assessment_complete(complete_msg, context)

        # Verify final state
        assert context.turn_number == 2  # 0, 1, 2
        assert context.total_actions == 4


# =============================================================================
# Integration Tests: Custom Agent Implementations
# =============================================================================


class CountingAgent(BaseAgent):
    """Test agent that counts actions without doing real work."""

    def __init__(self):
        self.start_count = 0
        self.turn_count = 0
        self.complete_count = 0

    async def on_assessment_start(self, message, context, ues):
        self.start_count += 1

    async def execute_turn(self, context, ues):
        self.turn_count += 1
        context.record_action()
        return TurnCompleteMessage(
            actions_taken=context.actions_this_turn,
            notes=f"Turn {self.turn_count}",
        )

    async def on_assessment_complete(self, message, context):
        self.complete_count += 1


class EarlyExitAgent(BaseAgent):
    """Test agent that always exits early."""

    async def on_assessment_start(self, message, context, ues):
        pass

    async def execute_turn(self, context, ues):
        return EarlyCompletionMessage(reason="Done immediately")


class TestCustomAgentBehaviors:
    """Tests for various agent behavior patterns."""

    @pytest.fixture
    def context(self, sample_time: datetime) -> AssessmentContext:
        """Create a test context."""
        return AssessmentContext(
            assessment_id="test",
            ues_url="http://localhost:8000",
            api_key="key",
            current_time=sample_time,
        )

    @pytest.fixture
    def mock_ues(self) -> MagicMock:
        """Create a basic mock UES client."""
        return create_mock_ues_client()

    @pytest.mark.asyncio
    async def test_counting_agent_tracks_lifecycle(
        self,
        context: AssessmentContext,
        mock_ues: MagicMock,
        sample_time: datetime,
    ):
        """CountingAgent tracks all lifecycle calls."""
        agent = CountingAgent()
        msg = AssessmentStartMessage(
            ues_url="http://localhost:8000",
            api_key="key",
            current_time=sample_time,
            initial_state_summary=InitialStateSummary(),
        )

        # Start
        await agent.on_assessment_start(msg, context, mock_ues)
        assert agent.start_count == 1

        # Multiple turns
        await agent.execute_turn(context, mock_ues)
        await agent.execute_turn(context, mock_ues)
        await agent.execute_turn(context, mock_ues)
        assert agent.turn_count == 3

        # Complete
        complete_msg = AssessmentCompleteMessage(
            reason=AssessmentCompleteReason.SCENARIO_COMPLETE,
        )
        await agent.on_assessment_complete(complete_msg, context)
        assert agent.complete_count == 1

    @pytest.mark.asyncio
    async def test_early_exit_agent_returns_completion(
        self,
        context: AssessmentContext,
        mock_ues: MagicMock,
    ):
        """EarlyExitAgent returns EarlyCompletionMessage immediately."""
        agent = EarlyExitAgent()

        response = await agent.execute_turn(context, mock_ues)

        assert isinstance(response, EarlyCompletionMessage)
        assert response.reason == "Done immediately"


# =============================================================================
# Integration Tests: Context Across Turns
# =============================================================================


class TestContextAcrossTurns:
    """Tests for context state management across multiple turns."""

    @pytest.fixture
    def context(self, sample_time: datetime) -> AssessmentContext:
        """Create a test context."""
        return AssessmentContext(
            assessment_id="test",
            ues_url="http://localhost:8000",
            api_key="key",
            current_time=sample_time,
        )

    @pytest.mark.asyncio
    async def test_action_count_accumulates_across_turns(
        self,
        context: AssessmentContext,
        sample_time: datetime,
    ):
        """Total actions accumulate while per-turn resets."""
        agent = CountingAgent()
        mock_ues = create_mock_ues_client()

        # Turn 1: 1 action
        await agent.execute_turn(context, mock_ues)
        assert context.actions_this_turn == 1
        assert context.total_actions == 1

        # Start new turn
        turn_msg = TurnStartMessage(
            current_time=sample_time + timedelta(hours=1),
            events_processed=0,
        )
        await agent.on_turn_start(turn_msg, context)

        # Turn 2: 1 action (per-turn resets, total accumulates)
        await agent.execute_turn(context, mock_ues)
        assert context.actions_this_turn == 1
        assert context.total_actions == 2

    @pytest.mark.asyncio
    async def test_custom_data_persists_across_turns(
        self,
        context: AssessmentContext,
        sample_time: datetime,
    ):
        """Custom data stored in context persists."""

        class StatefulAgent(BaseAgent):
            async def on_assessment_start(self, message, context, ues):
                context.set_custom("seen_emails", set())

            async def execute_turn(self, context, ues):
                seen = context.get_custom("seen_emails")
                seen.add(f"email-{context.turn_number}")
                return TurnCompleteMessage(actions_taken=0)

        agent = StatefulAgent()
        mock_ues = create_mock_ues_client()

        # Start
        msg = AssessmentStartMessage(
            ues_url="http://localhost:8000",
            api_key="key",
            current_time=sample_time,
            initial_state_summary=InitialStateSummary(),
        )
        await agent.on_assessment_start(msg, context, mock_ues)

        # Turn 0
        await agent.execute_turn(context, mock_ues)

        # Turn 1
        turn_msg = TurnStartMessage(
            current_time=sample_time + timedelta(hours=1),
            events_processed=0,
        )
        await agent.on_turn_start(turn_msg, context)
        await agent.execute_turn(context, mock_ues)

        # Verify data persisted
        seen = context.get_custom("seen_emails")
        assert "email-0" in seen
        assert "email-1" in seen


# =============================================================================
# Integration Tests: Error Scenarios
# =============================================================================


class TestErrorScenarios:
    """Tests for error handling scenarios."""

    @pytest.fixture
    def context(self, sample_time: datetime) -> AssessmentContext:
        """Create a test context."""
        return AssessmentContext(
            assessment_id="test",
            ues_url="http://localhost:8000",
            api_key="key",
            current_time=sample_time,
        )

    @pytest.mark.asyncio
    async def test_agent_can_handle_ues_error(self, context: AssessmentContext):
        """Agent can gracefully handle UES API errors."""

        class RobustAgent(BaseAgent):
            async def on_assessment_start(self, message, context, ues):
                pass

            async def execute_turn(self, context, ues):
                try:
                    await ues.email.get_state()
                except Exception as e:
                    return EarlyCompletionMessage(
                        reason=f"Error accessing UES: {e}"
                    )
                return TurnCompleteMessage(actions_taken=0)

        agent = RobustAgent()
        mock_ues = MagicMock()
        mock_ues.email.get_state = AsyncMock(side_effect=Exception("Connection failed"))

        response = await agent.execute_turn(context, mock_ues)

        assert isinstance(response, EarlyCompletionMessage)
        assert "Connection failed" in response.reason

    def test_parse_invalid_message_raises_error(self):
        """Parsing invalid JSON raises MessageParseError."""
        from agentbeats.purple.executor import MessageParseError

        with pytest.raises(MessageParseError):
            parse_green_message("not valid json")

    def test_parse_unknown_message_type_raises_error(self):
        """Parsing unknown message type raises MessageParseError."""
        from agentbeats.purple.executor import MessageParseError

        with pytest.raises(MessageParseError):
            parse_green_message('{"unknown_field": "value"}')
