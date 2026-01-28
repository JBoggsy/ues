"""Tests for the agent_testing.hooks module."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from ues.agent_testing.hooks import EventHookManager, RegisteredHook
from ues.agent_testing.results import EvalResult
from ues.agent_testing.schema import CriterionSchema, EvalTiming
from ues.agent_testing.context import EvalContext


@pytest.fixture
def sample_on_event_criterion():
    """Create a sample on_event criterion."""
    return CriterionSchema(
        id="email_quality",
        name="Email Quality",
        evaluator="check_email_quality",
        max_points=10.0,
        eval_timing=EvalTiming.ON_EVENT,
        event_filter="filter_emails",
        params={"min_length": 50},
    )


@pytest.fixture
def sample_post_scenario_criterion():
    """Create a sample post_scenario criterion."""
    return CriterionSchema(
        id="task_completion",
        name="Task Completion",
        evaluator="check_tasks",
        max_points=20.0,
        eval_timing=EvalTiming.POST_SCENARIO,
    )


@pytest.fixture
def mock_context():
    """Create a mock test context."""
    ctx = MagicMock(spec=EvalContext)
    ctx.with_trigger_event = MagicMock(return_value=ctx)
    ctx.event_history = []
    return ctx


class TestRegisteredHook:
    """Tests for the RegisteredHook class."""

    def test_matches_event_no_filter(self, sample_on_event_criterion):
        """Test that events match when no filter is set."""

        def evaluator(ctx, params):
            return EvalResult(score=1, max_score=1, explanation="Test")

        hook = RegisteredHook(
            criterion=sample_on_event_criterion,
            evaluator=evaluator,
            event_filter=None,  # No filter
        )

        # Any event should match
        assert hook.matches_event({"modality": "email"})
        assert hook.matches_event({"modality": "sms"})
        assert hook.matches_event({})

    def test_matches_event_with_filter(self, sample_on_event_criterion):
        """Test that filter controls matching."""

        def evaluator(ctx, params):
            return EvalResult(score=1, max_score=1, explanation="Test")

        def filter_emails(event):
            return event.get("modality") == "email"

        hook = RegisteredHook(
            criterion=sample_on_event_criterion,
            evaluator=evaluator,
            event_filter=filter_emails,
        )

        assert hook.matches_event({"modality": "email"})
        assert not hook.matches_event({"modality": "sms"})
        assert not hook.matches_event({})


class TestEventHookManager:
    """Tests for the EventHookManager class."""

    def test_register_hook(self, sample_on_event_criterion):
        """Test registering a hook."""
        manager = EventHookManager()

        def evaluator(ctx, params):
            return EvalResult(score=1, max_score=1, explanation="Test")

        manager.register_hook(
            criterion=sample_on_event_criterion,
            evaluator=evaluator,
        )

        assert manager.hook_count == 1
        assert "email_quality" in manager.registered_criterion_ids

    def test_register_hook_rejects_post_scenario(self, sample_post_scenario_criterion):
        """Test that post_scenario criteria are rejected."""
        manager = EventHookManager()

        def evaluator(ctx, params):
            return EvalResult(score=1, max_score=1, explanation="Test")

        with pytest.raises(ValueError) as exc_info:
            manager.register_hook(
                criterion=sample_post_scenario_criterion,
                evaluator=evaluator,
            )

        assert "on_event" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_dispatch_event_calls_matching_evaluator(
        self, sample_on_event_criterion, mock_context
    ):
        """Test that dispatch calls evaluator for matching events."""
        manager = EventHookManager()

        call_count = 0

        def evaluator(ctx, params):
            nonlocal call_count
            call_count += 1
            return EvalResult(score=1, max_score=1, explanation="Called")

        def filter_emails(event):
            return event.get("modality") == "email"

        manager.register_hook(
            criterion=sample_on_event_criterion,
            evaluator=evaluator,
            event_filter=filter_emails,
        )

        # Dispatch matching event
        results = await manager.dispatch_event({"modality": "email"}, mock_context)

        assert call_count == 1
        assert len(results) == 1
        assert results[0][0] == "email_quality"
        assert results[0][1].score == 1

    @pytest.mark.asyncio
    async def test_dispatch_event_skips_non_matching(
        self, sample_on_event_criterion, mock_context
    ):
        """Test that dispatch skips non-matching events."""
        manager = EventHookManager()

        call_count = 0

        def evaluator(ctx, params):
            nonlocal call_count
            call_count += 1
            return EvalResult(score=1, max_score=1, explanation="Called")

        def filter_emails(event):
            return event.get("modality") == "email"

        manager.register_hook(
            criterion=sample_on_event_criterion,
            evaluator=evaluator,
            event_filter=filter_emails,
        )

        # Dispatch non-matching event
        results = await manager.dispatch_event({"modality": "sms"}, mock_context)

        assert call_count == 0
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_dispatch_event_async_evaluator(
        self, sample_on_event_criterion, mock_context
    ):
        """Test that async evaluators are handled correctly."""
        manager = EventHookManager()

        async def async_evaluator(ctx, params):
            return EvalResult(score=2, max_score=3, explanation="Async")

        manager.register_hook(
            criterion=sample_on_event_criterion,
            evaluator=async_evaluator,
        )

        results = await manager.dispatch_event({"modality": "email"}, mock_context)

        assert len(results) == 1
        assert results[0][1].score == 2

    @pytest.mark.asyncio
    async def test_dispatch_event_handles_evaluator_error(
        self, sample_on_event_criterion, mock_context
    ):
        """Test that evaluator errors are handled gracefully."""
        manager = EventHookManager()

        def failing_evaluator(ctx, params):
            raise ValueError("Evaluator failed!")

        manager.register_hook(
            criterion=sample_on_event_criterion,
            evaluator=failing_evaluator,
        )

        results = await manager.dispatch_event({"modality": "email"}, mock_context)

        # Should still return a result, but with error info
        assert len(results) == 1
        assert results[0][1].score == 0
        assert "error" in results[0][1].explanation.lower()

    def test_get_accumulated_results(self, sample_on_event_criterion):
        """Test getting accumulated results."""
        manager = EventHookManager()

        def evaluator(ctx, params):
            return EvalResult(score=1, max_score=1, explanation="Test")

        manager.register_hook(
            criterion=sample_on_event_criterion,
            evaluator=evaluator,
        )

        # Manually add some results to simulate dispatches
        hook = manager.get_hook_for_criterion("email_quality")
        hook.results.append(EvalResult(score=1, max_score=1, explanation="R1"))
        hook.results.append(EvalResult(score=0.5, max_score=1, explanation="R2"))

        accumulated = manager.get_accumulated_results()

        assert "email_quality" in accumulated
        assert len(accumulated["email_quality"]) == 2

    def test_clear_results(self, sample_on_event_criterion):
        """Test clearing accumulated results."""
        manager = EventHookManager()

        def evaluator(ctx, params):
            return EvalResult(score=1, max_score=1, explanation="Test")

        manager.register_hook(
            criterion=sample_on_event_criterion,
            evaluator=evaluator,
        )

        # Add some results
        hook = manager.get_hook_for_criterion("email_quality")
        hook.results.append(EvalResult(score=1, max_score=1, explanation="R1"))

        # Clear
        manager.clear_results()

        # Should be empty
        accumulated = manager.get_accumulated_results()
        assert len(accumulated["email_quality"]) == 0

    def test_get_hook_for_criterion_not_found(self):
        """Test getting hook for non-existent criterion."""
        manager = EventHookManager()

        hook = manager.get_hook_for_criterion("nonexistent")

        assert hook is None

    @pytest.mark.asyncio
    async def test_multiple_hooks(self, mock_context):
        """Test multiple hooks can be registered and dispatched."""
        manager = EventHookManager()

        criterion1 = CriterionSchema(
            id="hook_1",
            name="Hook 1",
            evaluator="check_1",
            max_points=5.0,
            eval_timing=EvalTiming.ON_EVENT,
        )

        criterion2 = CriterionSchema(
            id="hook_2",
            name="Hook 2",
            evaluator="check_2",
            max_points=5.0,
            eval_timing=EvalTiming.ON_EVENT,
        )

        def evaluator1(ctx, params):
            return EvalResult(score=1, max_score=1, explanation="Hook 1")

        def evaluator2(ctx, params):
            return EvalResult(score=2, max_score=2, explanation="Hook 2")

        manager.register_hook(criterion=criterion1, evaluator=evaluator1)
        manager.register_hook(criterion=criterion2, evaluator=evaluator2)

        results = await manager.dispatch_event({"modality": "any"}, mock_context)

        assert len(results) == 2
        assert manager.hook_count == 2
