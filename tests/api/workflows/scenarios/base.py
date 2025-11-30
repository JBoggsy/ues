"""
Base classes for workflow scenario definitions.

This module provides the DSL (Domain Specific Language) for defining
workflow test scenarios in a declarative manner.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class StepType(Enum):
    """Types of workflow steps.

    Each step type maps to a specific API operation or verification action.
    """

    # Simulation lifecycle control
    START_SIMULATION = "start_simulation"
    STOP_SIMULATION = "stop_simulation"
    RESET_SIMULATION = "reset_simulation"

    # Time control operations
    ADVANCE_TIME = "advance_time"
    SET_TIME = "set_time"
    SKIP_TO_NEXT = "skip_to_next"
    PAUSE = "pause"
    RESUME = "resume"

    # Event operations
    CREATE_EVENT = "create_event"
    CREATE_IMMEDIATE_EVENT = "create_immediate_event"
    CANCEL_EVENT = "cancel_event"

    # State verification (reads state and runs assertions)
    VERIFY_STATE = "verify_state"
    VERIFY_EVENT_SUMMARY = "verify_event_summary"
    VERIFY_SIMULATION_STATUS = "verify_simulation_status"
    VERIFY_TIME_STATE = "verify_time_state"
    VERIFY_ENVIRONMENT = "verify_environment"

    # Modality convenience routes
    MODALITY_ACTION = "modality_action"
    MODALITY_QUERY = "modality_query"


@dataclass
class WorkflowStep:
    """A single step in a workflow scenario.

    Args:
        step_type: The type of operation to perform.
        description: Human-readable description of the step.
        params: Parameters for the operation (varies by step_type).
        expect_status: Expected HTTP status code (default 200).
        expect_error: Whether this step is expected to fail.
        assertions: List of assertion functions to run on the response.
        store_as: Optional key to store the response for later reference.
    """

    step_type: StepType
    description: str
    params: dict[str, Any] = field(default_factory=dict)

    # Expected outcomes
    expect_status: int = 200
    expect_error: bool = False

    # State assertions to run after this step (receive response dict)
    assertions: list[Callable[[dict[str, Any]], None]] = field(default_factory=list)

    # Store response for later reference by key name
    store_as: str | None = None


@dataclass
class WorkflowScenario:
    """Complete workflow scenario definition.

    A scenario represents a realistic multi-step workflow that tests
    the API's behavior across multiple operations.

    Args:
        name: Short name for the scenario.
        description: Detailed description of what the scenario tests.
        complexity: Complexity level ("simple", "medium", "complex").
        modalities: List of modalities used in this scenario.
        setup_events: Events to create and execute during setup phase.
        steps: Ordered list of workflow steps to execute.
        final_assertions: Assertions to run after all steps complete.
    """

    name: str
    description: str
    complexity: str
    modalities: list[str]

    # Initial state setup (immediate events executed at start)
    setup_events: list[dict[str, Any]] = field(default_factory=list)

    # Ordered list of workflow steps
    steps: list[WorkflowStep] = field(default_factory=list)

    # Final state expectations (receive the runner instance)
    final_assertions: list[Callable[["WorkflowRunner"], None]] = field(
        default_factory=list
    )


# Type alias for assertion functions
AssertionFunc = Callable[[dict[str, Any]], None]


def step(
    step_type: StepType,
    description: str,
    *,
    params: dict[str, Any] | None = None,
    expect_status: int = 200,
    expect_error: bool = False,
    assertions: list[AssertionFunc] | None = None,
    store_as: str | None = None,
) -> WorkflowStep:
    """Factory function for creating WorkflowStep instances.

    Provides a cleaner syntax for defining steps in scenarios.

    Args:
        step_type: The type of operation to perform.
        description: Human-readable description of the step.
        params: Parameters for the operation.
        expect_status: Expected HTTP status code.
        expect_error: Whether this step is expected to fail.
        assertions: List of assertion functions.
        store_as: Optional key to store the response.

    Returns:
        A configured WorkflowStep instance.
    """
    return WorkflowStep(
        step_type=step_type,
        description=description,
        params=params or {},
        expect_status=expect_status,
        expect_error=expect_error,
        assertions=assertions or [],
        store_as=store_as,
    )


# Import WorkflowRunner type for type hints (avoid circular import at runtime)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..runner import WorkflowRunner
