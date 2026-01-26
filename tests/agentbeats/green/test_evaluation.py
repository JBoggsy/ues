"""Tests for the evaluation module.

This module tests:
- CriterionDefinition model parsing
- EvaluationContext state access and filtering
- Built-in evaluators (check_email_sent, check_sms_sent, etc.)
- Evaluator class orchestration
- Custom evaluator loading
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentbeats.green.evaluation import (
    BUILTIN_EVALUATORS,
    CriterionDefinition,
    EvaluationContext,
    Evaluator,
    check_action_count,
    check_calendar_event_created,
    check_email_sent,
    check_no_actions,
    check_sms_sent,
    check_state_contains,
    parse_criteria_from_json,
)
from agentbeats.green.schemas import EvaluationDimension
from agentbeats.green.session import ActionLogEntry, AssessmentSession


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_session() -> AssessmentSession:
    """Create a mock assessment session with sample action log."""
    session = AssessmentSession(
        assessment_id="test-assessment-001",
        scenario_id="test-scenario",
        participant_url="http://localhost:9000",
        proctor_key="proctor-key",
        user_key="user-key",
        purple_agent_id="purple-agent-001",
        current_turn=3,
    )
    
    # Add sample actions
    session.action_log = [
        ActionLogEntry(
            turn=1,
            event_id="evt-001",
            modality="email",
            action_type="send",
            timestamp=datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
            summary="Sent email to bob@example.com",
            details={
                "to": "bob@example.com",
                "subject": "Meeting Tomorrow",
                "body": "Let's discuss the project.",
            },
        ),
        ActionLogEntry(
            turn=1,
            event_id="evt-002",
            modality="sms",
            action_type="send",
            timestamp=datetime(2024, 6, 15, 10, 5, 0, tzinfo=timezone.utc),
            summary="Sent SMS to +15551234567",
            details={
                "to": "+15551234567",
                "body": "Running late to the meeting",
            },
        ),
        ActionLogEntry(
            turn=2,
            event_id="evt-003",
            modality="calendar",
            action_type="create",
            timestamp=datetime(2024, 6, 15, 11, 0, 0, tzinfo=timezone.utc),
            summary="Created calendar event",
            details={
                "title": "Team Meeting",
                "start_time": "2024-06-16T14:00:00+00:00",
                "end_time": "2024-06-16T15:00:00+00:00",
            },
        ),
        ActionLogEntry(
            turn=3,
            event_id="evt-004",
            modality="email",
            action_type="send",
            timestamp=datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
            summary="Sent email to alice@example.com",
            details={
                "to": "alice@example.com",
                "subject": "Follow-up",
                "body": "Just following up on our conversation.",
            },
        ),
    ]
    
    return session


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create a mock AsyncUESClient."""
    client = AsyncMock()
    
    # Mock email state
    email_mock = MagicMock()
    email_mock.get_state = AsyncMock(return_value=MagicMock(
        model_dump=lambda: {"threads": {}, "inbox_count": 5}
    ))
    client.email = email_mock
    
    # Mock calendar state
    calendar_mock = MagicMock()
    calendar_mock.get_state = AsyncMock(return_value=MagicMock(
        model_dump=lambda: {"events": []}
    ))
    client.calendar = calendar_mock
    
    return client


@pytest.fixture
def eval_context(mock_client: AsyncMock, mock_session: AssessmentSession) -> EvaluationContext:
    """Create an EvaluationContext with mock dependencies."""
    return EvaluationContext(client=mock_client, session=mock_session)


# =============================================================================
# CriterionDefinition Tests
# =============================================================================


class TestCriterionDefinition:
    """Tests for the CriterionDefinition model."""

    def test_parse_minimal_criterion(self):
        """Test parsing a criterion with only required fields."""
        data = {
            "id": "test_criterion",
            "name": "Test Criterion",
            "evaluator": "check_email_sent",
        }
        criterion = CriterionDefinition.model_validate(data)
        
        assert criterion.id == "test_criterion"
        assert criterion.name == "Test Criterion"
        assert criterion.evaluator == "check_email_sent"
        assert criterion.max_points == 10  # default
        assert criterion.dimension == EvaluationDimension.ACCURACY  # default
        assert criterion.eval_timing == "post_scenario"  # default
        assert criterion.params == {}  # default

    def test_parse_full_criterion(self):
        """Test parsing a criterion with all fields."""
        data = {
            "id": "efficiency_check",
            "name": "Efficiency Check",
            "description": "Verify efficient execution",
            "evaluator": "check_action_count",
            "max_points": 15,
            "dimension": "efficiency",
            "eval_timing": "post_scenario",
            "params": {"max": 10},
        }
        criterion = CriterionDefinition.model_validate(data)
        
        assert criterion.id == "efficiency_check"
        assert criterion.name == "Efficiency Check"
        assert criterion.description == "Verify efficient execution"
        assert criterion.max_points == 15
        assert criterion.dimension == EvaluationDimension.EFFICIENCY
        assert criterion.params == {"max": 10}

    def test_parse_criteria_from_json(self):
        """Test the convenience function for parsing criteria lists."""
        criteria_data = [
            {"id": "c1", "name": "Criterion 1", "evaluator": "check_email_sent"},
            {"id": "c2", "name": "Criterion 2", "evaluator": "check_sms_sent"},
        ]
        
        criteria = parse_criteria_from_json(criteria_data)
        
        assert len(criteria) == 2
        assert criteria[0].id == "c1"
        assert criteria[1].id == "c2"


# =============================================================================
# EvaluationContext Tests
# =============================================================================


class TestEvaluationContext:
    """Tests for the EvaluationContext class."""

    def test_get_action_log(self, eval_context: EvaluationContext, mock_session: AssessmentSession):
        """Test retrieving the full action log."""
        log = eval_context.get_action_log()
        
        assert len(log) == 4
        assert log == mock_session.action_log

    def test_get_actions_by_modality(self, eval_context: EvaluationContext):
        """Test filtering actions by modality."""
        email_actions = eval_context.get_actions_by_modality("email")
        sms_actions = eval_context.get_actions_by_modality("sms")
        calendar_actions = eval_context.get_actions_by_modality("calendar")
        
        assert len(email_actions) == 2
        assert len(sms_actions) == 1
        assert len(calendar_actions) == 1
        assert all(a.modality == "email" for a in email_actions)

    def test_get_actions_by_type(self, eval_context: EvaluationContext):
        """Test filtering actions by type."""
        send_actions = eval_context.get_actions_by_type("send")
        create_actions = eval_context.get_actions_by_type("create")
        
        assert len(send_actions) == 3
        assert len(create_actions) == 1

    def test_get_actions_in_turn(self, eval_context: EvaluationContext):
        """Test filtering actions by turn number."""
        turn1_actions = eval_context.get_actions_in_turn(1)
        turn2_actions = eval_context.get_actions_in_turn(2)
        turn3_actions = eval_context.get_actions_in_turn(3)
        
        assert len(turn1_actions) == 2
        assert len(turn2_actions) == 1
        assert len(turn3_actions) == 1

    @pytest.mark.asyncio
    async def test_get_modality_state_caches(self, eval_context: EvaluationContext, mock_client: AsyncMock):
        """Test that modality state is cached after first call."""
        # First call - should hit the client
        state1 = await eval_context.get_modality_state("email")
        # Second call - should use cache
        state2 = await eval_context.get_modality_state("email")
        
        assert state1 == state2
        # Only one call to get_state
        mock_client.email.get_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_modality_state_unknown_modality(self, eval_context: EvaluationContext):
        """Test getting state for an unknown modality returns empty dict."""
        state = await eval_context.get_modality_state("unknown_modality")
        
        assert state == {}


# =============================================================================
# Built-in Evaluator Tests
# =============================================================================


class TestCheckEmailSent:
    """Tests for the check_email_sent evaluator."""

    @pytest.mark.asyncio
    async def test_email_found(self, eval_context: EvaluationContext):
        """Test when email to recipient is found."""
        params = {"to": "bob@example.com", "max_points": 10}
        
        score, explanation = await check_email_sent(eval_context, params)
        
        assert score == 10
        assert "successfully" in explanation

    @pytest.mark.asyncio
    async def test_email_not_found(self, eval_context: EvaluationContext):
        """Test when email to recipient is not found."""
        params = {"to": "nobody@example.com", "max_points": 10}
        
        score, explanation = await check_email_sent(eval_context, params)
        
        assert score == 0
        assert "No email found" in explanation

    @pytest.mark.asyncio
    async def test_email_with_subject_filter_match(self, eval_context: EvaluationContext):
        """Test email found when subject filter matches."""
        params = {
            "to": "bob@example.com",
            "subject_contains": "meeting",
            "max_points": 10,
        }
        
        score, explanation = await check_email_sent(eval_context, params)
        
        assert score == 10

    @pytest.mark.asyncio
    async def test_email_with_subject_filter_no_match(self, eval_context: EvaluationContext):
        """Test email not found when subject filter doesn't match."""
        params = {
            "to": "bob@example.com",
            "subject_contains": "urgent",
            "max_points": 10,
        }
        
        score, explanation = await check_email_sent(eval_context, params)
        
        assert score == 0

    @pytest.mark.asyncio
    async def test_email_missing_to_param(self, eval_context: EvaluationContext):
        """Test error when 'to' parameter is missing."""
        params = {"max_points": 10}
        
        score, explanation = await check_email_sent(eval_context, params)
        
        assert score == 0
        assert "Missing" in explanation

    @pytest.mark.asyncio
    async def test_email_case_insensitive(self, eval_context: EvaluationContext):
        """Test that email matching is case-insensitive."""
        params = {"to": "BOB@EXAMPLE.COM", "max_points": 10}
        
        score, explanation = await check_email_sent(eval_context, params)
        
        assert score == 10


class TestCheckSmsSent:
    """Tests for the check_sms_sent evaluator."""

    @pytest.mark.asyncio
    async def test_sms_found(self, eval_context: EvaluationContext):
        """Test when SMS to recipient is found."""
        params = {"to": "+15551234567", "max_points": 5}
        
        score, explanation = await check_sms_sent(eval_context, params)
        
        assert score == 5
        assert "successfully" in explanation

    @pytest.mark.asyncio
    async def test_sms_not_found(self, eval_context: EvaluationContext):
        """Test when SMS to recipient is not found."""
        params = {"to": "+15559999999", "max_points": 5}
        
        score, explanation = await check_sms_sent(eval_context, params)
        
        assert score == 0
        assert "No SMS found" in explanation

    @pytest.mark.asyncio
    async def test_sms_with_body_filter(self, eval_context: EvaluationContext):
        """Test SMS found with body filter."""
        params = {
            "to": "+15551234567",
            "body_contains": "late",
            "max_points": 5,
        }
        
        score, explanation = await check_sms_sent(eval_context, params)
        
        assert score == 5

    @pytest.mark.asyncio
    async def test_sms_phone_normalization(self, eval_context: EvaluationContext):
        """Test that phone numbers are normalized for comparison."""
        # Different formatting, same number
        params = {"to": "+1-555-123-4567", "max_points": 5}
        
        score, explanation = await check_sms_sent(eval_context, params)
        
        assert score == 5


class TestCheckCalendarEventCreated:
    """Tests for the check_calendar_event_created evaluator."""

    @pytest.mark.asyncio
    async def test_event_found(self, eval_context: EvaluationContext):
        """Test when calendar event is found."""
        params = {"max_points": 15}
        
        score, explanation = await check_calendar_event_created(eval_context, params)
        
        assert score == 15
        assert "created" in explanation

    @pytest.mark.asyncio
    async def test_event_with_title_filter_match(self, eval_context: EvaluationContext):
        """Test event found when title filter matches."""
        params = {"title_contains": "team", "max_points": 15}
        
        score, explanation = await check_calendar_event_created(eval_context, params)
        
        assert score == 15

    @pytest.mark.asyncio
    async def test_event_with_title_filter_no_match(self, eval_context: EvaluationContext):
        """Test event not found when title filter doesn't match."""
        params = {"title_contains": "lunch", "max_points": 15}
        
        score, explanation = await check_calendar_event_created(eval_context, params)
        
        assert score == 0

    @pytest.mark.asyncio
    async def test_event_with_date_filter(self, eval_context: EvaluationContext):
        """Test event found when date filter matches."""
        params = {"date": "2024-06-16", "max_points": 15}
        
        score, explanation = await check_calendar_event_created(eval_context, params)
        
        assert score == 15

    @pytest.mark.asyncio
    async def test_event_with_hour_filter(self, eval_context: EvaluationContext):
        """Test event found when hour filter matches."""
        params = {"hour": 14, "max_points": 15}
        
        score, explanation = await check_calendar_event_created(eval_context, params)
        
        assert score == 15

    @pytest.mark.asyncio
    async def test_event_no_create_actions(self, mock_client: AsyncMock):
        """Test when there are no calendar create actions."""
        session = AssessmentSession(
            assessment_id="test",
            scenario_id="test",
            participant_url="http://localhost",
            proctor_key="key",
            user_key="key",
            purple_agent_id="agent",
        )
        context = EvaluationContext(client=mock_client, session=session)
        params = {"max_points": 15}
        
        score, explanation = await check_calendar_event_created(context, params)
        
        assert score == 0
        assert "No matching" in explanation


class TestCheckActionCount:
    """Tests for the check_action_count evaluator."""

    @pytest.mark.asyncio
    async def test_count_within_bounds(self, eval_context: EvaluationContext):
        """Test when action count is within bounds."""
        params = {"min": 1, "max": 10, "max_points": 10}
        
        score, explanation = await check_action_count(eval_context, params)
        
        assert score == 10
        assert "within acceptable bounds" in explanation

    @pytest.mark.asyncio
    async def test_count_too_few(self, eval_context: EvaluationContext):
        """Test when action count is below minimum."""
        params = {"min": 10, "max_points": 10}
        
        score, explanation = await check_action_count(eval_context, params)
        
        assert score == 0
        assert "Too few" in explanation

    @pytest.mark.asyncio
    async def test_count_too_many(self, eval_context: EvaluationContext):
        """Test when action count exceeds maximum."""
        params = {"max": 2, "max_points": 10}
        
        score, explanation = await check_action_count(eval_context, params)
        
        assert score == 0
        assert "Too many" in explanation

    @pytest.mark.asyncio
    async def test_count_filtered_by_modality(self, eval_context: EvaluationContext):
        """Test counting actions for a specific modality."""
        params = {"modality": "email", "min": 2, "max": 2, "max_points": 10}
        
        score, explanation = await check_action_count(eval_context, params)
        
        assert score == 10  # 2 email actions


class TestCheckNoActions:
    """Tests for the check_no_actions evaluator."""

    @pytest.mark.asyncio
    async def test_no_actions_fail(self, eval_context: EvaluationContext):
        """Test when actions were taken (should fail)."""
        params = {"max_points": 10}
        
        score, explanation = await check_no_actions(eval_context, params)
        
        assert score == 0
        assert "Unexpected" in explanation

    @pytest.mark.asyncio
    async def test_no_actions_pass(self, mock_client: AsyncMock):
        """Test when no actions were taken (should pass)."""
        session = AssessmentSession(
            assessment_id="test",
            scenario_id="test",
            participant_url="http://localhost",
            proctor_key="key",
            user_key="key",
            purple_agent_id="agent",
        )
        context = EvaluationContext(client=mock_client, session=session)
        params = {"max_points": 10}
        
        score, explanation = await check_no_actions(context, params)
        
        assert score == 10
        assert "No" in explanation and "as expected" in explanation

    @pytest.mark.asyncio
    async def test_no_actions_modality_filter(self, eval_context: EvaluationContext):
        """Test checking no actions for a specific modality."""
        # There are no "contacts" actions
        params = {"modality": "contacts", "max_points": 10}
        
        score, explanation = await check_no_actions(eval_context, params)
        
        assert score == 10


class TestCheckStateContains:
    """Tests for the check_state_contains evaluator."""

    @pytest.mark.asyncio
    async def test_path_exists(self, eval_context: EvaluationContext):
        """Test checking that a path exists in state."""
        params = {
            "modality": "email",
            "path": "inbox_count",
            "exists": True,
            "max_points": 5,
        }
        
        score, explanation = await check_state_contains(eval_context, params)
        
        assert score == 5
        assert "exists" in explanation

    @pytest.mark.asyncio
    async def test_value_matches(self, eval_context: EvaluationContext):
        """Test checking that a value matches expected."""
        params = {
            "modality": "email",
            "path": "inbox_count",
            "expected": 5,
            "max_points": 5,
        }
        
        score, explanation = await check_state_contains(eval_context, params)
        
        assert score == 5
        assert "matches" in explanation

    @pytest.mark.asyncio
    async def test_value_mismatch(self, eval_context: EvaluationContext):
        """Test when value doesn't match expected."""
        params = {
            "modality": "email",
            "path": "inbox_count",
            "expected": 10,
            "max_points": 5,
        }
        
        score, explanation = await check_state_contains(eval_context, params)
        
        assert score == 0
        assert "expected 10" in explanation

    @pytest.mark.asyncio
    async def test_path_not_found(self, eval_context: EvaluationContext):
        """Test when path doesn't exist in state."""
        params = {
            "modality": "email",
            "path": "nonexistent.path",
            "exists": True,
            "max_points": 5,
        }
        
        score, explanation = await check_state_contains(eval_context, params)
        
        assert score == 0
        assert "not found" in explanation

    @pytest.mark.asyncio
    async def test_missing_required_params(self, eval_context: EvaluationContext):
        """Test error when required params are missing."""
        # Missing modality
        params = {"path": "test", "max_points": 5}
        score, explanation = await check_state_contains(eval_context, params)
        assert score == 0
        assert "Missing" in explanation

        # Missing path
        params = {"modality": "email", "max_points": 5}
        score, explanation = await check_state_contains(eval_context, params)
        assert score == 0
        assert "Missing" in explanation


# =============================================================================
# Evaluator Class Tests
# =============================================================================


class TestEvaluator:
    """Tests for the Evaluator class."""

    @pytest.mark.asyncio
    async def test_evaluate_single_criterion(
        self, mock_client: AsyncMock, mock_session: AssessmentSession
    ):
        """Test evaluating a single criterion."""
        criteria = [
            CriterionDefinition(
                id="test1",
                name="Test Criterion",
                evaluator="check_email_sent",
                max_points=10,
                params={"to": "bob@example.com"},
            )
        ]
        evaluator = Evaluator(mock_client, criteria)
        
        results = await evaluator.evaluate(mock_session)
        
        assert len(results) == 1
        assert results[0].id == "test1"
        assert results[0].score == 10
        assert results[0].max_score == 10

    @pytest.mark.asyncio
    async def test_evaluate_multiple_criteria(
        self, mock_client: AsyncMock, mock_session: AssessmentSession
    ):
        """Test evaluating multiple criteria."""
        criteria = [
            CriterionDefinition(
                id="email_check",
                name="Email Check",
                evaluator="check_email_sent",
                max_points=10,
                params={"to": "bob@example.com"},
            ),
            CriterionDefinition(
                id="sms_check",
                name="SMS Check",
                evaluator="check_sms_sent",
                max_points=5,
                params={"to": "+15551234567"},
            ),
            CriterionDefinition(
                id="action_count",
                name="Action Count",
                evaluator="check_action_count",
                max_points=10,
                dimension=EvaluationDimension.EFFICIENCY,
                params={"max": 10},
            ),
        ]
        evaluator = Evaluator(mock_client, criteria)
        
        results = await evaluator.evaluate(mock_session)
        
        assert len(results) == 3
        assert results[0].score == 10
        assert results[1].score == 5
        assert results[2].score == 10

    @pytest.mark.asyncio
    async def test_evaluate_unknown_evaluator(
        self, mock_client: AsyncMock, mock_session: AssessmentSession
    ):
        """Test handling of unknown evaluator name."""
        criteria = [
            CriterionDefinition(
                id="test",
                name="Test",
                evaluator="nonexistent_evaluator",
                max_points=10,
            )
        ]
        evaluator = Evaluator(mock_client, criteria)
        
        results = await evaluator.evaluate(mock_session)
        
        assert len(results) == 1
        assert results[0].score == 0
        assert "not found" in results[0].explanation

    @pytest.mark.asyncio
    async def test_evaluate_handles_evaluator_exception(
        self, mock_client: AsyncMock, mock_session: AssessmentSession
    ):
        """Test that evaluator exceptions are handled gracefully."""
        # Create a criterion with params that will cause an error
        # We'll mock the evaluator to raise an exception
        criteria = [
            CriterionDefinition(
                id="test",
                name="Test",
                evaluator="check_email_sent",
                max_points=10,
            )
        ]
        evaluator = Evaluator(mock_client, criteria)
        
        # Patch check_email_sent to raise an exception
        with patch.dict(BUILTIN_EVALUATORS, {"check_email_sent": AsyncMock(side_effect=RuntimeError("Test error"))}):
            results = await evaluator.evaluate(mock_session)
        
        assert len(results) == 1
        assert results[0].score == 0
        assert "error" in results[0].explanation.lower()

    @pytest.mark.asyncio
    async def test_evaluate_clamps_score(
        self, mock_client: AsyncMock, mock_session: AssessmentSession
    ):
        """Test that scores are clamped to valid range."""
        # Create a mock evaluator that returns an out-of-range score
        async def bad_evaluator(context, params):
            return (100, "Too high!")  # Returns 100 but max is 10
        
        criteria = [
            CriterionDefinition(
                id="test",
                name="Test",
                evaluator="bad_evaluator",
                max_points=10,
            )
        ]
        evaluator = Evaluator(mock_client, criteria)
        
        with patch.dict(BUILTIN_EVALUATORS, {"bad_evaluator": bad_evaluator}):
            results = await evaluator.evaluate(mock_session)
        
        assert results[0].score == 10  # Clamped to max_points

    @pytest.mark.asyncio
    async def test_custom_module_loading(
        self, mock_client: AsyncMock, mock_session: AssessmentSession
    ):
        """Test loading custom evaluators from a module."""
        criteria = [
            CriterionDefinition(
                id="custom_test",
                name="Custom Test",
                evaluator="custom_evaluator",
                max_points=15,
            )
        ]
        evaluator = Evaluator(mock_client, criteria, custom_module="test_module")
        
        # Mock the custom evaluator loading
        async def custom_evaluator(context, params):
            return (15, "Custom evaluator ran!")
        
        with patch("agentbeats.green.evaluation._load_custom_evaluator", return_value=custom_evaluator):
            results = await evaluator.evaluate(mock_session)
        
        assert results[0].score == 15
        assert "Custom evaluator ran!" in results[0].explanation

    def test_builtin_evaluators_registry(self):
        """Test that all expected evaluators are in the registry."""
        expected_evaluators = [
            "check_email_sent",
            "check_sms_sent",
            "check_calendar_event_created",
            "check_action_count",
            "check_no_actions",
            "check_state_contains",
        ]
        
        for name in expected_evaluators:
            assert name in BUILTIN_EVALUATORS
            assert callable(BUILTIN_EVALUATORS[name])


# =============================================================================
# Integration Tests
# =============================================================================


class TestEvaluatorIntegration:
    """Integration tests for the complete evaluation flow."""

    @pytest.mark.asyncio
    async def test_full_evaluation_flow(
        self, mock_client: AsyncMock, mock_session: AssessmentSession
    ):
        """Test complete evaluation flow from criteria to scores."""
        from agentbeats.green.schemas import Scores
        
        # Define multiple criteria across dimensions
        criteria_data = [
            {
                "id": "email_bob",
                "name": "Email to Bob",
                "evaluator": "check_email_sent",
                "max_points": 10,
                "dimension": "accuracy",
                "params": {"to": "bob@example.com"},
            },
            {
                "id": "email_alice",
                "name": "Email to Alice",
                "evaluator": "check_email_sent",
                "max_points": 10,
                "dimension": "accuracy",
                "params": {"to": "alice@example.com"},
            },
            {
                "id": "efficiency",
                "name": "Efficient Actions",
                "evaluator": "check_action_count",
                "max_points": 10,
                "dimension": "efficiency",
                "params": {"max": 10},
            },
            {
                "id": "no_dangerous_sms",
                "name": "No Unauthorized SMS",
                "evaluator": "check_no_actions",
                "max_points": 5,
                "dimension": "safety",
                "params": {"modality": "weather"},  # No weather actions
            },
        ]
        
        criteria = parse_criteria_from_json(criteria_data)
        evaluator = Evaluator(mock_client, criteria)
        
        # Run evaluation
        results = await evaluator.evaluate(mock_session)
        
        # Aggregate scores
        scores = Scores.from_criteria(results)
        
        # Verify results
        assert len(results) == 4
        assert scores.overall.score == 35  # 10 + 10 + 10 + 5
        assert scores.overall.max_score == 35
        assert scores.dimensions[EvaluationDimension.ACCURACY].score == 20
        assert scores.dimensions[EvaluationDimension.EFFICIENCY].score == 10
        assert scores.dimensions[EvaluationDimension.SAFETY].score == 5
