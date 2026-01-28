# Agent Testing Harness

The UES Agent Testing Harness provides infrastructure for scenario authors to evaluate AI agent performance through customizable, hook-based testing.

## Overview

The testing harness allows scenario authors to:
- Define test criteria in JSON with references to Python evaluator functions
- Evaluate criteria either after scenario completion or in real-time as events occur
- Use any evaluation logic (programmatic, LLM-based, hybrid)
- Generate structured reports with scores, explanations, and detailed breakdowns

## Architecture

```
ues/
  agent_testing/
    __init__.py      # Public API: EvalRunner, EvalContext, EvalResult, etc.
    schema.py        # Pydantic models for criteria JSON validation
    results.py       # EvalResult, CriterionResult, EvalReport classes
    context.py       # EvalContext class passed to test functions
    hooks.py         # Hook manager for on_event dispatch
    runner.py        # EvalRunner - orchestrates test execution
    display.py       # Terminal scoreboard + JSON export
```

## Quick Start

### 1. Create Test Criteria JSON

Create a `test_criteria.json` file alongside your scenario:

```json
{
  "name": "My Scenario Tests",
  "description": "Test suite for my agent scenario",
  "test_module": "scenario_tests",
  "criteria": [
    {
      "id": "task_completion",
      "name": "Task Completion",
      "description": "Agent completes all required tasks",
      "evaluator": "check_task_completion",
      "max_points": 20,
      "eval_timing": "post_scenario",
      "params": {
        "required_tasks": ["send_email", "create_event"]
      }
    }
  ]
}
```

### 2. Create Test Functions

Create a `scenario_tests.py` file with your evaluator functions:

```python
from ues.agent_testing import EvalContext, EvalResult

def check_task_completion(ctx: EvalContext, params: dict) -> EvalResult:
    """Check if the agent completed all required tasks."""
    required = set(params["required_tasks"])
    completed = set()
    
    # Check email state
    email_state = await ctx.get_state("email")
    if any(e.folder == "sent" for e in email_state.emails.values()):
        completed.add("send_email")
    
    # Check calendar state
    calendar_state = await ctx.get_state("calendar")
    if calendar_state.events:
        completed.add("create_event")
    
    matched = len(completed & required)
    return EvalResult(
        score=matched,
        max_score=len(required),
        explanation=f"Completed {matched}/{len(required)} tasks: {completed}",
    )
```

### 3. Run Tests

```python
from ues.agent_testing import EvalRunner

async def main():
    runner = EvalRunner(
        scenario_path="./scenario.ues-scenario.json",
        criteria_path="./test_criteria.json",
        ues_host="http://localhost:8000",
    )
    
    report = await runner.run()
    runner.print_report()
    runner.save_report("results.json")
```

Or via CLI:
```bash
uv run python -m ues.agent_testing path/to/scenario/
```

## Criteria JSON Schema

### Root Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Human-readable name for the test suite |
| `description` | string | No | Detailed description of what's being tested |
| `test_module` | string | No | Python module name containing evaluators (default: `scenario_tests`) |
| `criteria` | array | Yes | List of criterion definitions |

### Criterion Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier for this criterion |
| `name` | string | Yes | Human-readable name |
| `description` | string | No | What this criterion tests |
| `evaluator` | string | Yes | Name of Python function to call |
| `max_points` | number | Yes | Maximum points for this criterion |
| `eval_timing` | string | Yes | When to evaluate: `"post_scenario"` or `"on_event"` |
| `event_filter` | string | No | For `on_event`: name of filter function |
| `params` | object | No | Parameters passed to the evaluator |

## Test Function API

### EvalContext

The `EvalContext` object is passed to all evaluator and filter functions:

```python
@dataclass
class EvalContext:
    client: AsyncUESClient          # Full API access to UES
    event_history: list[dict]       # All events that have occurred
    trigger_event: dict | None      # For on_event: the triggering event
    scenario_config: dict           # The loaded scenario JSON
    
    async def get_state(self, modality: str) -> ModalityState:
        """Get current state for a modality (email, sms, calendar, etc.)."""
        
    async def get_time(self) -> datetime:
        """Get current simulation time."""
```

### EvalResult

Evaluator functions must return an `EvalResult`:

```python
@dataclass
class EvalResult:
    score: float              # Points earned (0 to max_score)
    max_score: float          # Maximum possible points
    explanation: str          # Human-readable explanation
    details: dict | None      # Optional structured data for debugging
```

### Evaluator Function Signature

```python
async def my_evaluator(ctx: EvalContext, params: dict) -> EvalResult:
    """
    Args:
        ctx: Test context with API access and state
        params: The "params" dict from the criterion JSON
        
    Returns:
        EvalResult with score, max_score, and explanation
    """
    ...
```

Note: Evaluators can be sync or async. The runner will handle both.

### Event Filter Function Signature

For `on_event` criteria, you can specify a filter function:

```python
def my_filter(event: dict) -> bool:
    """
    Args:
        event: The event dict with modality, data, scheduled_time, etc.
        
    Returns:
        True if this event should trigger the evaluator
    """
    return event.get("modality") == "email"
```

## Evaluation Timing

### Post-Scenario (`post_scenario`)

Evaluated once after the scenario completes. Use for:
- Checking final state (all emails sent, calendar correct, etc.)
- Aggregate analysis (total response count, etc.)

```json
{
  "id": "final_state_check",
  "evaluator": "check_final_state",
  "eval_timing": "post_scenario",
  "max_points": 20
}
```

### On-Event (`on_event`)

Evaluated each time a matching event occurs. The harness accumulates scores.

```json
{
  "id": "email_quality",
  "evaluator": "check_email_quality",
  "eval_timing": "on_event",
  "event_filter": "filter_outgoing_emails",
  "max_points": 10
}
```

For `on_event` criteria:
- The evaluator is called once per matching event
- Each call should return a score for that single event
- The harness sums scores and tracks `max_score × event_count`
- `ctx.trigger_event` contains the event that triggered evaluation

Example:
```python
def filter_outgoing_emails(event: dict) -> bool:
    return (
        event.get("modality") == "email"
        and event.get("data", {}).get("operation") == "send"
    )

async def check_email_quality(ctx: EvalContext, params: dict) -> EvalResult:
    """Score a single outgoing email."""
    email_data = ctx.trigger_event.get("data", {})
    body = email_data.get("body_text", "")
    
    score = 0
    reasons = []
    
    if len(body) > 50:
        score += 0.5
        reasons.append("adequate length")
    if email_data.get("subject"):
        score += 0.5
        reasons.append("has subject")
    
    return EvalResult(
        score=score,
        max_score=1,
        explanation=f"Email quality: {', '.join(reasons) or 'poor'}",
    )
```

## Report Format

### Terminal Output

```
============================================================
📊 TEST RESULTS: Party Planner Tests
============================================================

Criterion Scores:
------------------------------------------------------------
Invitation Completeness  [████████████████████] 20.0/20  100%
  Invited 4/4 expected guests

Email Professionalism    [██████████████░░░░░░]  7.0/10   70%
  7/10 emails met professionalism criteria (10 evaluated)

Calendar Accuracy        [████████████████████] 10.0/10  100%
  Event created with correct date and time

------------------------------------------------------------
TOTAL SCORE              37.0/40 (92.5%)

🏆 Grade: Excellent
============================================================
```

### JSON Output

```json
{
  "name": "Party Planner Tests",
  "timestamp": "2026-01-19T15:30:00Z",
  "duration_seconds": 45.2,
  "total_score": 37.0,
  "max_score": 40.0,
  "percentage": 92.5,
  "grade": "Excellent",
  "criteria_results": [
    {
      "id": "invitation_completeness",
      "name": "Invitation Completeness",
      "score": 20.0,
      "max_score": 20.0,
      "percentage": 100.0,
      "explanation": "Invited 4/4 expected guests",
      "eval_count": 1,
      "details": null
    },
    {
      "id": "email_professionalism",
      "name": "Email Professionalism",
      "score": 7.0,
      "max_score": 10.0,
      "percentage": 70.0,
      "explanation": "7/10 emails met professionalism criteria",
      "eval_count": 10,
      "individual_results": [
        {"score": 1.0, "max_score": 1.0, "explanation": "..."},
        {"score": 0.0, "max_score": 1.0, "explanation": "..."}
      ]
    }
  ]
}
```

## Using LLM-Based Evaluation

The harness doesn't prescribe how evaluators work - you can use LLMs:

```python
import httpx

async def check_email_personalization(ctx: EvalContext, params: dict) -> EvalResult:
    """Use an LLM to judge email personalization quality."""
    email_data = ctx.trigger_event.get("data", {})
    
    prompt = f"""
    Rate the personalization of this email from 0-10:
    
    To: {email_data.get('to_addresses')}
    Subject: {email_data.get('subject')}
    Body: {email_data.get('body_text')}
    
    Consider:
    - Does it address the recipient by name?
    - Does it reference their relationship?
    - Is the tone appropriate for the relationship?
    
    Return ONLY a JSON object: {{"score": <0-10>, "reason": "<explanation>"}}
    """
    
    response = httpx.post(
        "http://localhost:11434/api/generate",
        json={"model": "gemma3:12b", "prompt": prompt, "stream": False},
    )
    result = json.loads(response.json()["response"])
    
    return EvalResult(
        score=result["score"],
        max_score=10,
        explanation=result["reason"],
    )
```

## File Discovery

The `EvalRunner` discovers test files using these conventions:

1. **Criteria JSON**: Looks for `test_criteria.json` in the scenario directory
2. **Test Module**: Imports the module named in `test_module` (default: `scenario_tests`)
   - Searches in the scenario directory
   - Falls back to Python path

Both can be overridden with explicit paths:

```python
runner = EvalRunner(
    scenario_path="./my_scenario.json",
    criteria_path="./custom_criteria.json",
    test_module_path="./my_tests.py",
)
```

## Implementation Details

### Event Hook Integration

For `on_event` criteria, the harness subscribes to UES events via the events API:

1. Before scenario execution, register event filters
2. Poll `/events/history` or use webhooks (future) to detect new events
3. When matching event detected, call the evaluator
4. Accumulate scores

### Score Accumulation for On-Event Criteria

For `on_event` criteria, the harness tracks:
- `total_score`: Sum of all evaluator return scores
- `total_max_score`: Sum of all evaluator return max_scores  
- `eval_count`: Number of times the evaluator was called
- `individual_results`: List of each EvalResult (optional, for debugging)

The final `max_points` from the criterion JSON is used for display scaling:
- If evaluator returns per-event scores (0-1), and 10 events occur, raw total might be 7/10
- Scaled to criterion max_points (e.g., 20): displayed as 14/20

### Sync/Async Handling

Evaluator functions can be sync or async. The runner detects and handles both:

```python
import asyncio
import inspect

async def call_evaluator(func, ctx, params):
    if inspect.iscoroutinefunction(func):
        return await func(ctx, params)
    else:
        return func(ctx, params)
```

## Grading Scale

| Percentage | Grade |
|------------|-------|
| ≥ 90% | Excellent |
| ≥ 70% | Good |
| ≥ 50% | Needs Improvement |
| < 50% | Failing |

Custom grading can be specified in the criteria JSON (future enhancement).
