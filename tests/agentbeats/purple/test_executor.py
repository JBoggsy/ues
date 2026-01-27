"""Tests for Purple Agent executor module.

This module tests the PurpleExecutor class and helper functions for
handling the A2A protocol lifecycle.
"""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentbeats.purple.executor import (
    MessageParseError,
    PurpleExecutor,
    parse_green_message,
    serialize_response,
)
from agentbeats.purple.schemas import (
    AssessmentCompleteMessage,
    AssessmentCompleteReason,
    AssessmentStartMessage,
    EarlyCompletionMessage,
    InitialStateSummary,
    ModalityCounts,
    TurnCompleteMessage,
    TurnStartMessage,
)
from agentbeats.purple.context import AssessmentContext
from agentbeats.purple.base_agent import BaseAgent


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
        calendar=ModalityCounts(total=5),
        sms=ModalityCounts(total=2),
    )


@pytest.fixture
def assessment_start_message(
    sample_time: datetime,
    sample_initial_state: InitialStateSummary,
) -> AssessmentStartMessage:
    """Sample assessment start message."""
    return AssessmentStartMessage(
        ues_url="http://localhost:8000",
        api_key="test-api-key-123",
        current_time=sample_time,
        initial_state_summary=sample_initial_state,
    )


@pytest.fixture
def turn_start_message(sample_time: datetime) -> TurnStartMessage:
    """Sample turn start message."""
    return TurnStartMessage(
        current_time=sample_time + timedelta(hours=1),
        events_processed=3,
    )


@pytest.fixture
def assessment_complete_message() -> AssessmentCompleteMessage:
    """Sample assessment complete message."""
    return AssessmentCompleteMessage(
        reason=AssessmentCompleteReason.SCENARIO_COMPLETE,
    )


@pytest.fixture
def turn_complete_response() -> TurnCompleteMessage:
    """Sample turn complete response."""
    return TurnCompleteMessage(
        actions_taken=5,
        notes="Processed 5 emails",
        time_step=timedelta(hours=1),
    )


@pytest.fixture
def early_completion_response() -> EarlyCompletionMessage:
    """Sample early completion response."""
    return EarlyCompletionMessage(
        reason="All goals achieved",
    )


# =============================================================================
# Tests: parse_green_message
# =============================================================================


class TestParseGreenMessage:
    """Tests for the parse_green_message function."""

    def test_parse_assessment_start_message(
        self,
        assessment_start_message: AssessmentStartMessage,
    ):
        """Successfully parses AssessmentStartMessage from JSON."""
        json_str = assessment_start_message.model_dump_json()
        result = parse_green_message(json_str)

        assert isinstance(result, AssessmentStartMessage)
        assert result.ues_url == "http://localhost:8000"
        assert result.api_key == "test-api-key-123"
        assert result.initial_state_summary.email.total == 10

    def test_parse_turn_start_message(
        self,
        turn_start_message: TurnStartMessage,
    ):
        """Successfully parses TurnStartMessage from JSON."""
        json_str = turn_start_message.model_dump_json()
        result = parse_green_message(json_str)

        assert isinstance(result, TurnStartMessage)
        assert result.events_processed == 3

    def test_parse_assessment_complete_message(
        self,
        assessment_complete_message: AssessmentCompleteMessage,
    ):
        """Successfully parses AssessmentCompleteMessage from JSON."""
        json_str = assessment_complete_message.model_dump_json()
        result = parse_green_message(json_str)

        assert isinstance(result, AssessmentCompleteMessage)
        assert result.reason == AssessmentCompleteReason.SCENARIO_COMPLETE

    def test_parse_invalid_json_raises_error(self):
        """Raises MessageParseError for invalid JSON."""
        with pytest.raises(MessageParseError) as exc_info:
            parse_green_message("not valid json")

        assert "Invalid JSON" in exc_info.value.reason
        assert exc_info.value.raw_message == "not valid json"

    def test_parse_non_object_raises_error(self):
        """Raises MessageParseError for non-object JSON."""
        with pytest.raises(MessageParseError) as exc_info:
            parse_green_message('"just a string"')

        assert "Expected object" in exc_info.value.reason

    def test_parse_unknown_message_type_raises_error(self):
        """Raises MessageParseError for unrecognizable message type."""
        with pytest.raises(MessageParseError) as exc_info:
            parse_green_message('{"unknown_field": "value"}')

        assert "Cannot determine message type" in exc_info.value.reason

    def test_parse_invalid_assessment_start_raises_error(self):
        """Raises MessageParseError for malformed AssessmentStartMessage."""
        # Has ues_url but invalid (missing required fields)
        json_str = '{"ues_url": "http://localhost:8000", "api_key": "key"}'

        with pytest.raises(MessageParseError) as exc_info:
            parse_green_message(json_str)

        assert "Invalid AssessmentStartMessage" in exc_info.value.reason

    def test_parse_invalid_turn_start_raises_error(self):
        """Raises MessageParseError for malformed TurnStartMessage."""
        # Has events_processed but missing current_time
        json_str = '{"events_processed": 3}'

        with pytest.raises(MessageParseError) as exc_info:
            parse_green_message(json_str)

        # This should fail since it doesn't match any pattern well
        # current_time is required for TurnStartMessage
        assert "Cannot determine message type" in exc_info.value.reason or \
               "Invalid" in exc_info.value.reason


# =============================================================================
# Tests: serialize_response
# =============================================================================


class TestSerializeResponse:
    """Tests for the serialize_response function."""

    def test_serialize_turn_complete(
        self,
        turn_complete_response: TurnCompleteMessage,
    ):
        """Serializes TurnCompleteMessage to JSON."""
        result = serialize_response(turn_complete_response)
        data = json.loads(result)

        assert data["actions_taken"] == 5
        assert data["notes"] == "Processed 5 emails"
        assert "time_step" in data

    def test_serialize_early_completion(
        self,
        early_completion_response: EarlyCompletionMessage,
    ):
        """Serializes EarlyCompletionMessage to JSON."""
        result = serialize_response(early_completion_response)
        data = json.loads(result)

        assert data["reason"] == "All goals achieved"

    def test_serialize_minimal_turn_complete(self):
        """Serializes minimal TurnCompleteMessage."""
        response = TurnCompleteMessage(actions_taken=0)
        result = serialize_response(response)
        data = json.loads(result)

        assert data["actions_taken"] == 0

    def test_serialize_minimal_early_completion(self):
        """Serializes minimal EarlyCompletionMessage."""
        response = EarlyCompletionMessage()
        result = serialize_response(response)
        data = json.loads(result)

        # Should be valid JSON (may have null reason)
        assert isinstance(data, dict)


# =============================================================================
# Tests: MessageParseError
# =============================================================================


class TestMessageParseError:
    """Tests for the MessageParseError exception."""

    def test_exception_has_raw_message(self):
        """MessageParseError stores raw message."""
        error = MessageParseError("raw text", "some reason")
        assert error.raw_message == "raw text"

    def test_exception_has_reason(self):
        """MessageParseError stores reason."""
        error = MessageParseError("raw text", "some reason")
        assert error.reason == "some reason"

    def test_exception_message_format(self):
        """MessageParseError formats message correctly."""
        error = MessageParseError("raw text", "some reason")
        assert "Failed to parse Green Agent message" in str(error)
        assert "some reason" in str(error)


# =============================================================================
# Tests: PurpleExecutor
# =============================================================================


class MockAgent(BaseAgent):
    """Mock agent for testing the executor."""

    def __init__(self):
        self.on_assessment_start_called = False
        self.execute_turn_called = False
        self.on_turn_start_called = False
        self.on_assessment_complete_called = False
        self.turn_response: TurnCompleteMessage | EarlyCompletionMessage = (
            TurnCompleteMessage(actions_taken=0, notes="Mock turn")
        )

    async def on_assessment_start(self, message, context, ues):
        self.on_assessment_start_called = True
        self.assessment_start_message = message
        self.assessment_start_context = context
        self.assessment_start_ues = ues

    async def execute_turn(self, context, ues):
        self.execute_turn_called = True
        self.execute_turn_context = context
        self.execute_turn_ues = ues
        return self.turn_response

    async def on_turn_start(self, message, context):
        self.on_turn_start_called = True
        self.turn_start_message = message
        self.turn_start_context = context
        # Call parent to update context
        await super().on_turn_start(message, context)

    async def on_assessment_complete(self, message, context):
        self.on_assessment_complete_called = True
        self.assessment_complete_message = message
        self.assessment_complete_context = context


class TestPurpleExecutorInit:
    """Tests for PurpleExecutor initialization."""

    def test_init_with_factory(self):
        """Executor initializes with agent factory."""
        executor = PurpleExecutor(agent_factory=MockAgent)

        assert executor._agent_factory == MockAgent
        assert executor.agents == {}
        assert executor.contexts == {}
        assert executor.ues_clients == {}

    def test_init_with_lambda_factory(self):
        """Executor accepts lambda as factory."""
        executor = PurpleExecutor(agent_factory=lambda: MockAgent())

        assert callable(executor._agent_factory)


class TestPurpleExecutorContextManagement:
    """Tests for executor context/agent management."""

    def test_cleanup_context_removes_all(self):
        """_cleanup_context removes agent, context, and client."""
        executor = PurpleExecutor(agent_factory=MockAgent)

        # Manually add entries
        executor.agents["ctx-1"] = MockAgent()
        executor.contexts["ctx-1"] = MagicMock()
        executor.ues_clients["ctx-1"] = MagicMock()

        executor._cleanup_context("ctx-1")

        assert "ctx-1" not in executor.agents
        assert "ctx-1" not in executor.contexts
        assert "ctx-1" not in executor.ues_clients

    def test_cleanup_context_nonexistent_is_safe(self):
        """_cleanup_context handles missing context gracefully."""
        executor = PurpleExecutor(agent_factory=MockAgent)

        # Should not raise
        executor._cleanup_context("nonexistent")

    def test_cleanup_partial_context(self):
        """_cleanup_context handles partially populated context."""
        executor = PurpleExecutor(agent_factory=MockAgent)

        # Only agent exists
        executor.agents["ctx-1"] = MockAgent()

        # Should not raise
        executor._cleanup_context("ctx-1")
        assert "ctx-1" not in executor.agents


class TestPurpleExecutorAssessmentStart:
    """Tests for executor handling of assessment_start messages."""

    @pytest.fixture
    def executor(self) -> PurpleExecutor:
        """Create executor with mock agent."""
        return PurpleExecutor(agent_factory=MockAgent)

    @pytest.fixture
    def mock_updater(self) -> MagicMock:
        """Create mock TaskUpdater."""
        updater = MagicMock()
        updater.start_work = AsyncMock()
        updater.update_status = AsyncMock()
        updater.complete = AsyncMock()
        updater.failed = AsyncMock()
        updater._terminal_state_reached = False
        return updater

    @pytest.mark.asyncio
    async def test_handle_assessment_start_creates_agent(
        self,
        executor: PurpleExecutor,
        mock_updater: MagicMock,
        assessment_start_message: AssessmentStartMessage,
    ):
        """assessment_start creates agent and stores it."""
        await executor._handle_assessment_start(
            assessment_start_message,
            "ctx-123",
            mock_updater,
        )

        assert "ctx-123" in executor.agents
        assert isinstance(executor.agents["ctx-123"], MockAgent)

    @pytest.mark.asyncio
    async def test_handle_assessment_start_creates_context(
        self,
        executor: PurpleExecutor,
        mock_updater: MagicMock,
        assessment_start_message: AssessmentStartMessage,
    ):
        """assessment_start creates AssessmentContext."""
        await executor._handle_assessment_start(
            assessment_start_message,
            "ctx-123",
            mock_updater,
        )

        assert "ctx-123" in executor.contexts
        ctx = executor.contexts["ctx-123"]
        assert isinstance(ctx, AssessmentContext)
        assert ctx.assessment_id == "ctx-123"
        assert ctx.ues_url == "http://localhost:8000"
        assert ctx.api_key == "test-api-key-123"

    @pytest.mark.asyncio
    async def test_handle_assessment_start_creates_ues_client(
        self,
        executor: PurpleExecutor,
        mock_updater: MagicMock,
        assessment_start_message: AssessmentStartMessage,
    ):
        """assessment_start creates AsyncUESClient."""
        await executor._handle_assessment_start(
            assessment_start_message,
            "ctx-123",
            mock_updater,
        )

        assert "ctx-123" in executor.ues_clients
        ues = executor.ues_clients["ctx-123"]
        # Check it's configured correctly (uses private attribute)
        assert ues._base_url == "http://localhost:8000"

    @pytest.mark.asyncio
    async def test_handle_assessment_start_calls_agent_methods(
        self,
        executor: PurpleExecutor,
        mock_updater: MagicMock,
        assessment_start_message: AssessmentStartMessage,
    ):
        """assessment_start calls on_assessment_start and execute_turn."""
        await executor._handle_assessment_start(
            assessment_start_message,
            "ctx-123",
            mock_updater,
        )

        agent = executor.agents["ctx-123"]
        assert agent.on_assessment_start_called
        assert agent.execute_turn_called

    @pytest.mark.asyncio
    async def test_handle_assessment_start_sends_response(
        self,
        executor: PurpleExecutor,
        mock_updater: MagicMock,
        assessment_start_message: AssessmentStartMessage,
    ):
        """assessment_start sends turn response via updater."""
        await executor._handle_assessment_start(
            assessment_start_message,
            "ctx-123",
            mock_updater,
        )

        mock_updater.update_status.assert_called()


class TestPurpleExecutorTurnStart:
    """Tests for executor handling of turn_start messages."""

    @pytest.fixture
    def executor_with_context(
        self,
        sample_time: datetime,
    ) -> tuple[PurpleExecutor, MockAgent]:
        """Create executor with pre-existing agent and context."""
        executor = PurpleExecutor(agent_factory=MockAgent)
        agent = MockAgent()

        context = AssessmentContext(
            assessment_id="ctx-123",
            ues_url="http://localhost:8000",
            api_key="test-key",
            current_time=sample_time,
        )

        executor.agents["ctx-123"] = agent
        executor.contexts["ctx-123"] = context
        executor.ues_clients["ctx-123"] = MagicMock()

        return executor, agent

    @pytest.fixture
    def mock_updater(self) -> MagicMock:
        """Create mock TaskUpdater."""
        updater = MagicMock()
        updater.update_status = AsyncMock()
        return updater

    @pytest.mark.asyncio
    async def test_handle_turn_start_calls_on_turn_start(
        self,
        executor_with_context: tuple[PurpleExecutor, MockAgent],
        mock_updater: MagicMock,
        turn_start_message: TurnStartMessage,
    ):
        """turn_start calls agent's on_turn_start method."""
        executor, agent = executor_with_context

        await executor._handle_turn_start(
            turn_start_message,
            "ctx-123",
            mock_updater,
        )

        assert agent.on_turn_start_called
        assert agent.turn_start_message == turn_start_message

    @pytest.mark.asyncio
    async def test_handle_turn_start_calls_execute_turn(
        self,
        executor_with_context: tuple[PurpleExecutor, MockAgent],
        mock_updater: MagicMock,
        turn_start_message: TurnStartMessage,
    ):
        """turn_start calls agent's execute_turn method."""
        executor, agent = executor_with_context

        await executor._handle_turn_start(
            turn_start_message,
            "ctx-123",
            mock_updater,
        )

        assert agent.execute_turn_called

    @pytest.mark.asyncio
    async def test_handle_turn_start_updates_context(
        self,
        executor_with_context: tuple[PurpleExecutor, MockAgent],
        mock_updater: MagicMock,
        turn_start_message: TurnStartMessage,
    ):
        """turn_start updates context with new time and events."""
        executor, agent = executor_with_context

        await executor._handle_turn_start(
            turn_start_message,
            "ctx-123",
            mock_updater,
        )

        ctx = executor.contexts["ctx-123"]
        assert ctx.current_time == turn_start_message.current_time
        assert ctx.events_processed_last_turn == 3
        assert ctx.turn_number == 1

    @pytest.mark.asyncio
    async def test_handle_turn_start_missing_context_raises(
        self,
        mock_updater: MagicMock,
        turn_start_message: TurnStartMessage,
    ):
        """turn_start raises ValueError if no context exists."""
        executor = PurpleExecutor(agent_factory=MockAgent)

        with pytest.raises(ValueError) as exc_info:
            await executor._handle_turn_start(
                turn_start_message,
                "nonexistent",
                mock_updater,
            )

        assert "No active assessment" in str(exc_info.value)


class TestPurpleExecutorAssessmentComplete:
    """Tests for executor handling of assessment_complete messages."""

    @pytest.fixture
    def executor_with_context(
        self,
        sample_time: datetime,
    ) -> tuple[PurpleExecutor, MockAgent]:
        """Create executor with pre-existing agent and context."""
        executor = PurpleExecutor(agent_factory=MockAgent)
        agent = MockAgent()

        context = AssessmentContext(
            assessment_id="ctx-123",
            ues_url="http://localhost:8000",
            api_key="test-key",
            current_time=sample_time,
        )

        executor.agents["ctx-123"] = agent
        executor.contexts["ctx-123"] = context
        executor.ues_clients["ctx-123"] = MagicMock()

        return executor, agent

    @pytest.fixture
    def mock_updater(self) -> MagicMock:
        """Create mock TaskUpdater."""
        updater = MagicMock()
        return updater

    @pytest.mark.asyncio
    async def test_handle_assessment_complete_calls_agent(
        self,
        executor_with_context: tuple[PurpleExecutor, MockAgent],
        mock_updater: MagicMock,
        assessment_complete_message: AssessmentCompleteMessage,
    ):
        """assessment_complete calls agent's on_assessment_complete method."""
        executor, agent = executor_with_context

        await executor._handle_assessment_complete(
            assessment_complete_message,
            "ctx-123",
            mock_updater,
        )

        assert agent.on_assessment_complete_called
        assert agent.assessment_complete_message == assessment_complete_message

    @pytest.mark.asyncio
    async def test_handle_assessment_complete_cleans_up(
        self,
        executor_with_context: tuple[PurpleExecutor, MockAgent],
        mock_updater: MagicMock,
        assessment_complete_message: AssessmentCompleteMessage,
    ):
        """assessment_complete cleans up resources."""
        executor, agent = executor_with_context

        await executor._handle_assessment_complete(
            assessment_complete_message,
            "ctx-123",
            mock_updater,
        )

        assert "ctx-123" not in executor.agents
        assert "ctx-123" not in executor.contexts
        assert "ctx-123" not in executor.ues_clients

    @pytest.mark.asyncio
    async def test_handle_assessment_complete_missing_context_is_safe(
        self,
        mock_updater: MagicMock,
        assessment_complete_message: AssessmentCompleteMessage,
    ):
        """assessment_complete handles missing context gracefully."""
        executor = PurpleExecutor(agent_factory=MockAgent)

        # Should not raise
        await executor._handle_assessment_complete(
            assessment_complete_message,
            "nonexistent",
            mock_updater,
        )


class TestPurpleExecutorSendResponse:
    """Tests for executor _send_response method."""

    @pytest.fixture
    def executor(self) -> PurpleExecutor:
        """Create executor."""
        return PurpleExecutor(agent_factory=MockAgent)

    @pytest.fixture
    def mock_updater(self) -> MagicMock:
        """Create mock TaskUpdater."""
        updater = MagicMock()
        updater.update_status = AsyncMock()
        return updater

    @pytest.mark.asyncio
    async def test_send_response_turn_complete(
        self,
        executor: PurpleExecutor,
        mock_updater: MagicMock,
        turn_complete_response: TurnCompleteMessage,
    ):
        """_send_response sends TurnCompleteMessage."""
        await executor._send_response(
            turn_complete_response,
            "ctx-123",
            mock_updater,
        )

        mock_updater.update_status.assert_called_once()
        # Verify the response was serialized
        call_args = mock_updater.update_status.call_args
        message = call_args[0][1]  # Second positional arg
        # The message should contain our JSON
        assert "5" in str(message) or "actions_taken" in str(message)

    @pytest.mark.asyncio
    async def test_send_response_early_completion(
        self,
        executor: PurpleExecutor,
        mock_updater: MagicMock,
        early_completion_response: EarlyCompletionMessage,
    ):
        """_send_response sends EarlyCompletionMessage."""
        await executor._send_response(
            early_completion_response,
            "ctx-123",
            mock_updater,
        )

        mock_updater.update_status.assert_called_once()
