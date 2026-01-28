"""Test runner for agent testing.

This module provides the EvalRunner class, which orchestrates test execution
including loading criteria, discovering test modules, running evaluators,
and generating reports.
"""

import asyncio
import importlib.util
import inspect
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable

from ues.client import AsyncUESClient

from ues.agent_testing.context import EvalContext
from ues.agent_testing.display import format_report_terminal, save_report_json
from ues.agent_testing.hooks import EventHookManager
from ues.agent_testing.results import CriterionResult, EvalReport, EvalResult
from ues.agent_testing.schema import (
    CriterionSchema,
    EvalTiming,
    CriteriaSchema,
    load_criteria_from_file,
)


class EvalRunner:
    """Orchestrates agent test execution.

    The EvalRunner handles the complete test lifecycle:
    1. Load scenario and criteria configuration
    2. Discover and load test module with evaluator functions
    3. Register on_event hooks
    4. Execute scenario (or monitor running scenario)
    5. Dispatch events to on_event evaluators
    6. Run post_scenario evaluators
    7. Aggregate results and generate report

    Example:
        Basic usage::

            runner = EvalRunner(
                scenario_path="./scenario.ues-scenario.json",
                criteria_path="./test_criteria.json",
                ues_host="http://localhost:8000",
            )

            # Run tests and get report
            report = await runner.run()

            # Output results
            runner.print_report()
            runner.save_report("results.json")

        Manual lifecycle::

            async with runner:
                # Load and setup
                await runner.setup()

                # Monitor events during scenario execution
                while scenario_running:
                    await runner.process_pending_events()

                # Finalize and get results
                report = await runner.finalize()
    """

    def __init__(
        self,
        scenario_path: str | Path | None = None,
        criteria_path: str | Path | None = None,
        test_module_path: str | Path | None = None,
        ues_host: str = "http://localhost:8000",
        client: AsyncUESClient | None = None,
    ) -> None:
        """Initialize the test runner.

        Args:
            scenario_path: Path to the scenario JSON file. If provided,
                the runner will look for criteria in the same directory.
            criteria_path: Path to the test_criteria.json file. If not
                provided, will look for test_criteria.json in the scenario
                directory.
            test_module_path: Path to the Python module containing evaluator
                functions. If not provided, will use the test_module name
                from criteria config.
            ues_host: URL of the UES server.
            client: Optional pre-configured AsyncUESClient. If provided,
                the runner will use this instead of creating a new client.
        """
        self._scenario_path = Path(scenario_path) if scenario_path else None
        self._criteria_path = Path(criteria_path) if criteria_path else None
        self._test_module_path = Path(test_module_path) if test_module_path else None
        self._ues_host = ues_host
        self._external_client = client

        # Initialized during setup
        self._client: AsyncUESClient | None = None
        self._criteria: CriteriaSchema | None = None
        self._scenario_config: dict[str, Any] = {}
        self._test_module: Any = None
        self._hook_manager: EventHookManager | None = None
        self._context: EvalContext | None = None

        # Results
        self._report: EvalReport | None = None
        self._start_time: float | None = None
        self._last_event_id: str | None = None

    async def __aenter__(self) -> "EvalRunner":
        """Async context manager entry."""
        await self.setup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.cleanup()

    async def setup(self) -> None:
        """Initialize the runner: load configs, discover modules, setup hooks.

        This must be called before running tests or processing events.
        """
        self._start_time = time.time()

        # Setup client
        if self._external_client:
            self._client = self._external_client
        else:
            self._client = AsyncUESClient(base_url=self._ues_host)

        # Discover and load criteria
        self._criteria = self._load_criteria()

        # Load scenario config if provided
        if self._scenario_path and self._scenario_path.exists():
            with open(self._scenario_path) as f:
                self._scenario_config = json.load(f)

        # Discover and load test module
        self._test_module = self._load_test_module()

        # Setup hook manager and register on_event hooks
        self._hook_manager = EventHookManager()
        self._register_hooks()

        # Create context
        self._context = EvalContext(
            client=self._client,
            scenario_config=self._scenario_config,
            criteria_config=self._criteria.model_dump(),
        )

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self._client and not self._external_client:
            await self._client.close()

    def _load_criteria(self) -> CriteriaSchema:
        """Load and validate criteria configuration."""
        # Try explicit path first
        if self._criteria_path and self._criteria_path.exists():
            return load_criteria_from_file(str(self._criteria_path))

        # Try to find in scenario directory
        if self._scenario_path:
            scenario_dir = self._scenario_path.parent
            default_criteria = scenario_dir / "test_criteria.json"
            if default_criteria.exists():
                self._criteria_path = default_criteria
                return load_criteria_from_file(str(default_criteria))

        raise FileNotFoundError(
            "Could not find test_criteria.json. "
            "Provide criteria_path or place test_criteria.json in the scenario directory."
        )

    def _load_test_module(self) -> Any:
        """Load the Python module containing evaluator functions."""
        module_name = self._criteria.test_module

        # Try explicit path first
        if self._test_module_path and self._test_module_path.exists():
            return self._load_module_from_path(self._test_module_path, module_name)

        # Try to find in scenario directory
        if self._scenario_path:
            scenario_dir = self._scenario_path.parent

            # Try module_name.py
            module_file = scenario_dir / f"{module_name}.py"
            if module_file.exists():
                self._test_module_path = module_file
                return self._load_module_from_path(module_file, module_name)

        # Try importing from Python path
        try:
            return importlib.import_module(module_name)
        except ImportError:
            pass

        raise ImportError(
            f"Could not find test module '{module_name}'. "
            f"Create {module_name}.py in the scenario directory or ensure "
            f"it's importable from Python path."
        )

    def _load_module_from_path(self, path: Path, module_name: str) -> Any:
        """Load a Python module from a file path."""
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load module from {path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    def _get_function(self, name: str) -> Callable:
        """Get a function from the test module by name."""
        if not hasattr(self._test_module, name):
            raise AttributeError(
                f"Test module '{self._criteria.test_module}' has no function '{name}'"
            )
        func = getattr(self._test_module, name)
        if not callable(func):
            raise TypeError(f"'{name}' in test module is not callable")
        return func

    def _register_hooks(self) -> None:
        """Register on_event hooks from criteria."""
        for criterion in self._criteria.criteria:
            if criterion.eval_timing != EvalTiming.ON_EVENT:
                continue

            evaluator = self._get_function(criterion.evaluator)

            event_filter = None
            if criterion.event_filter:
                event_filter = self._get_function(criterion.event_filter)

            self._hook_manager.register_hook(
                criterion=criterion,
                evaluator=evaluator,
                event_filter=event_filter,
            )

    async def run(
        self,
        scenario_runner: Callable[["EvalRunner"], Any] | None = None,
    ) -> EvalReport:
        """Run the complete test cycle.

        This method:
        1. Sets up the runner if not already done
        2. Optionally runs a scenario runner function
        3. Processes any pending events
        4. Runs post_scenario evaluators
        5. Generates and returns the report

        Args:
            scenario_runner: Optional async function that runs the scenario.
                Receives the EvalRunner instance as argument. If not provided,
                the runner assumes the scenario has already been executed.

        Returns:
            The EvalReport with all results.
        """
        if not self._client:
            await self.setup()

        try:
            # Run scenario if provided
            if scenario_runner:
                if inspect.iscoroutinefunction(scenario_runner):
                    await scenario_runner(self)
                else:
                    scenario_runner(self)

            # Process any remaining events
            await self.process_pending_events()

            # Run post_scenario evaluators and finalize
            return await self.finalize()
        finally:
            await self.cleanup()

    async def process_pending_events(self) -> int:
        """Process any pending events through on_event hooks.

        Fetches events from the UES event history and dispatches them
        to registered hooks. Tracks which events have been processed
        to avoid duplicates.

        Returns:
            Number of events processed.
        """
        if not self._hook_manager or self._hook_manager.hook_count == 0:
            return 0

        # Get all events from history
        events = await self._client.events.history()
        processed = 0

        for event in events:
            event_dict = event.model_dump() if hasattr(event, "model_dump") else event
            event_id = event_dict.get("id") or event_dict.get("event_id")

            # Skip if already processed
            if self._last_event_id and event_id:
                # Simple approach: process all events each time
                # A more sophisticated approach would track processed IDs
                pass

            # Add to context history
            self._context.add_event(event_dict)

            # Dispatch to hooks
            await self._hook_manager.dispatch_event(event_dict, self._context)
            processed += 1

            if event_id:
                self._last_event_id = event_id

        return processed

    async def dispatch_event(self, event: dict[str, Any]) -> list[tuple[str, EvalResult]]:
        """Manually dispatch an event to hooks.

        Use this when you want to dispatch events directly rather than
        fetching from the UES event history.

        Args:
            event: The event dictionary to dispatch.

        Returns:
            List of (criterion_id, EvalResult) tuples.
        """
        if not self._hook_manager:
            return []

        self._context.add_event(event)
        return await self._hook_manager.dispatch_event(event, self._context)

    async def finalize(self) -> EvalReport:
        """Run post_scenario evaluators and generate the final report.

        Returns:
            The complete EvalReport.
        """
        criterion_results: list[CriterionResult] = []

        for criterion in self._criteria.criteria:
            if criterion.eval_timing == EvalTiming.POST_SCENARIO:
                result = await self._run_post_scenario_evaluator(criterion)
                criterion_results.append(result)
            else:
                # Aggregate on_event results
                result = self._aggregate_on_event_results(criterion)
                criterion_results.append(result)

        # Calculate duration
        duration = time.time() - self._start_time if self._start_time else 0

        # Create report
        self._report = EvalReport.create(
            name=self._criteria.name,
            criteria_results=criterion_results,
            duration_seconds=duration,
            scenario_path=str(self._scenario_path) if self._scenario_path else None,
            criteria_path=str(self._criteria_path) if self._criteria_path else None,
        )

        return self._report

    async def _run_post_scenario_evaluator(
        self, criterion: CriterionSchema
    ) -> CriterionResult:
        """Run a post_scenario evaluator and return its result."""
        evaluator = self._get_function(criterion.evaluator)

        try:
            if inspect.iscoroutinefunction(evaluator):
                result = await evaluator(self._context, criterion.params)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, lambda: evaluator(self._context, criterion.params)
                )

            # Scale score to criterion max_points
            scale_factor = criterion.max_points / result.max_score if result.max_score > 0 else 0
            scaled_score = result.score * scale_factor

            return CriterionResult(
                id=criterion.id,
                name=criterion.name,
                score=scaled_score,
                max_score=criterion.max_points,
                explanation=result.explanation,
                eval_count=1,
                raw_score=result.score,
                raw_max_score=result.max_score,
                individual_results=[result],
            )

        except Exception as e:
            return CriterionResult(
                id=criterion.id,
                name=criterion.name,
                score=0,
                max_score=criterion.max_points,
                explanation=f"Evaluator error: {e}",
                eval_count=1,
            )

    def _aggregate_on_event_results(self, criterion: CriterionSchema) -> CriterionResult:
        """Aggregate results from on_event evaluations."""
        hook = self._hook_manager.get_hook_for_criterion(criterion.id)

        if not hook or not hook.results:
            return CriterionResult(
                id=criterion.id,
                name=criterion.name,
                score=0,
                max_score=criterion.max_points,
                explanation="No matching events occurred",
                eval_count=0,
            )

        # Sum raw scores
        raw_score = sum(r.score for r in hook.results)
        raw_max_score = sum(r.max_score for r in hook.results)

        # Scale to criterion max_points
        if raw_max_score > 0:
            scaled_score = (raw_score / raw_max_score) * criterion.max_points
        else:
            scaled_score = 0

        # Build explanation
        if raw_max_score > 0:
            percentage = (raw_score / raw_max_score) * 100
            explanation = (
                f"{raw_score:.1f}/{raw_max_score:.1f} across {len(hook.results)} "
                f"evaluations ({percentage:.0f}%)"
            )
        else:
            explanation = f"Evaluated {len(hook.results)} events"

        return CriterionResult(
            id=criterion.id,
            name=criterion.name,
            score=scaled_score,
            max_score=criterion.max_points,
            explanation=explanation,
            eval_count=len(hook.results),
            raw_score=raw_score,
            raw_max_score=raw_max_score,
            individual_results=list(hook.results),
        )

    def print_report(self) -> None:
        """Print the test report to terminal."""
        if not self._report:
            print("No report available. Run tests first.")
            return
        print(format_report_terminal(self._report))

    def save_report(self, path: str | Path) -> None:
        """Save the test report to a JSON file.

        Args:
            path: Path to save the report.
        """
        if not self._report:
            raise RuntimeError("No report available. Run tests first.")
        save_report_json(self._report, path)

    @property
    def report(self) -> EvalReport | None:
        """Get the test report (None if tests haven't been run)."""
        return self._report

    @property
    def context(self) -> EvalContext | None:
        """Get the test context."""
        return self._context

    @property
    def client(self) -> AsyncUESClient | None:
        """Get the UES client."""
        return self._client
