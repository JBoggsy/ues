"""Integration tests for the agent_testing.runner module.

These tests use the actual UES API via ASGITransport for realistic testing.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

from httpx import ASGITransport

from ues.agent_testing import (
    EvalRunner,
    EvalContext,
    EvalResult,
    CriteriaSchema,
    CriterionSchema,
    EvalTiming,
)
from ues.client import AsyncUESClient
from ues.main import app


@pytest.fixture
def async_client():
    """Create an async UES client for testing."""
    transport = ASGITransport(app=app)
    return AsyncUESClient(transport=transport)


@pytest.fixture
def sample_scenario_dir(tmp_path):
    """Create a sample scenario directory with all required files."""
    # Create scenario file
    scenario = {
        "name": "Test Scenario",
        "description": "A test scenario",
        "simulation": {
            "start_time": "2026-01-19T08:00:00-08:00",
            "time_scale": 1.0,
        },
        "environment": {},
    }
    scenario_file = tmp_path / "scenario.ues-scenario.json"
    scenario_file.write_text(json.dumps(scenario))

    # Create criteria file
    criteria = {
        "name": "Test Criteria",
        "description": "Test criteria for integration testing",
        "test_module": "scenario_tests",
        "criteria": [
            {
                "id": "always_pass",
                "name": "Always Pass",
                "description": "A criterion that always passes",
                "evaluator": "check_always_pass",
                "max_points": 10,
                "eval_timing": "post_scenario",
                "params": {},
            },
            {
                "id": "half_score",
                "name": "Half Score",
                "description": "A criterion that gives half points",
                "evaluator": "check_half_score",
                "max_points": 20,
                "eval_timing": "post_scenario",
                "params": {"target": 50},
            },
        ],
    }
    criteria_file = tmp_path / "test_criteria.json"
    criteria_file.write_text(json.dumps(criteria))

    # Create test module
    test_module = '''
"""Test evaluator functions."""
from ues.agent_testing import EvalContext, EvalResult

def check_always_pass(ctx: EvalContext, params: dict) -> EvalResult:
    """Always returns full score."""
    return EvalResult(
        score=10,
        max_score=10,
        explanation="Always passes",
    )

def check_half_score(ctx: EvalContext, params: dict) -> EvalResult:
    """Returns half the max score."""
    target = params.get("target", 50)
    return EvalResult(
        score=target,
        max_score=100,
        explanation=f"Scored {target}/100",
    )
'''
    test_module_file = tmp_path / "scenario_tests.py"
    test_module_file.write_text(test_module)

    return tmp_path


@pytest.fixture
def on_event_scenario_dir(tmp_path):
    """Create a scenario directory with on_event criteria."""
    # Create scenario file
    scenario = {
        "name": "On-Event Test",
        "simulation": {
            "start_time": "2026-01-19T08:00:00-08:00",
        },
    }
    scenario_file = tmp_path / "scenario.ues-scenario.json"
    scenario_file.write_text(json.dumps(scenario))

    # Create criteria with on_event criterion
    criteria = {
        "name": "On-Event Criteria",
        "test_module": "scenario_tests",
        "criteria": [
            {
                "id": "email_quality",
                "name": "Email Quality",
                "evaluator": "check_email_quality",
                "max_points": 10,
                "eval_timing": "on_event",
                "event_filter": "filter_emails",
                "params": {"min_length": 10},
            },
        ],
    }
    criteria_file = tmp_path / "test_criteria.json"
    criteria_file.write_text(json.dumps(criteria))

    # Create test module
    test_module = '''
"""Test evaluator functions for on_event criteria."""
from ues.agent_testing import EvalContext, EvalResult

def filter_emails(event: dict) -> bool:
    """Filter for email events."""
    return event.get("modality") == "email"

def check_email_quality(ctx: EvalContext, params: dict) -> EvalResult:
    """Check email quality based on trigger event."""
    event = ctx.trigger_event
    if not event:
        return EvalResult(score=0, max_score=1, explanation="No trigger event")
    
    body = event.get("data", {}).get("body_text", "")
    min_length = params.get("min_length", 10)
    
    if len(body) >= min_length:
        return EvalResult(score=1, max_score=1, explanation="Email meets length requirement")
    else:
        return EvalResult(score=0, max_score=1, explanation=f"Email too short: {len(body)} < {min_length}")
'''
    test_module_file = tmp_path / "scenario_tests.py"
    test_module_file.write_text(test_module)

    return tmp_path


class TestEvalRunnerSetup:
    """Tests for EvalRunner setup and configuration."""

    @pytest.mark.asyncio
    async def test_setup_with_valid_paths(self, sample_scenario_dir, async_client):
        """Test that setup works with valid paths."""
        runner = EvalRunner(
            scenario_path=sample_scenario_dir / "scenario.ues-scenario.json",
            criteria_path=sample_scenario_dir / "test_criteria.json",
            client=async_client,
        )

        await runner.setup()

        assert runner._criteria is not None
        assert runner._criteria.name == "Test Criteria"
        assert len(runner._criteria.criteria) == 2
        assert runner._test_module is not None
        assert runner._context is not None

        await runner.cleanup()

    @pytest.mark.asyncio
    async def test_setup_auto_discovers_criteria(self, sample_scenario_dir, async_client):
        """Test that setup auto-discovers test_criteria.json."""
        runner = EvalRunner(
            scenario_path=sample_scenario_dir / "scenario.ues-scenario.json",
            # criteria_path not specified - should auto-discover
            client=async_client,
        )

        await runner.setup()

        assert runner._criteria is not None
        assert runner._criteria.name == "Test Criteria"

        await runner.cleanup()

    @pytest.mark.asyncio
    async def test_setup_fails_without_criteria(self, tmp_path, async_client):
        """Test that setup fails if criteria file not found."""
        # Create only scenario, no criteria
        scenario_file = tmp_path / "scenario.ues-scenario.json"
        scenario_file.write_text('{"name": "Test"}')

        runner = EvalRunner(
            scenario_path=scenario_file,
            client=async_client,
        )

        with pytest.raises(FileNotFoundError):
            await runner.setup()


class TestEvalRunnerExecution:
    """Tests for EvalRunner execution."""

    @pytest.mark.asyncio
    async def test_run_post_scenario_evaluators(self, sample_scenario_dir, async_client):
        """Test running post_scenario evaluators."""
        runner = EvalRunner(
            scenario_path=sample_scenario_dir / "scenario.ues-scenario.json",
            client=async_client,
        )

        report = await runner.run()

        assert report is not None
        assert report.name == "Test Criteria"
        assert len(report.criteria_results) == 2

        # Check always_pass criterion
        always_pass = next(r for r in report.criteria_results if r.id == "always_pass")
        assert always_pass.score == 10
        assert always_pass.max_score == 10

        # Check half_score criterion (50/100 scaled to 20 max_points = 10)
        half_score = next(r for r in report.criteria_results if r.id == "half_score")
        assert half_score.score == 10  # 50/100 * 20 = 10
        assert half_score.max_score == 20

    @pytest.mark.asyncio
    async def test_on_event_hooks_registered(self, on_event_scenario_dir, async_client):
        """Test that on_event hooks are registered."""
        runner = EvalRunner(
            scenario_path=on_event_scenario_dir / "scenario.ues-scenario.json",
            client=async_client,
        )

        await runner.setup()

        assert runner._hook_manager is not None
        assert runner._hook_manager.hook_count == 1
        assert "email_quality" in runner._hook_manager.registered_criterion_ids

        await runner.cleanup()

    @pytest.mark.asyncio
    async def test_dispatch_event_manually(self, on_event_scenario_dir, async_client):
        """Test manually dispatching events."""
        runner = EvalRunner(
            scenario_path=on_event_scenario_dir / "scenario.ues-scenario.json",
            client=async_client,
        )

        await runner.setup()

        # Dispatch an email event
        results = await runner.dispatch_event({
            "id": "test-event-1",
            "modality": "email",
            "data": {"body_text": "This is a test email with enough content."},
        })

        assert len(results) == 1
        criterion_id, result = results[0]
        assert criterion_id == "email_quality"
        assert result.score == 1  # Should pass (length > 10)

        # Dispatch a short email
        results = await runner.dispatch_event({
            "id": "test-event-2",
            "modality": "email",
            "data": {"body_text": "Short"},
        })

        assert len(results) == 1
        assert results[0][1].score == 0  # Should fail (length < 10)

        await runner.cleanup()

    @pytest.mark.asyncio
    async def test_finalize_aggregates_on_event_results(
        self, on_event_scenario_dir, async_client
    ):
        """Test that finalize aggregates on_event results."""
        runner = EvalRunner(
            scenario_path=on_event_scenario_dir / "scenario.ues-scenario.json",
            client=async_client,
        )

        await runner.setup()

        # Dispatch some events
        await runner.dispatch_event({
            "id": "1",
            "modality": "email",
            "data": {"body_text": "Long enough email content"},
        })
        await runner.dispatch_event({
            "id": "2",
            "modality": "email",
            "data": {"body_text": "Also long enough content"},
        })
        await runner.dispatch_event({
            "id": "3",
            "modality": "email",
            "data": {"body_text": "Short"},
        })

        report = await runner.finalize()

        email_quality = next(
            r for r in report.criteria_results if r.id == "email_quality"
        )
        # 2 passed, 1 failed = 2/3 * 10 max_points = 6.67
        assert email_quality.eval_count == 3
        assert email_quality.raw_score == 2  # 2 emails passed
        assert email_quality.raw_max_score == 3  # 3 emails evaluated
        assert abs(email_quality.score - 6.67) < 0.1  # Scaled score

        await runner.cleanup()


class TestEvalRunnerContextManager:
    """Tests for EvalRunner context manager usage."""

    @pytest.mark.asyncio
    async def test_async_context_manager(self, sample_scenario_dir, async_client):
        """Test using runner as async context manager."""
        async with EvalRunner(
            scenario_path=sample_scenario_dir / "scenario.ues-scenario.json",
            client=async_client,
        ) as runner:
            assert runner._criteria is not None
            assert runner._context is not None

            report = await runner.finalize()
            assert report is not None


class TestEvalRunnerReporting:
    """Tests for EvalRunner reporting methods."""

    @pytest.mark.asyncio
    async def test_print_report(self, sample_scenario_dir, async_client, capsys):
        """Test that print_report outputs to terminal."""
        runner = EvalRunner(
            scenario_path=sample_scenario_dir / "scenario.ues-scenario.json",
            client=async_client,
        )

        await runner.run()
        runner.print_report()

        captured = capsys.readouterr()
        assert "Test Criteria" in captured.out
        assert "Always Pass" in captured.out

    @pytest.mark.asyncio
    async def test_save_report(self, sample_scenario_dir, async_client, tmp_path):
        """Test saving report to JSON file."""
        runner = EvalRunner(
            scenario_path=sample_scenario_dir / "scenario.ues-scenario.json",
            client=async_client,
        )

        await runner.run()

        output_path = tmp_path / "results.json"
        runner.save_report(output_path)

        assert output_path.exists()
        data = json.loads(output_path.read_text())
        assert data["name"] == "Test Criteria"
        assert len(data["criteria_results"]) == 2

    @pytest.mark.asyncio
    async def test_report_property(self, sample_scenario_dir, async_client):
        """Test report property access."""
        runner = EvalRunner(
            scenario_path=sample_scenario_dir / "scenario.ues-scenario.json",
            client=async_client,
        )

        assert runner.report is None  # Before running

        await runner.run()

        assert runner.report is not None
        assert runner.report.name == "Test Criteria"
