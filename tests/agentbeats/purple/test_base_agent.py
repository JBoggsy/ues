"""Tests for Purple Agent base_agent module.

This module tests the BaseAgent abstract class and SimpleAgent implementation.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from agentbeats.purple.base_agent import BaseAgent, SimpleAgent
from agentbeats.purple.context import AssessmentContext
from agentbeats.purple.schemas import (
    AssessmentStartMessage,
    TurnStartMessage,
    AssessmentCompleteMessage,
    AssessmentCompleteReason,
    TurnCompleteMessage,
    EarlyCompletionMessage,
    InitialStateSummary,
    ModalityCounts,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_time() -> datetime:
    """Sample datetime for tests."""
    return datetime(2026, 1, 22, 9, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def context(sample_time: datetime) -> AssessmentContext:
    """Create a sample AssessmentContext for tests."""
    return AssessmentContext(
        assessment_id="test-001",
        ues_url="http://localhost:8000",
        api_key="test-key",
        current_time=sample_time,
        initial_state=InitialStateSummary(
            email=ModalityCounts(total=5, unread=3),
            chat=ModalityCounts(total=1, unread=1),
        ),
    )


@pytest.fixture
def assessment_start_message(sample_time: datetime) -> AssessmentStartMessage:
    """Create a sample AssessmentStartMessage."""
    return AssessmentStartMessage(
        ues_url="http://localhost:8000",
        api_key="test-key",
        current_time=sample_time,
        initial_state_summary=InitialStateSummary(
            email=ModalityCounts(total=5, unread=3),
            chat=ModalityCounts(total=1, unread=1),
        ),
    )


@pytest.fixture
def mock_ues_client() -> MagicMock:
    """Create a mock UES client for testing."""
    mock = MagicMock()

    # Mock chat.get_state() to return messages with user instructions
    mock_chat_state = MagicMock()
    mock_chat_state.messages = [
        MagicMock(content="Please help me manage my emails today.")
    ]
    mock.chat.get_state = AsyncMock(return_value=mock_chat_state)

    # Mock email.get_state()
    mock_email_state = MagicMock()
    mock_email_state.emails = []
    mock.email.get_state = AsyncMock(return_value=mock_email_state)

    return mock


# =============================================================================
# BaseAgent Abstract Class Tests
# =============================================================================


class TestBaseAgentAbstract:
    """Tests verifying BaseAgent is an abstract class."""

    def test_cannot_instantiate_base_agent(self):
        """BaseAgent cannot be instantiated directly."""
        with pytest.raises(TypeError, match="abstract"):
            BaseAgent()

    def test_must_implement_on_assessment_start(self, mock_ues_client):
        """Subclass must implement on_assessment_start."""

        class IncompleteAgent(BaseAgent):
            async def execute_turn(self, context, ues):
                return TurnCompleteMessage(actions_taken=0)

        with pytest.raises(TypeError, match="abstract"):
            IncompleteAgent()

    def test_must_implement_execute_turn(self, mock_ues_client):
        """Subclass must implement execute_turn."""

        class IncompleteAgent(BaseAgent):
            async def on_assessment_start(self, message, context, ues):
                pass

        with pytest.raises(TypeError, match="abstract"):
            IncompleteAgent()


# =============================================================================
# Concrete Agent Implementation Tests
# =============================================================================


class ConcreteTestAgent(BaseAgent):
    """A concrete agent implementation for testing."""

    def __init__(self):
        self.start_called = False
        self.turn_called = False
        self.turn_start_called = False
        self.complete_called = False
        self.actions_to_take = 0
        self.should_complete_early = False

    async def on_assessment_start(
        self,
        message: AssessmentStartMessage,
        context: AssessmentContext,
        ues,
    ) -> None:
        self.start_called = True
        chat_state = await ues.chat.get_state()
        if chat_state.messages:
            context.user_instructions = chat_state.messages[0].content

    async def execute_turn(
        self,
        context: AssessmentContext,
        ues,
    ) -> TurnCompleteMessage | EarlyCompletionMessage:
        self.turn_called = True

        if self.should_complete_early:
            return EarlyCompletionMessage(reason="Testing early completion")

        for _ in range(self.actions_to_take):
            context.record_action()

        return TurnCompleteMessage(
            actions_taken=context.actions_this_turn,
            notes=f"Completed turn {context.turn_number}",
            time_step=timedelta(hours=1),
        )

    async def on_turn_start(
        self,
        message: TurnStartMessage,
        context: AssessmentContext,
    ) -> None:
        self.turn_start_called = True
        await super().on_turn_start(message, context)

    async def on_assessment_complete(
        self,
        message: AssessmentCompleteMessage,
        context: AssessmentContext,
    ) -> None:
        self.complete_called = True


class TestConcreteAgentImplementation:
    """Tests for a concrete BaseAgent implementation."""

    def test_can_instantiate_concrete_agent(self):
        """Concrete implementation can be instantiated."""
        agent = ConcreteTestAgent()
        assert agent is not None

    @pytest.mark.asyncio
    async def test_on_assessment_start_called(
        self,
        assessment_start_message: AssessmentStartMessage,
        context: AssessmentContext,
        mock_ues_client: MagicMock,
    ):
        """on_assessment_start is called and retrieves instructions."""
        agent = ConcreteTestAgent()

        await agent.on_assessment_start(
            assessment_start_message, context, mock_ues_client
        )

        assert agent.start_called
        assert context.user_instructions == "Please help me manage my emails today."

    @pytest.mark.asyncio
    async def test_execute_turn_returns_turn_complete(
        self,
        context: AssessmentContext,
        mock_ues_client: MagicMock,
    ):
        """execute_turn returns TurnCompleteMessage."""
        agent = ConcreteTestAgent()
        agent.actions_to_take = 3

        result = await agent.execute_turn(context, mock_ues_client)

        assert agent.turn_called
        assert isinstance(result, TurnCompleteMessage)
        assert result.actions_taken == 3
        assert result.notes == "Completed turn 0"
        assert result.time_step == timedelta(hours=1)

    @pytest.mark.asyncio
    async def test_execute_turn_returns_early_completion(
        self,
        context: AssessmentContext,
        mock_ues_client: MagicMock,
    ):
        """execute_turn can return EarlyCompletionMessage."""
        agent = ConcreteTestAgent()
        agent.should_complete_early = True

        result = await agent.execute_turn(context, mock_ues_client)

        assert isinstance(result, EarlyCompletionMessage)
        assert result.reason == "Testing early completion"

    @pytest.mark.asyncio
    async def test_on_turn_start_updates_context(
        self,
        context: AssessmentContext,
        sample_time: datetime,
    ):
        """on_turn_start updates context with new time and events."""
        agent = ConcreteTestAgent()
        new_time = sample_time + timedelta(hours=2)
        message = TurnStartMessage(current_time=new_time, events_processed=5)

        await agent.on_turn_start(message, context)

        assert agent.turn_start_called
        assert context.current_time == new_time
        assert context.events_processed_last_turn == 5
        assert context.turn_number == 1  # Incremented

    @pytest.mark.asyncio
    async def test_on_assessment_complete_called(
        self,
        context: AssessmentContext,
    ):
        """on_assessment_complete is called for cleanup."""
        agent = ConcreteTestAgent()
        message = AssessmentCompleteMessage(
            reason=AssessmentCompleteReason.SCENARIO_COMPLETE,
            message="Assessment finished",
        )

        await agent.on_assessment_complete(message, context)

        assert agent.complete_called


# =============================================================================
# Default Method Implementation Tests
# =============================================================================


class MinimalAgent(BaseAgent):
    """Minimal agent that only implements required methods."""

    async def on_assessment_start(self, message, context, ues):
        pass

    async def execute_turn(self, context, ues):
        return TurnCompleteMessage(actions_taken=0)


class TestDefaultMethodImplementations:
    """Tests for default implementations of optional methods."""

    @pytest.mark.asyncio
    async def test_default_on_turn_start(
        self,
        context: AssessmentContext,
        sample_time: datetime,
    ):
        """Default on_turn_start updates context correctly."""
        agent = MinimalAgent()
        new_time = sample_time + timedelta(hours=1)
        message = TurnStartMessage(current_time=new_time, events_processed=3)

        # Record some actions to verify reset
        context.record_action()
        context.record_action()
        assert context.actions_this_turn == 2

        await agent.on_turn_start(message, context)

        assert context.turn_number == 1
        assert context.current_time == new_time
        assert context.events_processed_last_turn == 3
        assert context.actions_this_turn == 0  # Reset

    @pytest.mark.asyncio
    async def test_default_on_assessment_complete(
        self,
        context: AssessmentContext,
    ):
        """Default on_assessment_complete does nothing (no error)."""
        agent = MinimalAgent()
        message = AssessmentCompleteMessage(
            reason=AssessmentCompleteReason.TIMEOUT,
        )

        # Should not raise
        await agent.on_assessment_complete(message, context)


# =============================================================================
# SimpleAgent Tests
# =============================================================================


class TestSimpleAgent:
    """Tests for the SimpleAgent implementation."""

    def test_can_instantiate(self):
        """SimpleAgent can be instantiated."""
        agent = SimpleAgent()
        assert agent is not None

    @pytest.mark.asyncio
    async def test_retrieves_instructions(
        self,
        assessment_start_message: AssessmentStartMessage,
        context: AssessmentContext,
        mock_ues_client: MagicMock,
    ):
        """SimpleAgent retrieves user instructions from chat."""
        agent = SimpleAgent()

        await agent.on_assessment_start(
            assessment_start_message, context, mock_ues_client
        )

        assert context.user_instructions == "Please help me manage my emails today."

    @pytest.mark.asyncio
    async def test_retrieves_instructions_empty_chat(
        self,
        assessment_start_message: AssessmentStartMessage,
        context: AssessmentContext,
    ):
        """SimpleAgent handles empty chat gracefully."""
        mock_client = MagicMock()
        mock_chat_state = MagicMock()
        mock_chat_state.messages = []  # Empty
        mock_client.chat.get_state = AsyncMock(return_value=mock_chat_state)

        agent = SimpleAgent()

        await agent.on_assessment_start(
            assessment_start_message, context, mock_client
        )

        assert context.user_instructions is None

    @pytest.mark.asyncio
    async def test_execute_turn_returns_early_completion(
        self,
        context: AssessmentContext,
        mock_ues_client: MagicMock,
    ):
        """SimpleAgent immediately returns early completion."""
        agent = SimpleAgent()

        result = await agent.execute_turn(context, mock_ues_client)

        assert isinstance(result, EarlyCompletionMessage)
        assert "SimpleAgent" in result.reason
        assert "no" in result.reason.lower() or "not" in result.reason.lower()


# =============================================================================
# Type Checking Tests
# =============================================================================


class TestTypeHints:
    """Tests verifying type hints work correctly."""

    def test_turn_response_accepts_turn_complete(self):
        """TurnResponse type accepts TurnCompleteMessage."""
        from agentbeats.purple.schemas import TurnResponse

        response: TurnResponse = TurnCompleteMessage(actions_taken=5)
        assert response.actions_taken == 5

    def test_turn_response_accepts_early_completion(self):
        """TurnResponse type accepts EarlyCompletionMessage."""
        from agentbeats.purple.schemas import TurnResponse

        response: TurnResponse = EarlyCompletionMessage(reason="Done")
        assert response.reason == "Done"


# =============================================================================
# Integration Tests
# =============================================================================


class TestAgentLifecycleIntegration:
    """Integration tests simulating full agent lifecycle."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(
        self,
        assessment_start_message: AssessmentStartMessage,
        context: AssessmentContext,
        mock_ues_client: MagicMock,
        sample_time: datetime,
    ):
        """Simulate a complete agent lifecycle."""
        agent = ConcreteTestAgent()
        agent.actions_to_take = 2

        # 1. Assessment start
        await agent.on_assessment_start(
            assessment_start_message, context, mock_ues_client
        )
        assert agent.start_called
        assert context.user_instructions is not None

        # 2. First turn (turn 0)
        result = await agent.execute_turn(context, mock_ues_client)
        assert isinstance(result, TurnCompleteMessage)
        assert result.actions_taken == 2
        assert context.total_actions == 2

        # 3. Turn start (turn 1)
        turn_start = TurnStartMessage(
            current_time=sample_time + timedelta(hours=1),
            events_processed=1,
        )
        await agent.on_turn_start(turn_start, context)
        assert context.turn_number == 1
        assert context.actions_this_turn == 0

        # 4. Second turn
        agent.actions_to_take = 1
        result = await agent.execute_turn(context, mock_ues_client)
        assert result.actions_taken == 1
        assert context.total_actions == 3

        # 5. Assessment complete
        complete_msg = AssessmentCompleteMessage(
            reason=AssessmentCompleteReason.EARLY_COMPLETION,
        )
        await agent.on_assessment_complete(complete_msg, context)
        assert agent.complete_called

    @pytest.mark.asyncio
    async def test_early_completion_lifecycle(
        self,
        assessment_start_message: AssessmentStartMessage,
        context: AssessmentContext,
        mock_ues_client: MagicMock,
    ):
        """Test lifecycle when agent completes early."""
        agent = ConcreteTestAgent()
        agent.should_complete_early = True

        # Assessment start
        await agent.on_assessment_start(
            assessment_start_message, context, mock_ues_client
        )

        # First turn returns early completion
        result = await agent.execute_turn(context, mock_ues_client)
        assert isinstance(result, EarlyCompletionMessage)
        assert context.total_actions == 0  # No actions taken

        # Assessment complete
        complete_msg = AssessmentCompleteMessage(
            reason=AssessmentCompleteReason.EARLY_COMPLETION,
        )
        await agent.on_assessment_complete(complete_msg, context)
        assert agent.complete_called
