"""UES Benchmark Agent implementation.

This module contains the core Agent class that orchestrates benchmark
assessments: parsing requests, managing scenarios, coordinating with
purple agents, and producing evaluation results.
"""

from typing import Any

from pydantic import BaseModel, HttpUrl, ValidationError
from a2a.server.tasks import TaskUpdater
from a2a.types import Message, TaskState, Part, TextPart, DataPart
from a2a.utils import get_message_text, new_agent_text_message

from messenger import Messenger


class AssessmentConfig(BaseModel):
    """Configuration for a benchmark assessment.

    Attributes:
        scenario_id: ID of the scenario to run (required).
        time_limit_seconds: Maximum wall-clock time for assessment (optional).
        max_turns: Maximum number of turns before termination (optional).
        seed: Random seed for reproducibility (optional).
        verbose_updates: Whether to send detailed progress updates (optional).
    """

    scenario_id: str
    time_limit_seconds: int | None = None
    max_turns: int | None = None
    seed: int | None = None
    verbose_updates: bool = False


class EvalRequest(BaseModel):
    """Request format sent by AgentBeats platform to green agents.

    Attributes:
        participants: Map of role name to agent URL.
        config: Assessment configuration parameters.
    """

    participants: dict[str, HttpUrl]
    config: AssessmentConfig


class Agent:
    """UES Benchmark Agent that evaluates personal assistant agents.

    This agent orchestrates the full assessment lifecycle:
    1. Parse and validate the assessment request
    2. Reset UES and load the specified scenario
    3. Generate API keys and send assessment_start to purple agent
    4. Run the turn loop until termination
    5. Evaluate results and return assessment artifact
    """

    # Purple agent must be provided with role "assistant"
    required_roles: list[str] = ["assistant"]

    # scenario_id is required in config
    required_config_keys: list[str] = ["scenario_id"]

    def __init__(self):
        """Initialize the agent with a messenger for A2A communication."""
        self.messenger = Messenger()

    def validate_request(self, request: EvalRequest) -> tuple[bool, str]:
        """Validate that the request has all required participants and config.

        Args:
            request: The parsed evaluation request.

        Returns:
            Tuple of (is_valid, error_message).
        """
        missing_roles = set(self.required_roles) - set(request.participants.keys())
        if missing_roles:
            return False, f"Missing required participant roles: {missing_roles}"

        # Config validation is handled by Pydantic, but we can add extra checks
        if not request.config.scenario_id:
            return False, "scenario_id cannot be empty"

        return True, "ok"

    async def run(self, message: Message, updater: TaskUpdater) -> None:
        """Run a benchmark assessment.

        Args:
            message: The incoming A2A message containing the EvalRequest.
            updater: TaskUpdater for reporting progress and results.
        """
        input_text = get_message_text(message)

        # Parse and validate the request
        try:
            request = EvalRequest.model_validate_json(input_text)
            ok, msg = self.validate_request(request)
            if not ok:
                await updater.reject(new_agent_text_message(msg))
                return
        except ValidationError as e:
            await updater.reject(new_agent_text_message(f"Invalid request: {e}"))
            return

        # Extract configuration
        config = request.config
        assistant_url = str(request.participants["assistant"])

        # Report that we're starting
        await updater.update_status(
            TaskState.working,
            new_agent_text_message(
                f"Starting assessment with scenario: {config.scenario_id}"
            ),
        )

        # TODO: Implement full assessment lifecycle
        # 1. Reset UES to clean state
        # 2. Generate proctor API key (for self) and user API key (for purple agent)
        # 3. Load scenario from scenario_id
        # 4. Send assessment_start message to purple agent with:
        #    - UES URL
        #    - API key
        #    - Scenario description
        #    - Current simulator time
        #    - Initial state summary
        # 5. Turn loop:
        #    - Wait for turn_complete from purple agent
        #    - Advance simulation time
        #    - Process scheduled events
        #    - Check termination conditions
        #    - Send turn_start with new events
        # 6. On termination:
        #    - Retrieve full event trace
        #    - Run evaluation criteria
        #    - Compute scores
        # 7. Clean up: invalidate API keys

        # Placeholder result
        await updater.update_status(
            TaskState.working,
            new_agent_text_message("Assessment in progress..."),
        )

        # Return placeholder assessment result
        await updater.add_artifact(
            parts=[
                Part(root=TextPart(text="Assessment completed (placeholder)")),
                Part(
                    root=DataPart(
                        data={
                            "assessment_id": "placeholder",
                            "scenario_id": config.scenario_id,
                            "participant": assistant_url,
                            "status": "completed",
                            "scores": {
                                "overall": 0.0,
                                "dimensions": {},
                            },
                            "criteria_results": [],
                            "action_log": [],
                        }
                    )
                ),
            ],
            name="AssessmentResult",
        )
