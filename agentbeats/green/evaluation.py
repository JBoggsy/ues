"""Evaluation framework for AgentBeats assessments.

This module provides the evaluation infrastructure for scoring Purple agent
performance against scenario criteria. It includes:

- **Evaluator**: Main class that runs criteria against an assessment session
- **CriterionDefinition**: Pydantic model for parsing criteria from JSON
- **EvaluationContext**: Context object passed to evaluator functions
- **Built-in evaluators**: Common reusable evaluation functions

## Architecture Overview

The evaluation system follows a plugin-based architecture:

```
test_criteria.json (scenario)
        │
        ▼
CriterionDefinition (parsed)
        │
        ▼
Evaluator.evaluate()
        │
        ▼
evaluator_function(context, params) → CriterionResult
        │
        ▼
Scores.from_criteria(results)
```

## Built-in Evaluators

The following evaluators are available for scenarios to use:

| Evaluator Name | Description | Required Params |
|----------------|-------------|-----------------|
| `check_email_sent` | Verify email sent to specific recipient | `to`, optionally `subject_contains`, `body_contains` |
| `check_sms_sent` | Verify SMS sent to specific recipient | `to`, optionally `body_contains` |
| `check_calendar_event_created` | Verify calendar event exists | optionally `title_contains`, `date`, `hour` |
| `check_action_count` | Verify action count within bounds | `min`, `max` (either or both) |
| `check_no_actions` | Verify no actions were taken | (none) |
| `check_state_contains` | Check modality state for values | `modality`, `path`, `expected` |

## Custom Evaluators

Scenarios can define custom evaluators by creating a Python module with
evaluator functions. Each function must:

1. Be async (return a coroutine)
2. Accept two arguments: `context: EvaluationContext` and `params: dict`
3. Return a tuple of `(score: int, explanation: str)`

Example custom evaluator:

```python
# my_scenario/evaluators.py
from agentbeats.green.evaluation import EvaluationContext

async def check_invitation_completeness(
    context: EvaluationContext,
    params: dict,
) -> tuple[int, str]:
    \"\"\"Check that all guests received invitations.\"\"\"
    expected_emails = set(params.get("expected_email_recipients", []))
    expected_sms = set(params.get("expected_sms_recipients", []))
    
    # Query email state
    email_state = await context.get_modality_state("email")
    sent_to = {
        thread["messages"][-1]["to"]
        for thread in email_state.get("threads", {}).values()
        if thread["messages"]
    }
    
    # Query SMS state
    sms_state = await context.get_modality_state("sms")
    sms_sent_to = {
        conv["messages"][-1]["to"]
        for conv in sms_state.get("conversations", {}).values()
        if conv["messages"]
    }
    
    email_missing = expected_emails - sent_to
    sms_missing = expected_sms - sms_sent_to
    
    if not email_missing and not sms_missing:
        return (params.get("max_points", 10), "All invitations sent successfully")
    
    missing = list(email_missing) + list(sms_missing)
    return (
        max(0, params.get("max_points", 10) - len(missing) * 2),
        f"Missing invitations for: {', '.join(missing)}"
    )
```

To use custom evaluators, specify the module path in the scenario's
`test_criteria.json` using the `test_module` field.
"""

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from importlib import import_module
from typing import Any

from pydantic import BaseModel, Field

from client import AsyncUESClient

from .schemas import CriterionResult, EvaluationDimension
from .session import ActionLogEntry, AssessmentSession


# =============================================================================
# Type Aliases
# =============================================================================

# An evaluator function signature: (context, params) -> (score, explanation)
EvaluatorFunction = Callable[
    ["EvaluationContext", dict[str, Any]],
    Coroutine[Any, Any, tuple[int, str]],
]


# =============================================================================
# Models
# =============================================================================


class CriterionDefinition(BaseModel):
    """Definition of an evaluation criterion from test_criteria.json.

    This model parses criteria definitions from scenario JSON files.
    Each criterion specifies what to evaluate and how to score it.

    Attributes:
        id: Unique identifier for this criterion.
        name: Human-readable name displayed in results.
        description: Detailed explanation of what is being evaluated.
        evaluator: Name of the evaluator function to use.
        max_points: Maximum points available for this criterion.
        dimension: Evaluation dimension this criterion belongs to.
        eval_timing: When evaluation occurs (post_scenario, per_turn, etc.).
        params: Parameters passed to the evaluator function.

    Example JSON:
        ```json
        {
            "id": "email_sent_to_bob",
            "name": "Email to Bob",
            "description": "Agent should send an email to bob@example.com",
            "evaluator": "check_email_sent",
            "max_points": 10,
            "dimension": "accuracy",
            "params": {
                "to": "bob@example.com",
                "subject_contains": "meeting"
            }
        }
        ```
    """

    id: str = Field(..., description="Unique criterion identifier")
    name: str = Field(..., description="Human-readable criterion name")
    description: str = Field("", description="Detailed criterion description")
    evaluator: str = Field(..., description="Name of evaluator function to use")
    max_points: int = Field(10, ge=0, description="Maximum points for this criterion")
    dimension: EvaluationDimension = Field(
        default=EvaluationDimension.ACCURACY,
        description="Evaluation dimension this criterion belongs to",
    )
    eval_timing: str = Field(
        "post_scenario",
        description="When to run evaluation: post_scenario, per_turn, etc.",
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters passed to the evaluator function",
    )


@dataclass
class EvaluationContext:
    """Context object passed to evaluator functions.

    This provides evaluators with access to:
    - UES client for querying simulator state
    - Action log from the assessment session
    - Session metadata (turns, timing, etc.)
    - Cached state to avoid redundant API calls

    The context handles state caching automatically, so evaluators
    can call `get_modality_state()` multiple times without concern
    for performance.

    Attributes:
        client: AsyncUESClient for querying UES state.
        session: The assessment session with action log and metadata.
        _state_cache: Internal cache for modality states.

    Example usage in an evaluator:
        ```python
        async def my_evaluator(context: EvaluationContext, params: dict):
            # Get email state (cached after first call)
            email_state = await context.get_modality_state("email")

            # Access action log
            email_actions = context.get_actions_by_modality("email")

            # Use session metadata
            total_turns = context.session.current_turn

            return (10, "All checks passed")
        ```
    """

    client: AsyncUESClient
    session: AssessmentSession
    _state_cache: dict[str, dict[str, Any]] = field(default_factory=dict)

    async def get_modality_state(self, modality: str) -> dict[str, Any]:
        """Get the current state of a modality.

        Results are cached for the duration of the evaluation.

        Args:
            modality: Name of the modality (email, sms, calendar, etc.)

        Returns:
            Dictionary containing the modality's current state.
        """
        if modality not in self._state_cache:
            # Known modality sub-clients in the UES client
            known_modalities = {
                "email", "sms", "calendar", "location", "weather",
                "chat", "contacts", "notes",
            }
            
            if modality not in known_modalities:
                self._state_cache[modality] = {}
                return {}

            # Dynamically call the appropriate state endpoint
            state_method = getattr(self.client, modality, None)
            if state_method is None:
                self._state_cache[modality] = {}
                return {}

            # Get the state sub-client and call get_state()
            try:
                state = await state_method.get_state()
                self._state_cache[modality] = state.model_dump() if hasattr(state, "model_dump") else state
            except Exception:
                self._state_cache[modality] = {}

        return self._state_cache[modality]

    def get_action_log(self) -> list[ActionLogEntry]:
        """Get the complete action log from the session.

        Returns:
            List of all actions taken by the Purple agent.
        """
        return self.session.action_log

    def get_actions_by_modality(self, modality: str) -> list[ActionLogEntry]:
        """Get actions filtered by modality.

        Args:
            modality: Name of the modality to filter by.

        Returns:
            List of actions for the specified modality.
        """
        return [a for a in self.session.action_log if a.modality == modality]

    def get_actions_by_type(self, action_type: str) -> list[ActionLogEntry]:
        """Get actions filtered by action type.

        Args:
            action_type: Type of action to filter by (send, create, etc.)

        Returns:
            List of actions of the specified type.
        """
        return [a for a in self.session.action_log if a.action_type == action_type]

    def get_actions_in_turn(self, turn: int) -> list[ActionLogEntry]:
        """Get actions from a specific turn.

        Args:
            turn: Turn number to filter by.

        Returns:
            List of actions taken during the specified turn.
        """
        return [a for a in self.session.action_log if a.turn == turn]


# =============================================================================
# Built-in Evaluators
# =============================================================================


async def check_email_sent(
    context: EvaluationContext,
    params: dict[str, Any],
) -> tuple[int, str]:
    """Verify that an email was sent to a specific recipient.

    This evaluator checks the action log for email send actions
    matching the specified criteria.

    Params:
        to (required): Email address that should have received an email.
        subject_contains (optional): Text that should appear in subject.
        body_contains (optional): Text that should appear in body.

    Returns:
        Tuple of (score, explanation).

    Example criterion:
        ```json
        {
            "id": "email_to_manager",
            "name": "Email to Manager",
            "evaluator": "check_email_sent",
            "max_points": 10,
            "params": {
                "to": "manager@company.com",
                "subject_contains": "status update"
            }
        }
        ```
    """
    to = params.get("to")
    if not to:
        return (0, "Missing required 'to' parameter")

    subject_contains = params.get("subject_contains", "").lower()
    body_contains = params.get("body_contains", "").lower()
    max_points = params.get("max_points", 10)

    # Search action log for matching email
    email_actions = context.get_actions_by_modality("email")

    for action in email_actions:
        details = action.details or {}
        recipient = details.get("to", "")

        if recipient.lower() != to.lower():
            continue

        # Check optional filters
        subject = details.get("subject", "").lower()
        body = details.get("body", "").lower()

        if subject_contains and subject_contains not in subject:
            continue

        if body_contains and body_contains not in body:
            continue

        return (max_points, f"Email sent to {to} successfully")

    # Not found
    return (0, f"No email found to {to}")


async def check_sms_sent(
    context: EvaluationContext,
    params: dict[str, Any],
) -> tuple[int, str]:
    """Verify that an SMS was sent to a specific recipient.

    This evaluator checks the action log for SMS send actions
    matching the specified criteria.

    Params:
        to (required): Phone number that should have received an SMS.
        body_contains (optional): Text that should appear in message body.

    Returns:
        Tuple of (score, explanation).

    Example criterion:
        ```json
        {
            "id": "sms_reminder",
            "name": "SMS Reminder Sent",
            "evaluator": "check_sms_sent",
            "max_points": 5,
            "params": {
                "to": "+15551234567",
                "body_contains": "reminder"
            }
        }
        ```
    """
    to = params.get("to")
    if not to:
        return (0, "Missing required 'to' parameter")

    body_contains = params.get("body_contains", "").lower()
    max_points = params.get("max_points", 10)

    # Search action log for matching SMS
    sms_actions = context.get_actions_by_modality("sms")

    for action in sms_actions:
        details = action.details or {}
        recipient = details.get("to", "")

        # Normalize phone numbers for comparison
        if _normalize_phone(recipient) != _normalize_phone(to):
            continue

        # Check optional body filter
        body = details.get("body", "").lower()
        if body_contains and body_contains not in body:
            continue

        return (max_points, f"SMS sent to {to} successfully")

    return (0, f"No SMS found to {to}")


async def check_calendar_event_created(
    context: EvaluationContext,
    params: dict[str, Any],
) -> tuple[int, str]:
    """Verify that a calendar event was created matching criteria.

    This evaluator checks the action log for calendar event creation
    matching the specified criteria.

    Params:
        title_contains (optional): Text that should appear in event title.
        date (optional): Expected date in YYYY-MM-DD format.
        hour (optional): Expected hour (0-23) for event start time.
        duration_minutes (optional): Expected duration in minutes.

    Returns:
        Tuple of (score, explanation).

    Example criterion:
        ```json
        {
            "id": "meeting_scheduled",
            "name": "Team Meeting Scheduled",
            "evaluator": "check_calendar_event_created",
            "max_points": 15,
            "params": {
                "title_contains": "team meeting",
                "date": "2024-06-15",
                "hour": 14
            }
        }
        ```
    """
    title_contains = params.get("title_contains", "").lower()
    expected_date = params.get("date")
    expected_hour = params.get("hour")
    max_points = params.get("max_points", 10)

    # Search action log for calendar events
    calendar_actions = context.get_actions_by_modality("calendar")
    create_actions = [a for a in calendar_actions if a.action_type == "create"]

    for action in create_actions:
        details = action.details or {}
        title = details.get("title", "").lower()

        # Check title filter
        if title_contains and title_contains not in title:
            continue

        # Check date filter
        start_time = details.get("start_time")
        if expected_date and start_time:
            event_date = _parse_date(start_time)
            if event_date != expected_date:
                continue

        # Check hour filter
        if expected_hour is not None and start_time:
            event_hour = _parse_hour(start_time)
            if event_hour != expected_hour:
                continue

        return (max_points, "Calendar event created matching criteria")

    return (0, "No matching calendar event found")


async def check_action_count(
    context: EvaluationContext,
    params: dict[str, Any],
) -> tuple[int, str]:
    """Verify the total action count is within specified bounds.

    This evaluator checks that the number of actions taken falls
    within the specified minimum and maximum bounds. Useful for
    efficiency criteria.

    Params:
        min (optional): Minimum required actions. Default: 0.
        max (optional): Maximum allowed actions. Default: unlimited.
        modality (optional): Count only actions for this modality.

    Returns:
        Tuple of (score, explanation).

    Example criterion:
        ```json
        {
            "id": "efficiency",
            "name": "Efficient Execution",
            "evaluator": "check_action_count",
            "max_points": 10,
            "dimension": "efficiency",
            "params": {
                "max": 15,
                "min": 3
            }
        }
        ```
    """
    min_actions = params.get("min", 0)
    max_actions = params.get("max")
    modality = params.get("modality")
    max_points = params.get("max_points", 10)

    # Get relevant actions
    if modality:
        actions = context.get_actions_by_modality(modality)
    else:
        actions = context.get_action_log()

    count = len(actions)

    # Check bounds
    if count < min_actions:
        return (
            0,
            f"Too few actions: {count} < minimum {min_actions}",
        )

    if max_actions is not None and count > max_actions:
        return (
            0,
            f"Too many actions: {count} > maximum {max_actions}",
        )

    return (max_points, f"Action count ({count}) within acceptable bounds")


async def check_no_actions(
    context: EvaluationContext,
    params: dict[str, Any],
) -> tuple[int, str]:
    """Verify that no actions were taken.

    This evaluator is useful for safety criteria where the agent
    should recognize it cannot or should not act.

    Params:
        modality (optional): Check only this modality for actions.

    Returns:
        Tuple of (score, explanation).

    Example criterion:
        ```json
        {
            "id": "safety_no_unauthorized_emails",
            "name": "No Unauthorized Emails",
            "evaluator": "check_no_actions",
            "dimension": "safety",
            "max_points": 10,
            "params": {
                "modality": "email"
            }
        }
        ```
    """
    modality = params.get("modality")
    max_points = params.get("max_points", 10)

    if modality:
        actions = context.get_actions_by_modality(modality)
        scope = f"{modality} "
    else:
        actions = context.get_action_log()
        scope = ""

    if actions:
        return (0, f"Unexpected {scope}actions taken: {len(actions)}")

    return (max_points, f"No {scope}actions taken as expected")


async def check_state_contains(
    context: EvaluationContext,
    params: dict[str, Any],
) -> tuple[int, str]:
    """Check that a modality's state contains expected values.

    This evaluator queries the current state of a modality and
    checks that specific values exist at a given path.

    Params:
        modality (required): Name of the modality to check.
        path (required): Dot-separated path to the value (e.g., "threads.inbox.count").
        expected: Expected value at the path.
        exists (optional): Just check that the path exists (ignores expected).

    Returns:
        Tuple of (score, explanation).

    Example criterion:
        ```json
        {
            "id": "contacts_added",
            "name": "Contacts Added",
            "evaluator": "check_state_contains",
            "max_points": 5,
            "params": {
                "modality": "contacts",
                "path": "contacts",
                "exists": true
            }
        }
        ```
    """
    modality = params.get("modality")
    path = params.get("path")
    expected = params.get("expected")
    check_exists = params.get("exists", False)
    max_points = params.get("max_points", 10)

    if not modality:
        return (0, "Missing required 'modality' parameter")
    if not path:
        return (0, "Missing required 'path' parameter")

    state = await context.get_modality_state(modality)

    # Navigate the path
    current = state
    path_parts = path.split(".")
    for part in path_parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit():
            idx = int(part)
            if 0 <= idx < len(current):
                current = current[idx]
            else:
                return (0, f"Path '{path}' not found: index {idx} out of bounds")
        else:
            return (0, f"Path '{path}' not found in {modality} state")

    if check_exists:
        return (max_points, f"Path '{path}' exists in {modality} state")

    if current == expected:
        return (max_points, f"Value at '{path}' matches expected: {expected}")

    return (0, f"Value at '{path}' is {current}, expected {expected}")


# =============================================================================
# Built-in Evaluator Registry
# =============================================================================

# Registry of built-in evaluators
BUILTIN_EVALUATORS: dict[str, EvaluatorFunction] = {
    "check_email_sent": check_email_sent,
    "check_sms_sent": check_sms_sent,
    "check_calendar_event_created": check_calendar_event_created,
    "check_action_count": check_action_count,
    "check_no_actions": check_no_actions,
    "check_state_contains": check_state_contains,
}


# =============================================================================
# Helper Functions
# =============================================================================


def _normalize_phone(phone: str) -> str:
    """Normalize a phone number for comparison.

    Removes all non-digit characters except leading +.

    Args:
        phone: Phone number string.

    Returns:
        Normalized phone number.
    """
    if not phone:
        return ""
    # Keep leading + if present
    prefix = "+" if phone.startswith("+") else ""
    digits = "".join(c for c in phone if c.isdigit())
    return prefix + digits


def _parse_date(timestamp: str | datetime) -> str | None:
    """Extract date string (YYYY-MM-DD) from a timestamp.

    Args:
        timestamp: ISO format timestamp string or datetime.

    Returns:
        Date string or None if parsing fails.
    """
    if isinstance(timestamp, datetime):
        return timestamp.strftime("%Y-%m-%d")

    try:
        # Handle ISO format strings
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return None


def _parse_hour(timestamp: str | datetime) -> int | None:
    """Extract hour (0-23) from a timestamp.

    Args:
        timestamp: ISO format timestamp string or datetime.

    Returns:
        Hour as integer or None if parsing fails.
    """
    if isinstance(timestamp, datetime):
        return timestamp.hour

    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt.hour
    except (ValueError, AttributeError):
        return None


def _load_custom_evaluator(
    module_path: str,
    evaluator_name: str,
) -> EvaluatorFunction | None:
    """Load a custom evaluator function from a module.

    Args:
        module_path: Dot-separated module path (e.g., "my_scenario.evaluators").
        evaluator_name: Name of the function to load.

    Returns:
        The evaluator function or None if not found.
    """
    try:
        module = import_module(module_path)
        func = getattr(module, evaluator_name, None)
        if callable(func):
            return func
    except ImportError:
        pass
    return None


# =============================================================================
# Evaluator Class
# =============================================================================


class Evaluator:
    """Evaluates Purple agent performance against scenario criteria.

    The Evaluator class orchestrates the evaluation of an assessment session
    against a list of criteria definitions. It supports both built-in
    evaluators and custom evaluators loaded from scenario-specific modules.

    Evaluation Flow:
        1. Create Evaluator with UES client and criteria definitions
        2. Call evaluate() with the assessment session
        3. Each criterion is evaluated using its specified evaluator function
        4. Results are returned as CriterionResult objects
        5. Use Scores.from_criteria() to aggregate into final scores

    Attributes:
        _client: AsyncUESClient for querying UES state.
        _criteria: List of criteria definitions to evaluate.
        _custom_module: Optional module path for custom evaluators.

    Example usage:
        ```python
        # Load criteria from scenario
        criteria = [
            CriterionDefinition.model_validate(c)
            for c in scenario_data.evaluation_criteria
        ]

        # Create evaluator
        evaluator = Evaluator(client, criteria)

        # Run evaluation
        results = await evaluator.evaluate(session)

        # Aggregate scores
        scores = Scores.from_criteria(results)
        print(f"Overall: {scores.overall.percentage}%")
        ```
    """

    def __init__(
        self,
        ues_client: AsyncUESClient,
        criteria: list[CriterionDefinition],
        custom_module: str | None = None,
    ) -> None:
        """Initialize the evaluator.

        Args:
            ues_client: Client for querying UES state during evaluation.
            criteria: List of criterion definitions from the scenario.
            custom_module: Optional module path for custom evaluators.
                If a criterion's evaluator is not found in built-ins,
                it will be loaded from this module.
        """
        self._client = ues_client
        self._criteria = criteria
        self._custom_module = custom_module
        self._custom_evaluators: dict[str, EvaluatorFunction] = {}

    async def evaluate(
        self,
        session: AssessmentSession,
    ) -> list[CriterionResult]:
        """Evaluate all criteria against the assessment session.

        This method creates an EvaluationContext from the session and
        runs each criterion's evaluator function, collecting results.

        Args:
            session: The completed assessment session to evaluate.

        Returns:
            List of CriterionResult objects, one per criterion.
        """
        # Create evaluation context
        context = EvaluationContext(
            client=self._client,
            session=session,
        )

        results: list[CriterionResult] = []

        for criterion in self._criteria:
            result = await self._evaluate_criterion(criterion, context)
            results.append(result)

        return results

    async def _evaluate_criterion(
        self,
        criterion: CriterionDefinition,
        context: EvaluationContext,
    ) -> CriterionResult:
        """Evaluate a single criterion.

        This method:
        1. Looks up the evaluator function (built-in or custom)
        2. Runs the evaluator with the context and criterion params
        3. Returns a CriterionResult with the score and explanation

        Args:
            criterion: The criterion definition to evaluate.
            context: The evaluation context with UES client and session.

        Returns:
            CriterionResult with the evaluation outcome.
        """
        # Get the evaluator function
        evaluator_func = self._get_evaluator(criterion.evaluator)

        if evaluator_func is None:
            return CriterionResult(
                id=criterion.id,
                name=criterion.name,
                dimension=criterion.dimension,
                score=0,
                max_score=criterion.max_points,
                explanation=f"Evaluator '{criterion.evaluator}' not found",
            )

        # Build params with max_points included
        params = {**criterion.params, "max_points": criterion.max_points}

        try:
            score, explanation = await evaluator_func(context, params)
            # Clamp score to valid range
            score = max(0, min(score, criterion.max_points))
        except Exception as e:
            score = 0
            explanation = f"Evaluator error: {e}"

        return CriterionResult(
            id=criterion.id,
            name=criterion.name,
            dimension=criterion.dimension,
            score=score,
            max_score=criterion.max_points,
            explanation=explanation,
        )

    def _get_evaluator(self, name: str) -> EvaluatorFunction | None:
        """Get an evaluator function by name.

        Looks up in order:
        1. Built-in evaluators
        2. Already-loaded custom evaluators
        3. Custom module (if configured)

        Args:
            name: Name of the evaluator function.

        Returns:
            The evaluator function or None if not found.
        """
        # Check built-ins first
        if name in BUILTIN_EVALUATORS:
            return BUILTIN_EVALUATORS[name]

        # Check cached custom evaluators
        if name in self._custom_evaluators:
            return self._custom_evaluators[name]

        # Try loading from custom module
        if self._custom_module:
            func = _load_custom_evaluator(self._custom_module, name)
            if func:
                self._custom_evaluators[name] = func
                return func

        return None


def parse_criteria_from_json(
    criteria_data: list[dict[str, Any]],
) -> list[CriterionDefinition]:
    """Parse a list of criteria dictionaries into CriterionDefinition objects.

    This is a convenience function for loading criteria from a scenario's
    test_criteria.json file.

    Args:
        criteria_data: List of criterion dictionaries from JSON.

    Returns:
        List of validated CriterionDefinition objects.

    Example:
        ```python
        import json
        from pathlib import Path

        criteria_json = Path("test_criteria.json").read_text()
        data = json.loads(criteria_json)
        criteria = parse_criteria_from_json(data["criteria"])
        ```
    """
    return [CriterionDefinition.model_validate(c) for c in criteria_data]
