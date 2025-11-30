"""
Workflow execution engine.

The WorkflowRunner executes workflow scenarios step-by-step,
handling API calls, state management, and assertion validation.
"""

from datetime import datetime
from typing import Any

from fastapi.testclient import TestClient

from .scenarios.base import WorkflowScenario, WorkflowStep, StepType
from .builders import EventBuilder


class WorkflowRunner:
    """Executes workflow scenarios against the API.

    The runner handles:
    - Executing setup events
    - Running each workflow step in order
    - Building events from EventBuilder instances
    - Storing responses for later reference
    - Running assertions after each step
    - Printing progress for debugging

    Args:
        client: FastAPI TestClient for making requests.
        engine: The SimulationEngine instance (for direct access if needed).
        verbose: Whether to print progress messages.
    """

    def __init__(
        self,
        client: TestClient,
        engine: Any,
        verbose: bool = True,
    ):
        self.client = client
        self.engine = engine
        self.verbose = verbose

        # Track simulation state
        self.base_time: datetime | None = None
        self.stored_responses: dict[str, Any] = {}
        self.step_results: list[dict[str, Any]] = []

    def run(self, scenario: WorkflowScenario) -> None:
        """Execute a complete workflow scenario.

        Args:
            scenario: The scenario definition to execute.

        Raises:
            AssertionError: If any step or assertion fails.
        """
        self._print_header(scenario)

        # Get the current simulation time as base
        time_response = self.client.get("/simulator/time")
        if time_response.status_code == 200:
            time_data = time_response.json()
            self.base_time = datetime.fromisoformat(
                time_data.get("current_time", datetime.now().isoformat())
            )
        else:
            self.base_time = datetime.now()

        # Execute setup events if any
        if scenario.setup_events:
            self._run_setup(scenario.setup_events)

        # Execute each step
        for i, step in enumerate(scenario.steps, 1):
            self._print_step(i, step)
            result = self._execute_step(step)
            self.step_results.append(result)
            self._print_step_complete()

        # Run final assertions
        if scenario.final_assertions:
            self._log("Running final assertions...")
            for assertion in scenario.final_assertions:
                assertion(self)
            self._log("  ✓ All final assertions passed")

        self._print_footer(scenario)

    def _run_setup(self, setup_events: list[dict[str, Any]]) -> None:
        """Execute setup events at simulation start."""
        self._log("Setting up initial state...")

        for i, event_data in enumerate(setup_events, 1):
            # Handle EventBuilder instances
            if isinstance(event_data, EventBuilder):
                event_data = event_data.build_immediate()

            response = self.client.post("/events/immediate", json=event_data)
            # Accept both 200 and 201 as success codes
            if response.status_code not in (200, 201):
                raise AssertionError(
                    f"Setup event {i} failed: {response.status_code} - {response.json()}"
                )
            self._log(f"  Created setup event {i}")

        # Advance time slightly to execute setup events
        self.client.post("/simulator/time/advance", json={"seconds": 0.1})
        self._log("  ✓ Setup complete\n")

    def _execute_step(self, step: WorkflowStep) -> dict[str, Any]:
        """Execute a single workflow step.

        Args:
            step: The step to execute.

        Returns:
            The response JSON from the API.

        Raises:
            AssertionError: If the response status doesn't match expectations
                or if any assertion fails.
        """
        handler = self._get_handler(step.step_type)
        response = handler(step)

        # Check expected status
        if step.expect_error:
            if response.status_code < 400:
                raise AssertionError(
                    f"Expected error status, got {response.status_code}"
                )
        else:
            if response.status_code != step.expect_status:
                raise AssertionError(
                    f"Expected status {step.expect_status}, got {response.status_code}: "
                    f"{response.json()}"
                )

        result = response.json()

        # Store response if requested
        if step.store_as:
            self.stored_responses[step.store_as] = result

        # Run step-specific assertions
        for assertion in step.assertions:
            assertion(result)

        return result

    def _get_handler(self, step_type: StepType):
        """Get the handler function for a step type."""
        handlers = {
            StepType.START_SIMULATION: self._handle_start,
            StepType.STOP_SIMULATION: self._handle_stop,
            StepType.RESET_SIMULATION: self._handle_reset,
            StepType.ADVANCE_TIME: self._handle_advance,
            StepType.SET_TIME: self._handle_set_time,
            StepType.SKIP_TO_NEXT: self._handle_skip,
            StepType.PAUSE: self._handle_pause,
            StepType.RESUME: self._handle_resume,
            StepType.CREATE_EVENT: self._handle_create_event,
            StepType.CREATE_IMMEDIATE_EVENT: self._handle_immediate_event,
            StepType.CANCEL_EVENT: self._handle_cancel_event,
            StepType.VERIFY_STATE: self._handle_verify_state,
            StepType.VERIFY_EVENT_SUMMARY: self._handle_verify_summary,
            StepType.VERIFY_SIMULATION_STATUS: self._handle_verify_status,
            StepType.VERIFY_TIME_STATE: self._handle_verify_time,
            StepType.VERIFY_ENVIRONMENT: self._handle_verify_environment,
            StepType.MODALITY_ACTION: self._handle_modality_action,
            StepType.MODALITY_QUERY: self._handle_modality_query,
        }
        return handlers[step_type]

    # -------------------------------------------------------------------------
    # Step Handlers
    # -------------------------------------------------------------------------

    def _handle_start(self, step: WorkflowStep):
        """Handle START_SIMULATION step."""
        return self.client.post("/simulation/start", json=step.params or {})

    def _handle_stop(self, step: WorkflowStep):
        """Handle STOP_SIMULATION step."""
        return self.client.post("/simulation/stop")

    def _handle_reset(self, step: WorkflowStep):
        """Handle RESET_SIMULATION step."""
        return self.client.post("/simulation/reset")

    def _handle_advance(self, step: WorkflowStep):
        """Handle ADVANCE_TIME step."""
        seconds = step.params.get("seconds", 0)
        return self.client.post(
            "/simulator/time/advance",
            json={"seconds": seconds},
        )

    def _handle_set_time(self, step: WorkflowStep):
        """Handle SET_TIME step."""
        target = step.params.get("target_time")
        if isinstance(target, datetime):
            target = target.isoformat()
        return self.client.post(
            "/simulator/time/set",
            json={"target_time": target},
        )

    def _handle_skip(self, step: WorkflowStep):
        """Handle SKIP_TO_NEXT step."""
        return self.client.post("/simulator/time/skip-to-next")

    def _handle_pause(self, step: WorkflowStep):
        """Handle PAUSE step."""
        return self.client.post("/simulator/time/pause")

    def _handle_resume(self, step: WorkflowStep):
        """Handle RESUME step."""
        return self.client.post("/simulator/time/resume")

    def _handle_create_event(self, step: WorkflowStep):
        """Handle CREATE_EVENT step."""
        event_data = step.params.get("event")

        # Handle EventBuilder instances
        if isinstance(event_data, EventBuilder):
            event_data = event_data.build(self.base_time or datetime.now())

        return self.client.post("/events", json=event_data)

    def _handle_immediate_event(self, step: WorkflowStep):
        """Handle CREATE_IMMEDIATE_EVENT step."""
        event_data = step.params.get("event")

        # Handle EventBuilder instances
        if isinstance(event_data, EventBuilder):
            event_data = event_data.build_immediate()

        return self.client.post("/events/immediate", json=event_data)

    def _handle_cancel_event(self, step: WorkflowStep):
        """Handle CANCEL_EVENT step."""
        event_id = step.params.get("event_id")
        return self.client.delete(f"/events/{event_id}")

    def _handle_verify_state(self, step: WorkflowStep):
        """Handle VERIFY_STATE step (get modality state)."""
        modality = step.params.get("modality")
        return self.client.get(f"/{modality}/state")

    def _handle_verify_summary(self, step: WorkflowStep):
        """Handle VERIFY_EVENT_SUMMARY step."""
        return self.client.get("/events/summary")

    def _handle_verify_status(self, step: WorkflowStep):
        """Handle VERIFY_SIMULATION_STATUS step."""
        return self.client.get("/simulation/status")

    def _handle_verify_time(self, step: WorkflowStep):
        """Handle VERIFY_TIME_STATE step."""
        return self.client.get("/simulator/time")

    def _handle_verify_environment(self, step: WorkflowStep):
        """Handle VERIFY_ENVIRONMENT step."""
        return self.client.get("/environment/state")

    def _handle_modality_action(self, step: WorkflowStep):
        """Handle MODALITY_ACTION step."""
        modality = step.params.get("modality")
        action = step.params.get("action")
        data = step.params.get("data", {})
        return self.client.post(f"/{modality}/{action}", json=data)

    def _handle_modality_query(self, step: WorkflowStep):
        """Handle MODALITY_QUERY step."""
        modality = step.params.get("modality")
        query = step.params.get("query", {})
        return self.client.post(f"/{modality}/query", json=query)

    # -------------------------------------------------------------------------
    # Logging Helpers
    # -------------------------------------------------------------------------

    def _log(self, message: str) -> None:
        """Print a message if verbose mode is enabled."""
        if self.verbose:
            print(message)

    def _print_header(self, scenario: WorkflowScenario) -> None:
        """Print scenario header."""
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"Running: {scenario.name}")
            print(f"Description: {scenario.description}")
            print(f"Complexity: {scenario.complexity}")
            print(f"Modalities: {', '.join(scenario.modalities)}")
            print(f"Steps: {len(scenario.steps)}")
            print(f"{'='*60}\n")

    def _print_step(self, index: int, step: WorkflowStep) -> None:
        """Print step start."""
        if self.verbose:
            print(f"Step {index}: {step.description}")

    def _print_step_complete(self) -> None:
        """Print step completion."""
        if self.verbose:
            print("  ✓ Complete\n")

    def _print_footer(self, scenario: WorkflowScenario) -> None:
        """Print scenario completion."""
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"✅ Scenario '{scenario.name}' passed!")
            print(f"   {len(scenario.steps)} steps executed successfully")
            print(f"{'='*60}\n")
