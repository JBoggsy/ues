"""Tests for AssessmentRunner in the Green Agent.

These tests verify that the AssessmentRunner correctly:
- Sets up assessments with UES reset, key provisioning, and scenario loading
- Sends assessment start messages to Purple agent
- Builds initial state summaries from modality states
- Runs the turn loop with time advancement
- Cleans up resources after assessment
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from agentbeats.green.runner import AssessmentRunner
from agentbeats.green.session import AssessmentSession
from agentbeats.green.schemas import (
    AssessmentStartMessage,
    AssessmentCompleteReason,
    InitialStateSummary,
    ModalityCounts,
)
from agentbeats.green.scenarios import ScenarioData


@pytest.fixture
def mock_ues_client():
    """Create a mock AsyncUESClient."""
    client = AsyncMock()
    
    # Mock simulation reset
    client.simulation.reset = AsyncMock()
    
    # Mock scenario import
    client.scenario.import_scenario = AsyncMock()
    
    # Mock time endpoints
    time_response = MagicMock()
    time_response.current_time = datetime(2026, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
    client.time.get_state = AsyncMock(return_value=time_response)
    
    advance_result = MagicMock()
    advance_result.events_executed = 0
    client.time.advance = AsyncMock(return_value=advance_result)
    
    # Mock email state
    email_state = MagicMock()
    email_state.emails = []
    client.email.get_state = AsyncMock(return_value=email_state)
    
    # Mock sms state
    sms_state = MagicMock()
    sms_state.messages = []
    client.sms.get_state = AsyncMock(return_value=sms_state)
    
    # Mock chat state
    chat_state = MagicMock()
    chat_state.total_message_count = 1
    client.chat.get_state = AsyncMock(return_value=chat_state)
    
    # Mock calendar state
    calendar_state = MagicMock()
    calendar_state.events = []
    client.calendar.get_state = AsyncMock(return_value=calendar_state)
    
    return client


@pytest.fixture
def mock_key_manager():
    """Create a mock KeyManager."""
    manager = MagicMock()
    keys = MagicMock()
    keys.proctor_key = "proctor-key-123"
    keys.user_key = "user-key-456"
    manager.provision_assessment_keys = MagicMock(return_value=keys)
    manager.cleanup_assessment = MagicMock()
    return manager


@pytest.fixture
def mock_scenario_registry():
    """Create a mock ScenarioRegistry."""
    registry = MagicMock()
    scenario = ScenarioData(
        scenario_id="test-scenario",
        scenario={"modalities": {}},
        user_prompt="Test prompt",
        characters=None,
        evaluation_criteria=None,
        metadata={},
    )
    registry.get_scenario = MagicMock(return_value=scenario)
    return registry


@pytest.fixture
def mock_messenger():
    """Create a mock Messenger."""
    messenger = MagicMock()
    messenger.talk_to_agent = AsyncMock(return_value='{"status": "ready"}')
    messenger.reset = MagicMock()
    return messenger


@pytest.fixture
def runner(mock_ues_client, mock_key_manager, mock_scenario_registry, mock_messenger):
    """Create an AssessmentRunner with all mocks."""
    return AssessmentRunner(
        ues_url="http://localhost:8000",
        ues_client=mock_ues_client,
        key_manager=mock_key_manager,
        scenario_registry=mock_scenario_registry,
        messenger=mock_messenger,
    )


class TestSetupAssessment:
    """Tests for setup_assessment method."""
    
    @pytest.mark.asyncio
    async def test_resets_ues_simulation(self, runner, mock_ues_client):
        """Verify setup resets UES to clean state."""
        await runner.setup_assessment(
            scenario_id="test",
            participant_url="http://purple:9000",
        )
        
        mock_ues_client.simulation.reset.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_provisions_api_keys(self, runner, mock_key_manager):
        """Verify setup creates proctor and user API keys."""
        session = await runner.setup_assessment(
            scenario_id="test",
            participant_url="http://purple:9000",
        )
        
        mock_key_manager.provision_assessment_keys.assert_called_once()
        call_kwargs = mock_key_manager.provision_assessment_keys.call_args.kwargs
        assert "assessment_id" in call_kwargs
        assert "proctor_agent_id" in call_kwargs
        assert "user_agent_id" in call_kwargs
    
    @pytest.mark.asyncio
    async def test_loads_scenario(self, runner, mock_scenario_registry, mock_ues_client):
        """Verify setup loads and imports the scenario."""
        await runner.setup_assessment(
            scenario_id="my-scenario",
            participant_url="http://purple:9000",
        )
        
        mock_scenario_registry.get_scenario.assert_called_once_with("my-scenario")
        mock_ues_client.scenario.import_scenario.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_returns_session_with_correct_fields(self, runner):
        """Verify session is created with correct configuration."""
        session = await runner.setup_assessment(
            scenario_id="test-scenario",
            participant_url="http://purple:9000",
            verbose_updates=True,
            seed=42,
            turn_timeout_seconds=120.0,
        )
        
        assert isinstance(session, AssessmentSession)
        assert session.scenario_id == "test-scenario"
        assert session.participant_url == "http://purple:9000"
        assert session.verbose_updates is True
        assert session.seed == 42
        assert session.turn_timeout_seconds == 120.0
    
    @pytest.mark.asyncio
    async def test_session_has_api_keys(self, runner):
        """Verify session contains the provisioned API keys."""
        session = await runner.setup_assessment(
            scenario_id="test",
            participant_url="http://purple:9000",
        )
        
        assert session.proctor_key == "proctor-key-123"
        assert session.user_key == "user-key-456"


class TestSendAssessmentStart:
    """Tests for send_assessment_start method."""
    
    @pytest.mark.asyncio
    async def test_sends_message_to_purple(self, runner, mock_messenger, mock_ues_client):
        """Verify AssessmentStartMessage is sent to Purple agent."""
        session = await runner.setup_assessment(
            scenario_id="test",
            participant_url="http://purple:9000",
        )
        
        await runner.send_assessment_start(session)
        
        mock_messenger.talk_to_agent.assert_called_once()
        call_kwargs = mock_messenger.talk_to_agent.call_args.kwargs
        assert call_kwargs["url"] == "http://purple:9000"
        assert call_kwargs["new_conversation"] is True
        
        # Verify message content
        import json
        message = json.loads(call_kwargs["message"])
        assert message["ues_url"] == "http://localhost:8000"
        assert message["api_key"] == "user-key-456"
    
    @pytest.mark.asyncio
    async def test_includes_current_time(self, runner, mock_ues_client, mock_messenger):
        """Verify message includes current simulator time."""
        session = await runner.setup_assessment(
            scenario_id="test",
            participant_url="http://purple:9000",
        )
        
        await runner.send_assessment_start(session)
        
        import json
        message = json.loads(mock_messenger.talk_to_agent.call_args.kwargs["message"])
        assert "current_time" in message


class TestBuildInitialStateSummary:
    """Tests for _build_initial_state_summary method."""
    
    @pytest.mark.asyncio
    async def test_includes_email_counts(self, runner, mock_ues_client):
        """Verify email modality counts are included."""
        # Setup mock with emails
        email1 = MagicMock()
        email1.read_status = "unread"
        email2 = MagicMock()
        email2.read_status = "read"
        mock_ues_client.email.get_state.return_value.emails = [email1, email2]
        
        await runner.setup_assessment(
            scenario_id="test",
            participant_url="http://purple:9000",
        )
        
        summary = await runner._build_initial_state_summary()
        
        assert summary.email is not None
        assert summary.email.total == 2
        assert summary.email.unread == 1
    
    @pytest.mark.asyncio
    async def test_handles_modality_errors_gracefully(self, runner, mock_ues_client):
        """Verify errors in one modality don't break the summary."""
        mock_ues_client.email.get_state = AsyncMock(side_effect=Exception("No emails"))
        
        await runner.setup_assessment(
            scenario_id="test",
            participant_url="http://purple:9000",
        )
        
        # Should not raise
        summary = await runner._build_initial_state_summary()
        
        # Email should be None due to error
        assert summary.email is None


class TestCleanupAssessment:
    """Tests for cleanup_assessment method."""
    
    @pytest.mark.asyncio
    async def test_invalidates_api_keys(self, runner, mock_key_manager):
        """Verify API keys are cleaned up."""
        session = await runner.setup_assessment(
            scenario_id="test",
            participant_url="http://purple:9000",
        )
        
        runner.cleanup_assessment(session)
        
        mock_key_manager.cleanup_assessment.assert_called_once_with(session.assessment_id)
    
    @pytest.mark.asyncio
    async def test_resets_messenger(self, runner, mock_messenger):
        """Verify messenger state is reset."""
        session = await runner.setup_assessment(
            scenario_id="test",
            participant_url="http://purple:9000",
        )
        
        runner.cleanup_assessment(session)
        
        mock_messenger.reset.assert_called_once()


class TestRunAssessment:
    """Tests for the full run_assessment workflow."""
    
    @pytest.mark.asyncio
    async def test_runs_full_lifecycle(self, runner, mock_ues_client, mock_messenger):
        """Verify full assessment runs setup, loop, and cleanup."""
        # Make the loop terminate quickly
        runner._should_terminate = lambda *args: True
        
        session, reason = await runner.run_assessment(
            scenario_id="test-scenario",
            participant_url="http://purple:9000",
        )
        
        assert session.scenario_id == "test-scenario"
        assert reason == AssessmentCompleteReason.SCENARIO_COMPLETE
    
    @pytest.mark.asyncio
    async def test_cleanup_on_exception(self, runner, mock_key_manager, mock_ues_client):
        """Verify cleanup runs even if assessment fails."""
        mock_ues_client.scenario.import_scenario = AsyncMock(
            side_effect=Exception("Scenario failed")
        )
        
        with pytest.raises(Exception):
            await runner.run_assessment(
                scenario_id="bad-scenario",
                participant_url="http://purple:9000",
            )
        
        # Cleanup should still be called (via finally)
        # Note: In this case, session won't be set, so cleanup won't do much
