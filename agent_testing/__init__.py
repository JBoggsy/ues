"""UES Agent Testing Harness.

This package provides infrastructure for evaluating AI agent performance
through customizable, hook-based testing.

Main Classes:
    EvalRunner: Orchestrates evaluation execution
    EvalContext: Context passed to evaluator functions
    EvalResult: Result returned by evaluator functions
    CriterionResult: Aggregated result for a criterion
    EvalReport: Complete evaluation report

Example:
    Basic usage::

        from agent_testing import EvalRunner, EvalContext, EvalResult

        # Create test functions in scenario_tests.py
        async def check_task_completion(ctx: EvalContext, params: dict) -> EvalResult:
            email_state = await ctx.get_state("email")
            sent_count = sum(1 for e in email_state.emails.values() if e.folder == "sent")
            return EvalResult(
                score=min(sent_count, params["expected"]),
                max_score=params["expected"],
                explanation=f"Sent {sent_count} emails",
            )

        # Run tests
        runner = EvalRunner(
            scenario_path="./scenario.ues-scenario.json",
            criteria_path="./test_criteria.json",
        )
        report = await runner.run()
        runner.print_report()

See docs/AGENT_TESTING.md for complete documentation.
"""

from agent_testing.context import EvalContext
from agent_testing.display import (
    format_report_summary,
    format_report_terminal,
    load_report_json,
    save_report_json,
)
from agent_testing.hooks import EventHookManager, RegisteredHook
from agent_testing.results import CriterionResult, EvalReport, EvalResult
from agent_testing.runner import EvalRunner
from agent_testing.schema import (
    CriteriaSchema,
    CriterionSchema,
    EvalTiming,
    load_criteria_from_dict,
    load_criteria_from_file,
)


__all__ = [
    # Main classes
    "EvalRunner",
    "EvalContext",
    "EvalResult",
    "CriterionResult",
    "EvalReport",
    # Schema
    "CriteriaSchema",
    "CriterionSchema",
    "EvalTiming",
    "load_criteria_from_file",
    "load_criteria_from_dict",
    # Hooks
    "EventHookManager",
    "RegisteredHook",
    # Display
    "format_report_terminal",
    "format_report_summary",
    "save_report_json",
    "load_report_json",
]
